#include "filesystem/zip_archive.h"
#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <sys/stat.h>
#include <unistd.h>
#include <zlib.h>

using namespace storm::filesystem;
namespace fs = std::filesystem;
namespace {
using Bytes = std::vector<std::uint8_t>;
void put16(Bytes& b, std::uint16_t n) { b.push_back(n & 255); b.push_back(n >> 8); }
void put32(Bytes& b, std::uint32_t n) { put16(b, n & 65535); put16(b, n >> 16); }
void put64(Bytes& b, std::uint64_t n) { put32(b, std::uint32_t(n)); put32(b, std::uint32_t(n >> 32)); }
void text(Bytes& b, const std::string& s) { b.insert(b.end(), s.begin(), s.end()); }
void save(std::ofstream& file, const Bytes& b) { file.write(reinterpret_cast<const char*>(b.data()), std::streamsize(b.size())); if (!file) throw std::runtime_error("fixture write"); }
Bytes contents(const fs::path& path) { std::ifstream f(path, std::ios::binary); return Bytes(std::istreambuf_iterator<char>(f), {}); }
Bytes deflate(const Bytes& data) {
    z_stream z{};
    if (deflateInit2(&z, 6, Z_DEFLATED, -MAX_WBITS, 8, Z_DEFAULT_STRATEGY) != Z_OK) throw std::runtime_error("fixture deflate init");
    Bytes result(compressBound(data.size()) + 16);
    z.next_in = const_cast<Bytef*>(data.data()); z.avail_in = uInt(data.size());
    z.next_out = result.data(); z.avail_out = uInt(result.size());
    const int status = ::deflate(&z, Z_FINISH);
    result.resize(z.total_out); deflateEnd(&z);
    if (status != Z_STREAM_END) throw std::runtime_error("fixture deflate");
    return result;
}
struct Fixture {
    std::string name;
    Bytes data;
    std::uint16_t method = 0;
    bool descriptor = false;
    bool zip64 = false;
    std::uint32_t attributes = 0100644u << 16;
    bool descriptor_signature = true;
};
struct Layout { std::vector<std::uint64_t> local, central, payload; std::uint64_t central_start = 0, eocd = 0; };
Layout archive(const fs::path& path, const std::vector<Fixture>& entries, bool end64 = false, std::uint64_t prefix = 0) {
    std::ofstream file(path, std::ios::binary);
    if (!file) throw std::runtime_error("fixture open");
    file.seekp(std::streamoff(prefix));
    Layout layout; std::vector<Bytes> central;
    for (const auto& e : entries) {
        const auto start = std::uint64_t(file.tellp()); layout.local.push_back(start);
        const auto packed = e.method == 8 ? deflate(e.data) : e.data;
        const auto crc = std::uint32_t(crc32(0, e.data.data(), uInt(e.data.size())));
        const auto flags = std::uint16_t(e.descriptor ? 8 : 0);
        Bytes extra;
        if (e.zip64) { put16(extra, 1); put16(extra, 16); put64(extra, e.descriptor ? 0 : e.data.size()); put64(extra, e.descriptor ? 0 : packed.size()); }
        Bytes local; put32(local, 0x04034b50); put16(local, e.zip64 ? 45 : 20); put16(local, flags); put16(local, e.method);
        put16(local, 0); put16(local, 0); put32(local, e.descriptor ? 0 : crc);
        put32(local, e.zip64 ? UINT32_MAX : (e.descriptor ? 0 : std::uint32_t(packed.size())));
        put32(local, e.zip64 ? UINT32_MAX : (e.descriptor ? 0 : std::uint32_t(e.data.size())));
        put16(local, e.name.size()); put16(local, extra.size()); text(local, e.name); local.insert(local.end(), extra.begin(), extra.end());
        save(file, local); layout.payload.push_back(std::uint64_t(file.tellp())); save(file, packed);
        if (e.descriptor) {
            Bytes d; if (e.descriptor_signature) put32(d, 0x08074b50); put32(d, crc);
            if (e.zip64) { put64(d, packed.size()); put64(d, e.data.size()); } else { put32(d, packed.size()); put32(d, e.data.size()); }
            save(file, d);
        }
        extra.clear();
        if (e.zip64 || start > UINT32_MAX) {
            put16(extra, 1); put16(extra, (e.zip64 ? 16 : 0) + (start > UINT32_MAX ? 8 : 0));
            if (e.zip64) { put64(extra, e.data.size()); put64(extra, packed.size()); }
            if (start > UINT32_MAX) put64(extra, start);
        }
        Bytes c; put32(c, 0x02014b50); put16(c, (3 << 8) | 45); put16(c, e.zip64 ? 45 : 20);
        put16(c, flags); put16(c, e.method); put16(c, 0); put16(c, 0); put32(c, crc);
        put32(c, e.zip64 ? UINT32_MAX : std::uint32_t(packed.size())); put32(c, e.zip64 ? UINT32_MAX : std::uint32_t(e.data.size()));
        put16(c, e.name.size()); put16(c, extra.size()); put16(c, 0); put16(c, 0); put16(c, 0); put32(c, e.attributes);
        put32(c, start > UINT32_MAX ? UINT32_MAX : std::uint32_t(start)); text(c, e.name); c.insert(c.end(), extra.begin(), extra.end()); central.push_back(c);
    }
    layout.central_start = std::uint64_t(file.tellp());
    for (const auto& c : central) { layout.central.push_back(std::uint64_t(file.tellp())); save(file, c); }
    const auto central_size = std::uint64_t(file.tellp()) - layout.central_start;
    if (end64) {
        const auto end_offset = std::uint64_t(file.tellp());
        Bytes z; put32(z, 0x06064b50); put64(z, 44); put16(z, 45); put16(z, 45); put32(z, 0); put32(z, 0);
        put64(z, entries.size()); put64(z, entries.size()); put64(z, central_size); put64(z, layout.central_start); save(file, z);
        Bytes locator; put32(locator, 0x07064b50); put32(locator, 0); put64(locator, end_offset); put32(locator, 1); save(file, locator);
    }
    layout.eocd = std::uint64_t(file.tellp());
    Bytes e; put32(e, 0x06054b50); put16(e, 0); put16(e, 0); put16(e, end64 ? 0xffff : entries.size()); put16(e, end64 ? 0xffff : entries.size());
    put32(e, end64 ? UINT32_MAX : central_size); put32(e, end64 ? UINT32_MAX : layout.central_start); put16(e, 0); save(file, e); return layout;
}
void patch(const fs::path& path, std::uint64_t offset, std::uint32_t value, unsigned width = 4) {
    std::fstream file(path, std::ios::binary | std::ios::in | std::ios::out); file.seekp(std::streamoff(offset));
    for (unsigned i = 0; i < width; ++i) file.put(char(value >> (i * 8)));
    if (!file) throw std::runtime_error("fixture patch");
}
struct Cleanup { fs::path path; ~Cleanup() { std::error_code ignored; fs::remove_all(path, ignored); } };
}

int main() {
    unsigned checks = 0;
    const auto check = [&](bool ok) { ++checks; if (!ok) throw std::runtime_error("zip check " + std::to_string(checks)); };
    const auto error = [&](auto action, const char* code) { bool seen = false; try { action(); } catch (const ZipError& e) { seen = std::string(e.code()) == code; if (!seen) std::cerr << "expected " << code << ", got " << e.what() << '\n'; } check(seen); };
    const auto root = fs::temp_directory_path() / ("storm-zip-tests-" + std::to_string(getpid()));
    Cleanup cleanup{root};
    try {
        check(fs::create_directory(root));
        const auto zip = root / "fixture.zip";
        Bytes payload(512 * 1024 + 37);
        for (std::size_t i = 0; i < payload.size(); ++i) payload[i] = std::uint8_t((i * 17 + (i >> 8)) & 255);
        const Bytes hello{'h','e','l','l','o'};
        for (bool big : {false, true}) for (bool descriptor : {false, true}) for (bool signed_descriptor : {false, true}) {
            archive(zip, {{"Game/", {}, 0, false, false, (0040755u << 16) | 0x10}, {"Game/Default.xex", hello, 0, descriptor, big, 0100644u << 16, signed_descriptor}, {"Game/data/asset.bin", payload, 8, descriptor, big, 0100644u << 16, signed_descriptor}}, big);
            ZipArchive reader(zip); check(reader.entries().size() == 3); check(reader.total_uncompressed() == payload.size() + hello.size());
            check(reader.entries()[1].name == "Game/Default.xex");
            const auto out = root / "output"; std::uint64_t previous = 0; std::size_t callbacks = 0;
            reader.extract(out, [&](const ZipProgress& p) { check(p.bytes_written >= previous && p.bytes_written <= p.total_bytes); previous = p.bytes_written; ++callbacks; return true; });
            check(callbacks >= 7); check(previous == reader.total_uncompressed());
            check(contents(out / "Game/Default.xex") == hello); check(contents(out / "Game/data/asset.bin") == payload);
            error([&] { reader.extract(out); }, "ZIP_DESTINATION_EXISTS"); fs::remove_all(out);
        }
        // Empty directory entries may themselves use DEFLATE, including ZIP64
        // sizes and data descriptors. Never skip validation of their streams.
        for (bool big : {false, true}) for (bool descriptor : {false, true}) {
            archive(zip, {{"compressed/", {}, 8, descriptor, big, (0040755u << 16) | 0x10},
                          {"compressed/value", hello, 8}}, big);
            ZipArchive reader(zip);
            reader.extract(root / "deflated-directory");
            check(fs::is_directory(root / "deflated-directory/compressed"));
            check(contents(root / "deflated-directory/compressed/value") == hello);
            fs::remove_all(root / "deflated-directory");
        }
        auto directory_layout = archive(zip, {{"broken/", {}, 8, false, false, (0040755u << 16) | 0x10}});
        patch(zip, directory_layout.payload[0], 7, 1);
        { ZipArchive reader(zip); error([&] { reader.extract(root / "broken-directory"); }, "ZIP_DEFLATE_INVALID_OR_TRUNCATED"); }
        archive(zip, {{"nonempty/", hello, 8, false, false, (0040755u << 16) | 0x10}});
        error([&] { ZipArchive reader(zip); }, "ZIP_DIRECTORY_PAYLOAD_UNSUPPORTED");
        // This four-byte fixture's actual CRC equals the optional descriptor
        // signature. Both signed and unsigned descriptors must remain valid.
        const Bytes signature_crc{0xac, 0x0a, 0x7a, 0xd5};
        check(crc32(0, signature_crc.data(), uInt(signature_crc.size())) == 0x08074b50);
        for (bool big : {false, true}) for (bool signed_descriptor : {false, true}) {
            archive(zip, {{"crc-signature", signature_crc, 8, true, big, 0100644u << 16, signed_descriptor}}, big);
            ZipArchive reader(zip);
            reader.extract(root / "descriptor-crc-signature");
            check(contents(root / "descriptor-crc-signature/crc-signature") == signature_crc);
            fs::remove_all(root / "descriptor-crc-signature");
        }
        // A sparse file exercises actual 64-bit file seeks and central/local offsets
        // beyond 4 GiB without allocating or reading that amount of disk or RAM.
        const auto sparse = root / "sparse.zip";
        archive(sparse, {{"offset.bin", hello}}, true, (1ull << 32) + 123);
        check(fs::file_size(sparse) > (1ull << 32));
        struct stat info{}; check(::stat(sparse.c_str(), &info) == 0);
        check(std::uint64_t(info.st_blocks) * 512 < 1024 * 1024);
        { ZipArchive reader(sparse); reader.extract(root / "sparse-out"); check(contents(root / "sparse-out/offset.bin") == hello); }
        fs::remove(sparse);

        const std::vector<std::string> bad_names = {"../outside", "/absolute", "C:/drive", "a\\b", "a//b", "a/./b", "a/../b", "trailing. ", "a/", ""};
        for (const auto& name : bad_names) {
            archive(zip, {{name, hello}});
            error([&] { ZipArchive bad(zip); }, name == "a/" ? "ZIP_DIRECTORY_NAME_MISMATCH" : "ZIP_UNSAFE_PATH");
        }
        archive(zip, {{std::string("nul\0name", 8), hello}}); error([&] { ZipArchive bad(zip); }, "ZIP_UNSAFE_PATH");
        archive(zip, {{"caf\xc3\xa9.bin", hello}}); error([&] { ZipArchive bad(zip); }, "ZIP_NON_ASCII_PATH_UNSUPPORTED");
        archive(zip, {{"same", hello}, {"same", hello}}); error([&] { ZipArchive bad(zip); }, "ZIP_DUPLICATE_PATH");
        archive(zip, {{"same", hello}, {"SAME", hello}}); error([&] { ZipArchive bad(zip); }, "ZIP_DUPLICATE_PATH");
        archive(zip, {{"dir/a", hello}, {"DIR/b", hello}}); error([&] { ZipArchive bad(zip); }, "ZIP_CASE_COLLISION");
        archive(zip, {{"dir", hello}, {"dir/a", hello}}); error([&] { ZipArchive bad(zip); }, "ZIP_FILE_DIRECTORY_CONFLICT");
        archive(zip, {{"link", hello, 0, false, false, 0120777u << 16}}); error([&] { ZipArchive bad(zip); }, "ZIP_SPECIAL_FILE_UNSUPPORTED");
        archive(zip, {{"pipe", {}, 0, false, false, 0010600u << 16}}); error([&] { ZipArchive bad(zip); }, "ZIP_SPECIAL_FILE_UNSUPPORTED");
        archive(zip, {{"bad/", {}, 0, false, false, 0100644u << 16}}); error([&] { ZipArchive bad(zip); }, "ZIP_DIRECTORY_NAME_MISMATCH");
        archive(zip, {{"bzip", hello, 12}}); error([&] { ZipArchive bad(zip); }, "ZIP_COMPRESSION_UNSUPPORTED");
        auto layout = archive(zip, {{"encrypted", hello}}); patch(zip, layout.central[0] + 8, 1, 2); error([&] { ZipArchive bad(zip); }, "ZIP_ENCRYPTION_UNSUPPORTED");
        layout = archive(zip, {{"value", hello}}); patch(zip, layout.central[0] + 8, 16, 2); error([&] { ZipArchive bad(zip); }, "ZIP_FLAGS_UNSUPPORTED");
        layout = archive(zip, {{"value", hello}}); patch(zip, layout.local[0] + 30, 'X', 1); error([&] { ZipArchive bad(zip); }, "ZIP_LOCAL_NAME_MISMATCH");
        layout = archive(zip, {{"value", hello}}); patch(zip, layout.local[0] + 14, 0); error([&] { ZipArchive bad(zip); }, "ZIP_LOCAL_SIZE_OR_CRC_MISMATCH");
        layout = archive(zip, {{"value", hello, 0, true}}); patch(zip, layout.payload[0] + hello.size() + 4, 0); error([&] { ZipArchive bad(zip); }, "ZIP_DESCRIPTOR_MISMATCH");
        layout = archive(zip, {{"value", hello}}); patch(zip, layout.eocd + 4, 1, 2); error([&] { ZipArchive bad(zip); }, "ZIP_MULTIDISK_UNSUPPORTED");
        layout = archive(zip, {{"value", hello}}, true); patch(zip, layout.eocd - 20, 0); error([&] { ZipArchive bad(zip); }, "ZIP64_LOCATOR_MISSING");
        archive(zip, {{"value", hello}}); fs::resize_file(zip, 20); error([&] { ZipArchive bad(zip); }, "ZIP_TRUNCATED");
        archive(zip, {{"value", hello}}); fs::resize_file(zip, fs::file_size(zip) - 1); error([&] { ZipArchive bad(zip); }, "ZIP_EOCD_NOT_FOUND");

        archive(zip, {{"value", hello}});
        ZipLimits limits; limits.max_archive_bytes = 10; error([&] { ZipArchive bad(zip, limits); }, "ZIP_ARCHIVE_SIZE_LIMIT");
        limits = {}; limits.max_file_bytes = 4; error([&] { ZipArchive bad(zip, limits); }, "ZIP_FILE_SIZE_LIMIT");
        limits = {}; limits.max_total_bytes = 4; error([&] { ZipArchive bad(zip, limits); }, "ZIP_TOTAL_SIZE_LIMIT");
        limits = {}; limits.max_entries = 0; error([&] { ZipArchive bad(zip, limits); }, "ZIP_METADATA_LIMIT");
        layout = archive(zip, {{"value", hello, 8}}); patch(zip, layout.central[0] + 24, 100 * 1024 * 1024); error([&] { ZipArchive bad(zip); }, "ZIP_EXPANSION_LIMIT");

        layout = archive(zip, {{"value", hello}}); patch(zip, layout.payload[0], 'X', 1);
        { ZipArchive reader(zip); error([&] { reader.extract(root / "bad-crc"); }, "ZIP_CRC_MISMATCH"); }
        layout = archive(zip, {{"value", hello, 8}}); patch(zip, layout.payload[0], 7, 1);
        { ZipArchive reader(zip); error([&] { reader.extract(root / "bad-deflate"); }, "ZIP_DEFLATE_INVALID_OR_TRUNCATED"); }
        archive(zip, {{"empty", {}, 8}});
        { ZipArchive reader(zip); reader.extract(root / "empty-out"); check(fs::file_size(root / "empty-out/empty") == 0); }
        archive(zip, {{"big", payload, 8}});
        { ZipArchive reader(zip); error([&] { reader.extract(root / "cancel-before", [](const ZipProgress&) { return false; }); }, "ZIP_CANCELLED"); check(!fs::exists(root / "cancel-before")); }
        { ZipArchive reader(zip); error([&] { reader.extract(root / "cancel-during", [](const ZipProgress& p) { return p.bytes_written < 128 * 1024; }); }, "ZIP_CANCELLED"); check(fs::file_size(root / "cancel-during/big") == 128 * 1024); }
        fs::create_directory(root / "outside"); fs::create_directory_symlink(root / "outside", root / "symlink-root");
        { ZipArchive reader(zip); error([&] { reader.extract(root / "symlink-root"); }, "ZIP_DESTINATION_EXISTS"); check(fs::is_empty(root / "outside")); }
        // Even a caller racing extraction via a progress callback cannot make a
        // crafted directory symlink redirect writes outside the new staging root.
        archive(zip, {{"dir/value", hello}});
        { ZipArchive reader(zip); bool planted = false;
          error([&] { reader.extract(root / "race", [&](const ZipProgress& p) { if (!p.entry_name.empty() && !planted) { fs::create_directory_symlink(root / "outside", root / "race/dir"); planted = true; } return true; }); }, "ZIP_UNSAFE_OUTPUT_DIRECTORY");
          check(fs::is_empty(root / "outside")); }
        std::cout << "ZIP streaming: " << checks << " checks passed; ZIP64, CRC, bounds, cancellation and path confinement\n";
        return 0;
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
