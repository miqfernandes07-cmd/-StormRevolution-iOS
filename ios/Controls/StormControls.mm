#import "Localization/StormLocalization.h"
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

@interface StormTouchButton : UIButton
@end
@implementation StormTouchButton
- (BOOL)pointInside:(CGPoint)point withEvent:(UIEvent *)event {
  return self.enabled && !self.hidden && CGRectContainsPoint(CGRectInset(self.bounds, -6, -6), point);
}
@end

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
  uint32_t _shortcutButtons;
  NSUInteger _shortcutEpoch;
  NSInteger _shortcutTag;
}
- (instancetype)initWithFrame:(CGRect)frame {
  self = [super initWithFrame:frame];
  if (!self) return nil;
  _items = [NSMutableArray array];
  _controlScale = 1;
  _controlOpacity = .85;
  _inputActive = YES;
  _hapticsEnabled = YES;
  _shortcutPulseDuration = .18;
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
    UIButton *button = [StormTouchButton buttonWithType:UIButtonTypeCustom];
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
  _leftStick = [self makeStick:@"L" tag:17 label:SL(@"Analógico esquerdo")];
  _rightStick = [self makeStick:@"R" tag:18 label:SL(@"Analógico direito")];
  _leftKnob = (UILabel *)_leftStick.subviews.firstObject;
  _rightKnob = (UILabel *)_rightStick.subviews.firstObject;
  for (NSUInteger i = 0; i < 3; ++i) {
    UIButton *button = [StormTouchButton buttonWithType:UIButtonTypeCustom];
    button.tag = 19 + i; button.hidden = YES;
    [button setTitle:@[SL(@"Jutsu"),SL(@"Supremo"),SL(@"Dash")][i] forState:UIControlStateNormal];
    [button setTitleColor:[UIColor colorWithRed:.65 green:.85 blue:1 alpha:1] forState:UIControlStateNormal];
    button.titleLabel.font = [UIFont systemFontOfSize:11 weight:UIFontWeightBold];
    button.titleLabel.adjustsFontSizeToFitWidth = YES;
    button.backgroundColor = Surface(); button.layer.borderWidth = 1;
    button.layer.borderColor = [UIColor colorWithRed:.35 green:.65 blue:1 alpha:.4].CGColor;
    button.accessibilityIdentifier = @[@"shortcut-jutsu",@"shortcut-ultimate",@"shortcut-dash"][i];
    button.accessibilityLabel = button.currentTitle;
    [button addTarget:self action:@selector(shortcutDown:) forControlEvents:UIControlEventTouchDown];
    [button addTarget:self action:@selector(shortcutCancelled:) forControlEvents:UIControlEventTouchCancel];
    UIPanGestureRecognizer *move = [[UIPanGestureRecognizer alloc] initWithTarget:self action:@selector(moveControl:)];
    move.enabled = NO; [button addGestureRecognizer:move]; [_items addObject:button]; [self addSubview:button];
  }
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
  stick.accessibilityHint = SL(@"Arraste em qualquer direção. Solte para centralizar.");
  stick.accessibilityIdentifier = tag == 17 ? @"xbox-left-stick" : @"xbox-right-stick";
  UIPanGestureRecognizer *pan = [[UIPanGestureRecognizer alloc] initWithTarget:self action:@selector(moveStick:)];
  pan.maximumNumberOfTouches = 1;
  [stick addGestureRecognizer:pan];
  UITapGestureRecognizer *click = [[UITapGestureRecognizer alloc] initWithTarget:self action:@selector(clickStick:)];
  click.numberOfTapsRequired = 2;
  [stick addGestureRecognizer:click];
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
- (NSString *)connectionDescription { return _connectionDescription ?: SL(@"Nenhum controle conectado"); }
- (NSString *)positionsKey { return (_mobileLayout && _mobileActionLabels) ? @"touchPositionsActionsV1" : (_mobileLayout ? @"touchPositionsMobileV3" : PositionsKey); }
- (void)setMobileLayout:(BOOL)value {
  _mobileLayout = value;
  [self resetInput];
  [self setNeedsLayout];
}
- (void)setPlayStationLabels:(BOOL)value {
  _playStationLabels = value;
  [self updateButtonLabels];
}
- (void)setMobileActionLabels:(BOOL)value {
  if (_mobileActionLabels != value) [self resetInput];
  _mobileActionLabels = value; [self updateButtonLabels]; [self setNeedsLayout];
}
- (void)updateButtonLabels {
  BOOL value = _playStationLabels;
  NSArray *names = _mobileActionLabels ? @[SL(@"Pulo"),SL(@"Ataque"),SL(@"Kunai"),SL(@"Chakra"),SL(@"Aliado 1"),SL(@"Aliado 2"),SL(@"Subst."),SL(@"Guarda"),SL(@"PAUSA"),SL(@"VOLTAR"),@"L3",@"R3"] : (value ? @[@"✕", @"○", @"□", @"△", @"L1", @"R1", @"L2", @"R2", @"OPTIONS", @"SHARE", @"L3", @"R3"]
                         : @[@"A", @"B", @"X", @"Y", @"LB", @"RB", @"LT", @"RT", @"START", @"BACK", @"LS", @"RS"]);
  NSArray *colors = value ? @[[UIColor colorWithRed:.43 green:.70 blue:1 alpha:1],
      [UIColor colorWithRed:1 green:.47 blue:.53 alpha:1],
      [UIColor colorWithRed:.90 green:.57 blue:.88 alpha:1],
      [UIColor colorWithRed:.40 green:.90 blue:.72 alpha:1]] : @[
      [UIColor colorWithRed:.35 green:.82 blue:.42 alpha:1], [UIColor colorWithRed:1 green:.37 blue:.36 alpha:1],
      [UIColor colorWithRed:.32 green:.65 blue:1 alpha:1], [UIColor colorWithRed:1 green:.82 blue:.24 alpha:1]];
  for (NSUInteger i = 0; i < names.count; ++i) {
    UIButton *button = (UIButton *)_items[i];
    [button setTitle:names[i] forState:UIControlStateNormal];
    button.accessibilityLabel = names[i];
    if (i < 4) button.titleLabel.font = [UIFont systemFontOfSize:_mobileActionLabels ? 12 : (value ? 24 : 19) weight:UIFontWeightSemibold];
    button.titleLabel.adjustsFontSizeToFitWidth = YES;
    if (i < 4) [button setTitleColor:colors[i] forState:UIControlStateNormal];
  }
  [(UIButton *)_items[19] setTitle:SL(@"Supremo") forState:UIControlStateNormal];
  [self setNeedsLayout];
}
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
  [StormControls resetSavedLayoutForMobile:_mobileLayout actions:_mobileActionLabels];
  [self setNeedsLayout];
}
+ (void)resetSavedLayoutForMobile:(BOOL)mobile {
  [self resetSavedLayoutForMobile:mobile actions:NO];
}
+ (void)resetSavedLayoutForMobile:(BOOL)mobile actions:(BOOL)actions {
  [NSUserDefaults.standardUserDefaults removeObjectForKey:(mobile && actions) ? @"touchPositionsActionsV1" : (mobile ? @"touchPositionsMobileV3" : PositionsKey)];
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
  const CGFloat fit = _mobileLayout ? MIN(1.1, height / 350) : MIN(width / 350, height / 330);
  NSDictionary *saved = [NSUserDefaults.standardUserDefaults dictionaryForKey:[self positionsKey]];
  const CGFloat unit = fit * (_mobileActionLabels ? MIN(1.2, _controlScale) : _controlScale);
  const CGFloat faceX = width - 103 * unit, faceY = height - 99 * unit;
  const CGPoint mobilePoints[] = {{faceX, faceY+44*unit},{faceX+44*unit,faceY},
    {faceX-44*unit,faceY},{faceX,faceY-44*unit},
    {110*unit,72*unit},{width-110*unit,72*unit},{48*unit,72*unit},{width-48*unit,72*unit},
    {width/2+45*unit,height-24*unit},{width/2-45*unit,height-24*unit},
    {103*unit,height-22*unit},{width-205*unit,height-22*unit},
    {54*unit,height-205*unit},{54*unit,height-133*unit},{18*unit,height-169*unit},{90*unit,height-169*unit},
    {105*unit,height-83*unit},{width-205*unit,height-89*unit}};
  for (NSUInteger i = 0; i < _items.count; ++i) {
    UIView *view = _items[i];
    view.hidden = i >= 18 ? !(_mobileLayout && _mobileActionLabels) : (_mobileLayout && (i == 10 || i == 11));
    CGFloat itemWidth = i < 4 ? 44 : (i < 8 ? 50 : (i < 10 ? 44 : (i < 12 ? 42 : 28)));
    CGFloat itemHeight = i < 4 ? 44 : (i < 8 ? 34 : (i < 12 ? 30 : 28));
    if (i >= ButtonCount && i < 18) itemWidth = itemHeight = i == 16 ? 80 : 70;
    if (_mobileLayout) {
      if (i < 4) itemWidth = itemHeight = 46;
      else if (i < 8) { itemWidth = 52; itemHeight = 30; }
      else if (i < 10) { itemWidth = 72; itemHeight = 25; }
      else if (i < 12) { itemWidth = 36; itemHeight = 24; }
      else if (i < 16) itemWidth = itemHeight = 32;
      else if (i < 18) itemWidth = itemHeight = i == 16 ? 86 : 62;
    }
    if (i >= 18) { itemWidth = 64; itemHeight = 38; }
    if (_mobileActionLabels && i == 1) itemWidth = itemHeight = 56;
    CGFloat scale = MIN(_controlScale, (i >= 12 && i < 16) ? 1.15 : 1.25) * fit;
    // No transforms are needed: moving hit targets stays predictable when editing.
    view.bounds = CGRectMake(0, 0, itemWidth * scale, itemHeight * scale);
    view.layer.cornerRadius = (i < 4 || (i >= 12 && i < 18)) ? itemWidth * scale / 2 : 12 * scale;
    CGPoint position = CGPointMake(.5,.5);
    if (i < 18) {
      position = CGPointMake(points[i].x / 350, points[i].y / 330);
      if (_mobileLayout) position = CGPointMake(mobilePoints[i].x / width, mobilePoints[i].y / height);
      if (_mobileLayout && _mobileActionLabels && i >= 4 && i < 8) position.y = 48 * unit / height;
    } else {
      position = CGPointMake((width - (187 - 70 * (i - 18)) * unit) / width, (height - 192 * unit) / height);
    }
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
    if (i >= ButtonCount && i < 18) {
      UILabel *knob = (UILabel *)view.subviews.firstObject;
      knob.bounds = CGRectMake(0, 0, itemWidth * scale * .58, itemHeight * scale * .58);
      knob.center = CGPointMake(view.bounds.size.width / 2, view.bounds.size.height / 2);
      knob.layer.cornerRadius = knob.bounds.size.width / 2;
      knob.text = _mobileActionLabels ? (i == 16 ? SL(@"MOVER") : SL(@"CÂM.")) : (_mobileLayout ? (i == 16 ? @"L3" : @"R3") : (i == 16 ? @"L" : @"R"));
      knob.font = [UIFont systemFontOfSize:_mobileActionLabels ? 10 : 12 weight:UIFontWeightBold];
      view.accessibilityHint = _mobileLayout ? SL(@"Arraste para mover. Toque duas vezes para clicar o analógico.") : SL(@"Arraste para mover.");
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
  Snapshot touch = _touchState; touch.buttons |= _shortcutButtons;
  Snapshot value = _inputActive ? Xbox::combine(touch, _physicalState) : Snapshot{};
  for (NSUInteger i = 0; i < ButtonCount; ++i) {
    UIButton *button = (UIButton *)_items[i];
    BOOL pressed = i == 6 ? value.lt > .1f : (i == 7 ? value.rt > .1f : (value.buttons & ButtonBits[i]) != 0);
    button.backgroundColor = pressed ? [UIColor colorWithRed:.27 green:.34 blue:.43 alpha:1] : Surface();
    button.layer.borderWidth = pressed ? 2 : 1;
    button.accessibilityValue = pressed ? SL(@"Pressionado") : SL(@"Solto");
  }
  for (NSUInteger i = 18; i < _items.count; ++i) {
    UIButton *button = (UIButton *)_items[i]; BOOL active = button.tag == _shortcutTag;
    button.backgroundColor = active ? [UIColor colorWithRed:.20 green:.35 blue:.52 alpha:1] : Surface();
    button.accessibilityValue = active ? SL(@"Executando") : SL(@"Pronto");
  }
  if (self.inputChanged) self.inputChanged(value.buttons, value.lx, value.ly, value.rx, value.ry, value.lt, value.rt);
}
- (void)touchDown:(UIButton *)button {
  if (_editingControls || !_inputActive || button.tag < 1 || button.tag > (NSInteger)ButtonCount) return;
  [self cancelShortcuts];
  _touchState.buttons |= ButtonBits[button.tag - 1];
  if (button.tag == 7) _touchState.lt = 1;
  if (button.tag == 8) _touchState.rt = 1;
    if (_hapticsEnabled) [_haptic impactOccurred];
  [self emit];
}
- (void)cancelShortcuts {
  _shortcutEpoch++; _shortcutButtons = 0; _shortcutTag = 0;
}
- (void)shortcutCancelled:(UIButton *)button { [self cancelShortcuts]; [self emit]; }
- (void)shortcutDown:(UIButton *)button {
  if (!_inputActive || _editingControls || !_mobileLayout || !_mobileActionLabels) return;
  NSArray<NSNumber *> *steps;
  if (button.tag == 19) steps = @[@(Xbox::y),@0,@(Xbox::b),@0];
  else if (button.tag == 20) steps = @[@(Xbox::y),@0,@(Xbox::y),@0,@(Xbox::b),@0];
  else if (button.tag == 21) steps = @[@(Xbox::y),@0,@(Xbox::a),@0];
  else return;
  [self cancelShortcuts];
  const NSUInteger epoch = _shortcutEpoch;
  _shortcutTag = button.tag; _shortcutButtons = steps.firstObject.unsignedIntValue; [self emit];
  NSTimeInterval pulse = std::isfinite(_shortcutPulseDuration) ? MIN(.35,MAX(.08,_shortcutPulseDuration)) : .18;
  __weak StormControls *weakSelf = self;
  for (NSUInteger i = 1; i < steps.count; ++i) {
    uint32_t bits = steps[i].unsignedIntValue; BOOL last = i == steps.count-1;
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(i*pulse*NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
      StormControls *controls = weakSelf;
      if (!controls || controls->_shortcutEpoch != epoch || !controls->_inputActive || controls->_editingControls) return;
      controls->_shortcutButtons = bits; if (last) controls->_shortcutTag = 0; [controls emit];
    });
  }
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
    NSMutableDictionary *positions = [[NSUserDefaults.standardUserDefaults dictionaryForKey:[self positionsKey]] mutableCopy] ?: [NSMutableDictionary dictionary];
    positions[[NSString stringWithFormat:@"%ld", (long)item.tag - 1]] = @[@(item.center.x / MAX(1, self.bounds.size.width)), @(item.center.y / MAX(1, self.bounds.size.height))];
    [NSUserDefaults.standardUserDefaults setObject:positions forKey:[self positionsKey]];
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
- (void)clickStick:(UITapGestureRecognizer *)gesture {
  if (_editingControls || !_inputActive || gesture.state != UIGestureRecognizerStateRecognized) return;
  const uint32_t bit = gesture.view == _leftStick ? Xbox::left_stick : Xbox::right_stick;
  _touchState.buttons |= bit;
  [self emit];
  __weak StormControls *weakSelf = self;
  dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 100 * NSEC_PER_MSEC), dispatch_get_main_queue(), ^{
    StormControls *controls = weakSelf;
    if (!controls) return;
    controls->_touchState.buttons &= ~bit;
    [controls emit];
  });
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
  NSString *description = _controller ? [NSString stringWithFormat:SL(@"Controle conectado: %@"), _controller.vendorName ?: @"Gamepad"] : SL(@"Nenhum controle conectado");
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
  [self cancelShortcuts];
  _touchState = {}; _physicalState = {};
  [self updateStickIndicators];
  [self emit];
}
@end
