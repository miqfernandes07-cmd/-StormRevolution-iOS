#import <UIKit/UIKit.h>
#import "App/StormViewController.h"
void StormRunImportSmoke(void);

@interface StormAppDelegate : UIResponder <UIApplicationDelegate>
@property(nonatomic, strong) UIWindow *window;
@end
@implementation StormAppDelegate
- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)options {
  (void)application; (void)options;
  self.window = [[UIWindow alloc] initWithFrame:UIScreen.mainScreen.bounds];
  self.window.rootViewController = [[StormViewController alloc] init];
  [self.window makeKeyAndVisible];
  if ([NSProcessInfo.processInfo.arguments containsObject:@"--import-smoke-test"])
    dispatch_async(dispatch_get_main_queue(), ^{ StormRunImportSmoke(); });
  return YES;
}
@end

int main(int argc, char *argv[]) {
  @autoreleasepool { return UIApplicationMain(argc, argv, nil, NSStringFromClass(StormAppDelegate.class)); }
}
