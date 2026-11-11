#import "App/StormViewController.h"
#import "Metal/StormMetalView.h"
#import "Controls/StormControls.h"
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>
#import <CommonCrypto/CommonDigest.h>
#include "storm_runtime.h"
#include <cstring>

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

@implementation StormViewController {
  StormRuntime *_runtime;
  StormMetalView *_metal;
  StormControls *_controls;
  UITextView *_logs;
  UILabel *_status;
  UIButton *_importButton;
  UIButton *_launchButton;
  BOOL _identityMatches;
  BOOL _runtimeTestPassed;
  BOOL _smoke;
}
- (void)viewDidLoad {
  [super viewDidLoad];
  self.view.backgroundColor = UIColor.systemBackgroundColor;
  _runtime = storm_runtime_create();
  _runtimeTestPassed = storm_runtime_self_test() == 0;
  _smoke = [NSProcessInfo.processInfo.arguments containsObject:@"--smoke-test"];
  UIScrollView *scroll = [[UIScrollView alloc] init];
  scroll.canCancelContentTouches = NO;
  scroll.delaysContentTouches = NO;
  scroll.translatesAutoresizingMaskIntoConstraints = NO;
  [self.view addSubview:scroll];
  UIStackView *stack = [[UIStackView alloc] init];
  stack.axis = UILayoutConstraintAxisVertical;
  stack.spacing = 10;
  stack.translatesAutoresizingMaskIntoConstraints = NO;
  [scroll addSubview:stack];
  [NSLayoutConstraint activateConstraints:@[
    [scroll.topAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.topAnchor],
    [scroll.bottomAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.bottomAnchor],
    [scroll.leadingAnchor constraintEqualToAnchor:self.view.leadingAnchor constant:12],
    [scroll.trailingAnchor constraintEqualToAnchor:self.view.trailingAnchor constant:-12],
    [stack.topAnchor constraintEqualToAnchor:scroll.contentLayoutGuide.topAnchor constant:10],
    [stack.bottomAnchor constraintEqualToAnchor:scroll.contentLayoutGuide.bottomAnchor constant:-10],
    [stack.leadingAnchor constraintEqualToAnchor:scroll.contentLayoutGuide.leadingAnchor],
    [stack.trailingAnchor constraintEqualToAnchor:scroll.contentLayoutGuide.trailingAnchor],
    [stack.widthAnchor constraintEqualToAnchor:scroll.frameLayoutGuide.widthAnchor]
  ]];
  UILabel *title = [[UILabel alloc] init];
  title.text = @"STORM REVOLUTION · infraestrutura";
  title.font = [UIFont preferredFontForTextStyle:UIFontTextStyleHeadline];
  [stack addArrangedSubview:title];
  _status = [[UILabel alloc] init];
  _status.numberOfLines = 0;
  _status.text = @"O jogo ainda não executa. O triângulo abaixo testa apenas Metal. Sem medição de FPS do jogo.";
  [stack addArrangedSubview:_status];
  _metal = [[StormMetalView alloc] initWithFrame:CGRectZero];
  [_metal.heightAnchor constraintEqualToConstant:180].active = YES;
  [stack addArrangedSubview:_metal];
  __weak StormViewController *weakSelf = self;
  _metal.diagnosticCompletion = ^(BOOL passed, NSString *message) {
    StormViewController *self = weakSelf;
    if (!self) return;
    [self log:message];
    if (self->_smoke) {
      NSDictionary *result = @{@"runtime_self_test":@(self->_runtimeTestPassed), @"metal_command_completed":@(passed),
        @"game_executed":@NO, @"pixel_comparison_performed":@NO};
      NSURL *documents = [NSFileManager.defaultManager URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject;
      NSData *json = [NSJSONSerialization dataWithJSONObject:result options:NSJSONWritingPrettyPrinted error:nil];
      NSError *error = nil;
      if (![json writeToURL:[documents URLByAppendingPathComponent:@"smoke-result.json"] options:NSDataWritingAtomic error:&error]) [self log:error.localizedDescription];
    }
  };
  _importButton = [self button:@"Importar pasta do jogo pelo Arquivos" action:@selector(importGame)];
  _launchButton = [self button:@"Iniciar jogo (AOT ainda indisponível)" action:@selector(launchGame)];
  [stack addArrangedSubview:_importButton];
  [stack addArrangedSubview:_launchButton];
  UISegmentedControl *fps = [[UISegmentedControl alloc] initWithItems:@[@"Qualidade · 30", @"Desempenho · 60"]];
  fps.selectedSegmentIndex = [NSUserDefaults.standardUserDefaults integerForKey:@"performanceMode"];
  [fps addTarget:self action:@selector(changeMode:) forControlEvents:UIControlEventValueChanged];
  [stack addArrangedSubview:fps];
  [self changeMode:fps];
  UISwitch *adaptive = [[UISwitch alloc] init];
  adaptive.on = [NSUserDefaults.standardUserDefaults boolForKey:@"adaptiveResolution"];
  _metal.adaptiveResolution = adaptive.on;
  [adaptive addTarget:self action:@selector(changeAdaptive:) forControlEvents:UIControlEventValueChanged];
  [stack addArrangedSubview:[self row:@"Resolução adaptativa (diagnóstico)" control:adaptive]];
  _controls = [[StormControls alloc] initWithFrame:CGRectZero];
  [_controls.heightAnchor constraintEqualToConstant:220].active = YES;
  _controls.inputChanged = ^(uint32_t buttons, float lx, float ly, float rx, float ry, float lt, float rt) {
    StormViewController *self = weakSelf;
    if (self && self->_runtime) storm_runtime_set_input(self->_runtime, buttons, lx, ly, rx, ry, lt, rt);
  };
  [stack addArrangedSubview:_controls];
  UISwitch *edit = [[UISwitch alloc] init];
  [edit addTarget:self action:@selector(changeEdit:) forControlEvents:UIControlEventValueChanged];
  [stack addArrangedSubview:[self row:@"Arrastar controles para reposicionar" control:edit]];
  for (NSUInteger i = 0; i < 2; ++i) {
    UISlider *slider = [[UISlider alloc] init];
    slider.tag = i;
    slider.minimumValue = i == 0 ? .65 : .2;
    slider.maximumValue = i == 0 ? 1.4 : 1;
    NSString *key = i == 0 ? @"controlScale" : @"controlOpacity";
    NSNumber *saved = [NSUserDefaults.standardUserDefaults objectForKey:key];
    slider.value = saved ? saved.floatValue : (i == 0 ? 1 : .7);
    [slider.widthAnchor constraintEqualToConstant:160].active = YES;
    [slider addTarget:self action:@selector(changeControl:) forControlEvents:UIControlEventValueChanged];
    [stack addArrangedSubview:[self row:i == 0 ? @"Tamanho dos controles" : @"Opacidade dos controles" control:slider]];
    [self changeControl:slider];
  }
  UILabel *audio = [[UILabel alloc] init];
  audio.numberOfLines = 0;
  audio.text = @"Áudio: backend/XMA não implementados. Comandos: A/B/X/Y e ombros preservam o layout Xbox; ações do jogo ainda não verificadas.";
  audio.font = [UIFont preferredFontForTextStyle:UIFontTextStyleFootnote];
  [stack addArrangedSubview:audio];
  _logs = [[UITextView alloc] init];
  _logs.editable = NO;
  _logs.font = [UIFont monospacedSystemFontOfSize:11 weight:UIFontWeightRegular];
  [_logs.heightAnchor constraintEqualToConstant:180].active = YES;
  [stack addArrangedSubview:_logs];
  [self log:_runtimeTestPassed ? @"Runtime self-test passed. This does not execute game code." : @"Runtime self-test FAILED"];
  if (!_runtime) [self log:@"Runtime allocation failed"];
  [NSNotificationCenter.defaultCenter addObserver:self selector:@selector(suspend:) name:UIApplicationWillResignActiveNotification object:nil];
  [NSNotificationCenter.defaultCenter addObserver:self selector:@selector(resume:) name:UIApplicationDidBecomeActiveNotification object:nil];
  [NSNotificationCenter.defaultCenter addObserver:self selector:@selector(thermal:) name:NSProcessInfoThermalStateDidChangeNotification object:nil];
  [self validateInstalled];
}
- (UIButton *)button:(NSString *)title action:(SEL)selector {
  UIButton *button = [UIButton buttonWithType:UIButtonTypeSystem];
  [button setTitle:title forState:UIControlStateNormal];
  [button addTarget:self action:selector forControlEvents:UIControlEventTouchUpInside];
  return button;
}
- (UIStackView *)row:(NSString *)title control:(UIView *)control {
  UILabel *label = [[UILabel alloc] init]; label.text = title; label.numberOfLines = 0;
  UIStackView *row = [[UIStackView alloc] initWithArrangedSubviews:@[label, control]];
  row.axis = UILayoutConstraintAxisHorizontal; row.spacing = 8; row.alignment = UIStackViewAlignmentCenter;
  return row;
}
- (void)log:(NSString *)message {
  if (!message) return;
  NSLog(@"STORM: %@", message);
  NSString *next = [(_logs.text ?: @"") stringByAppendingFormat:@"%@\n", message];
  // Keep UI logs bounded; private asset names/bytes are never uploaded.
  _logs.text = next.length > 24000 ? [next substringFromIndex:next.length - 24000] : next;
}
- (void)changeMode:(UISegmentedControl *)control {
  BOOL performance = control.selectedSegmentIndex == 1;
  _metal.preferredFramesPerSecond = performance ? 60 : 30;
  _metal.resolutionScale = performance ? .65 : 1;
  [_metal applyResolution];
  [NSUserDefaults.standardUserDefaults setInteger:control.selectedSegmentIndex forKey:@"performanceMode"];
}
- (void)changeAdaptive:(UISwitch *)control { _metal.adaptiveResolution = control.on; [NSUserDefaults.standardUserDefaults setBool:control.on forKey:@"adaptiveResolution"]; }
- (void)changeEdit:(UISwitch *)control { _controls.editingControls = control.on; }
- (void)changeControl:(UISlider *)control {
  if (control.tag == 0) _controls.controlScale = control.value; else _controls.controlOpacity = control.value;
  [NSUserDefaults.standardUserDefaults setFloat:control.value forKey:control.tag == 0 ? @"controlScale" : @"controlOpacity"];
}
- (void)importGame {
  UIDocumentPickerViewController *picker = [[UIDocumentPickerViewController alloc] initForOpeningContentTypes:@[UTTypeFolder] asCopy:NO];
  picker.delegate = self;
  picker.allowsMultipleSelection = NO;
  [self presentViewController:picker animated:YES completion:nil];
}
- (void)documentPicker:(UIDocumentPickerViewController *)controller didPickDocumentsAtURLs:(NSArray<NSURL *> *)urls {
  (void)controller;
  NSURL *source = urls.firstObject;
  if (!source) return;
  _importButton.enabled = _launchButton.enabled = NO;
  _identityMatches = NO;
  [self log:@"Copying selected directory into the application sandbox; original is unchanged."];
  dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
    BOOL scoped = [source startAccessingSecurityScopedResource];
    NSFileManager *manager = NSFileManager.defaultManager;
    NSURL *destination = GameURL();
    NSURL *parent = destination.URLByDeletingLastPathComponent;
    NSURL *staging = [parent URLByAppendingPathComponent:[@".incoming-" stringByAppendingString:NSUUID.UUID.UUIDString] isDirectory:YES];
    __block NSError *error = nil;
    [manager createDirectoryAtURL:parent withIntermediateDirectories:YES attributes:nil error:&error];
    NSFileCoordinator *coordinator = [[NSFileCoordinator alloc] initWithFilePresenter:nil];
    __block NSDictionary *validation = nil;
    NSError *coordinationError = nil;
    if (!error) [coordinator coordinateReadingItemAtURL:source options:NSFileCoordinatorReadingWithoutChanges error:&coordinationError byAccessor:^(NSURL *readURL) {
      // Refuse symlinks rather than following references outside the chosen asset directory.
      NSNumber *rootLink = nil;
      if (![readURL getResourceValue:&rootLink forKey:NSURLIsSymbolicLinkKey error:&error]) return;
      if (rootLink.boolValue) { error = ImportError(@"Symbolic-link directory is not accepted"); return; }
      NSDirectoryEnumerator *entries = [manager enumeratorAtURL:readURL includingPropertiesForKeys:@[NSURLIsSymbolicLinkKey] options:0 errorHandler:^BOOL(NSURL *url, NSError *failure) { (void)url; error = failure; return NO; }];
      for (NSURL *entry in entries) {
        NSNumber *link = nil;
        if (![entry getResourceValue:&link forKey:NSURLIsSymbolicLinkKey error:&error]) return;
        if (link.boolValue) { error = ImportError(@"Symbolic links inside game directory are not accepted"); return; }
      }
      if (error || ![manager copyItemAtURL:readURL toURL:staging error:&error]) return;
      validation = ValidateXEX([staging URLByAppendingPathComponent:@"default.xex"], &error);
      if (!validation || ![validation[@"reference_matches"] boolValue]) {
        if (!error) error = ImportError([NSString stringWithFormat:@"Executable differs from documented reference: %@", validation]);
        return;
      }
      // Atomic replacement preserves the previous import if copying or validation fails.
      if ([manager fileExistsAtPath:destination.path]) {
        [manager replaceItemAtURL:destination withItemAtURL:staging backupItemName:nil options:0 resultingItemURL:nil error:&error];
      } else [manager moveItemAtURL:staging toURL:destination error:&error];
    }];
    if (!error) error = coordinationError;
    [manager removeItemAtURL:staging error:nil];
    if (scoped) [source stopAccessingSecurityScopedResource];
    dispatch_async(dispatch_get_main_queue(), ^{
      self->_importButton.enabled = self->_launchButton.enabled = YES;
      [self log:error ? error.localizedDescription : @"Imported matching executable. Game AOT and asset compatibility remain pending."];
      [self validateInstalled];
    });
  });
}
- (void)validateInstalled {
  dispatch_async(dispatch_get_global_queue(QOS_CLASS_UTILITY, 0), ^{
    NSError *error = nil;
    NSDictionary *validation = ValidateXEX([GameURL() URLByAppendingPathComponent:@"default.xex"], &error);
    dispatch_async(dispatch_get_main_queue(), ^{
      self->_identityMatches = [validation[@"reference_matches"] boolValue];
      [self log:validation ? [NSString stringWithFormat:@"XEX identity: %@", validation] : @"No validated local default.xex. Import a legally obtained extracted game directory."];
    });
  });
}
- (void)launchGame {
  if (!_runtime) { [self log:@"Runtime unavailable"]; return; }
  if (!_identityMatches) { [self log:@"Launch refused: original executable identity has not been validated."]; return; }
  int result = storm_runtime_start(_runtime, GameURL().fileSystemRepresentation);
  NSString *detail = [NSString stringWithUTF8String:storm_runtime_last_error(_runtime)];
  [self log:[NSString stringWithFormat:@"Runtime start result=%d: %@", result, detail ?: @""]];
  _status.text = result == 0 ? @"Runtime returned success; game boot still requires observable verification." : @"Inicialização recusada pelo runtime. Imagem AOT do jogo ainda ausente.";
}
- (void)suspend:(NSNotification *)notification {
  (void)notification; _metal.paused = YES; [_controls resetInput];
  if (_runtime) storm_runtime_stop(_runtime);
  [self log:@"Application inactive: rendering paused, input reset, runtime stopped."];
}
- (void)resume:(NSNotification *)notification { (void)notification; _metal.paused = NO; }
- (void)thermal:(NSNotification *)notification {
  (void)notification;
  if (NSProcessInfo.processInfo.thermalState >= NSProcessInfoThermalStateSerious) {
    _metal.preferredFramesPerSecond = 30; _metal.resolutionScale = .5; [_metal applyResolution];
    [self log:@"Thermal pressure: diagnostic limited to 30 FPS at half resolution."];
  }
}
- (void)didReceiveMemoryWarning {
  [super didReceiveMemoryWarning];
  _metal.resolutionScale = .5; [_metal applyResolution];
  [self log:@"Memory warning: reduced diagnostic render target size."];
}
- (void)dealloc {
  [NSNotificationCenter.defaultCenter removeObserver:self];
  storm_runtime_destroy(_runtime);
}
@end
