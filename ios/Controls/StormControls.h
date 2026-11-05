#import <UIKit/UIKit.h>
#include <stdint.h>

@interface StormControls : UIView
@property(nonatomic, copy) void (^inputChanged)(uint32_t, float, float, float, float, float, float);
@property(nonatomic) BOOL editingControls;
@property(nonatomic) CGFloat controlScale;
@property(nonatomic) CGFloat controlOpacity;
- (void)resetInput;
@end
