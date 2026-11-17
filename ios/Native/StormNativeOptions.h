#import <UIKit/UIKit.h>

@interface StormNativeOptions : UITableViewController
@property(nonatomic, copy) void (^changed)(NSString *key);
@property(nonatomic, copy) void (^editControls)(void);
@property(nonatomic, copy) void (^resetControls)(void);
@property(nonatomic, copy) void (^shareLogs)(UIViewController *presenter);
@property(nonatomic, copy) void (^closed)(void);
@end
