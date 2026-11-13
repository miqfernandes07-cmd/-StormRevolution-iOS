#include "filesystem/zip_archive.h"

#include <algorithm>
#include <array>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <limits>
#include <map>
#include <set>
#include <sys/stat.h>
#include <unistd.h>
#include <zlib.h>

namespace storm::filesystem {
namespace {
[[noreturn]] void fail(const char* code) { throw ZipError(code); }
std::uint16_t u16(const std::uint8_t* p) { return std::uint16_t(p[0]) | (std::uint16_t(p[1]) << 8); }
std::uint32_t u32(const std::uint8_t* p) { return std::uint32_t(u16(p)) | (std::uint32_t(u16(p + 2)) << 16); }
std::uint64_t u64(const std::uint8_t* p) { return std::uint64_t(u32(p)) | (std::uint64_t(u32(p + 4)) << 32); }
std::uint64_t add(std::uint64_t a, std::uint64_t b) {
    if (b > UINT64_MAX - a) fail("ZIP_INTEGER_OVERFLOW");
    return a + b;
}
void signature(const std::vector<std::uint8_t>& bytes, std::uint32_t expected) {
    if (bytes.size() < 4 || u32(bytes.data()) != expected) fail("ZIP_HEADER_SIGNATURE");
}
std::string lowercase(std::string value) {
    for (char& c : value) if (c >= 'A' && c <= 'Z') c = char(c + ('a' - 'A'));
    return value;
}
std::vector<std::string> components(const std::string& name) {
    std::vector<std::string> result;
    std::size_t start = 0;
    while (start < name.size()) {
        auto end = name.find('/', start);
        if (end == std::string::npos) end = name.size();
        result.push_back(name.substr(start, end - start));
        start = end + 1;
    }
    return result;
}
void check_name(const std::string& name) {
    if (name.empty() || name.size() > 4096 || name.front() == '/') fail("ZIP_UNSAFE_PATH");
    // The game archive uses ASCII paths. Refuse other encodings for now rather
    // than allowing Unicode normalization/case aliases on Apple's filesystems.
    for (unsigned char c : name) {
        if (c >= 0x80) fail("ZIP_NON_ASCII_PATH_UNSUPPORTED");
        if (c < 0x20 || c == 0x7f || c == '\\' || c == ':') fail("ZIP_UNSAFE_PATH");
    }
    const auto parts = components(name);
    if (parts.size() > 64) fail("ZIP_PATH_DEPTH_LIMIT");
    for (const auto& part : parts) {
        if (part.empty() || part == "." || part == ".." || part.size() > 255 ||
            part.back() == '.' || part.back() == ' ') fail("ZIP_UNSAFE_PATH");
    }
}
std::vector<std::uint8_t> zip64_extra(const std::vector<std::uint8_t>& extra) {
    std::vector<std::uint8_t> result;
    bool seen = false;
    std::size_t i = 0;
    while (i < extra.size()) {
        if (extra.size() - i < 4) fail("ZIP_EXTRA_TRUNCATED");
        const auto tag = u16(extra.data() + i), length = u16(extra.data() + i + 2);
        i += 4;
        if (length > extra.size() - i) fail("ZIP_EXTRA_TRUNCATED");
        if (tag == 1) {
            if (seen) fail("ZIP64_EXTRA_DUPLICATE");
            seen = true;
            result.assign(extra.begin() + i, extra.begin() + i + length);
        }
        i += length;
    }
    return result;
}
std::uint64_t consume64(const std::vector<std::uint8_t>& values, std::size_t& index) {
    if (values.size() - std::min(values.size(), index) < 8) fail("ZIP64_EXTRA_MISSING");
    auto value = u64(values.data() + index); index += 8; return value;
}
class FD {
public:
    explicit FD(int value = -1) : value_(value) {}
    ~FD() { if (value_ >= 0) ::close(value_); }
    FD(const FD&) = delete;
    FD& operator=(const FD&) = delete;
    FD(FD&& other) noexcept : value_(other.value_) { other.value_ = -1; }
    FD& operator=(FD&& other) noexcept {
        if (this != &other) { if (value_ >= 0) ::close(value_); value_ = other.value_; other.value_ = -1; }
        return *this;
    }
    int get() const noexcept { return value_; }
private:
    int value_;
};
FD directory_at(int parent, const std::string& name) {
    if (::mkdirat(parent, name.c_str(), 0700) != 0 && errno != EEXIST) fail("ZIP_CREATE_DIRECTORY_FAILED");
    int fd = ::openat(parent, name.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) fail("ZIP_UNSAFE_OUTPUT_DIRECTORY");
    return FD(fd);
}
void write_all(int fd, const std::uint8_t* data, std::size_t count) {
    while (count) {
        const auto written = ::write(fd, data, count);
        if (written < 0 && errno == EINTR) continue;
        if (written <= 0) fail(errno == ENOSPC ? "ZIP_NO_SPACE" : "ZIP_WRITE_FAILED");
        data += written; count -= static_cast<std::size_t>(written);
    }
}
struct Inflater {
    z_stream stream{};
    Inflater() { if (::inflateInit2(&stream, -MAX_WBITS) != Z_OK) fail("ZIP_INFLATE_INIT_FAILED"); }
    ~Inflater() { ::inflateEnd(&stream); }
};
} // namespace

ZipArchive::ZipArchive(const std::filesystem::path& source, ZipLimits limits)
    : stream_(source, std::ios::binary), limits_(limits) {
    if (!stream_) fail("ZIP_OPEN_FAILED");
    stream_.seekg(0, std::ios::end);
    const auto end = stream_.tellg();
    if (end < 0) fail("ZIP_SEEK_FAILED");
    size_ = static_cast<std::uint64_t>(end);
    if (size_ > limits_.max_archive_bytes) fail("ZIP_ARCHIVE_SIZE_LIMIT");
    if (size_ < 22) fail("ZIP_TRUNCATED");
    inspect();
}

std::vector<std::uint8_t> ZipArchive::read(std::uint64_t offset, std::size_t count) {
    if (offset > size_ || count > size_ - offset || offset > std::uint64_t(std::numeric_limits<std::streamoff>::max())) fail("ZIP_TRUNCATED");
    std::vector<std::uint8_t> data(count);
    stream_.clear(); stream_.seekg(static_cast<std::streamoff>(offset));
    if (!stream_ || (count && !stream_.read(reinterpret_cast<char*>(data.data()), static_cast<std::streamsize>(count)))) fail("ZIP_READ_FAILED");
    return data;
}

void ZipArchive::inspect() {
    const auto tail_size = static_cast<std::size_t>(std::min<std::uint64_t>(size_, 65535 + 22));
    const auto tail = read(size_ - tail_size, tail_size);
    std::size_t eocd = tail.size();
    for (std::size_t i = tail.size() - 22 + 1; i-- > 0;) {
        if (u32(tail.data() + i) == 0x06054b50 && i + 22 + u16(tail.data() + i + 20) == tail.size()) { eocd = i; break; }
    }
    if (eocd == tail.size()) fail("ZIP_EOCD_NOT_FOUND");
    const auto* e = tail.data() + eocd;
    if (u16(e + 4) || u16(e + 6) || u16(e + 8) != u16(e + 10)) fail("ZIP_MULTIDISK_UNSUPPORTED");
    std::uint64_t count = u16(e + 10), central_size = u32(e + 12), central_offset = u32(e + 16);
    const std::uint64_t eocd_offset = size_ - tail_size + eocd;
    std::uint64_t central_end_limit = eocd_offset;
    const bool sentinel = count == 0xffff || central_size == UINT32_MAX || central_offset == UINT32_MAX;
    bool locator_present = false;
    if (eocd_offset >= 20) locator_present = u32(read(eocd_offset - 20, 4).data()) == 0x07064b50;
    if (sentinel || locator_present) {
        if (!locator_present) fail("ZIP64_LOCATOR_MISSING");
        const auto locator = read(eocd_offset - 20, 20);
        if (u32(locator.data() + 4) || u32(locator.data() + 16) != 1) fail("ZIP_MULTIDISK_UNSUPPORTED");
        const auto zip64_offset = u64(locator.data() + 8);
        const auto record = read(zip64_offset, 56); signature(record, 0x06064b50);
        const auto* z = record.data();
        const auto record_size = u64(z + 4);
        if (record_size < 44 || record_size > 1024 * 1024 || add(zip64_offset, add(12, record_size)) != eocd_offset - 20) fail("ZIP64_EOCD_RANGE");
        if (u32(z + 16) || u32(z + 20) || u64(z + 24) != u64(z + 32)) fail("ZIP_MULTIDISK_UNSUPPORTED");
        if ((count != 0xffff && count != u64(z + 32)) ||
            (central_size != UINT32_MAX && central_size != u64(z + 40)) ||
            (central_offset != UINT32_MAX && central_offset != u64(z + 48))) fail("ZIP64_EOCD_MISMATCH");
        count = u64(z + 32); central_size = u64(z + 40); central_offset = u64(z + 48);
        central_end_limit = zip64_offset;
    }
    if (count > limits_.max_entries || central_size > limits_.max_central_bytes) fail("ZIP_METADATA_LIMIT");
    if (add(central_offset, central_size) != central_end_limit || count > central_size / 46) fail("ZIP_CENTRAL_RANGE");
    std::map<std::string, bool> explicit_paths;
    std::map<std::string, std::string> spellings;
    std::uint64_t position = central_offset;
    for (std::uint64_t n = 0; n < count; ++n) {
        if (position > central_end_limit || central_end_limit - position < 46) fail("ZIP_CENTRAL_TRUNCATED");
        const auto header = read(position, 46); signature(header, 0x02014b50); const auto* p = header.data();
        const auto flags = u16(p + 8), method = u16(p + 10), name_size = u16(p + 28), extra_size = u16(p + 30), comment_size = u16(p + 32);
        // Only DEFLATE speed flags, data descriptors and the UTF-8 marker are accepted.
        if (flags & ~std::uint16_t(0x080e)) fail((flags & 1) ? "ZIP_ENCRYPTION_UNSUPPORTED" : "ZIP_FLAGS_UNSUPPORTED");
        if (method != 0 && method != 8) fail("ZIP_COMPRESSION_UNSUPPORTED");
        if (method == 0 && (flags & 6)) fail("ZIP_FLAGS_UNSUPPORTED");
        const auto next = add(position, 46ull + name_size + extra_size + comment_size);
        if (next > central_end_limit) fail("ZIP_CENTRAL_TRUNCATED");
        const auto name_bytes = read(position + 46, name_size);
        std::string name(name_bytes.begin(), name_bytes.end()); check_name(name);
        const bool directory = name.back() == '/';
        const auto attributes = u32(p + 38);
        const auto unix_kind = (attributes >> 16) & 0170000;
        if (unix_kind && unix_kind != 0100000 && unix_kind != 0040000) fail("ZIP_SPECIAL_FILE_UNSUPPORTED");
        if ((unix_kind == 0040000 || (attributes & 0x10)) && !directory) fail("ZIP_DIRECTORY_NAME_MISMATCH");
        if (unix_kind == 0100000 && directory) fail("ZIP_DIRECTORY_NAME_MISMATCH");
        const std::string key_name = directory ? name.substr(0, name.size() - 1) : name;
        const auto key = lowercase(key_name);
        if (!explicit_paths.emplace(key, directory).second) fail("ZIP_DUPLICATE_PATH");
        std::string prefix;
        for (const auto& part : components(name)) {
            if (!prefix.empty()) prefix += '/';
            prefix += part;
            auto inserted = spellings.emplace(lowercase(prefix), prefix);
            if (!inserted.second && inserted.first->second != prefix) fail("ZIP_CASE_COLLISION");
        }
        ZipEntry entry{name, directory, u32(p + 20), u32(p + 24)};
        Record r; r.local_offset = u32(p + 42); r.crc = u32(p + 16); r.flags = flags; r.method = method;
        const auto values = zip64_extra(read(position + 46 + name_size, extra_size));
        std::size_t index = 0;
        r.zip64_descriptor = entry.uncompressed_size == UINT32_MAX || entry.compressed_size == UINT32_MAX;
        if (entry.uncompressed_size == UINT32_MAX) entry.uncompressed_size = consume64(values, index);
        if (entry.compressed_size == UINT32_MAX) entry.compressed_size = consume64(values, index);
        if (r.local_offset == UINT32_MAX) r.local_offset = consume64(values, index);
        auto disk = std::uint32_t(u16(p + 34));
        if (disk == 0xffff) {
            if (index > values.size() || values.size() - index < 4) fail("ZIP64_EXTRA_MISSING");
            disk = u32(values.data() + index);
        }
        if (disk) fail("ZIP_MULTIDISK_UNSUPPORTED");
        if (entry.uncompressed_size > limits_.max_file_bytes) fail("ZIP_FILE_SIZE_LIMIT");
        total_ = add(total_, entry.uncompressed_size);
        if (total_ > limits_.max_total_bytes) fail("ZIP_TOTAL_SIZE_LIMIT");
        if (entry.uncompressed_size > 16ull * 1024 * 1024 && limits_.max_expansion_ratio &&
            (entry.compressed_size == 0 || (entry.uncompressed_size - 1) / entry.compressed_size >= limits_.max_expansion_ratio)) fail("ZIP_EXPANSION_LIMIT");
        if (method == 0 && entry.compressed_size != entry.uncompressed_size) fail("ZIP_STORED_SIZE_MISMATCH");
        // ZIP writers may encode an empty directory using a raw DEFLATE stream
        // (usually two bytes). Its decoded contents must still be empty, and
        // extraction validates that stream just like any other entry.
        if (directory && (entry.uncompressed_size || r.crc)) fail("ZIP_DIRECTORY_PAYLOAD_UNSUPPORTED");
        if (r.local_offset > central_offset || central_offset - r.local_offset < 30) fail("ZIP_LOCAL_RANGE");
        const auto local = read(r.local_offset, 30); signature(local, 0x04034b50); const auto* l = local.data();
        if (u16(l + 6) != flags || u16(l + 8) != method || u16(l + 26) != name_size) fail("ZIP_LOCAL_MISMATCH");
        const auto local_extra_size = u16(l + 28);
        r.data_offset = add(r.local_offset, 30ull + name_size + local_extra_size);
        if (r.data_offset > central_offset || entry.compressed_size > central_offset - r.data_offset) fail("ZIP_LOCAL_RANGE");
        if (read(r.local_offset + 30, name_size) != name_bytes) fail("ZIP_LOCAL_NAME_MISMATCH");
        const auto local_values = zip64_extra(read(r.local_offset + 30 + name_size, local_extra_size));
        std::uint64_t local_unpacked = u32(l + 22), local_packed = u32(l + 18);
        std::size_t local_index = 0;
        const bool local_zip64 = local_unpacked == UINT32_MAX || local_packed == UINT32_MAX;
        if (local_unpacked == UINT32_MAX) local_unpacked = consume64(local_values, local_index);
        if (local_packed == UINT32_MAX) local_packed = consume64(local_values, local_index);
        if (!(flags & 8)) {
            if (u32(l + 14) != r.crc || local_unpacked != entry.uncompressed_size || local_packed != entry.compressed_size) fail("ZIP_LOCAL_SIZE_OR_CRC_MISMATCH");
        } else if ((u32(l + 14) && u32(l + 14) != r.crc) ||
                   (local_unpacked && local_unpacked != entry.uncompressed_size) ||
                   (local_packed && local_packed != entry.compressed_size)) fail("ZIP_LOCAL_SIZE_OR_CRC_MISMATCH");
        r.end_offset = add(r.data_offset, entry.compressed_size);
        if (flags & 8) {
            r.zip64_descriptor = r.zip64_descriptor || local_zip64;
            const auto bytes = r.zip64_descriptor ? 20u : 12u;
            if (r.end_offset > central_offset || central_offset - r.end_offset < bytes) fail("ZIP_DESCRIPTOR_TRUNCATED");
            auto descriptor_offset = r.end_offset;
            const auto first = read(descriptor_offset, 4);
            const auto descriptor_matches = [&](std::uint64_t offset) {
                if (offset > central_offset || central_offset - offset < bytes) return false;
                const auto descriptor = read(offset, bytes); const auto* d = descriptor.data();
                const auto packed = r.zip64_descriptor ? u64(d + 4) : std::uint64_t(u32(d + 4));
                const auto unpacked = r.zip64_descriptor ? u64(d + 12) : std::uint64_t(u32(d + 8));
                return u32(d) == r.crc && packed == entry.compressed_size && unpacked == entry.uncompressed_size;
            };
            // The optional signature has the same representation as a valid
            // CRC32. Only consume it when the following fields agree with the
            // central directory; otherwise try the unsigned descriptor.
            if (u32(first.data()) == 0x08074b50 && descriptor_matches(descriptor_offset + 4)) descriptor_offset += 4;
            else if (!descriptor_matches(descriptor_offset)) fail("ZIP_DESCRIPTOR_MISMATCH");
            r.end_offset = descriptor_offset + bytes;
        }
        entries_.push_back(std::move(entry)); records_.push_back(r); position = next;
    }
    if (position != central_end_limit) fail("ZIP_CENTRAL_COUNT_MISMATCH");
    for (const auto& item : explicit_paths) {
        for (auto slash = item.first.find('/'); slash != std::string::npos; slash = item.first.find('/', slash + 1)) {
            auto parent = explicit_paths.find(item.first.substr(0, slash));
            if (parent != explicit_paths.end() && !parent->second) fail("ZIP_FILE_DIRECTORY_CONFLICT");
        }
    }
    std::vector<std::pair<std::uint64_t, std::uint64_t>> ranges;
    for (const auto& r : records_) ranges.emplace_back(r.local_offset, r.end_offset);
    std::sort(ranges.begin(), ranges.end());
    for (std::size_t i = 1; i < ranges.size(); ++i) if (ranges[i].first < ranges[i - 1].second) fail("ZIP_OVERLAPPING_ENTRIES");
}

void ZipArchive::extract(const std::filesystem::path& destination, Progress progress) {
    ZipProgress state; state.entry_count = entries_.size(); state.total_bytes = total_;
    auto notify = [&] { if (progress && !progress(state)) fail("ZIP_CANCELLED"); };
    notify();
    // No mkdir -p: staging's parent belongs to the app; refuse a pre-existing root.
    if (::mkdir(destination.c_str(), 0700) != 0) fail(errno == EEXIST ? "ZIP_DESTINATION_EXISTS" : "ZIP_CREATE_DIRECTORY_FAILED");
    FD root(::open(destination.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
    if (root.get() < 0) fail("ZIP_UNSAFE_OUTPUT_DIRECTORY");
    std::array<std::uint8_t, 128 * 1024> input{}, output{};
    for (std::size_t i = 0; i < entries_.size(); ++i) {
        const auto& entry = entries_[i]; const auto& r = records_[i];
        state.entry_index = i; state.entry_name = entry.name; notify();
        auto parts = components(entry.name);
        FD parent(::dup(root.get()));
        if (parent.get() < 0) fail("ZIP_OPEN_OUTPUT_FAILED");
        for (std::size_t j = 0; j + 1 < parts.size(); ++j) parent = directory_at(parent.get(), parts[j]);
        FD file;
        if (entry.directory) {
            auto directory = directory_at(parent.get(), parts.back());
        } else {
            file = FD(::openat(parent.get(), parts.back().c_str(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600));
            if (file.get() < 0) fail("ZIP_CREATE_OUTPUT_FAILED");
        }
        std::uint64_t packed = 0, unpacked = 0;
        uLong crc = ::crc32(0, Z_NULL, 0);
        auto consume_output = [&](const std::uint8_t* bytes, std::size_t count) {
            if (unpacked > entry.uncompressed_size || count > entry.uncompressed_size - unpacked) fail("ZIP_EXPANDED_SIZE_MISMATCH");
            write_all(file.get(), bytes, count);
            crc = ::crc32(crc, bytes, static_cast<uInt>(count));
            unpacked += count; state.bytes_written += count; notify();
        };
        stream_.clear(); stream_.seekg(static_cast<std::streamoff>(r.data_offset));
        if (!stream_) fail("ZIP_SEEK_FAILED");
        if (r.method == 0) {
            while (packed < entry.compressed_size) {
                const auto count = static_cast<std::size_t>(std::min<std::uint64_t>(input.size(), entry.compressed_size - packed));
                if (!stream_.read(reinterpret_cast<char*>(input.data()), static_cast<std::streamsize>(count))) fail("ZIP_READ_FAILED");
                packed += count; consume_output(input.data(), count);
            }
        } else {
            Inflater inflater; auto& z = inflater.stream;
            bool finished = false;
            while (!finished) {
                if (z.avail_in == 0 && packed < entry.compressed_size) {
                    const auto count = static_cast<std::size_t>(std::min<std::uint64_t>(input.size(), entry.compressed_size - packed));
                    if (!stream_.read(reinterpret_cast<char*>(input.data()), static_cast<std::streamsize>(count))) fail("ZIP_READ_FAILED");
                    packed += count; z.next_in = input.data(); z.avail_in = static_cast<uInt>(count);
                }
                z.next_out = output.data(); z.avail_out = static_cast<uInt>(output.size());
                const auto before = z.avail_in;
                const int result = ::inflate(&z, Z_NO_FLUSH);
                const auto count = output.size() - z.avail_out;
                consume_output(output.data(), count);
                if (result == Z_STREAM_END) finished = true;
                else if (result != Z_OK || (before == z.avail_in && count == 0)) fail("ZIP_DEFLATE_INVALID_OR_TRUNCATED");
            }
            if (z.avail_in || packed != entry.compressed_size) fail("ZIP_DEFLATE_TRAILING_DATA");
        }
        if (unpacked != entry.uncompressed_size) fail("ZIP_EXPANDED_SIZE_MISMATCH");
        if (static_cast<std::uint32_t>(crc) != r.crc) fail("ZIP_CRC_MISMATCH");
    }
    state.entry_index = entries_.size(); state.entry_name.clear(); notify();
}
} // namespace storm::filesystem
