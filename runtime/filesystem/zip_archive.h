#pragma once

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <functional>
#include <stdexcept>
#include <string>
#include <vector>

namespace storm::filesystem {

struct ZipLimits {
    std::uint64_t max_archive_bytes = 32ull * 1024 * 1024 * 1024;
    std::uint64_t max_total_bytes = 32ull * 1024 * 1024 * 1024;
    std::uint64_t max_file_bytes = 16ull * 1024 * 1024 * 1024;
    std::uint64_t max_central_bytes = 32ull * 1024 * 1024;
    std::uint32_t max_entries = 100000;
    std::uint32_t max_expansion_ratio = 1000;
};

struct ZipEntry {
    std::string name; // Validated relative UTF-8/ASCII path, no backslashes.
    bool directory = false;
    std::uint64_t compressed_size = 0;
    std::uint64_t uncompressed_size = 0;
};

struct ZipProgress {
    std::size_t entry_index = 0; // Zero based; entry_count means finished.
    std::size_t entry_count = 0;
    std::string entry_name;
    std::uint64_t bytes_written = 0;
    std::uint64_t total_bytes = 0;
};

class ZipError : public std::runtime_error {
public:
    explicit ZipError(const std::string& code) : std::runtime_error(code) {}
    const char* code() const noexcept { return what(); }
};

// ZIP/ZIP64 metadata inspection and bounded streaming extraction on POSIX hosts
// (Linux/WSL, macOS and iOS). Uses system zlib for raw DEFLATE. No game-specific
// transformation, AOT generation or integrity claim beyond ZIP sizes and CRC32.
// The archive stream stays open between inspection and extraction. Callers must
// coordinate source-file access and serialize use of an instance.
class ZipArchive {
public:
    using Progress = std::function<bool(const ZipProgress&)>;
    explicit ZipArchive(const std::filesystem::path& source, ZipLimits limits = {});
    const std::vector<ZipEntry>& entries() const noexcept { return entries_; }
    std::uint64_t total_uncompressed() const noexcept { return total_; }
    // Creates a NEW destination directory. Existing destinations are refused.
    // On failure, a partial staging directory may remain; the caller removes it.
    // No existing files are overwritten; path traversal and symlinks are refused.
    void extract(const std::filesystem::path& destination, Progress progress = {});

private:
    struct Record {
        std::uint64_t local_offset = 0;
        std::uint64_t data_offset = 0;
        std::uint64_t end_offset = 0;
        std::uint32_t crc = 0;
        std::uint16_t flags = 0;
        std::uint16_t method = 0;
        bool zip64_descriptor = false;
    };
    std::ifstream stream_;
    ZipLimits limits_;
    std::uint64_t size_ = 0;
    std::uint64_t total_ = 0;
    std::vector<ZipEntry> entries_;
    std::vector<Record> records_;
    std::vector<std::uint8_t> read(std::uint64_t offset, std::size_t count);
    void inspect();
};
} // namespace storm::filesystem
