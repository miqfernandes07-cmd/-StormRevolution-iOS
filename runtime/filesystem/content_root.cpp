#include "filesystem/content_root.h"
#include <fstream>
#include <limits>
#include <stdexcept>

namespace storm::filesystem {
ContentRoot::ContentRoot(const std::filesystem::path& root) : root_(std::filesystem::canonical(root)) {
    if (!std::filesystem::is_directory(root_)) throw std::invalid_argument("CONTENT_NOT_DIRECTORY");
}
std::filesystem::path ContentRoot::resolve(const std::filesystem::path& relative) const {
    if (relative.empty() || relative.is_absolute() || relative.has_root_name())
        throw std::invalid_argument("CONTENT_PATH_NOT_RELATIVE");
    auto current = root_;
    for (const auto& part : relative) {
        if (part == "..") throw std::invalid_argument("CONTENT_PATH_TRAVERSAL");
        if (part == ".") continue;
        current /= part;
        if (std::filesystem::is_symlink(std::filesystem::symlink_status(current)))
            throw std::invalid_argument("CONTENT_SYMLINK_REJECTED");
    }
    return current;
}
std::vector<std::uint8_t> ContentRoot::read(const std::filesystem::path& relative, std::size_t max_bytes) const {
    const auto path = resolve(relative);
    if (!std::filesystem::is_regular_file(path)) throw std::runtime_error("CONTENT_NOT_REGULAR_FILE");
    const auto size = std::filesystem::file_size(path);
    if (size > max_bytes || size > std::uintmax_t(std::numeric_limits<std::streamsize>::max()))
        throw std::runtime_error("CONTENT_SIZE_LIMIT");
    std::vector<std::uint8_t> bytes(static_cast<std::size_t>(size));
    std::ifstream stream(path,std::ios::binary);
    if (!stream || (size && !stream.read(reinterpret_cast<char*>(bytes.data()),static_cast<std::streamsize>(size))))
        throw std::runtime_error("CONTENT_READ_FAILED");
    if (stream.peek() != std::char_traits<char>::eof()) throw std::runtime_error("CONTENT_CHANGED_DURING_READ");
    return bytes;
}
} // namespace storm::filesystem
