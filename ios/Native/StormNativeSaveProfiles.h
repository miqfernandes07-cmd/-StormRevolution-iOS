#import <Foundation/Foundation.h>

@interface StormNativeSaveProfiles : NSObject
+ (NSURL *)activeURL;
+ (NSURL *)normalURL;
+ (NSURL *)cheatURL;
// Before title launch only. The SDK retains this path, then resolves it when
// mounting saves. Switching the symlink preserves the normal profile entirely.
+ (BOOL)selectCheats:(BOOL)enabled error:(NSError **)error;
@end
