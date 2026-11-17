#import <UIKit/UIKit.h>
#import "Controls/StormControls.h"
#import "Native/StormNativeOptions.h"
#import "Native/StormNativePreferences.h"
#include "input/xbox360_mapping.h"

@interface ControlsSmoke : UIResponder <UIApplicationDelegate>
@property(nonatomic,strong) UIWindow *window;
@end
@implementation ControlsSmoke
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)options {
  self.window = [[UIWindow alloc] initWithFrame:UIScreen.mainScreen.bounds];
  UIViewController *root = [UIViewController new];
  self.window.rootViewController = root;
  [self.window makeKeyAndVisible];
  dispatch_after(dispatch_time(DISPATCH_TIME_NOW, NSEC_PER_SEC), dispatch_get_main_queue(), ^{
    [self runChecks:root];
  });
  return YES;
}
- (void)runChecks:(UIViewController *)root {
  NSMutableArray *failures = [NSMutableArray array];
  __block NSUInteger checks = 0;
  void (^check)(BOOL,NSString *) = ^(BOOL passed, NSString *name) {
    checks++; if (!passed) [failures addObject:name];
  };
  NSUserDefaults *defaults = NSUserDefaults.standardUserDefaults;
  for (NSString *key in @[@"StormNativePreferencesV3", @"touchPositionsMobileV3", @"touchPositionsXbox360V2"]) [defaults removeObjectForKey:key];
  StormControls *controls = [StormControls new];
  controls.translatesAutoresizingMaskIntoConstraints = NO;
  controls.playStationLabels = YES; controls.mobileLayout = YES; controls.hapticsEnabled = NO;
  controls.backgroundColor = [UIColor colorWithRed:.04 green:.06 blue:.10 alpha:1];
  [root.view addSubview:controls];
  [NSLayoutConstraint activateConstraints:@[
    [controls.leadingAnchor constraintEqualToAnchor:root.view.safeAreaLayoutGuide.leadingAnchor],
    [controls.trailingAnchor constraintEqualToAnchor:root.view.safeAreaLayoutGuide.trailingAnchor],
    [controls.topAnchor constraintEqualToAnchor:root.view.safeAreaLayoutGuide.topAnchor],
    [controls.bottomAnchor constraintEqualToAnchor:root.view.safeAreaLayoutGuide.bottomAnchor]]];
  [root.view layoutIfNeeded];
  __block uint32_t bits = 0; __block float leftTrigger = 0;
  controls.inputChanged = ^(uint32_t b,float lx,float ly,float rx,float ry,float lt,float rt) { bits = b; leftTrigger = lt; };
  UIButton *cross = (UIButton *)[controls viewWithTag:1];
  check([cross.currentTitle isEqual:@"✕"], @"PlayStation face label");
  [cross sendActionsForControlEvents:UIControlEventTouchDown];
  check(bits == storm::input::xbox360::a, @"Cross maps to logical A");
  UIButton *circle = (UIButton *)[controls viewWithTag:2];
  [circle sendActionsForControlEvents:UIControlEventTouchDown];
  check(bits == (storm::input::xbox360::a | storm::input::xbox360::b), @"Simultaneous face inputs");
  [cross sendActionsForControlEvents:UIControlEventTouchUpInside];
  check(bits == storm::input::xbox360::b, @"Independent face release");
  [circle sendActionsForControlEvents:UIControlEventTouchCancel];
  check(bits == 0, @"Cancelled touch releases input");
  UIButton *trigger = (UIButton *)[controls viewWithTag:7];
  [trigger sendActionsForControlEvents:UIControlEventTouchDown]; check(leftTrigger == 1, @"L2 analog trigger");
  [controls resetInput]; check(bits == 0 && leftTrigger == 0, @"Reset releases buttons and triggers");
  controls.editingControls = YES;
  [cross sendActionsForControlEvents:UIControlEventTouchDown]; check(bits == 0, @"Layout editing blocks game input");
  controls.editingControls = NO;
  for (NSNumber *mobile in @[@YES,@NO]) {
    controls.mobileLayout = mobile.boolValue;
    for (NSNumber *scale in @[@.65,@1,@1.4]) {
      controls.controlScale = scale.doubleValue; [controls layoutIfNeeded];
      for (UIView *item in controls.subviews) if (!item.hidden) {
        check(CGRectContainsRect(CGRectInset(controls.bounds,-.1,-.1),item.frame), @"Visible control inside screen");
      }
    }
  }
  controls.mobileLayout = YES; controls.controlScale = 1; controls.controlOpacity = .65; [controls layoutIfNeeded];
  check([controls viewWithTag:11].hidden && [controls viewWithTag:12].hidden, @"Mobile stick clicks use double tap");
  controls.playStationLabels = NO; check([cross.currentTitle isEqual:@"A"], @"Xbox labels remain available");
  controls.playStationLabels = YES;
  StormNativeOptions *settings = [StormNativeOptions new]; [settings loadViewIfNeeded];
  check([settings numberOfSectionsInTableView:settings.tableView] == 4, @"Settings sections");
  UITableViewCell *fps = [settings tableView:settings.tableView cellForRowAtIndexPath:[NSIndexPath indexPathForRow:5 inSection:1]];
  UISegmentedControl *rate = (UISegmentedControl *)fps.accessoryView;
  rate.selectedSegmentIndex = 1; [rate sendActionsForControlEvents:UIControlEventValueChanged];
  check([StormNativePreferences.values[@"fps"] integerValue] == 60, @"Settings persist user selection");
  check([StormNativePreferences.runtimeValues[@"gpu.frame_limit"] isEqual:@"60"], @"Selected FPS reaches runtime configuration");
  UITableViewCell *credit = [settings tableView:settings.tableView cellForRowAtIndexPath:[NSIndexPath indexPathForRow:0 inSection:3]];
  check([credit.textLabel.text containsString:@"MiquéiasF07"], @"Requested credit");
  [StormNativePreferences setValue:@30 forKey:@"fps"];
  NSDictionary *report = @{@"passed":@(failures.count == 0), @"checks":@(checks), @"failures":failures,
    @"scope":@"Actual UIKit controls and settings; programmatic input events", @"game_executed":@NO, @"physical_touch_tested":@NO};
  NSString *path = [NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject stringByAppendingPathComponent:@"controls-smoke.json"];
  [[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:nil] writeToFile:path atomically:YES];
  if ([NSProcessInfo.processInfo.arguments containsObject:@"--options"]) {
    UINavigationController *nav = [[UINavigationController alloc] initWithRootViewController:settings];
    nav.modalPresentationStyle = UIModalPresentationFullScreen;
    [root presentViewController:nav animated:NO completion:^{
      NSString *ready = [path.stringByDeletingLastPathComponent stringByAppendingPathComponent:@"options-ready.txt"];
      [@"Settings presentation completed" writeToFile:ready atomically:YES encoding:NSUTF8StringEncoding error:nil];
    }];
  }
}
@end
int main(int argc,char **argv) { @autoreleasepool { return UIApplicationMain(argc,argv,nil,NSStringFromClass(ControlsSmoke.class)); } }
