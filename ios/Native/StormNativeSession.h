#import <UIKit/UIKit.h>

@interface StormNativeSession : NSObject
@property(nonatomic, readonly) BOOL ready;
- (instancetype)initWithWindow:(UIWindow *)window;
- (BOOL)attachControls;
- (void)showFailure:(NSString *)message;
- (void)invalidate;
@end
