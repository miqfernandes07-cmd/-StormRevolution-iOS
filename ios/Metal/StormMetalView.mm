#import "Metal/StormMetalView.h"

@implementation StormMetalView {
  id<MTLCommandQueue> _queue;
  id<MTLRenderPipelineState> _pipeline;
  dispatch_semaphore_t _inFlight;
  BOOL _reported;
  NSString *_initializationError;
  double _lastGPUTimeMilliseconds;
  NSUInteger _completedFrames;
}
- (instancetype)initWithFrame:(CGRect)frame {
  self = [super initWithFrame:frame device:MTLCreateSystemDefaultDevice()];
  if (!self) return nil;
  self.delegate = self;
  self.preferredFramesPerSecond = 30;
  self.colorPixelFormat = MTLPixelFormatBGRA8Unorm;
  self.clearColor = MTLClearColorMake(.03, .04, .08, 1);
  self.autoResizeDrawable = NO;
  _resolutionScale = 1;
  _inFlight = dispatch_semaphore_create(3);
  _queue = [self.device newCommandQueue];
  NSError *error = nil;
  NSURL *libraryURL = [NSBundle.mainBundle URLForResource:@"default" withExtension:@"metallib"];
  id<MTLLibrary> library = libraryURL ? [self.device newLibraryWithURL:libraryURL error:&error] : nil;
  MTLRenderPipelineDescriptor *descriptor = [[MTLRenderPipelineDescriptor alloc] init];
  descriptor.vertexFunction = [library newFunctionWithName:@"diagnostic_vertex"];
  descriptor.fragmentFunction = [library newFunctionWithName:@"diagnostic_fragment"];
  descriptor.colorAttachments[0].pixelFormat = self.colorPixelFormat;
  if (descriptor.vertexFunction && descriptor.fragmentFunction)
    _pipeline = [self.device newRenderPipelineStateWithDescriptor:descriptor error:&error];
  if (!_pipeline || !_queue) _initializationError = error.localizedDescription ?: @"Metal device/library unavailable";
  return self;
}
- (double)lastGPUTimeMilliseconds { return _lastGPUTimeMilliseconds; }
- (void)layoutSubviews { [super layoutSubviews]; [self applyResolution]; }
- (void)applyResolution {
  CGFloat scale = self.window.screen.scale ?: UIScreen.mainScreen.scale;
  self.drawableSize = CGSizeMake(MAX(1, self.bounds.size.width * scale * _resolutionScale),
                                MAX(1, self.bounds.size.height * scale * _resolutionScale));
}
- (void)mtkView:(MTKView *)view drawableSizeWillChange:(CGSize)size { (void)view; (void)size; }
- (void)drawInMTKView:(MTKView *)view {
  if (_initializationError) {
    if (!_reported && self.diagnosticCompletion) { _reported = YES; self.diagnosticCompletion(NO, _initializationError); }
    return;
  }
  if (dispatch_semaphore_wait(_inFlight, DISPATCH_TIME_NOW) != 0) return;
  MTLRenderPassDescriptor *pass = view.currentRenderPassDescriptor;
  id<CAMetalDrawable> drawable = view.currentDrawable;
  if (!pass || !drawable) { dispatch_semaphore_signal(_inFlight); return; }
  id<MTLCommandBuffer> command = [_queue commandBuffer];
  id<MTLRenderCommandEncoder> encoder = [command renderCommandEncoderWithDescriptor:pass];
  if (!command || !encoder) { dispatch_semaphore_signal(_inFlight); return; }
  [encoder setRenderPipelineState:_pipeline];
  [encoder drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:0 vertexCount:3];
  [encoder endEncoding];
  [command presentDrawable:drawable];
  __weak StormMetalView *weakSelf = self;
  dispatch_semaphore_t semaphore = _inFlight;
  [command addCompletedHandler:^(id<MTLCommandBuffer> result) {
    dispatch_semaphore_signal(semaphore);
    BOOL passed = result.status == MTLCommandBufferStatusCompleted;
    double gpuMS = (result.GPUEndTime - result.GPUStartTime) * 1000;
    dispatch_async(dispatch_get_main_queue(), ^{
      StormMetalView *strongSelf = weakSelf;
      if (!strongSelf) return;
      strongSelf->_lastGPUTimeMilliseconds = gpuMS;
      if (!strongSelf->_reported && strongSelf.diagnosticCompletion) {
        strongSelf->_reported = YES;
        strongSelf.diagnosticCompletion(passed, passed ? @"Metal diagnostic command completed (not game rendering)" : result.error.localizedDescription);
      }
      if (strongSelf.adaptiveResolution && ++strongSelf->_completedFrames % 60 == 0 && gpuMS > 0) {
        double budget = 1000.0 / strongSelf.preferredFramesPerSecond;
        CGFloat delta = gpuMS > budget * .9 ? -.05 : (gpuMS < budget * .6 ? .025 : 0);
        strongSelf.resolutionScale = MIN(1, MAX(.5, strongSelf.resolutionScale + delta));
        [strongSelf applyResolution];
      }
    });
  }];
  [command commit];
}
@end
