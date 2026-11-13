#import "Controls/StormControls.h"
#import <GameController/GameController.h>
#include "input/xbox360_mapping.h"
#include <cmath>

namespace {
using storm::input::Snapshot;
namespace Xbox = storm::input::xbox360;
NSString *const PositionsKey = @"touchPositionsXbox360V2";
constexpr NSUInteger ButtonCount = 16;
const uint32_t ButtonBits[ButtonCount] = {
    Xbox::a, Xbox::b, Xbox::x, Xbox::y, Xbox::left_shoulder, Xbox::right_shoulder,
    0, 0, Xbox::start, Xbox::back, Xbox::left_stick, Xbox::right_stick,
    Xbox::up, Xbox::down, Xbox::left, Xbox::right};
UIColor *Surface(void) { return [UIColor colorWithRed:.12 green:.15 blue:.21 alpha:1]; }
UIColor *Muted(void) { return [UIColor colorWithRed:.64 green:.70 blue:.79 alpha:1]; }
CGFloat ClampCenter(CGFloat value, CGFloat length, CGFloat halfSize) {
    if (length <= halfSize * 2) return length / 2;
    return MIN(length - halfSize, MAX(halfSize, value));
}
}

@implementation StormControls {
  NSMutableArray<UIView *> *_items;
  UIView *_leftStick;
  UIView *_rightStick;
  UILabel *_leftKnob;
  UILabel *_rightKnob;
  Snapshot _touchState;
  Snapshot _physicalState;
  GCController *_controller;
  UIImpactFeedbackGenerator *_haptic;
  BOOL _inputActive;
  NSString *_connectionDescription;
}
- (instancetype)initWithFrame:(CGRect)frame {
  self = [super initWithFrame:frame];
  if (!self) return nil;
  _items = [NSMutableArray array];
  _controlScale = 1;
  _controlOpacity = .85;
  _inputActive = YES;
  _haptic = [[UIImpactFeedbackGenerator alloc] initWithStyle:UIImpactFeedbackStyleLight];
  self.multipleTouchEnabled = YES;
  self.backgroundColor = [UIColor colorWithRed:.055 green:.075 blue:.115 alpha:1];
  self.layer.cornerRadius = 20;
  self.clipsToBounds = YES;
  self.accessibilityIdentifier = @"xbox360-control-surface";
  NSArray<NSString *> *names = @[@"A", @"B", @"X", @"Y", @"LB", @"RB", @"LT", @"RT",
                                  @"START", @"BACK", @"LS", @"RS", @"↑", @"↓", @"←", @"→"];
  NSArray<NSString *> *labels = @[@"Botão A", @"Botão B", @"Botão X", @"Botão Y",
      @"Ombro esquerdo LB", @"Ombro direito RB", @"Gatilho esquerdo LT", @"Gatilho direito RT",
      @"Start", @"Back", @"Clique do analógico esquerdo LS", @"Clique do analógico direito RS",
      @"Direcional para cima", @"Direcional para baixo", @"Direcional para esquerda", @"Direcional para direita"];
  NSArray<UIColor *> *colors = @[
      [UIColor colorWithRed:.35 green:.82 blue:.42 alpha:1],
      [UIColor colorWithRed:1 green:.37 blue:.36 alpha:1],
      [UIColor colorWithRed:.32 green:.65 blue:1 alpha:1],
      [UIColor colorWithRed:1 green:.82 blue:.24 alpha:1]];
  for (NSUInteger i = 0; i < names.count; ++i) {
    UIButton *button = [UIButton buttonWithType:UIButtonTypeCustom];
    button.tag = i + 1;
    [button setTitle:names[i] forState:UIControlStateNormal];
    [button setTitleColor:i < 4 ? colors[i] : UIColor.whiteColor forState:UIControlStateNormal];
    button.titleLabel.font = [UIFont systemFontOfSize:i < 4 ? 19 : (i < 12 ? 10 : 17) weight:UIFontWeightBold];
    button.backgroundColor = Surface();
    button.layer.borderColor = [UIColor colorWithWhite:1 alpha:.13].CGColor;
    button.layer.borderWidth = 1;
    button.accessibilityLabel = labels[i];
    button.accessibilityIdentifier = [@"xbox-" stringByAppendingString:names[i]];
    [button addTarget:self action:@selector(touchDown:) forControlEvents:UIControlEventTouchDown];
    [button addTarget:self action:@selector(touchUp:) forControlEvents:UIControlEventTouchUpInside | UIControlEventTouchUpOutside | UIControlEventTouchCancel];
    UIPanGestureRecognizer *move = [[UIPanGestureRecognizer alloc] initWithTarget:self action:@selector(moveControl:)];
    move.enabled = NO;
    [button addGestureRecognizer:move];
    [_items addObject:button];
    [self addSubview:button];
  }
  _leftStick = [self makeStick:@"L" tag:17 label:@"Analógico esquerdo"];
  _rightStick = [self makeStick:@"R" tag:18 label:@"Analógico direito"];
  _leftKnob = (UILabel *)_leftStick.subviews.firstObject;
  _rightKnob = (UILabel *)_rightStick.subviews.firstObject;
  NSNotificationCenter *center = NSNotificationCenter.defaultCenter;
  [center addObserver:self selector:@selector(controllersChanged:) name:GCControllerDidConnectNotification object:nil];
  [center addObserver:self selector:@selector(controllersChanged:) name:GCControllerDidDisconnectNotification object:nil];
  [center addObserver:self selector:@selector(suspendInput:) name:UIApplicationWillResignActiveNotification object:nil];
  [center addObserver:self selector:@selector(resumeInput:) name:UIApplicationDidBecomeActiveNotification object:nil];
  [self controllersChanged:nil];
  return self;
}
- (UIView *)makeStick:(NSString *)name tag:(NSInteger)tag label:(NSString *)label {
  UIView *stick = [[UIView alloc] init];
  stick.backgroundColor = [UIColor colorWithRed:.08 green:.11 blue:.16 alpha:1];
  stick.layer.borderColor = [UIColor colorWithWhite:1 alpha:.12].CGColor;
  stick.layer.borderWidth = 1;
  stick.tag = tag;
  stick.isAccessibilityElement = YES;
  stick.accessibilityLabel = label;
  stick.accessibilityHint = @"Arraste em qualquer direção. Solte para centralizar.";
  stick.accessibilityIdentifier = tag == 17 ? @"xbox-left-stick" : @"xbox-right-stick";
  UIPanGestureRecognizer *pan = [[UIPanGestureRecognizer alloc] initWithTarget:self action:@selector(moveStick:)];
  pan.maximumNumberOfTouches = 1;
  [stick addGestureRecognizer:pan];
  UILabel *knob = [[UILabel alloc] init];
  knob.text = name;
  knob.textAlignment = NSTextAlignmentCenter;
  knob.font = [UIFont systemFontOfSize:12 weight:UIFontWeightBold];
  knob.textColor = Muted();
  knob.backgroundColor = Surface();
  knob.clipsToBounds = YES;
  knob.isAccessibilityElement = NO;
  [stick addSubview:knob];
  [_items addObject:stick];
  [self addSubview:stick];
  return stick;
}
- (void)dealloc {
  _controller.extendedGamepad.valueChangedHandler = nil;
  [NSNotificationCenter.defaultCenter removeObserver:self];
}
- (NSString *)connectionDescription { return _connectionDescription ?: @"Nenhum controle conectado"; }
- (void)setControlScale:(CGFloat)value {
  _controlScale = std::isfinite(value) ? MIN(1.4, MAX(.65, value)) : 1;
  [self setNeedsLayout];
}
- (void)setControlOpacity:(CGFloat)value {
  _controlOpacity = std::isfinite(value) ? MIN(1, MAX(.2, value)) : .85;
  [self setNeedsLayout];
}
- (void)setEditingControls:(BOOL)value {
  _editingControls = value;
  for (UIView *item in _items) if (item != _leftStick && item != _rightStick)
    for (UIGestureRecognizer *gesture in item.gestureRecognizers) gesture.enabled = value;
  [self resetInput];
}
- (void)resetLayout {
  [NSUserDefaults.standardUserDefaults removeObjectForKey:PositionsKey];
  [self setNeedsLayout];
}
- (void)layoutSubviews {
  [super layoutSubviews];
  const CGFloat width = self.bounds.size.width, height = self.bounds.size.height;
  if (width <= 0 || height <= 0) return;
  // Reference layout is 350 x 330; position proportions adapt to either orientation.
  // Size is capped separately so the default layout cannot collide at max slider size.
  const CGPoint points[] = {{280,192},{322,150},{238,150},{280,108},
      {108,24},{242,24},{40,24},{310,24},{220,86},{160,86},
      {145,180},{280,272},{65,220},{65,286},{32,253},{98,253},{65,120},{208,260}};
  const CGFloat fit = MIN(width / 350, height / 330);
  NSDictionary *saved = [NSUserDefaults.standardUserDefaults dictionaryForKey:PositionsKey];
  for (NSUInteger i = 0; i < _items.count; ++i) {
    UIView *view = _items[i];
    CGFloat itemWidth = i < 4 ? 44 : (i < 8 ? 50 : (i < 10 ? 44 : (i < 12 ? 42 : 28)));
    CGFloat itemHeight = i < 4 ? 44 : (i < 8 ? 34 : (i < 12 ? 30 : 28));
    if (i >= ButtonCount) itemWidth = itemHeight = i == 16 ? 80 : 70;
    CGFloat scale = MIN(_controlScale, (i >= 12 && i < 16) ? 1.15 : 1.25) * fit;
    // No transforms are needed: moving hit targets stays predictable when editing.
    view.bounds = CGRectMake(0, 0, itemWidth * scale, itemHeight * scale);
    view.layer.cornerRadius = (i < 4 || i >= 12) ? itemWidth * scale / 2 : 10 * scale;
    CGPoint position = CGPointMake(points[i].x / 350, points[i].y / 330);
    id stored = saved[[NSString stringWithFormat:@"%lu", (unsigned long)i]];
    if ([stored isKindOfClass:NSArray.class] && [stored count] == 2 &&
        [stored[0] isKindOfClass:NSNumber.class] && [stored[1] isKindOfClass:NSNumber.class]) {
      double x = [stored[0] doubleValue], y = [stored[1] doubleValue];
      if (std::isfinite(x) && std::isfinite(y) && x >= 0 && x <= 1 && y >= 0 && y <= 1)
        position = CGPointMake(x, y);
    }
    view.center = CGPointMake(ClampCenter(position.x * width, width, view.bounds.size.width / 2),
                              ClampCenter(position.y * height, height, view.bounds.size.height / 2));
    view.alpha = _controlOpacity;
    if (i >= ButtonCount) {
      UILabel *knob = (UILabel *)view.subviews.firstObject;
      knob.bounds = CGRectMake(0, 0, itemWidth * scale * .58, itemHeight * scale * .58);
      knob.center = CGPointMake(view.bounds.size.width / 2, view.bounds.size.height / 2);
      knob.layer.cornerRadius = knob.bounds.size.width / 2;
    }
  }
  [self updateStickIndicators];
}
- (void)updateStickIndicators {
  _leftKnob.transform = CGAffineTransformMakeTranslation(_touchState.lx * _leftStick.bounds.size.width * .18,
                                                          -_touchState.ly * _leftStick.bounds.size.height * .18);
  _rightKnob.transform = CGAffineTransformMakeTranslation(_touchState.rx * _rightStick.bounds.size.width * .18,
                                                           -_touchState.ry * _rightStick.bounds.size.height * .18);
}
- (void)emit {
  Snapshot value = _inputActive ? Xbox::combine(_touchState, _physicalState) : Snapshot{};
  for (NSUInteger i = 0; i < ButtonCount; ++i) {
    UIButton *button = (UIButton *)_items[i];
    BOOL pressed = i == 6 ? value.lt > .1f : (i == 7 ? value.rt > .1f : (value.buttons & ButtonBits[i]) != 0);
    button.backgroundColor = pressed ? [UIColor colorWithRed:.27 green:.34 blue:.43 alpha:1] : Surface();
    button.layer.borderWidth = pressed ? 2 : 1;
    button.accessibilityValue = pressed ? @"Pressionado" : @"Solto";
  }
  if (self.inputChanged) self.inputChanged(value.buttons, value.lx, value.ly, value.rx, value.ry, value.lt, value.rt);
}
- (void)touchDown:(UIButton *)button {
  if (_editingControls || !_inputActive || button.tag < 1 || button.tag > (NSInteger)ButtonCount) return;
  _touchState.buttons |= ButtonBits[button.tag - 1];
  if (button.tag == 7) _touchState.lt = 1;
  if (button.tag == 8) _touchState.rt = 1;
  [_haptic impactOccurred];
  [self emit];
}
- (void)touchUp:(UIButton *)button {
  if (button.tag < 1 || button.tag > (NSInteger)ButtonCount) return;
  _touchState.buttons &= ~ButtonBits[button.tag - 1];
  if (button.tag == 7) _touchState.lt = 0;
  if (button.tag == 8) _touchState.rt = 0;
  [self emit];
}
- (void)moveControl:(UIPanGestureRecognizer *)gesture {
  if (!_editingControls) return;
  UIView *item = gesture.view;
  CGPoint delta = [gesture translationInView:self];
  item.center = CGPointMake(ClampCenter(item.center.x + delta.x, self.bounds.size.width, item.bounds.size.width / 2),
                            ClampCenter(item.center.y + delta.y, self.bounds.size.height, item.bounds.size.height / 2));
  [gesture setTranslation:CGPointZero inView:self];
  if (gesture.state == UIGestureRecognizerStateEnded || gesture.state == UIGestureRecognizerStateCancelled) {
    NSMutableDictionary *positions = [[NSUserDefaults.standardUserDefaults dictionaryForKey:PositionsKey] mutableCopy] ?: [NSMutableDictionary dictionary];
    positions[[NSString stringWithFormat:@"%ld", (long)item.tag - 1]] = @[@(item.center.x / MAX(1, self.bounds.size.width)), @(item.center.y / MAX(1, self.bounds.size.height))];
    [NSUserDefaults.standardUserDefaults setObject:positions forKey:PositionsKey];
  }
}
- (void)moveStick:(UIPanGestureRecognizer *)gesture {
  if (_editingControls) { [self moveControl:gesture]; return; }
  UIView *stick = gesture.view;
  CGPoint point = [gesture locationInView:stick];
  const float radiusX = MAX(1, stick.bounds.size.width / 2), radiusY = MAX(1, stick.bounds.size.height / 2);
  float x = (point.x - radiusX) / radiusX, y = (radiusY - point.y) / radiusY;
  const float magnitude = std::sqrt(x * x + y * y);
  if (magnitude > 1) { x /= magnitude; y /= magnitude; }
  if (!_inputActive || gesture.state == UIGestureRecognizerStateEnded || gesture.state == UIGestureRecognizerStateCancelled || gesture.state == UIGestureRecognizerStateFailed) x = y = 0;
  if (stick == _leftStick) { _touchState.lx = x; _touchState.ly = y; }
  else { _touchState.rx = x; _touchState.ry = y; }
  [self updateStickIndicators];
  [self emit];
}
- (void)readController:(GCExtendedGamepad *)pad {
  if (!_inputActive || !pad || pad != _controller.extendedGamepad) return;
  uint32_t bits = 0;
  if (pad.dpad.up.pressed) bits |= Xbox::up;
  if (pad.dpad.down.pressed) bits |= Xbox::down;
  if (pad.dpad.left.pressed) bits |= Xbox::left;
  if (pad.dpad.right.pressed) bits |= Xbox::right;
  if (pad.buttonMenu.pressed) bits |= Xbox::start;
  if (pad.buttonOptions.pressed) bits |= Xbox::back;
  if (pad.leftThumbstickButton.pressed) bits |= Xbox::left_stick;
  if (pad.rightThumbstickButton.pressed) bits |= Xbox::right_stick;
  if (pad.leftShoulder.pressed) bits |= Xbox::left_shoulder;
  if (pad.rightShoulder.pressed) bits |= Xbox::right_shoulder;
  if (pad.buttonA.pressed) bits |= Xbox::a;
  if (pad.buttonB.pressed) bits |= Xbox::b;
  if (pad.buttonX.pressed) bits |= Xbox::x;
  if (pad.buttonY.pressed) bits |= Xbox::y;
  // GameController reports up as positive Y, matching the Xbox runtime convention.
  _physicalState = {bits, pad.leftThumbstick.xAxis.value, pad.leftThumbstick.yAxis.value,
                    pad.rightThumbstick.xAxis.value, pad.rightThumbstick.yAxis.value,
                    pad.leftTrigger.value, pad.rightTrigger.value};
  [self emit];
}
- (void)controllersChanged:(NSNotification *)notification {
  (void)notification;
  if (!NSThread.isMainThread) {
    __weak StormControls *weakSelf = self;
    dispatch_async(dispatch_get_main_queue(), ^{ [weakSelf controllersChanged:nil]; });
    return;
  }
  NSArray<GCController *> *connected = GCController.controllers;
  GCController *next = _controller && [connected containsObject:_controller] && _controller.extendedGamepad ? _controller : nil;
  if (!next) for (GCController *candidate in connected) if (candidate.extendedGamepad) { next = candidate; break; }
  if (next != _controller) {
    _controller.extendedGamepad.valueChangedHandler = nil;
    _controller = next;
    _physicalState = {}; // Do not erase held touchscreen controls on hotplug.
    _controller.handlerQueue = dispatch_get_main_queue();
    __weak StormControls *weakSelf = self;
    _controller.extendedGamepad.valueChangedHandler = ^(GCExtendedGamepad *pad, GCControllerElement *element) {
      (void)element;
      [weakSelf readController:pad];
    };
    [self readController:_controller.extendedGamepad];
    [self emit];
  }
  NSString *description = _controller ? [NSString stringWithFormat:@"Controle conectado: %@", _controller.vendorName ?: @"Gamepad"] : @"Nenhum controle conectado";
  if (![_connectionDescription isEqualToString:description]) {
    _connectionDescription = [description copy];
    if (self.connectionChanged) self.connectionChanged(_connectionDescription);
    if (self.window) UIAccessibilityPostNotification(UIAccessibilityAnnouncementNotification, _connectionDescription);
  }
}
- (void)suspendInput:(NSNotification *)notification {
  (void)notification;
  _inputActive = NO;
  [self resetInput];
}
- (void)resumeInput:(NSNotification *)notification {
  (void)notification;
  _inputActive = YES;
  [self controllersChanged:nil];
  [self readController:_controller.extendedGamepad];
}
- (void)resetInput {
  _touchState = {}; _physicalState = {};
  [self updateStickIndicators];
  [self emit];
}
@end
