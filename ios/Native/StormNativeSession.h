#import <UIKit/UIKit.h>

@interface StormNativeSession : NSObject
@property(nonatomic, readonly) BOOL ready;
@property(nonatomic, readonly) BOOL launchRequested;
@property(nonatomic, copy) void (^overlayChanged)(BOOL visible);
@property(nonatomic, copy) NSDictionary * (^frameStatistics)(void);
- (instancetype)initWithWindow:(UIWindow *)window;
- (BOOL)attachControls;
- (void)showFailure:(NSString *)message;
- (void)invalidate;
@end
