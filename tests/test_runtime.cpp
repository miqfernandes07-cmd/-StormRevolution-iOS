#include "storm_runtime.h"
#include "cpu/context.h"
#include "memory/guest_memory.h"
#include "kernel/imports.h"
#include "input/input_state.h"
#include "filesystem/content_root.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <thread>

namespace {
unsigned checks = 0;
void check(bool value, const char* message) {
    ++checks;
    if (!value) throw std::runtime_error(message);
}
template<class E, class F> void throws(F action, const char* message) {
    ++checks;
    try { action(); } catch (const E&) { return; }
    throw std::runtime_error(message);
}
struct TemporaryDirectory {
    std::filesystem::path path;
    TemporaryDirectory() {
        for (unsigned i = 0; i < 100; ++i) {
            path = std::filesystem::temp_directory_path() / ("storm-test-" +
                std::to_string(storm::kernel::monotonic_nanoseconds()) + "-" + std::to_string(i));
            if (std::filesystem::create_directory(path)) return;
        }
        throw std::runtime_error("Cannot create temporary directory");
    }
    ~TemporaryDirectory() { std::error_code ec; std::filesystem::remove_all(path,ec); }
};
}

int main() {
    try {
        using storm::memory::GuestMemory;
        GuestMemory memory(0x1003, 256);
        check(memory.allocate(16,16) == 0x1010,"alignment uses guest addresses");
        check(memory.allocate(16,32) == 0x1020,"32-byte allocation");
        memory.store32(0x1003,0x12345678);
        check(memory.load8(0x1003) == 0x12 && memory.load8(0x1006) == 0x78,"big-endian bytes");
        check(memory.load32(0x1003) == 0x12345678,"unaligned BE load");
        memory.store64(0x10FB,0x0123456789ABCDEFULL);
        check(memory.load64(0x10FB) == 0x0123456789ABCDEFULL,"end boundary 64-bit access");
        throws<std::out_of_range>([&]{ memory.load32(0x1100); },"out of region read");
        throws<std::out_of_range>([&]{ memory.store64(0x10FC,0); },"out of region store");
        throws<std::out_of_range>([&]{ memory.load8(0x1002); },"underflow read");
        throws<std::invalid_argument>([&]{ memory.allocate(1,3); },"nonpower alignment");
        throws<std::invalid_argument>([&]{ memory.allocate(0,16); },"zero allocation");
        throws<std::bad_alloc>([&]{ memory.allocate(std::numeric_limits<std::size_t>::max(),16); },"allocation overflow");
        throws<std::invalid_argument>([]{ GuestMemory bad(0xFFFFFFFF,2); },"32-bit region overflow");
        GuestMemory high(0xFFFFFFF0,16);
        high.store32(0xFFFFFFFC,0xAABBCCDD);
        check(high.load32(0xFFFFFFFC)==0xAABBCCDD,"top of guest space");
        throws<std::out_of_range>([&]{ high.load64(0xFFFFFFFC); },"top overflow");

        storm::cpu::Vector128 a,b;
        a.set_word(0,0xFFFFFFFF); a.set_word(1,0x80000000); a.set_word(2,2); a.set_word(3,3);
        b.set_word(0,1); b.set_word(1,0x80000000); b.set_word(2,5); b.set_word(3,7);
        auto sum = storm::cpu::add_u32(a,b);
        check(sum.word(0)==0 && sum.word(1)==0 && sum.word(2)==7 && sum.word(3)==10,"vector wrapping add");
        check(a.bytes[0]==0xFF && a.bytes[4]==0x80,"canonical vector byte order");
        check(storm::cpu::bit_xor(a,b).word(0)==0xFFFFFFFE,"vector xor");
        throws<std::out_of_range>([&]{ a.word(4); },"vector lane guard");

        storm::kernel::Imports imports;
        storm::cpu::Context cpu;
        imports.add("synthetic",1,[](storm::cpu::Context& c){ c.gpr[3] = c.gpr[4]+1; });
        cpu.gpr[4]=41; imports.invoke("synthetic",1,cpu);
        check(cpu.gpr[3]==42,"registered import executes");
        throws<std::invalid_argument>([&]{ imports.add("synthetic",1,[](storm::cpu::Context&){}); },"duplicate import");
        try { imports.invoke("xboxkrnl.exe",999,cpu); throw std::logic_error("missing import silently passed"); }
        catch (const std::runtime_error& e) { check(std::string(e.what())=="IMPORT_UNRESOLVED:xboxkrnl.exe:999","identifiable unresolved import"); }
        const auto t = storm::kernel::monotonic_nanoseconds();
        check(storm::kernel::monotonic_nanoseconds()>=t,"monotonic timer");

        storm::input::InputState input;
        input.update({0xFFFFFFFF,2,-2,std::numeric_limits<float>::quiet_NaN(),0,-1,2});
        auto state=input.snapshot();
        check(state.buttons==0xF3FF && state.lx==1 && state.ly==-1 && state.rx==0 && state.lt==0 && state.rt==1,"controller normalization");
        std::thread writer([&]{ for(unsigned i=0;i<1000;++i) input.update({0x1000,0.5f,0.5f}); });
        for(unsigned i=0;i<1000;++i) { auto s=input.snapshot(); check(s.lx>=-1 && s.lx<=1,"thread-safe snapshot"); }
        writer.join();
        check(input.snapshot().buttons==0x1000,"controller callback updates");

        TemporaryDirectory directory;
        const auto content_dir=directory.path/"content";
        std::filesystem::create_directory(content_dir);
        { std::ofstream file(content_dir/"resource.bin",std::ios::binary); file << "abc"; }
        storm::filesystem::ContentRoot content(content_dir);
        auto bytes=content.read("resource.bin");
        check(bytes.size()==3 && bytes[0]=='a' && bytes[2]=='c',"resource bytes read");
        throws<std::invalid_argument>([&]{ content.resolve("../outside"); },"directory traversal");
        throws<std::invalid_argument>([&]{ content.resolve(directory.path); },"absolute content path");
        throws<std::runtime_error>([&]{ content.read("resource.bin",2); },"resource size budget");
        throws<std::runtime_error>([&]{ content.read("missing.bin"); },"missing resource");
        std::error_code symlink_error;
        std::filesystem::create_directory_symlink(directory.path,content_dir/"escape",symlink_error);
        if (!symlink_error) throws<std::invalid_argument>([&]{ content.resolve("escape/resource.bin"); },"symlink escape");

        check(storm_runtime_self_test()==0,"bootstrap infrastructure self test");
        StormRuntime* runtime=storm_runtime_create();
        check(runtime!=nullptr,"runtime create");
        check(storm_runtime_start(nullptr,nullptr)==STORM_INVALID_ARGUMENT,"null handle");
        check(storm_runtime_start(runtime,nullptr)==STORM_INVALID_ARGUMENT,"null game path");
        check(storm_runtime_start(runtime,content_dir.string().c_str())==STORM_IO_ERROR,"missing xex");
        { std::ofstream xex(content_dir/"default.xex",std::ios::binary); xex << "synthetic test placeholder"; }
        check(storm_runtime_start(runtime,content_dir.string().c_str())==STORM_AOT_IMAGE_MISSING,"no false game boot");
        check(std::string(storm_runtime_last_error(runtime)).find("RUNTIME_AOT_IMAGE_MISSING")==0,"explicit no AOT diagnostic");
        storm_runtime_set_input(runtime,0x1000,0,0,0,0,0,0);
        storm_runtime_stop(runtime);
        check(std::string(storm_runtime_last_error(runtime)).empty(),"stop clears state");
        storm_runtime_destroy(runtime);
        std::cout << "runtime: " << checks << " checks passed (infrastructure, no game execution)\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr << "runtime test failed: " << e.what() << '\n';
        return 1;
    }
}
