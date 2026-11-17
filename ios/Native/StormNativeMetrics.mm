#import "StormNativeMetrics.h"
#include <cmath>

@implementation StormNativeMetrics {
  NSMutableArray<NSDictionary *> *_samples;
}
- (instancetype)init {
  if ((self = [super init])) _samples = [NSMutableArray array];
  return self;
}
- (void)addStatistics:(NSDictionary *)statistics overlayOpen:(BOOL)overlayOpen {
  double fps = [statistics[@"fps"] doubleValue], milliseconds = [statistics[@"frameTimeMs"] doubleValue];
  if (!std::isfinite(fps) || fps <= 0 || !std::isfinite(milliseconds) || milliseconds < 0) return;
  NSString *thermal = @"unknown";
  switch (NSProcessInfo.processInfo.thermalState) {
    case NSProcessInfoThermalStateNominal: thermal = @"nominal"; break;
    case NSProcessInfoThermalStateFair: thermal = @"fair"; break;
    case NSProcessInfoThermalStateSerious: thermal = @"serious"; break;
    case NSProcessInfoThermalStateCritical: thermal = @"critical"; break;
  }
  [_samples addObject:@{@"time":@(NSDate.date.timeIntervalSince1970), @"fps":@(fps),
    @"frameTimeMs":@(milliseconds), @"frameCount":statistics[@"frames"] ?: @0,
    @"overlayOpen":@(overlayOpen), @"thermalState":thermal,
    @"lowPowerMode":@(NSProcessInfo.processInfo.lowPowerModeEnabled)}];
  if (_samples.count > 60) [_samples removeObjectAtIndex:0];
}
- (NSDictionary *)report {
  NSMutableArray<NSNumber *> *fps = [NSMutableArray array];
  for (NSDictionary *sample in _samples) if (![sample[@"overlayOpen"] boolValue]) [fps addObject:sample[@"fps"]];
  [fps sortUsingSelector:@selector(compare:)];
  NSMutableDictionary *summary = [@{@"count":@(fps.count)} mutableCopy];
  if (fps.count) {
    double sum = 0; for (NSNumber *value in fps) sum += value.doubleValue;
    summary[@"minFps"] = fps.firstObject; summary[@"maxFps"] = fps.lastObject;
    summary[@"medianFps"] = fps[fps.count/2]; summary[@"meanFps"] = @(sum/fps.count);
  }
  return @{@"scope":@"SDK presentation statistics, not separate CPU/GPU profiling; includes game menus and pauses",
    @"capacity":@60, @"summaryExcludingOverlay":summary, @"samples":[_samples copy]};
}
@end
