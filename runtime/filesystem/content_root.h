#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

namespace storm::filesystem {
// User-controlled app data only. Paths are relative and may not traverse symlinks.
class ContentRoot {
public:
    explicit ContentRoot(const std::filesystem::path& root);
    std::filesystem::path resolve(const std::filesystem::path& relative) const;
    std::vector<std::uint8_t> read(const std::filesystem::path& relative,
                                 std::size_t max_bytes = 64*1024*1024) const;
private:
    std::filesystem::path root_;
};
} // namespace storm::filesystem
