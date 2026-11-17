#import "StormNativeSession.h"
#import "Controls/StormControls.h"
#import "Import/StormGameImporter.h"
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>
#include <SDL3/SDL.h>
#include <algorithm>
#include <cmath>

@interface StormNativeSession () <UIDocumentPickerDelegate>
@property(nonatomic, weak) UIWindow *window;
@property(nonatomic) UIView *panel;
@property(nonatomic) UILabel *status;
@property(nonatomic) UIButton *importButton;
@property(nonatomic) StormGameImporter *importer;
@property(nonatomic) StormControls *controls;
@property(nonatomic, readwrite) BOOL ready;
@property(nonatomic) BOOL invalidated;
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
  _panel.backgroundColor = [UIColor colorWithWhite:0.07 alpha:0.97];
  _panel.translatesAutoresizingMaskIntoConstraints = NO;
  UIView *root = window.rootViewController.view;
  [root addSubview:_panel];
  [NSLayoutConstraint activateConstraints:@[
    [_panel.leadingAnchor constraintEqualToAnchor:root.leadingAnchor],
    [_panel.trailingAnchor constraintEqualToAnchor:root.trailingAnchor],
    [_panel.topAnchor constraintEqualToAnchor:root.topAnchor],
    [_panel.bottomAnchor constraintEqualToAnchor:root.bottomAnchor]]];
  UILabel *title = [UILabel new];
  title.text = @"Storm Revolution • experimental";
  title.textColor = UIColor.whiteColor;
  title.font = [UIFont boldSystemFontOfSize:23];
  _status = [UILabel new];
  _status.text = @"Verificando os arquivos instalados…";
  _status.textColor = UIColor.whiteColor;
  _status.numberOfLines = 0;
  _importButton = [UIButton buttonWithType:UIButtonTypeSystem];
  [_importButton setTitle:@"Importar meu ZIP do jogo" forState:UIControlStateNormal];
  [_importButton addTarget:self action:@selector(chooseZIP) forControlEvents:UIControlEventTouchUpInside];
  _importButton.enabled = NO;
  UIStackView *stack = [[UIStackView alloc] initWithArrangedSubviews:@[title, _status, _importButton]];
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
    session.ready = !error && [validation[@"reference_matches"] boolValue];
    session.status.text = session.ready ? @"Arquivos preparados. Iniciando…" : @"Importe o ZIP da sua cópia do jogo. A extração precisa de espaço livre para os arquivos.";
    session.importButton.enabled = !session.ready;
  }];
  return self;
}
- (void)chooseZIP {
  UIDocumentPickerViewController *picker = [[UIDocumentPickerViewController alloc]
      initForOpeningContentTypes:@[UTTypeZIP] asCopy:NO];
  picker.delegate = self;
  [self.window.rootViewController presentViewController:picker animated:YES completion:nil];
}
- (void)documentPicker:(UIDocumentPickerViewController *)controller didPickDocumentsAtURLs:(NSArray<NSURL *> *)urls {
  if (!urls.count || self.invalidated) return;
  self.importButton.enabled = NO;
  __weak StormNativeSession *weakSelf = self;
  [self.importer importZIPAtURL:urls.firstObject progress:^(double fraction, NSString *message) {
    StormNativeSession *session = weakSelf;
    if (!session || session.invalidated) return;
    session.status.text = fraction >= 1 ? @"Arquivos preparados. Verificando…" : message;
  } completion:^(NSDictionary *validation, NSError *error) {
    StormNativeSession *session = weakSelf;
    if (!session || session.invalidated) return;
    session.ready = !error && [validation[@"reference_matches"] boolValue];
    session.status.text = session.ready ? @"Arquivos preparados. Iniciando…" : (error.localizedDescription ?: @"A cópia importada não corresponde ao executável suportado.");
    session.importButton.enabled = !session.ready;
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
  self.controls.controlOpacity = 0.65;
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
  return YES;
}
- (void)showFailure:(NSString *)message {
  self.ready = NO;
  self.importButton.enabled = NO;
  self.status.text = message;
  [self.controls removeFromSuperview];
  if (!self.panel.superview) [self.window.rootViewController.view addSubview:self.panel];
}
- (void)invalidate {
  self.invalidated = YES;
  [self.importer cancel];
  [self.controls resetInput];
  self.controls.inputChanged = nil;
  [self.controls removeFromSuperview];
  [self.panel removeFromSuperview];
  if (_pad) SDL_CloseJoystick(_pad);
  _pad = nullptr;
  if (_padID) SDL_DetachVirtualJoystick(_padID);
  _padID = 0;
}
@end
