#import "Controls/StormControls.h"
#import <GameController/GameController.h>
#include <cmath>

@implementation StormControls {
  NSMutableArray<UIView *> *_items;
  UIView *_stick;
  UILabel *_stickLabel;
  uint32_t _touchButtons;
  uint32_t _physicalButtons;
  float _touchLX, _touchLY, _touchLT, _touchRT;
  float _physicalLX, _physicalLY, _physicalRX, _physicalRY, _physicalLT, _physicalRT;
  GCController *_controller;
  UIImpactFeedbackGenerator *_haptic;
}
- (instancetype)initWithFrame:(CGRect)frame {
  self = [super initWithFrame:frame];
  if (!self) return nil;
  _items = [NSMutableArray array];
  _controlScale = 1;
  _controlOpacity = .7;
  _haptic = [[UIImpactFeedbackGenerator alloc] initWithStyle:UIImpactFeedbackStyleLight];
  self.multipleTouchEnabled = YES;
  self.backgroundColor = [UIColor colorWithWhite:.08 alpha:1];
  NSArray<NSString *> *names = @[@"A", @"B", @"X", @"Y", @"LB", @"RB", @"LT", @"RT", @"Start", @"Back"];
  for (NSUInteger i = 0; i < names.count; ++i) {
    UIButton *button = [UIButton buttonWithType:UIButtonTypeSystem];
    button.tag = i + 1;
    [button setTitle:names[i] forState:UIControlStateNormal];
    button.backgroundColor = [UIColor colorWithWhite:.25 alpha:1];
    button.tintColor = UIColor.whiteColor;
    button.layer.cornerRadius = 21;
    [button addTarget:self action:@selector(touchDown:) forControlEvents:UIControlEventTouchDown];
    [button addTarget:self action:@selector(touchUp:) forControlEvents:UIControlEventTouchUpInside | UIControlEventTouchUpOutside | UIControlEventTouchCancel];
    UIPanGestureRecognizer *move = [[UIPanGestureRecognizer alloc] initWithTarget:self action:@selector(moveControl:)];
    move.enabled = NO;
    [button addGestureRecognizer:move];
    [_items addObject:button];
    [self addSubview:button];
  }
  _stick = [[UIView alloc] init];
  _stick.backgroundColor = [UIColor colorWithWhite:.3 alpha:1];
  _stick.layer.cornerRadius = 42;
  _stick.tag = 11;
  [_stick addGestureRecognizer:[[UIPanGestureRecognizer alloc] initWithTarget:self action:@selector(moveStick:)]];
  _stickLabel = [[UILabel alloc] initWithFrame:CGRectMake(0, 0, 84, 84)];
  _stickLabel.text = @"L";
  _stickLabel.textAlignment = NSTextAlignmentCenter;
  _stickLabel.textColor = UIColor.whiteColor;
  [_stick addSubview:_stickLabel];
  [_items addObject:_stick];
  [self addSubview:_stick];
  [NSNotificationCenter.defaultCenter addObserver:self selector:@selector(controllersChanged:) name:GCControllerDidConnectNotification object:nil];
  [NSNotificationCenter.defaultCenter addObserver:self selector:@selector(controllersChanged:) name:GCControllerDidDisconnectNotification object:nil];
  [self controllersChanged:nil];
  return self;
}
- (void)dealloc {
  _controller.extendedGamepad.valueChangedHandler = nil;
  [NSNotificationCenter.defaultCenter removeObserver:self];
}
- (void)setControlScale:(CGFloat)value { _controlScale = MIN(1.4, MAX(.65, value)); [self setNeedsLayout]; }
- (void)setControlOpacity:(CGFloat)value { _controlOpacity = MIN(1, MAX(.2, value)); [self setNeedsLayout]; }
- (void)setEditingControls:(BOOL)value {
  _editingControls = value;
  for (UIView *item in _items) if (item != _stick)
    for (UIGestureRecognizer *gesture in item.gestureRecognizers) gesture.enabled = value;
  [self resetInput];
}
- (void)layoutSubviews {
  [super layoutSubviews];
  const CGPoint defaults[] = {{.82,.72},{.92,.50},{.72,.50},{.82,.28},{.12,.13},{.88,.13},{.27,.13},{.73,.13},{.57,.80},{.43,.80},{.20,.57}};
  NSDictionary *saved = [NSUserDefaults.standardUserDefaults dictionaryForKey:@"touchPositions"];
  for (NSUInteger i = 0; i < _items.count; ++i) {
    UIView *view = _items[i];
    NSArray *point = saved[[NSString stringWithFormat:@"%lu", (unsigned long)i]];
    CGPoint position = defaults[i];
    if (point.count == 2) position = CGPointMake([point[0] doubleValue], [point[1] doubleValue]);
    CGFloat width = view == _stick ? 84 : ((i == 8 || i == 9) ? 58 : 42);
    view.bounds = CGRectMake(0, 0, width, view == _stick ? 84 : 42);
    view.transform = CGAffineTransformMakeScale(_controlScale, _controlScale);
    view.center = CGPointMake(MIN(self.bounds.size.width - width * _controlScale / 2, MAX(width * _controlScale / 2, position.x * self.bounds.size.width)),
                              MIN(self.bounds.size.height - 42 * _controlScale, MAX(42 * _controlScale, position.y * self.bounds.size.height)));
    view.alpha = _controlOpacity;
  }
}
- (void)emit {
  if (self.inputChanged) self.inputChanged(_touchButtons | _physicalButtons,
      fabsf(_physicalLX) > .1f ? _physicalLX : _touchLX,
      fabsf(_physicalLY) > .1f ? _physicalLY : _touchLY,
      _physicalRX, _physicalRY, MAX(_touchLT, _physicalLT), MAX(_touchRT, _physicalRT));
}
- (void)touchDown:(UIButton *)button {
  if (_editingControls) return;
  static const uint32_t bits[] = {1u<<12, 1u<<13, 1u<<14, 1u<<15, 1u<<8, 1u<<9, 0, 0, 1u<<4, 1u<<5};
  _touchButtons |= bits[button.tag - 1];
  if (button.tag == 7) _touchLT = 1;
  if (button.tag == 8) _touchRT = 1;
  [_haptic impactOccurred];
  [self emit];
}
- (void)touchUp:(UIButton *)button {
  static const uint32_t bits[] = {1u<<12, 1u<<13, 1u<<14, 1u<<15, 1u<<8, 1u<<9, 0, 0, 1u<<4, 1u<<5};
  _touchButtons &= ~bits[button.tag - 1];
  if (button.tag == 7) _touchLT = 0;
  if (button.tag == 8) _touchRT = 0;
  [self emit];
}
- (void)moveControl:(UIPanGestureRecognizer *)gesture {
  if (!_editingControls) return;
  UIView *item = gesture.view;
  CGPoint delta = [gesture translationInView:self];
  item.center = CGPointMake(MIN(self.bounds.size.width - item.frame.size.width / 2, MAX(item.frame.size.width / 2, item.center.x + delta.x)),
                            MIN(self.bounds.size.height - item.frame.size.height / 2, MAX(item.frame.size.height / 2, item.center.y + delta.y)));
  [gesture setTranslation:CGPointZero inView:self];
  if (gesture.state == UIGestureRecognizerStateEnded || gesture.state == UIGestureRecognizerStateCancelled) {
    NSMutableDictionary *positions = [[NSUserDefaults.standardUserDefaults dictionaryForKey:@"touchPositions"] mutableCopy] ?: [NSMutableDictionary dictionary];
    positions[[NSString stringWithFormat:@"%ld", (long)item.tag - 1]] = @[@(item.center.x / MAX(1, self.bounds.size.width)), @(item.center.y / MAX(1, self.bounds.size.height))];
    [NSUserDefaults.standardUserDefaults setObject:positions forKey:@"touchPositions"];
  }
}
- (void)moveStick:(UIPanGestureRecognizer *)gesture {
  if (_editingControls) { [self moveControl:gesture]; return; }
  CGPoint p = [gesture locationInView:_stick];
  float x = (p.x - 42) / 42, y = (42 - p.y) / 42;
  float magnitude = sqrtf(x*x + y*y);
  if (magnitude > 1) { x /= magnitude; y /= magnitude; }
  if (gesture.state == UIGestureRecognizerStateEnded || gesture.state == UIGestureRecognizerStateCancelled || gesture.state == UIGestureRecognizerStateFailed) x = y = 0;
  _touchLX = x; _touchLY = y;
  _stickLabel.transform = CGAffineTransformMakeTranslation(x * 16, -y * 16);
  [self emit];
}
- (void)controllersChanged:(NSNotification *)notification {
  (void)notification;
  _controller.extendedGamepad.valueChangedHandler = nil;
  _controller = nil;
  [self resetInput];
  for (GCController *controller in GCController.controllers) if (controller.extendedGamepad) { _controller = controller; break; }
  _controller.handlerQueue = dispatch_get_main_queue();
  __weak StormControls *weakSelf = self;
  _controller.extendedGamepad.valueChangedHandler = ^(GCExtendedGamepad *pad, GCControllerElement *element) {
    (void)element;
    StormControls *self = weakSelf;
    if (!self) return;
    uint32_t b = 0;
    if (pad.dpad.up.pressed) b |= 1u<<0;
    if (pad.dpad.down.pressed) b |= 1u<<1;
    if (pad.dpad.left.pressed) b |= 1u<<2;
    if (pad.dpad.right.pressed) b |= 1u<<3;
    if (pad.buttonMenu.pressed) b |= 1u<<4;
    if (pad.buttonOptions.pressed) b |= 1u<<5;
    if (pad.leftThumbstickButton.pressed) b |= 1u<<6;
    if (pad.rightThumbstickButton.pressed) b |= 1u<<7;
    if (pad.leftShoulder.pressed) b |= 1u<<8;
    if (pad.rightShoulder.pressed) b |= 1u<<9;
    if (pad.buttonA.pressed) b |= 1u<<12;
    if (pad.buttonB.pressed) b |= 1u<<13;
    if (pad.buttonX.pressed) b |= 1u<<14;
    if (pad.buttonY.pressed) b |= 1u<<15;
    self->_physicalButtons = b;
    self->_physicalLX = pad.leftThumbstick.xAxis.value;
    self->_physicalLY = pad.leftThumbstick.yAxis.value;
    self->_physicalRX = pad.rightThumbstick.xAxis.value;
    self->_physicalRY = pad.rightThumbstick.yAxis.value;
    self->_physicalLT = pad.leftTrigger.value;
    self->_physicalRT = pad.rightTrigger.value;
    [self emit];
  };
}
- (void)resetInput {
  _touchButtons = _physicalButtons = 0;
  _touchLX = _touchLY = _touchLT = _touchRT = 0;
  _physicalLX = _physicalLY = _physicalRX = _physicalRY = _physicalLT = _physicalRT = 0;
  _stickLabel.transform = CGAffineTransformIdentity;
  [self emit];
}
@end
