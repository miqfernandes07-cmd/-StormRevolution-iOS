// Exercises the real POSIX mapping helper without a game or an iOS simulator.
#include "base/memory_posix.h"
#include <sys/stat.h>
#include <cstdio>
#include <limits>

static int checks;
#define CHECK(value) do { ++checks; if (!(value)) { \
  std::fprintf(stderr, "Mapping check failed at line %d: %s (errno %d)\n", __LINE__, #value, errno); \
  return 1; } } while (false)

int main() {
  using rex::memory::detail::CreatePrivateMappingFile;
  const size_t page = static_cast<size_t>(getpagesize());
  const size_t offset = size_t{1} << 32;
  const size_t length = 0x120000000ULL + page;
  int fd = CreatePrivateMappingFile(length, false);
  CHECK(fd >= 0);
  struct stat info{};
  CHECK(fstat(fd, &info) == 0);
  CHECK(static_cast<size_t>(info.st_size) == length);
  CHECK(info.st_nlink == 0);
  CHECK((info.st_mode & 0077) == 0);
  CHECK(static_cast<size_t>(info.st_blocks) * 512 < 1024 * 1024);
  CHECK((fcntl(fd, F_GETFD) & FD_CLOEXEC) != 0);
  void *a = mmap(nullptr, page, PROT_READ | PROT_WRITE, MAP_SHARED, fd, offset);
  void *b = mmap(nullptr, page, PROT_READ | PROT_WRITE, MAP_SHARED, fd, offset);
  CHECK(a != MAP_FAILED && b != MAP_FAILED);
  auto first = static_cast<volatile unsigned char *>(a);
  auto second = static_cast<volatile unsigned char *>(b);
  CHECK(first[0] == 0 && second[page - 1] == 0);
  first[0] = 0xAB;
  CHECK(second[0] == 0xAB);
  second[page - 1] = 0x56;
  CHECK(first[page - 1] == 0x56);
  CHECK(close(fd) == 0);
  second[2] = 0x45;
  CHECK(first[2] == 0x45);
  CHECK(munmap(a, page) == 0 && munmap(b, page) == 0);
  fd = CreatePrivateMappingFile(page, true);
  CHECK(fd >= 0);
  CHECK((fcntl(fd, F_GETFD) & FD_CLOEXEC) != 0);
  CHECK((fcntl(fd, F_GETFL) & O_ACCMODE) == O_RDONLY);
  CHECK(mmap(nullptr, page, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0) == MAP_FAILED);
  CHECK(errno == EACCES);
  a = mmap(nullptr, page, PROT_READ, MAP_SHARED, fd, 0);
  CHECK(a != MAP_FAILED);
  CHECK(close(fd) == 0);
  CHECK(*static_cast<volatile unsigned char *>(a) == 0);
  CHECK(munmap(a, page) == 0);
  CHECK(CreatePrivateMappingFile(0, false) == -1 && errno == EINVAL);
  CHECK(CreatePrivateMappingFile(std::numeric_limits<size_t>::max(), false) == -1 && errno == EOVERFLOW);
  std::printf("Private sparse mapping: %d checks passed; coherent aliases above 4 GiB\n", checks);
}
