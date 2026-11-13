#import "Import/StormGameImporter.h"
#import <CommonCrypto/CommonDigest.h>
#include "filesystem/zip_archive.h"
#include <atomic>
#include <cstring>
#include <filesystem>
#include <memory>
#include <chrono>

static NSString *const ExpectedSHA1 = @"c9c1cf1fc4d7a535542edb1aae19751d4ed7e090";
static uint32_t ReadBE32(const uint8_t *p) {
  return uint32_t(p[0]) << 24 | uint32_t(p[1]) << 16 | uint32_t(p[2]) << 8 | p[3];
}
static NSError *ImportError(NSString *message) {
  return [NSError errorWithDomain:@"StormImport" code:1 userInfo:@{NSLocalizedDescriptionKey:message}];
}
static NSURL *GameURL(void) {
  NSURL *support = [NSFileManager.defaultManager URLsForDirectory:NSApplicationSupportDirectory inDomains:NSUserDomainMask].firstObject;
  return [support URLByAppendingPathComponent:@"Game" isDirectory:YES];
}
// This check identifies the documented XEX revision; it is not a game compatibility claim.
static NSDictionary *ValidateXEX(NSURL *url, NSError **error) {
  NSNumber *size = nil;
  if (![url getResourceValue:&size forKey:NSURLFileSizeKey error:error]) return nil;
  if (size.unsignedLongLongValue < 24) { *error = ImportError(@"XEX truncated: fewer than 24 bytes"); return nil; }
  if (size.unsignedLongLongValue != 11776000) {
    *error = ImportError([NSString stringWithFormat:@"XEX size mismatch: %@ bytes; expected 11776000", size]); return nil;
  }
  NSInputStream *stream = [NSInputStream inputStreamWithURL:url];
  [stream open];
  CC_SHA1_CTX hash;
  CC_SHA1_Init(&hash);
  uint8_t buffer[65536];
  NSInteger count;
  while ((count = [stream read:buffer maxLength:sizeof(buffer)]) > 0) CC_SHA1_Update(&hash, buffer, (CC_LONG)count);
  NSError *streamError = stream.streamError;
  [stream close];
  if (count < 0) { *error = streamError ?: ImportError(@"Cannot read XEX"); return nil; }
  uint8_t digest[CC_SHA1_DIGEST_LENGTH];
  CC_SHA1_Final(digest, &hash);
  NSMutableString *sha1 = [NSMutableString string];
  for (uint8_t byte : digest) [sha1 appendFormat:@"%02x", byte];
  NSFileHandle *file = [NSFileHandle fileHandleForReadingFromURL:url error:error];
  if (!file) return nil;
  // Bounded header read: unknown giant headers are refused, never trusted as offsets.
  NSData *data = [file readDataUpToLength:(NSUInteger)MIN(size.unsignedLongLongValue, 1024ull * 1024) error:error];
  [file closeFile];
  if (!data || data.length < 24 || std::memcmp(data.bytes, "XEX2", 4) != 0) {
    *error = ImportError(@"Invalid XEX2 magic/header"); return nil;
  }
  const uint8_t *p = (const uint8_t *)data.bytes;
  uint32_t optionalCount = ReadBE32(p + 20), security = ReadBE32(p + 16);
  if (optionalCount > (data.length - 24) / 8) { *error = ImportError(@"Optional header table outside bounded header"); return nil; }
  uint32_t title = 0, version = 0, region = 0, media = 0;
  BOOL hasExecution = NO, hasRegion = NO;
  for (uint32_t i = 0; i < optionalCount; ++i) {
    uint32_t key = ReadBE32(p + 24 + i * 8), offset = ReadBE32(p + 28 + i * 8);
    if (key == 0x00040006) {
      if (hasExecution || uint64_t(offset) + 24 > data.length) { *error = ImportError(@"Duplicate or out-of-range execution-info header"); return nil; }
      version = ReadBE32(p + offset + 4);
      media = ReadBE32(p + offset);
      title = ReadBE32(p + offset + 12);
      hasExecution = YES;
    }
  }
  if (uint64_t(security) + 0x17c <= data.length && security >= 24) {
    region = ReadBE32(p + security + 0x178);
    hasRegion = YES;
  }
  BOOL matches = hasExecution && hasRegion && title == 0x4E4D0868 && media == 0x29E320A9 && version == 0x00000004 &&
      (region & 0xff) != 0 && size.unsignedLongLongValue == 11776000 && [sha1 isEqualToString:ExpectedSHA1];
  return @{@"sha1":sha1, @"size":size, @"title_id":[NSString stringWithFormat:@"%08X", title],
    @"version_raw":[NSString stringWithFormat:@"%08X", version], @"media_id":[NSString stringWithFormat:@"%08X", media],
    @"region_mask":[NSString stringWithFormat:@"%08X", region],
    @"reference_matches":@(matches), @"note":@"Identity only. Assets and AOT image are not validated by this check."};
}

#import <UIKit/UIKit.h>

namespace {
NSString *ArchiveMessage(const std::string& code) {
  if (code == "ZIP_CANCELLED") return @"Importação cancelada. Sua instalação anterior foi preservada.";
  if (code.find("CRC") != std::string::npos || code.find("TRUNCATED") != std::string::npos)
    return @"O ZIP parece incompleto ou corrompido. Verifique sua cópia e tente novamente.";
  if (code.find("ENCRYPT") != std::string::npos)
    return @"Este ZIP está protegido por senha. Use uma cópia sem senha.";
  if (code.find("COMPRESSION") != std::string::npos)
    return @"Este método de compressão não é compatível. Use ZIP com Deflate ou sem compressão.";
  if (code == "ZIP_NON_ASCII_PATH_UNSUPPORTED")
    return @"Esta versão aceita somente nomes de arquivos sem acentos no ZIP. Preserve os nomes originais dos recursos do jogo.";
  return @"Não foi possível preparar este ZIP. Verifique o arquivo e o espaço livre.";
}
void CheckCancelled(const std::shared_ptr<std::atomic<bool>>& cancelled) {
  if (cancelled->load()) throw std::runtime_error("ZIP_CANCELLED");
}
}

@implementation StormGameImporter {
  std::shared_ptr<std::atomic<bool>> _cancelled;
  BOOL _busy;
}
+ (NSURL *)gameURL { return GameURL(); }
+ (void)validateInstalledWithCompletion:(void (^)(NSDictionary *, NSError *))completion {
  dispatch_async(dispatch_get_global_queue(QOS_CLASS_UTILITY, 0), ^{
    NSError *error = nil;
    NSDictionary *validation = ValidateXEX([GameURL() URLByAppendingPathComponent:@"default.xex"], &error);
    dispatch_async(dispatch_get_main_queue(), ^{ completion(validation, error); });
  });
}
- (void)cancel { if (_cancelled) _cancelled->store(true); }
- (void)importZIPAtURL:(NSURL *)source
             progress:(void (^)(double, NSString *))progress
           completion:(void (^)(NSDictionary *, NSError *))completion {
  NSAssert(NSThread.isMainThread, @"Import requests must originate on the main queue");
  if (_busy) { completion(nil, ImportError(@"Já existe uma importação em andamento.")); return; }
  _busy = YES;
  _cancelled = std::make_shared<std::atomic<bool>>(false);
  const auto cancelled = _cancelled;
  __block UIBackgroundTaskIdentifier background = UIBackgroundTaskInvalid;
  background = [UIApplication.sharedApplication beginBackgroundTaskWithName:@"Preparar jogo" expirationHandler:^{
    cancelled->store(true);
    if (background != UIBackgroundTaskInvalid) {
      [UIApplication.sharedApplication endBackgroundTask:background];
      background = UIBackgroundTaskInvalid;
    }
  }];
  progress(0, @"Acessando o ZIP…");
  dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
    const BOOL scoped = [source startAccessingSecurityScopedResource];
    NSFileManager *manager = NSFileManager.defaultManager;
    NSURL *destination = GameURL();
    NSURL *parent = destination.URLByDeletingLastPathComponent;
    NSURL *staging = [parent URLByAppendingPathComponent:[@".incoming-" stringByAppendingString:NSUUID.UUID.UUIDString] isDirectory:YES];
    __block NSError *error = nil;
    __block NSDictionary *validation = nil;
    [manager createDirectoryAtURL:parent withIntermediateDirectories:YES attributes:nil error:&error];
    // Imported assets and transient extraction data must not enter iCloud backup.
    if (!error) [parent setResourceValue:@YES forKey:NSURLIsExcludedFromBackupKey error:nil];
    // A terminated import cannot run its cleanup handler. Only our own abandoned
    // staging names are removed on the next serial import; Game is never touched.
    if (!error) {
      NSArray<NSURL *> *children = [manager contentsOfDirectoryAtURL:parent includingPropertiesForKeys:nil options:0 error:&error];
      for (NSURL *child in children) {
        if ([child.lastPathComponent hasPrefix:@".incoming-"] && ![manager removeItemAtURL:child error:&error]) break;
      }
    }
    NSFileCoordinator *coordinator = [[NSFileCoordinator alloc] initWithFilePresenter:nil];
    NSError *coordinationError = nil;
    if (!error) [coordinator coordinateReadingItemAtURL:source options:NSFileCoordinatorReadingWithoutChanges error:&coordinationError byAccessor:^(NSURL *readURL) {
      try {
        CheckCancelled(cancelled);
        NSNumber *regular = nil, *link = nil;
        if (![readURL getResourceValue:&regular forKey:NSURLIsRegularFileKey error:&error] ||
            ![readURL getResourceValue:&link forKey:NSURLIsSymbolicLinkKey error:&error]) return;
        if (!regular.boolValue || link.boolValue) { error = ImportError(@"Selecione um arquivo ZIP regular pelo aplicativo Arquivos."); return; }
        storm::filesystem::ZipArchive archive(readURL.fileSystemRepresentation);
        const auto capacity = std::filesystem::space(parent.fileSystemRepresentation);
        constexpr uint64_t reserve = 256ull * 1024 * 1024;
        if (capacity.available < reserve || archive.total_uncompressed() > capacity.available - reserve) {
          NSString *needed = [NSByteCountFormatter stringFromByteCount:(long long)(archive.total_uncompressed()+reserve) countStyle:NSByteCountFormatterCountStyleFile];
          error = ImportError([NSString stringWithFormat:@"Libere pelo menos %@ para preparar esta cópia. A instalação anterior será mantida durante a extração.", needed]);
          return;
        }
        NSString *executable = nil;
        for (const auto& entry : archive.entries()) {
          if (entry.directory) continue;
          NSString *name = [[NSString alloc] initWithBytes:entry.name.data() length:entry.name.size() encoding:NSUTF8StringEncoding];
          if (!name) { error = ImportError(@"O ZIP contém um nome de arquivo com codificação incompatível."); return; }
          if ([name.lastPathComponent caseInsensitiveCompare:@"default.xex"] == NSOrderedSame) {
            if (executable) { error = ImportError(@"O ZIP contém mais de um default.xex. Use uma única cópia extraída do jogo."); return; }
            executable = name;
          }
        }
        if (!executable) { error = ImportError(@"Não encontramos default.xex no ZIP. Use os arquivos extraídos da versão Xbox 360, não uma ISO ou APK."); return; }
        auto lastUpdate = std::chrono::steady_clock::now();
        archive.extract(staging.fileSystemRepresentation, [&](const storm::filesystem::ZipProgress& state) {
          if (cancelled->load()) return false;
          const auto now = std::chrono::steady_clock::now();
          if (now-lastUpdate < std::chrono::milliseconds(150) && state.bytes_written < state.total_bytes) return true;
          lastUpdate = now;
          const double fraction = state.total_bytes ? double(state.bytes_written)/double(state.total_bytes) : 1.0;
          NSString *done = [NSByteCountFormatter stringFromByteCount:(long long)state.bytes_written countStyle:NSByteCountFormatterCountStyleFile];
          NSString *total = [NSByteCountFormatter stringFromByteCount:(long long)state.total_bytes countStyle:NSByteCountFormatterCountStyleFile];
          NSString *message = [NSString stringWithFormat:@"Extraindo %@ de %@", done, total];
          dispatch_async(dispatch_get_main_queue(), ^{ progress(.02+.88*fraction, message); });
          return true;
        });
        CheckCancelled(cancelled);
        dispatch_async(dispatch_get_main_queue(), ^{ progress(.93, @"Verificando a versão do jogo…"); });
        NSURL *xex = [staging URLByAppendingPathComponent:executable];
        validation = ValidateXEX(xex, &error);
        if (!validation || ![validation[@"reference_matches"] boolValue]) {
          if (!error) error = ImportError(@"O executável não corresponde à versão Xbox 360 compatível com este projeto. Sua instalação anterior foi preservada.");
          return;
        }
        CheckCancelled(cancelled);
        NSURL *gameRoot = xex.URLByDeletingLastPathComponent;
        // Normalize case through a temporary name, including on case-insensitive APFS.
        if (![xex.lastPathComponent isEqualToString:@"default.xex"]) {
          NSURL *temporary = [gameRoot URLByAppendingPathComponent:[@".normalizing-" stringByAppendingString:NSUUID.UUID.UUIDString]];
          if (![manager moveItemAtURL:xex toURL:temporary error:&error] ||
              ![manager moveItemAtURL:temporary toURL:[gameRoot URLByAppendingPathComponent:@"default.xex"] error:&error]) return;
        }
        CheckCancelled(cancelled);
        [gameRoot setResourceValue:@YES forKey:NSURLIsExcludedFromBackupKey error:nil];
        dispatch_async(dispatch_get_main_queue(), ^{ progress(.98, @"Concluindo a preparação…"); });
        // Commit is deliberately not cancellable: preserve the previous import until validation passes.
        if ([manager fileExistsAtPath:destination.path]) {
          [manager replaceItemAtURL:destination withItemAtURL:gameRoot backupItemName:nil options:0 resultingItemURL:nil error:&error];
        } else {
          [manager moveItemAtURL:gameRoot toURL:destination error:&error];
        }
      } catch (const std::exception& failure) {
        const std::string code = failure.what();
        error = [NSError errorWithDomain:@"StormZIP" code:cancelled->load() ? NSUserCancelledError : 1
          userInfo:@{NSLocalizedDescriptionKey:ArchiveMessage(code), @"diagnostic":([NSString stringWithUTF8String:code.c_str()] ?: @"ZIP_ERROR")}];
      }
    }];
    if (!error) error = coordinationError;
    [manager removeItemAtURL:staging error:nil];
    if (scoped) [source stopAccessingSecurityScopedResource];
    dispatch_async(dispatch_get_main_queue(), ^{
      self->_busy = NO;
      if (background != UIBackgroundTaskInvalid) {
        [UIApplication.sharedApplication endBackgroundTask:background];
        background = UIBackgroundTaskInvalid;
      }
      if (!error) progress(1, @"Arquivos preparados. A execução do jogo aguarda a versão AOT.");
      completion(error ? nil : validation, error);
    });
  });
}
@end
