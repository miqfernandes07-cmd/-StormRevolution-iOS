#import "StormNativeMetrics.h"
#include <cmath>
#import <os/proc.h>
#import <mach/mach.h>

@implementation StormNativeMetrics {
  NSMutableArray<NSDictionary *> *_samples;
  NSTimeInterval _lastSampleUptime;
  NSNumber *_lastFrameCount;
}
- (instancetype)init {
  if ((self = [super init])) _samples = [NSMutableArray array];
  return self;
}
- (void)addStatistics:(NSDictionary *)statistics overlayOpen:(BOOL)overlayOpen {
  double fps = [statistics[@"fps"] doubleValue], milliseconds = [statistics[@"frameTimeMs"] doubleValue];
  if (!std::isfinite(fps) || (fps < 0 || (fps == 0 && !_lastFrameCount)) || !std::isfinite(milliseconds) || milliseconds < 0) return;
  task_vm_info_data_t memory = {};
  mach_msg_type_number_t count = TASK_VM_INFO_COUNT;
  BOOL hasFootprint = task_info(mach_task_self(), TASK_VM_INFO, (task_info_t)&memory, &count) == KERN_SUCCESS;
  NSString *thermal = @"unknown";
  switch (NSProcessInfo.processInfo.thermalState) {
    case NSProcessInfoThermalStateNominal: thermal = @"nominal"; break;
    case NSProcessInfoThermalStateFair: thermal = @"fair"; break;
    case NSProcessInfoThermalStateSerious: thermal = @"serious"; break;
    case NSProcessInfoThermalStateCritical: thermal = @"critical"; break;
  }
  NSNumber *frameCount = statistics[@"frames"];
  NSTimeInterval uptime = NSProcessInfo.processInfo.systemUptime;
  NSTimeInterval elapsed = uptime - _lastSampleUptime;
  NSMutableDictionary *sample = [@{@"time":@(NSDate.date.timeIntervalSince1970), @"fps":@(fps),
    @"frameTimeMs":@(milliseconds), @"frameCount":frameCount ?: @0,
    @"overlayOpen":@(overlayOpen), @"thermalState":thermal,
    @"lowPowerMode":@(NSProcessInfo.processInfo.lowPowerModeEnabled),
    @"memoryAvailableMB":@(os_proc_available_memory()/(1024*1024)),
    @"processFootprintMB":hasFootprint ? @(memory.phys_footprint/(1024.0*1024.0)) : NSNull.null} mutableCopy];
  if (frameCount && _lastFrameCount && elapsed > 0 &&
      frameCount.unsignedLongLongValue >= _lastFrameCount.unsignedLongLongValue) {
    unsigned long long delta = frameCount.unsignedLongLongValue - _lastFrameCount.unsignedLongLongValue;
    sample[@"frameDelta"] = @(delta);
    sample[@"sampleIntervalMs"] = @(elapsed * 1000);
    sample[@"intervalFps"] = @(delta / elapsed);
  }
  _lastSampleUptime = uptime;
  _lastFrameCount = frameCount;
  [_samples addObject:sample];
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
