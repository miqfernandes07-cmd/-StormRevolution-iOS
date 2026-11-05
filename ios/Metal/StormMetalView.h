#import <MetalKit/MetalKit.h>
@interface StormMetalView : MTKView <MTKViewDelegate>
@property(nonatomic, copy) void (^diagnosticCompletion)(BOOL, NSString *);
@property(nonatomic) CGFloat resolutionScale;
@property(nonatomic) BOOL adaptiveResolution;
@property(nonatomic, readonly) double lastGPUTimeMilliseconds;
- (void)applyResolution;
@end
