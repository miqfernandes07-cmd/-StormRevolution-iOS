#import "StormNativePreferences.h"

@implementation StormNativePreferences
+ (NSDictionary *)values {
  NSMutableDictionary *values = [@{@"playstation":@YES, @"mobile":@YES,
    @"scale":@1.0, @"opacity":@0.55, @"touch":@YES, @"haptics":@NO,
    @"fill":@YES, @"compatible":@YES, @"async":@NO, @"fps":@30,
    @"resolution":@"1280x720", @"renderScale":@1, @"anisotropy":@2,
    @"fxaa":@NO, @"stats":@NO, @"clearCache":@NO} mutableCopy];
  NSDictionary *saved = [NSUserDefaults.standardUserDefaults dictionaryForKey:@"StormNativePreferencesV3"];
  for (NSString *key in values.allKeys) {
    id value = saved[key];
    if (([values[key] isKindOfClass:NSString.class] && [value isKindOfClass:NSString.class]) ||
        ([values[key] isKindOfClass:NSNumber.class] && [value isKindOfClass:NSNumber.class])) values[key] = value;
  }
  return values;
}
+ (void)setValue:(id)value forKey:(NSString *)key {
  NSMutableDictionary *values = [[self values] mutableCopy];
  if (value) values[key] = value;
  [NSUserDefaults.standardUserDefaults setObject:values forKey:@"StormNativePreferencesV3"];
}
+ (NSDictionary<NSString *,NSString *> *)runtimeValues {
  NSDictionary *v = [self values];
  BOOL compatible = [v[@"compatible"] boolValue];
  NSInteger scale = [v[@"renderScale"] integerValue] == 2 ? 2 : 1;
  NSInteger fps = [v[@"fps"] integerValue] == 60 ? 60 : 30;
  NSInteger anisotropy = [v[@"anisotropy"] integerValue];
  if (anisotropy != 0 && anisotropy != 2 && anisotropy != 3) anisotropy = 2;
  NSString *resolution = [v[@"resolution"] isEqual:@"640x480"] ? @"640x480" : @"1280x720";
  return @{
    @"gpu.xenos.present_letterbox": [v[@"fill"] boolValue] ? @"false" : @"true",
    @"gpu.xenos.present_safe_area_x":@"100", @"gpu.xenos.present_safe_area_y":@"100",
    @"gpu.vulkan.render_target_path": compatible ? @"fsi" : @"",
    @"runtime.title_memory_mb":compatible ? @"512" : @"480",
    @"gpu.xenos.async_shader_compilation": [v[@"async"] boolValue] ? @"true" : @"false",
    @"gpu.vulkan.async_skip_incomplete_frames":@"false",
    @"gpu.xenos.readback_resolve": compatible ? @"full" : @"none",
    @"gpu.vulkan.readback_resolve": compatible ? @"true" : @"false",
    @"gpu.xenos.readback_memexport":@"true", @"gpu.xenos.readback_memexport_fast":@"false",
    @"gpu.xenos.force_convert_quad_lists_to_triangle_lists":@"true",
    @"gpu.xenos.force_convert_triangle_fans_to_lists":@"true",
    @"gpu.xenos.force_convert_line_loops_to_strips":@"true",
    @"gpu.xenos.texture_cache_memory_limit_soft":@"256",
    @"gpu.xenos.texture_cache_memory_limit_hard":@"384",
    @"gpu.vulkan.pipeline_creation_threads":@"2",
    @"gpu.frame_limit":[NSString stringWithFormat:@"%ld", (long)fps],
    @"gpu.vsync":@"true", @"gpu.anisotropic_override":[NSString stringWithFormat:@"%ld",(long)anisotropy],
    @"gpu.resolution_scale_x":[NSString stringWithFormat:@"%ld",(long)scale],
    @"gpu.resolution_scale_y":[NSString stringWithFormat:@"%ld",(long)scale],
    @"gpu.xenos.swap_post_effect":[v[@"fxaa"] boolValue] ? @"fxaa" : @"none",
    @"ui.resolution":resolution};
}
@end
