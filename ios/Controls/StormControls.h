#import <UIKit/UIKit.h>
#include <stdint.h>

@interface StormControls : UIView
@property(nonatomic, copy) void (^inputChanged)(uint32_t, float, float, float, float, float, float);
// Status and input callbacks are delivered on the main queue. Pairing belongs
// to iOS Settings; this view accepts supported extended GameController profiles.
@property(nonatomic, copy) void (^connectionChanged)(NSString *);
@property(nonatomic, copy, readonly) NSString *connectionDescription;
@property(nonatomic) BOOL editingControls;
@property(nonatomic) CGFloat controlScale;
@property(nonatomic) CGFloat controlOpacity;
- (void)resetInput;
- (void)resetLayout;
@end
