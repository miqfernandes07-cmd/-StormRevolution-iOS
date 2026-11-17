#import <UIKit/UIKit.h>

@interface StormNativeHome : UIView
@property(nonatomic, strong, readonly) UILabel *statusLabel;
@property(nonatomic, strong, readonly) UIButton *playButton;
@property(nonatomic, strong, readonly) UIButton *importButton;
@property(nonatomic, strong, readonly) UIButton *optionsButton;
- (void)refreshLanguage;
@end
