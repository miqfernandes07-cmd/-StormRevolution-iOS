#import "StormNativeHome.h"
#import <QuartzCore/QuartzCore.h>

namespace {
UIColor *Ink(CGFloat r, CGFloat g, CGFloat b) { return [UIColor colorWithRed:r green:g blue:b alpha:1]; }
UILabel *Text(NSString *text, CGFloat size, UIFontWeight weight, UIColor *color) {
  UILabel *label = [UILabel new]; label.text = text; label.textColor = color;
  label.font = [UIFont systemFontOfSize:size weight:weight];
  label.adjustsFontSizeToFitWidth = YES; label.minimumScaleFactor = .8;
  return label;
}
UIView *Card(UIColor *color, CGFloat radius) {
  UIView *view = [UIView new]; view.backgroundColor = color;
  view.layer.cornerRadius = radius; view.layer.cornerCurve = kCACornerCurveContinuous;
  view.layer.borderColor = [UIColor colorWithWhite:1 alpha:.08].CGColor;
  view.layer.borderWidth = 1; view.clipsToBounds = YES; return view;
}
}

@implementation StormNativeHome {
  CAGradientLayer *_background;
  CAGradientLayer *_heroGradient;
  CAShapeLayer *_orbit;
  UIView *_hero;
  UIView *_library;
  UILabel *_brand;
  UILabel *_collection;
  UILabel *_eyebrow;
  UILabel *_title;
  UILabel *_subtitle;
  UILabel *_libraryTitle;
  UILabel *_credit;
  UILabel *_version;
  UIImageView *_emblem;
  UIImageView *_folder;
}
- (instancetype)initWithFrame:(CGRect)frame {
  if (!(self = [super initWithFrame:frame])) return nil;
  self.accessibilityIdentifier = @"native-home";
  self.overrideUserInterfaceStyle = UIUserInterfaceStyleDark;
  _background = [CAGradientLayer layer];
  _background.colors = @[(id)Ink(.025,.04,.07).CGColor,(id)Ink(.06,.10,.17).CGColor];
  _background.startPoint = CGPointMake(0,1); _background.endPoint = CGPointMake(1,0);
  [self.layer addSublayer:_background];
  _brand = Text(@"STORM  /  REVOLUTION",15,UIFontWeightHeavy,UIColor.whiteColor);
  _collection = Text(@"SUA BIBLIOTECA",10,UIFontWeightSemibold,Ink(.50,.65,.78));
  _collection.textAlignment = NSTextAlignmentRight;
  [self addSubview:_brand]; [self addSubview:_collection];
  _hero = Card(Ink(.10,.14,.21),26); [self addSubview:_hero];
  _heroGradient = [CAGradientLayer layer];
  _heroGradient.colors = @[(id)Ink(.09,.13,.20).CGColor,(id)Ink(.20,.16,.17).CGColor];
  _heroGradient.startPoint = CGPointMake(0,.5); _heroGradient.endPoint = CGPointMake(1,0);
  [_hero.layer insertSublayer:_heroGradient atIndex:0];
  _orbit = [CAShapeLayer layer]; _orbit.strokeColor = [UIColor colorWithRed:1 green:.63 blue:.30 alpha:.14].CGColor;
  _orbit.lineWidth = 1; _orbit.fillColor = UIColor.clearColor.CGColor; [_hero.layer addSublayer:_orbit];
  _emblem = [[UIImageView alloc] initWithImage:[UIImage systemImageNamed:@"flame.fill"]];
  _emblem.contentMode = UIViewContentModeScaleAspectFit; _emblem.tintColor = Ink(1,.62,.32); _emblem.alpha = .18;
  _emblem.isAccessibilityElement = NO; [_hero addSubview:_emblem];
  _eyebrow = Text(@"A PRÓXIMA BATALHA É SUA",10,UIFontWeightBold,Ink(1,.71,.48)); [_hero addSubview:_eyebrow];
  _title = Text(@"STORM\nREVOLUTION",38,UIFontWeightHeavy,UIColor.whiteColor);
  _title.numberOfLines = 2; _title.accessibilityLabel = @"Storm Revolution"; [_hero addSubview:_title];
  _subtitle = Text(@"Sua arena. Seu controle.",13,UIFontWeightRegular,Ink(.68,.73,.81)); [_hero addSubview:_subtitle];
  _playButton = [UIButton buttonWithType:UIButtonTypeSystem];
  UIButtonConfiguration *play = [UIButtonConfiguration filledButtonConfiguration];
  play.title = @"Jogar"; play.image = [UIImage systemImageNamed:@"play.fill"]; play.imagePadding = 10;
  play.baseBackgroundColor = Ink(1,.64,.35); play.baseForegroundColor = Ink(.08,.055,.04);
  play.background.cornerRadius = 15;
  play.titleTextAttributesTransformer = ^NSDictionary *(NSDictionary *attributes) {
    NSMutableDictionary *result = attributes.mutableCopy; result[NSFontAttributeName] = [UIFont systemFontOfSize:16 weight:UIFontWeightBold]; return result;
  };
  _playButton.configuration = play; _playButton.enabled = NO; _playButton.accessibilityIdentifier = @"home-play";
  [_hero addSubview:_playButton];
  _library = Card(Ink(.08,.12,.18),22); [self addSubview:_library];
  _folder = [[UIImageView alloc] initWithImage:[UIImage systemImageNamed:@"folder.fill"]];
  _folder.tintColor = Ink(.50,.75,1); _folder.contentMode = UIViewContentModeScaleAspectFit; [_library addSubview:_folder];
  _libraryTitle = Text(@"SEU JOGO",10,UIFontWeightBold,Ink(.55,.70,.83)); [_library addSubview:_libraryTitle];
  _statusLabel = Text(@"Verificando os arquivos…",13,UIFontWeightMedium,Ink(.88,.91,.96));
  _statusLabel.numberOfLines = 3; _statusLabel.accessibilityIdentifier = @"home-status"; [_library addSubview:_statusLabel];
  _importButton = [UIButton buttonWithType:UIButtonTypeSystem];
  UIButtonConfiguration *importConfiguration = [UIButtonConfiguration plainButtonConfiguration];
  importConfiguration.title = @"Importar ZIP"; importConfiguration.image = [UIImage systemImageNamed:@"plus.circle.fill"]; importConfiguration.imagePadding = 7;
  importConfiguration.contentInsets = NSDirectionalEdgeInsetsMake(0,0,0,0); importConfiguration.baseForegroundColor = Ink(.51,.76,1);
  _importButton.configuration = importConfiguration; _importButton.contentHorizontalAlignment = UIControlContentHorizontalAlignmentLeft;
  _importButton.enabled = NO; _importButton.accessibilityIdentifier = @"home-import"; [_library addSubview:_importButton];
  _optionsButton = [UIButton buttonWithType:UIButtonTypeSystem];
  UIButtonConfiguration *settings = [UIButtonConfiguration tintedButtonConfiguration];
  settings.title = @"Do seu jeito"; settings.subtitle = @"Controles e gráficos";
  settings.image = [UIImage systemImageNamed:@"slider.horizontal.3"]; settings.imagePadding = 12;
  settings.titleAlignment = UIButtonConfigurationTitleAlignmentLeading;
  settings.contentInsets = NSDirectionalEdgeInsetsMake(14,16,14,12);
  settings.baseForegroundColor = Ink(.82,.91,1); settings.baseBackgroundColor = Ink(.18,.30,.44);
  settings.background.cornerRadius = 22;
  _optionsButton.configuration = settings; _optionsButton.contentHorizontalAlignment = UIControlContentHorizontalAlignmentLeft;
  _optionsButton.accessibilityIdentifier = @"home-options"; [self addSubview:_optionsButton];
  _credit = Text(@"Créditos  /  MiquéiasF07",11,UIFontWeightMedium,Ink(.58,.64,.73)); [self addSubview:_credit];
  NSString *version = [NSBundle.mainBundle objectForInfoDictionaryKey:@"CFBundleShortVersionString"] ?: @"0.4.1";
  _version = Text([@"v" stringByAppendingString:version],11,UIFontWeightMedium,Ink(.44,.52,.64));
  _version.textAlignment = NSTextAlignmentRight; [self addSubview:_version];
  return self;
}
- (void)layoutSubviews {
  [super layoutSubviews];
  _background.frame = self.bounds;
  CGRect safe = UIEdgeInsetsInsetRect(self.bounds,self.safeAreaInsets);
  CGFloat margin = safe.size.height < 350 ? 14 : 20;
  CGRect content = CGRectInset(safe,margin,margin);
  CGFloat gap = 14, top = CGRectGetMinY(content), left = CGRectGetMinX(content), width = content.size.width;
  _brand.frame = CGRectMake(left,top,width*.65,24);
  _collection.frame = CGRectMake(left+width*.65,top,width*.35,24);
  CGFloat mainTop = top+38, mainHeight = MAX(160,content.size.height-66);
  CGFloat heroWidth = (width-gap)*.61, sideLeft = left+heroWidth+gap, sideWidth = width-heroWidth-gap;
  _hero.frame = CGRectMake(left,mainTop,heroWidth,mainHeight);
  _heroGradient.frame = _hero.bounds;
  CGFloat pad = mainHeight < 220 ? 18 : 24;
  _eyebrow.frame = CGRectMake(pad,18,heroWidth-pad*2,16);
  CGFloat titleHeight = mainHeight < 220 ? 70 : 92;
  _title.font = [UIFont systemFontOfSize:mainHeight < 220 ? 29 : 38 weight:UIFontWeightHeavy];
  _title.frame = CGRectMake(pad,39,heroWidth-pad*2,titleHeight);
  _subtitle.frame = CGRectMake(pad,39+titleHeight+5,heroWidth-pad*2,20);
  _playButton.frame = CGRectMake(pad,mainHeight-62,142,44);
  _emblem.frame = CGRectMake(heroWidth*.58,mainHeight*.10,heroWidth*.48,mainHeight*.75);
  UIBezierPath *rings = [UIBezierPath bezierPath];
  for (int i=0;i<4;i++) { CGFloat diameter=mainHeight*.68+i*42; [rings appendPath:[UIBezierPath bezierPathWithOvalInRect:CGRectMake(heroWidth*.92-diameter/2,mainHeight*.38-diameter/2,diameter,diameter)]]; }
  _orbit.path = rings.CGPath;
  CGFloat settingsHeight = 78, libraryHeight = mainHeight-settingsHeight-gap;
  _library.frame = CGRectMake(sideLeft,mainTop,sideWidth,libraryHeight);
  _folder.frame = CGRectMake(16,15,20,20); _libraryTitle.frame = CGRectMake(44,16,sideWidth-60,18);
  _statusLabel.frame = CGRectMake(16,42,sideWidth-32,MAX(20,libraryHeight-96));
  _importButton.frame = CGRectMake(16,libraryHeight-48,sideWidth-32,44);
  _optionsButton.frame = CGRectMake(sideLeft,mainTop+libraryHeight+gap,sideWidth,settingsHeight);
  CGFloat footer = CGRectGetMaxY(content)-18;
  _credit.frame = CGRectMake(left,footer,width*.8,18); _version.frame = CGRectMake(left+width*.8,footer,width*.2,18);
}
@end
