#import "StormNativeSession.h"
#import "Controls/StormControls.h"
#import "Import/StormGameImporter.h"
#import "StormNativePreferences.h"
#import "StormNativeOptions.h"
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>
#import <os/proc.h>
#include <SDL3/SDL.h>
#include <rex/settings_registry.h>
#include <algorithm>
#include <cmath>

@interface StormNativeSession () <UIDocumentPickerDelegate>
@property(nonatomic, weak) UIWindow *window;
@property(nonatomic) UIView *panel;
@property(nonatomic) UILabel *status;
@property(nonatomic) UIButton *importButton;
@property(nonatomic) UIButton *playButton;
@property(nonatomic) UIButton *menuButton;
@property(nonatomic) UILabel *statisticsLabel;
@property(nonatomic) NSTimer *statisticsTimer;
@property(nonatomic) StormGameImporter *importer;
@property(nonatomic) StormControls *controls;
@property(nonatomic, readwrite) BOOL ready;
@property(nonatomic, readwrite) BOOL launchRequested;
@property(nonatomic) BOOL invalidated;
@property(nonatomic) BOOL fatalFailure;
@property(nonatomic) BOOL inputBlocked;
@property(nonatomic) BOOL editingPreview;
@end

@implementation StormNativeSession {
  SDL_JoystickID _padID;
  SDL_Joystick *_pad;
}
- (instancetype)initWithWindow:(UIWindow *)window {
  if (!(self = [super init])) return nil;
  _window = window;
  _importer = [StormGameImporter new];
  _panel = [UIView new];
  _panel.backgroundColor = [UIColor colorWithRed:.035 green:.045 blue:.075 alpha:1];
  _panel.translatesAutoresizingMaskIntoConstraints = NO;
  UIView *root = window.rootViewController.view;
  [root addSubview:_panel];
  [NSLayoutConstraint activateConstraints:@[
    [_panel.leadingAnchor constraintEqualToAnchor:root.leadingAnchor],
    [_panel.trailingAnchor constraintEqualToAnchor:root.trailingAnchor],
    [_panel.topAnchor constraintEqualToAnchor:root.topAnchor],
    [_panel.bottomAnchor constraintEqualToAnchor:root.bottomAnchor]]];
  UILabel *title = [UILabel new];
  title.text = @"STORM REVOLUTION";
  title.textColor = UIColor.whiteColor;
  title.font = [UIFont systemFontOfSize:28 weight:UIFontWeightHeavy];
  title.adjustsFontSizeToFitWidth = YES;
  UILabel *subtitle = [UILabel new];
  subtitle.text = @"Sua arena. Seu controle.";
  subtitle.font = [UIFont systemFontOfSize:16 weight:UIFontWeightMedium];
  subtitle.textColor = [UIColor colorWithRed:.59 green:.69 blue:.84 alpha:1];
  _status = [UILabel new];
  _status.text = @"Verificando os arquivos instalados…";
  _status.textColor = [UIColor colorWithWhite:.78 alpha:1];
  _status.font = [UIFont systemFontOfSize:13];
  _status.numberOfLines = 0;
  _importButton = [UIButton buttonWithType:UIButtonTypeSystem];
  [_importButton setTitle:@"Importar meu ZIP do jogo" forState:UIControlStateNormal];
  [_importButton addTarget:self action:@selector(chooseZIP) forControlEvents:UIControlEventTouchUpInside];
  _importButton.enabled = NO;
  _playButton = [UIButton buttonWithType:UIButtonTypeSystem];
  UIButtonConfiguration *playConfiguration = [UIButtonConfiguration filledButtonConfiguration];
  playConfiguration.title = @"Jogar";
  playConfiguration.image = [UIImage systemImageNamed:@"play.fill"];
  playConfiguration.imagePadding = 10;
  playConfiguration.baseBackgroundColor = [UIColor colorWithRed:.42 green:.65 blue:1 alpha:1];
  playConfiguration.baseForegroundColor = [UIColor colorWithWhite:.04 alpha:1];
  playConfiguration.cornerStyle = UIButtonConfigurationCornerStyleLarge;
  _playButton.configuration = playConfiguration;
  _playButton.enabled = NO;
  [_playButton addTarget:self action:@selector(play) forControlEvents:UIControlEventTouchUpInside];
  UIButton *options = [UIButton buttonWithType:UIButtonTypeSystem];
  [options setTitle:@"Controles e gráficos" forState:UIControlStateNormal];
  [options addTarget:self action:@selector(showOptions) forControlEvents:UIControlEventTouchUpInside];
  UIStackView *actions = [[UIStackView alloc] initWithArrangedSubviews:@[_playButton,options,_importButton]];
  actions.axis = UILayoutConstraintAxisHorizontal; actions.spacing = 18;
  UILabel *credit = [UILabel new];
  credit.text = @"Créditos • MiquéiasF07";
  credit.font = [UIFont systemFontOfSize:12 weight:UIFontWeightMedium];
  credit.textColor = [UIColor colorWithWhite:.55 alpha:1];
  UIStackView *stack = [[UIStackView alloc] initWithArrangedSubviews:@[title,subtitle,_status,actions,credit]];
  stack.axis = UILayoutConstraintAxisVertical;
  stack.spacing = 18;
  stack.translatesAutoresizingMaskIntoConstraints = NO;
  [_panel addSubview:stack];
  [NSLayoutConstraint activateConstraints:@[
    [stack.centerYAnchor constraintEqualToAnchor:_panel.centerYAnchor],
    [stack.leadingAnchor constraintEqualToAnchor:_panel.safeAreaLayoutGuide.leadingAnchor constant:32],
    [stack.trailingAnchor constraintEqualToAnchor:_panel.safeAreaLayoutGuide.trailingAnchor constant:-32]]];
  __weak StormNativeSession *weakSelf = self;
  [StormGameImporter validateInstalledWithCompletion:^(NSDictionary *validation, NSError *error) {
    StormNativeSession *session = weakSelf;
    if (!session || session.invalidated) return;
    if (session.fatalFailure) return;
    session.ready = !error && [validation[@"reference_matches"] boolValue];
    session.status.text = session.ready ? @"Jogo instalado. Prepare os ajustes e entre na arena." : @"Importe o ZIP completo da sua cópia para começar.";
    session.playButton.enabled = session.ready;
    session.importButton.enabled = YES;
  }];
  _menuButton = [UIButton buttonWithType:UIButtonTypeSystem];
  UIButtonConfiguration *menuConfiguration = [UIButtonConfiguration tintedButtonConfiguration];
  menuConfiguration.image = [UIImage systemImageNamed:@"slider.horizontal.3"];
  menuConfiguration.cornerStyle = UIButtonConfigurationCornerStyleCapsule;
  menuConfiguration.baseForegroundColor = UIColor.whiteColor;
  menuConfiguration.baseBackgroundColor = [UIColor colorWithWhite:.08 alpha:.7];
  _menuButton.configuration = menuConfiguration;
  _menuButton.accessibilityLabel = @"Abrir ajustes de controles e gráficos";
  _menuButton.translatesAutoresizingMaskIntoConstraints = NO;
  _menuButton.hidden = YES;
  [_menuButton addTarget:self action:@selector(menuPressed) forControlEvents:UIControlEventTouchUpInside];
  [root addSubview:_menuButton];
  _statisticsLabel = [UILabel new];
  _statisticsLabel.font = [UIFont monospacedDigitSystemFontOfSize:11 weight:UIFontWeightSemibold];
  _statisticsLabel.textColor = [UIColor colorWithRed:.56 green:.94 blue:.78 alpha:1];
  _statisticsLabel.backgroundColor = [UIColor colorWithWhite:0 alpha:.55];
  _statisticsLabel.layer.cornerRadius = 7; _statisticsLabel.clipsToBounds = YES;
  _statisticsLabel.textAlignment = NSTextAlignmentCenter;
  _statisticsLabel.translatesAutoresizingMaskIntoConstraints = NO;
  _statisticsLabel.hidden = YES;
  [root addSubview:_statisticsLabel];
  [NSLayoutConstraint activateConstraints:@[
    [_menuButton.trailingAnchor constraintEqualToAnchor:root.safeAreaLayoutGuide.trailingAnchor constant:-8],
    [_menuButton.topAnchor constraintEqualToAnchor:root.safeAreaLayoutGuide.topAnchor constant:6],
    [_menuButton.heightAnchor constraintEqualToConstant:34],
    [_statisticsLabel.leadingAnchor constraintEqualToAnchor:root.safeAreaLayoutGuide.leadingAnchor constant:8],
    [_statisticsLabel.topAnchor constraintEqualToAnchor:root.safeAreaLayoutGuide.topAnchor constant:6],
    [_statisticsLabel.widthAnchor constraintEqualToConstant:112],[_statisticsLabel.heightAnchor constraintEqualToConstant:23]]];
  [NSNotificationCenter.defaultCenter addObserver:self selector:@selector(memoryWarning:) name:UIApplicationDidReceiveMemoryWarningNotification object:nil];
  _statisticsTimer = [NSTimer scheduledTimerWithTimeInterval:2 repeats:YES block:^(NSTimer *timer) { [weakSelf refreshStatistics]; }];
  [self writeSessionReport:@"home"];
  return self;
}
- (void)play { if (self.ready && !self.fatalFailure) self.launchRequested = YES; }
- (void)chooseZIP {
  UIDocumentPickerViewController *picker = [[UIDocumentPickerViewController alloc]
      initForOpeningContentTypes:@[UTTypeZIP] asCopy:NO];
  picker.delegate = self;
  [self.window.rootViewController presentViewController:picker animated:YES completion:nil];
}
- (void)documentPicker:(UIDocumentPickerViewController *)controller didPickDocumentsAtURLs:(NSArray<NSURL *> *)urls {
  if (!urls.count || self.invalidated) return;
  self.importButton.enabled = NO;
  self.playButton.enabled = NO;
  __weak StormNativeSession *weakSelf = self;
  [self.importer importZIPAtURL:urls.firstObject progress:^(double fraction, NSString *message) {
    StormNativeSession *session = weakSelf;
    if (!session || session.invalidated) return;
    session.status.text = fraction >= 1 ? @"Arquivos preparados. Verificando…" : message;
  } completion:^(NSDictionary *validation, NSError *error) {
    StormNativeSession *session = weakSelf;
    if (!session || session.invalidated) return;
    session.ready = !error && [validation[@"reference_matches"] boolValue];
    session.status.text = session.ready ? @"Jogo instalado. Toque em Jogar." : (error.localizedDescription ?: @"A cópia importada não corresponde ao executável suportado.");
    session.playButton.enabled = session.ready;
    session.importButton.enabled = YES;
  }];
}
- (void)updateButtons:(uint32_t)buttons lx:(float)lx ly:(float)ly rx:(float)rx ry:(float)ry lt:(float)lt rt:(float)rt {
  if (!_pad) return;
  static const uint32_t masks[] = {0x1000,0x2000,0x4000,0x8000,0x20,0,0x10,0x40,0x80,0x100,0x200,1,2,4,8};
  for (int i = 0; i < 15; ++i) SDL_SetJoystickVirtualButton(_pad, i, (buttons & masks[i]) != 0);
  const float axes[] = {lx,-ly,rx,-ry};
  for (int i = 0; i < 4; ++i)
    SDL_SetJoystickVirtualAxis(_pad, i, (Sint16)std::lround(std::clamp(axes[i], -1.0f, 1.0f) * 32767));
  SDL_SetJoystickVirtualAxis(_pad, 4, (Sint16)(std::lround(std::clamp(lt, 0.0f, 1.0f) * 65535) - 32768));
  SDL_SetJoystickVirtualAxis(_pad, 5, (Sint16)(std::lround(std::clamp(rt, 0.0f, 1.0f) * 65535) - 32768));
}
- (BOOL)attachControls {
  SDL_VirtualJoystickDesc description;
  SDL_INIT_INTERFACE(&description);
  description.type = SDL_JOYSTICK_TYPE_GAMEPAD;
  description.naxes = 6;
  description.nbuttons = 15;
  description.axis_mask = (1u << 6) - 1;
  description.button_mask = (1u << 15) - 1;
  description.name = "Storm Touch";
  _padID = SDL_AttachVirtualJoystick(&description);
  if (_padID) _pad = SDL_OpenJoystick(_padID);
  if (!_pad) {
    [self showFailure:[NSString stringWithFormat:@"Falha ao criar controles: %s", SDL_GetError()]];
    return NO;
  }
  [self updateButtons:0 lx:0 ly:0 rx:0 ry:0 lt:0 rt:0];
  self.controls = [StormControls new];
  self.controls.backgroundColor = UIColor.clearColor;
  self.controls.layer.cornerRadius = 0;
  [self applyControlPreferences];
  self.controls.translatesAutoresizingMaskIntoConstraints = NO;
  __weak StormNativeSession *weakSelf = self;
  self.controls.inputChanged = ^(uint32_t b, float lx, float ly, float rx, float ry, float lt, float rt) {
    [weakSelf updateButtons:b lx:lx ly:ly rx:rx ry:ry lt:lt rt:rt];
  };
  UIView *root = self.window.rootViewController.view;
  [root addSubview:self.controls];
  [NSLayoutConstraint activateConstraints:@[
    [self.controls.leadingAnchor constraintEqualToAnchor:root.safeAreaLayoutGuide.leadingAnchor],
    [self.controls.trailingAnchor constraintEqualToAnchor:root.safeAreaLayoutGuide.trailingAnchor],
    [self.controls.topAnchor constraintEqualToAnchor:root.safeAreaLayoutGuide.topAnchor],
    [self.controls.bottomAnchor constraintEqualToAnchor:root.safeAreaLayoutGuide.bottomAnchor]]];
  [self.panel removeFromSuperview];
  [root bringSubviewToFront:self.menuButton];
  [root bringSubviewToFront:self.statisticsLabel];
  self.menuButton.hidden = NO;
  [self writeSessionReport:@"title-launch"];
  return YES;
}
- (void)applyControlPreferences {
  NSDictionary *v = StormNativePreferences.values;
  self.controls.playStationLabels = [v[@"playstation"] boolValue];
  self.controls.mobileLayout = [v[@"mobile"] boolValue];
  self.controls.controlScale = [v[@"scale"] doubleValue];
  self.controls.controlOpacity = [v[@"opacity"] doubleValue];
  self.controls.hapticsEnabled = [v[@"haptics"] boolValue];
  self.controls.hidden = ![v[@"touch"] boolValue];
  self.statisticsLabel.hidden = !self.launchRequested || ![v[@"stats"] boolValue];
}
- (void)setInputBlocked:(BOOL)blocked {
  if (_inputBlocked == blocked) return;
  _inputBlocked = blocked;
  [self.controls resetInput];
  if (self.overlayChanged) self.overlayChanged(blocked);
}
- (void)menuPressed {
  if (self.controls.editingControls) {
    self.controls.editingControls = NO;
    [self.menuButton setTitle:nil forState:UIControlStateNormal];
    self.inputBlocked = NO;
    if (self.editingPreview) {
      [self.controls removeFromSuperview]; self.controls = nil;
      self.editingPreview = NO;
      self.panel.hidden = NO;
      self.menuButton.hidden = YES;
    }
  } else [self showOptions];
}
- (void)showOptions {
  if (self.invalidated || self.window.rootViewController.presentedViewController) return;
  self.inputBlocked = YES;
  StormNativeOptions *options = [StormNativeOptions new];
  __weak StormNativeSession *weakSelf = self;
  options.closed = ^{ weakSelf.inputBlocked = NO; };
  options.changed = ^(NSString *key) {
    StormNativeSession *session = weakSelf;
    if (!session || session.invalidated) return;
    [session applyControlPreferences];
    NSDictionary *values = StormNativePreferences.runtimeValues;
    NSArray *live = @[@"gpu.xenos.present_letterbox", @"gpu.frame_limit", @"gpu.xenos.async_shader_compilation", @"gpu.vulkan.async_skip_incomplete_frames"];
    for (NSString *name in live) {
      auto changed = rex::GetSettingsRegistry().SetText(rex::SettingLayer::kRuntime,name.UTF8String,[values[name] UTF8String]);
      if (!changed) NSLog(@"StormNative settings: %s", changed.error().GetDescription().c_str());
    }
    [session writeSessionReport:@"settings-changed"];
  };
  options.editControls = ^{
    StormNativeSession *session = weakSelf;
    if (!session || session.invalidated) return;
    [StormNativePreferences setValue:@YES forKey:@"touch"];
    if (!session.controls) {
      session.editingPreview = YES;
      session.panel.hidden = YES;
      session.controls = [StormControls new];
      session.controls.backgroundColor = UIColor.clearColor;
      session.controls.layer.cornerRadius = 0;
      session.controls.translatesAutoresizingMaskIntoConstraints = NO;
      UIView *root = session.window.rootViewController.view;
      [root addSubview:session.controls];
      [NSLayoutConstraint activateConstraints:@[
        [session.controls.leadingAnchor constraintEqualToAnchor:root.safeAreaLayoutGuide.leadingAnchor],
        [session.controls.trailingAnchor constraintEqualToAnchor:root.safeAreaLayoutGuide.trailingAnchor],
        [session.controls.topAnchor constraintEqualToAnchor:root.safeAreaLayoutGuide.topAnchor],
        [session.controls.bottomAnchor constraintEqualToAnchor:root.safeAreaLayoutGuide.bottomAnchor]]];
      [root bringSubviewToFront:session.menuButton];
    }
    [session applyControlPreferences];
    session.controls.editingControls = YES;
    session.menuButton.hidden = NO;
    [session.menuButton setTitle:@"Concluir" forState:UIControlStateNormal];
  };
  options.resetControls = ^{ [weakSelf.controls resetLayout]; };
  options.shareLogs = ^(UIViewController *presenter) { [weakSelf shareLogsFrom:presenter]; };
  UINavigationController *navigation = [[UINavigationController alloc] initWithRootViewController:options];
  navigation.overrideUserInterfaceStyle = UIUserInterfaceStyleDark;
  navigation.modalInPresentation = YES;
  [self.window.rootViewController presentViewController:navigation animated:YES completion:nil];
}
- (NSURL *)logsURL {
  return [[NSFileManager.defaultManager URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject URLByAppendingPathComponent:@"Logs"];
}
- (void)writeSessionReport:(NSString *)phase {
  NSURL *folder = [self logsURL];
  [NSFileManager.defaultManager createDirectoryAtURL:folder withIntermediateDirectories:YES attributes:nil error:nil];
  NSDictionary *report = @{@"phase":phase, @"os":UIDevice.currentDevice.systemVersion,
    @"appBuild":[NSBundle.mainBundle objectForInfoDictionaryKey:@"CFBundleVersion"] ?: @"unknown",
    @"memoryAvailableMB":@(os_proc_available_memory() / (1024 * 1024)),
    @"preferences":StormNativePreferences.values, @"runtimeRequested":StormNativePreferences.runtimeValues,
    @"updatedAt":NSDate.date.description};
  NSData *data = [NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:nil];
  [data writeToURL:[folder URLByAppendingPathComponent:@"native-session.json"] atomically:YES];
}
- (void)refreshStatistics {
  if (self.invalidated) return;
  if (self.frameStatistics) {
    NSDictionary *stats = self.frameStatistics();
    self.statisticsLabel.text = [NSString stringWithFormat:@"%.1f FPS", [stats[@"fps"] doubleValue]];
  }
  [self writeSessionReport:self.launchRequested ? @"title-running" : @"home"];
}
- (void)memoryWarning:(NSNotification *)notification { [self writeSessionReport:@"memory-warning"]; }
- (void)shareLogsFrom:(UIViewController *)presenter {
  [self writeSessionReport:@"export"];
  NSArray<NSURL *> *files = [NSFileManager.defaultManager contentsOfDirectoryAtURL:[self logsURL] includingPropertiesForKeys:nil options:0 error:nil];
  NSMutableArray *items = [NSMutableArray array];
  for (NSURL *url in files) if ([url.pathExtension.lowercaseString isEqual:@"log"] || [url.lastPathComponent isEqual:@"native-session.json"]) [items addObject:url];
  if (!items.count) return;
  UIActivityViewController *activity = [[UIActivityViewController alloc] initWithActivityItems:items applicationActivities:nil];
  activity.popoverPresentationController.sourceView = presenter.view;
  activity.popoverPresentationController.sourceRect = CGRectMake(presenter.view.bounds.size.width/2, presenter.view.bounds.size.height/2, 1, 1);
  [presenter presentViewController:activity animated:YES completion:nil];
}
- (void)showFailure:(NSString *)message {
  self.ready = NO;
  self.fatalFailure = YES;
  self.importButton.enabled = NO;
  self.status.text = message;
  [self.controls removeFromSuperview];
  if (!self.panel.superview) [self.window.rootViewController.view addSubview:self.panel];
}
- (void)invalidate {
  self.invalidated = YES;
  [self.statisticsTimer invalidate]; self.statisticsTimer = nil;
  [NSNotificationCenter.defaultCenter removeObserver:self];
  self.inputBlocked = NO;
  self.overlayChanged = nil;
  self.frameStatistics = nil;
  [self.importer cancel];
  [self.controls resetInput];
  self.controls.inputChanged = nil;
  [self.controls removeFromSuperview];
  [self.panel removeFromSuperview];
  [self.menuButton removeFromSuperview];
  [self.statisticsLabel removeFromSuperview];
  if (_pad) SDL_CloseJoystick(_pad);
  _pad = nullptr;
  if (_padID) SDL_DetachVirtualJoystick(_padID);
  _padID = 0;
}
@end
