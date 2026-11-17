#import <UIKit/UIKit.h>
#import "Controls/StormControls.h"
#import "Native/StormNativeOptions.h"
#import "Native/StormNativePreferences.h"
#import "Native/StormNativeHome.h"
#import "Native/StormNativeMetrics.h"
#import "Localization/StormLocalization.h"
#import "Import/StormGameImporter.h"
#import "Native/StormNativeSaveProfiles.h"
#include <cmath>
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
  // Enter from a run-loop timer, not a main-queue block. The shortcut checks
  // pump the run loop and must let scheduled main-queue input steps run.
  [self performSelector:@selector(runChecks:) withObject:root afterDelay:1];
  return YES;
}
- (void)runChecks:(UIViewController *)root {
  NSMutableArray *failures = [NSMutableArray array];
  __block NSUInteger checks = 0;
  void (^check)(BOOL,NSString *) = ^(BOOL passed, NSString *name) {
    checks++; if (!passed) [failures addObject:name];
  };
  NSUserDefaults *defaults = NSUserDefaults.standardUserDefaults;
  for (NSString *key in @[@"StormNativePreferencesV3", @"touchPositionsMobileV3", @"touchPositionsXbox360V2", @"touchPositionsActionsV1"]) [defaults removeObjectForKey:key];
  [defaults removeObjectForKey:@"StormNativeRendererRevision"];
  [StormNativePreferences setValue:@"pt" forKey:@"appLanguage"];
  [StormNativePreferences setValue:@NO forKey:@"expandedMemory"];
  [StormNativePreferences setValue:@.8 forKey:@"opacity"];
  [StormNativePreferences prepareForLaunch];
  check([StormNativePreferences.values[@"clearCache"] boolValue], @"Renderer upgrade schedules cache removal");
  check([StormNativePreferences.values[@"opacity"] doubleValue] == .8, @"Renderer upgrade preserves touch preferences");
  [StormNativePreferences setValue:@NO forKey:@"clearCache"];
  [StormNativePreferences prepareForLaunch];
  check(![StormNativePreferences.values[@"clearCache"] boolValue], @"Cache migration runs once");
  for (NSNumber *profile in @[@YES,@NO]) {
    [StormNativePreferences setValue:profile forKey:@"compatible"];
    check([StormNativePreferences.runtimeValues[@"gpu.vulkan.render_target_path"] isEqual:@"host"], @"Both profiles avoid the regressed FSI path");
  }
  [StormNativePreferences setValue:@YES forKey:@"compatible"];
  check([StormNativePreferences.runtimeValues[@"gpu.vulkan.dynamic_rendering"] isEqual:@"false"], @"Safe profile uses classic render passes");
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
  controls.mobileActionLabels = YES;
  check([circle.currentTitle isEqual:@"Ataque"] && [cross.currentTitle isEqual:@"Pulo"], @"Mobile action names preserve manual inputs");
  for (NSNumber *scale in @[@.65,@1,@1.4]) {
    controls.controlScale = scale.doubleValue; [controls layoutIfNeeded];
    for (NSInteger tag=19;tag<=21;tag++) {
      UIView *shortcut = [controls viewWithTag:tag];
      check(!shortcut.hidden && CGRectContainsRect(CGRectInset(controls.bounds,-.1,-.1),shortcut.frame), @"Mobile shortcut remains on screen");
      for (NSInteger face=1;face<=8;face++) check(!CGRectIntersectsRect(shortcut.frame,[controls viewWithTag:face].frame), @"Shortcut avoids face and shoulder controls");
    }
  }
  controls.controlScale = 1; [controls layoutIfNeeded]; controls.shortcutPulseDuration = .08;
  NSMutableArray<NSNumber *> *events = [NSMutableArray array];
  __block uint32_t previous = 0;
  controls.inputChanged = ^(uint32_t b,float lx,float ly,float rx,float ry,float lt,float rt) {
    bits = b;
    if (b != previous) { [events addObject:@(b)]; previous=b; }
  };
  void (^pump)(NSTimeInterval) = ^(NSTimeInterval seconds) {
    NSDate *end = [NSDate dateWithTimeIntervalSinceNow:seconds];
    while (end.timeIntervalSinceNow > 0) [NSRunLoop.currentRunLoop runUntilDate:[NSDate dateWithTimeIntervalSinceNow:.01]];
    [NSRunLoop.currentRunLoop runUntilDate:[NSDate dateWithTimeIntervalSinceNow:.02]];
  };
  NSArray *sequences = @[@[@(storm::input::xbox360::y),@0,@(storm::input::xbox360::b),@0],
    @[@(storm::input::xbox360::y),@0,@(storm::input::xbox360::y),@0,@(storm::input::xbox360::b),@0],
    @[@(storm::input::xbox360::y),@0,@(storm::input::xbox360::a),@0]];
  for (NSInteger i=0;i<3;i++) {
    [controls resetInput]; [events removeAllObjects]; previous=0;
    [(UIButton *)[controls viewWithTag:19+i] sendActionsForControlEvents:UIControlEventTouchDown];
    pump(.08*([sequences[i] count]-1)+.07);
    check([events isEqual:sequences[i]] && bits==0, @"Shortcut emits the complete ordered input sequence and releases");
  }
  UIButton *ultimate = (UIButton *)[controls viewWithTag:20];
  [ultimate sendActionsForControlEvents:UIControlEventTouchDown];
  [NSNotificationCenter.defaultCenter postNotificationName:UIApplicationWillResignActiveNotification object:nil];
  pump(.5); check(bits==0, @"Background cancellation prevents delayed shortcut input");
  [NSNotificationCenter.defaultCenter postNotificationName:UIApplicationDidBecomeActiveNotification object:nil];
  [ultimate sendActionsForControlEvents:UIControlEventTouchDown];
  controls.editingControls=YES; pump(.5); check(bits==0, @"Control editing cancels all queued steps");
  controls.editingControls=NO;
  [ultimate sendActionsForControlEvents:UIControlEventTouchDown];
  [circle sendActionsForControlEvents:UIControlEventTouchDown];
  pump(.5); check(bits==storm::input::xbox360::b, @"Manual input overrides shortcut without being released by old steps");
  [circle sendActionsForControlEvents:UIControlEventTouchUpInside];
  [ultimate sendActionsForControlEvents:UIControlEventTouchDown];
  [ultimate sendActionsForControlEvents:UIControlEventTouchCancel];
  pump(.5); check(bits==0, @"Cancelled shortcut touch cannot leave inputs held");
  [defaults setObject:@{@"0":@[@.2,@.3]} forKey:@"touchPositionsMobileV3"];
  [defaults setObject:@{@"0":@[@.5,@.6]} forKey:@"touchPositionsActionsV1"];
  [StormControls resetSavedLayoutForMobile:YES actions:YES];
  check([defaults dictionaryForKey:@"touchPositionsMobileV3"]!=nil && [defaults dictionaryForKey:@"touchPositionsActionsV1"]==nil, @"Action layout reset preserves PlayStation mobile positions");
  [defaults removeObjectForKey:@"touchPositionsMobileV3"];
  StormNativeOptions *settings = [StormNativeOptions new]; [settings loadViewIfNeeded];
  check([settings numberOfSectionsInTableView:settings.tableView] == 4, @"Settings sections");
  UITableViewCell *fps = [settings tableView:settings.tableView cellForRowAtIndexPath:[NSIndexPath indexPathForRow:5 inSection:1]];
  UISegmentedControl *rate = (UISegmentedControl *)fps.accessoryView;
  rate.selectedSegmentIndex = 1; [rate sendActionsForControlEvents:UIControlEventValueChanged];
  check([StormNativePreferences.values[@"fps"] integerValue] == 60, @"Settings persist user selection");
  check([StormNativePreferences.runtimeValues[@"gpu.frame_limit"] isEqual:@"60"], @"Selected FPS reaches runtime configuration");
  UITableViewCell *profileCell = [settings tableView:settings.tableView cellForRowAtIndexPath:[NSIndexPath indexPathForRow:1 inSection:1]];
  UISegmentedControl *profile = (UISegmentedControl *)profileCell.accessoryView;
  profile.selectedSegmentIndex=1; [profile sendActionsForControlEvents:UIControlEventValueChanged];
  NSDictionary *fast = StormNativePreferences.runtimeValues;
  check([fast[@"gpu.xenos.readback_resolve"] isEqual:@"fast"] && [fast[@"gpu.xenos.readback_memexport_fast"] isEqual:@"true"], @"Fast profile selects buffered readbacks");
  check([fast[@"gpu.vulkan.render_target_path"] isEqual:@"host"] && [fast[@"gpu.vulkan.dynamic_rendering"] isEqual:@"false"] && [fast[@"runtime.title_memory_mb"] isEqual:@"512"], @"Fast profile preserves the working renderer and memory budget");
  profile.selectedSegmentIndex=3; [profile sendActionsForControlEvents:UIControlEventValueChanged];
  NSDictionary *performance = StormNativePreferences.runtimeValues;
  check([performance[@"gpu.xenos.readback_resolve"] isEqual:@"none"] && [performance[@"gpu.vulkan.readback_resolve"] isEqual:@"false"], @"Performance profile removes measured resolve readbacks");
  check([performance[@"gpu.xenos.readback_memexport"] isEqual:@"true"] && [performance[@"gpu.xenos.readback_memexport_fast"] isEqual:@"false"], @"Performance profile preserves current memexport data");
  check([performance[@"gpu.vulkan.render_target_path"] isEqual:@"host"] && [performance[@"gpu.vulkan.dynamic_rendering"] isEqual:@"false"] && [performance[@"gpu.xenos.direct_host_resolve"] isEqual:@"false"], @"Performance profile retains Safe renderer settings");
  profile.selectedSegmentIndex=0; [profile sendActionsForControlEvents:UIControlEventValueChanged];
  check([StormNativePreferences.runtimeValues[@"gpu.xenos.readback_resolve"] isEqual:@"full"] && [StormNativePreferences.runtimeValues[@"gpu.xenos.readback_memexport_fast"] isEqual:@"false"], @"Safe profile restores exact prior readback settings");
  StormNativeMetrics *metrics = [StormNativeMetrics new];
  [metrics addStatistics:@{@"fps":@(NAN),@"frameTimeMs":@1} overlayOpen:NO];
  [metrics addStatistics:@{@"fps":@0,@"frameTimeMs":@0} overlayOpen:NO];
  check([metrics.report[@"samples"] count]==0, @"Performance metrics reject startup zero and nonfinite FPS");
  for (NSInteger i=0;i<65;i++) [metrics addStatistics:@{@"fps":i%2 ? @10 : @20,@"frameTimeMs":@50,@"frames":@(i)} overlayOpen:NO];
  NSDictionary *measurement=metrics.report;
  check([measurement[@"samples"] count]==60 && [measurement[@"summaryExcludingOverlay"][@"meanFps"] doubleValue]==15, @"Performance history stays bounded and reports known mean");
  [metrics addStatistics:@{@"fps":@60,@"frameTimeMs":@16.6} overlayOpen:YES];
  check([metrics.report[@"summaryExcludingOverlay"][@"count"] integerValue]==59, @"Native settings overlay is excluded from FPS summary");
  check([NSJSONSerialization dataWithJSONObject:metrics.report options:0 error:nil]!=nil, @"Performance export is valid JSON");
  UITableViewCell *credit = [settings tableView:settings.tableView cellForRowAtIndexPath:[NSIndexPath indexPathForRow:0 inSection:3]];
  check([credit.textLabel.text containsString:@"MiquéiasF07"], @"Requested credit");
  // Actual UI in each supported language; switching app language must never
  // write the guest console's language setting or alter graphics preferences.
  NSDictionary *beforeLanguage = StormNativePreferences.runtimeValues;
  NSDictionary *expectedTitles = @{@"pt":@"Ajustes",@"en":@"Settings",@"es":@"Ajustes",@"fr":@"Réglages",@"de":@"Einstellungen",@"it":@"Impostazioni",@"ja":@"設定"};
  NSDictionary *expectedAttacks = @{@"pt":@"Ataque",@"en":@"Attack",@"es":@"Ataque",@"fr":@"Attaque",@"de":@"Angriff",@"it":@"Attacco",@"ja":@"攻撃"};
  NSDictionary *expectedPlay = @{@"pt":@"Jogar",@"en":@"Play",@"es":@"Jugar",@"fr":@"Jouer",@"de":@"Spielen",@"it":@"Gioca",@"ja":@"プレイ"};
  StormNativeHome *languageHome = [StormNativeHome new];
  for (NSString *language in @[@"pt",@"en",@"es",@"fr",@"de",@"it",@"ja"]) {
    [StormNativePreferences setValue:language forKey:@"appLanguage"];
    StormNativeOptions *translated = [StormNativeOptions new]; [translated loadViewIfNeeded];
    check([translated.title isEqual:expectedTitles[language]], @"Settings use selected app language");
    controls.mobileActionLabels = YES;
    check([circle.currentTitle isEqual:expectedAttacks[language]], @"Touch controls use selected app language");
    [languageHome refreshLanguage];
    check([languageHome.playButton.configuration.title isEqual:expectedPlay[language]], @"Existing home updates language immediately");
    check([StormNativePreferences.runtimeValues isEqual:beforeLanguage], @"App language leaves guest language and graphics untouched");
  }
  [StormNativePreferences setValue:@"unsupported" forKey:@"appLanguage"];
  check([StormAppLanguages() containsObject:StormAppLanguage()], @"Unknown app language falls back to supported system language");
  [StormNativePreferences setValue:@"pt" forKey:@"appLanguage"];
  controls.mobileActionLabels = YES;
  [StormNativePreferences setValue:@YES forKey:@"expandedMemory"];
  check([StormNativePreferences.runtimeValues[@"runtime.title_memory_mb"] isEqual:@"0"], @"Expanded memory removes the SDK title commit budget cap");
  check([StormNativePreferences.runtimeValues[@"gpu.xenos.texture_cache_memory_limit_hard"] isEqual:@"512"], @"Expanded memory permits a larger texture cache");
  [StormNativePreferences setValue:@NO forKey:@"expandedMemory"];
  check([StormNativePreferences.runtimeValues[@"runtime.title_memory_mb"] isEqual:@"512"], @"Disabling expanded memory restores the compatible title budget");
  // Migrate a tiny synthetic installation, checking the inode to establish
  // that no duplicate copy is made. Also exercise conflict and idempotence.
  NSFileManager *fm = NSFileManager.defaultManager;
  NSURL *oldGame = [[fm URLsForDirectory:NSApplicationSupportDirectory inDomains:NSUserDomainMask].firstObject URLByAppendingPathComponent:@"Game"];
  NSURL *newGame = StormGameImporter.gameURL;
  BOOL emptySandbox = ![fm fileExistsAtPath:oldGame.path] && ![fm fileExistsAtPath:newGame.path];
  check(emptySandbox, @"Migration test only uses a clean synthetic sandbox");
  if (emptySandbox) {
    NSError *error = nil;
    [fm createDirectoryAtURL:oldGame withIntermediateDirectories:YES attributes:nil error:&error];
    NSURL *oldFile = [oldGame URLByAppendingPathComponent:@"synthetic.txt"];
    [@"preserve-content" writeToURL:oldFile atomically:YES encoding:NSUTF8StringEncoding error:&error];
    NSNumber *inode = [fm attributesOfItemAtPath:oldFile.path error:&error][NSFileSystemFileNumber];
    BOOL migrated = [StormGameImporter prepareGameDirectory:&error];
    NSURL *newFile = [newGame URLByAppendingPathComponent:@"synthetic.txt"];
    check(migrated && !error && ![fm fileExistsAtPath:oldGame.path] && [inode isEqual:[fm attributesOfItemAtPath:newFile.path error:nil][NSFileSystemFileNumber]], @"Existing game moves atomically without duplicate content");
    check([[NSString stringWithContentsOfURL:newFile encoding:NSUTF8StringEncoding error:nil] isEqual:@"preserve-content"], @"Migration preserves file bytes");
    check([StormGameImporter prepareGameDirectory:&error], @"Game migration is idempotent");
    check([newGame.URLByDeletingLastPathComponent.path isEqual:[fm URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject.path], @"Game is in Files-visible Documents");
    [fm createDirectoryAtURL:oldGame withIntermediateDirectories:YES attributes:nil error:nil];
    error = nil;
    check(![StormGameImporter prepareGameDirectory:&error] && error && [fm fileExistsAtPath:oldGame.path] && [fm fileExistsAtPath:newFile.path], @"Migration refuses conflicting directories and preserves both");
    [fm removeItemAtURL:oldGame error:nil]; [fm removeItemAtURL:newGame error:nil];
  }
  [StormNativePreferences setValue:@30 forKey:@"fps"];
  NSURL *normalUser = StormNativeSaveProfiles.normalURL, *cheatUser = StormNativeSaveProfiles.cheatURL, *activeUser = StormNativeSaveProfiles.activeURL;
  BOOL cleanProfiles = ![fm fileExistsAtPath:normalUser.path] && ![fm fileExistsAtPath:cheatUser.path] && ![fm fileExistsAtPath:activeUser.path];
  check(cleanProfiles, @"Save profile test requires clean synthetic sandbox");
  if (cleanProfiles) {
    NSError *error = nil;
    [fm createDirectoryAtURL:normalUser withIntermediateDirectories:YES attributes:nil error:&error];
    NSURL *normalFile = [normalUser URLByAppendingPathComponent:@"synthetic-save.txt"];
    [@"normal-progress" writeToURL:normalFile atomically:YES encoding:NSUTF8StringEncoding error:&error];
    check([StormNativeSaveProfiles selectCheats:YES error:&error] && !error, @"Cheat profile clones existing progress before use");
    NSURL *activeFile = [activeUser URLByAppendingPathComponent:@"synthetic-save.txt"];
    check([[NSString stringWithContentsOfURL:activeFile encoding:NSUTF8StringEncoding error:nil] isEqual:@"normal-progress"], @"Selected alias reaches cloned save");
    [@"cheated-progress" writeToURL:activeFile atomically:YES encoding:NSUTF8StringEncoding error:&error];
    check([[NSString stringWithContentsOfURL:normalFile encoding:NSUTF8StringEncoding error:nil] isEqual:@"normal-progress"], @"Cheat save writes preserve original bytes");
    check([StormNativeSaveProfiles selectCheats:NO error:&error] && [[NSString stringWithContentsOfURL:activeFile encoding:NSUTF8StringEncoding error:nil] isEqual:@"normal-progress"], @"Disabling cheat mode restores normal progress");
    check([StormNativeSaveProfiles selectCheats:YES error:&error] && [[NSString stringWithContentsOfURL:activeFile encoding:NSUTF8StringEncoding error:nil] isEqual:@"cheated-progress"], @"Re-enabling cheat mode preserves its own progress");
    [fm removeItemAtURL:activeUser error:nil];
    [@"preserve-conflict" writeToURL:activeUser atomically:YES encoding:NSUTF8StringEncoding error:nil];
    error = nil;
    check(![StormNativeSaveProfiles selectCheats:NO error:&error] && error && [[NSString stringWithContentsOfURL:activeUser encoding:NSUTF8StringEncoding error:nil] isEqual:@"preserve-conflict"], @"Save profile selection refuses conflicting files");
    [fm removeItemAtURL:activeUser error:nil]; [fm removeItemAtURL:normalUser error:nil]; [fm removeItemAtURL:cheatUser error:nil];
  }
  StormNativeHome *home = [[StormNativeHome alloc] initWithFrame:root.view.bounds];
  home.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
  [root.view addSubview:home]; [home layoutIfNeeded];
  check(home.cheatSwitch != nil && [home.cheatSwitch.accessibilityIdentifier isEqual:@"home-cheats"], @"Home exposes the cheat toggle");
  check(!home.playButton.enabled && !home.importButton.enabled, @"Home waits for installed-file validation");
  for (UIButton *button in @[home.playButton,home.importButton,home.optionsButton]) {
    CGRect frame = [button convertRect:button.bounds toView:home];
    check(CGRectContainsRect(CGRectInset(home.bounds,-.1,-.1),frame) && frame.size.height >= 44, @"Home action stays visible with a 44-point touch target");
  }
  __block NSUInteger requests = 0;
  [home.playButton addAction:[UIAction actionWithHandler:^(UIAction *action) { requests++; }] forControlEvents:UIControlEventTouchUpInside];
  home.playButton.enabled = YES;
  [home.playButton sendActionsForControlEvents:UIControlEventTouchUpInside];
  check(requests == 1, @"Home play action remains wired");
  home.statusLabel.text = @"Tudo pronto para jogar. Seus arquivos estão instalados.";
  home.importButton.enabled = YES;
  if (![NSProcessInfo.processInfo.arguments containsObject:@"--home"]) [home removeFromSuperview];
  NSDictionary *report = @{@"passed":@(failures.count == 0), @"checks":@(checks), @"failures":failures,
    @"scope":@"Actual UIKit controls and settings; programmatic input events", @"game_executed":@NO, @"physical_touch_tested":@NO};
  NSString *path = [NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject stringByAppendingPathComponent:@"controls-smoke.json"];
  [[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:nil] writeToFile:path atomically:YES];
  if ([NSProcessInfo.processInfo.arguments containsObject:@"--home"]) {
    [controls removeFromSuperview];
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 2*NSEC_PER_SEC), dispatch_get_main_queue(), ^{
      NSString *ready = [path.stringByDeletingLastPathComponent stringByAppendingPathComponent:@"home-ready.txt"];
      [@"Home layout completed" writeToFile:ready atomically:YES encoding:NSUTF8StringEncoding error:nil];
    });
  }
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
