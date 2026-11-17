#import <Foundation/Foundation.h>

@interface StormNativeMetrics : NSObject
- (void)addStatistics:(NSDictionary *)statistics overlayOpen:(BOOL)overlayOpen;
- (NSDictionary *)report;
@end
