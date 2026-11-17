#import <Foundation/Foundation.h>

@interface StormNativePreferences : NSObject
+ (NSDictionary<NSString *, id> *)values;
+ (void)setValue:(id)value forKey:(NSString *)key;
+ (NSDictionary<NSString *, NSString *> *)runtimeValues;
@end
