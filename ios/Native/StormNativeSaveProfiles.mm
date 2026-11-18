#import "StormNativeSaveProfiles.h"
#include <sys/stat.h>
#include <unistd.h>
#include <cstdio>
#include <cerrno>

static NSURL *Support(void) {
  return [NSFileManager.defaultManager URLsForDirectory:NSApplicationSupportDirectory inDomains:NSUserDomainMask].firstObject;
}
@implementation StormNativeSaveProfiles
+ (NSURL *)activeURL { return [Support() URLByAppendingPathComponent:@"SelectedUser"]; }
+ (NSURL *)normalURL { return [Support() URLByAppendingPathComponent:@"User"]; }
+ (NSURL *)cheatURL { return [Support() URLByAppendingPathComponent:@"CheatUser"]; }
+ (BOOL)selectCheats:(BOOL)enabled error:(NSError **)error {
  @synchronized(self) {
    NSFileManager *fm = NSFileManager.defaultManager;
    NSURL *normal = self.normalURL, *cheat = self.cheatURL, *active = self.activeURL;
    if (![fm createDirectoryAtURL:normal withIntermediateDirectories:YES attributes:nil error:error]) return NO;
    if (enabled && ![fm fileExistsAtPath:cheat.path]) {
      NSURL *staging = [Support() URLByAppendingPathComponent:[@".cheat-profile-" stringByAppendingString:NSUUID.UUID.UUIDString]];
      if (![fm copyItemAtURL:normal toURL:staging error:error]) { [fm removeItemAtURL:staging error:nil]; return NO; }
      if (renamex_np(staging.fileSystemRepresentation, cheat.fileSystemRepresentation, RENAME_EXCL) != 0) {
        int saved = errno; [fm removeItemAtURL:staging error:nil];
        if (error) *error = [NSError errorWithDomain:NSPOSIXErrorDomain code:saved userInfo:nil];
        return NO;
      }
    }
    struct stat info;
    if (lstat(active.fileSystemRepresentation, &info) == 0 && !S_ISLNK(info.st_mode)) {
      if (error) *error = [NSError errorWithDomain:NSCocoaErrorDomain code:NSFileWriteFileExistsError userInfo:@{NSFilePathErrorKey:active.path}];
      return NO;
    }
    NSURL *temporary = [Support() URLByAppendingPathComponent:[@".selected-user-" stringByAppendingString:NSUUID.UUID.UUIDString]];
    NSURL *target = enabled ? cheat : normal;
    if (symlink(target.fileSystemRepresentation, temporary.fileSystemRepresentation) != 0) {
      if (error) *error = [NSError errorWithDomain:NSPOSIXErrorDomain code:errno userInfo:nil];
      return NO;
    }
    if (rename(temporary.fileSystemRepresentation, active.fileSystemRepresentation) != 0) {
      int saved = errno; unlink(temporary.fileSystemRepresentation);
      if (error) *error = [NSError errorWithDomain:NSPOSIXErrorDomain code:saved userInfo:nil];
      return NO;
    }
    return YES;
  }
}
@end
