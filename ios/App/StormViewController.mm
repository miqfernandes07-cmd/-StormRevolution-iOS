#import "App/StormViewController.h"
#import "Metal/StormMetalView.h"
#import "Controls/StormControls.h"
#import "Import/StormGameImporter.h"
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>
#import <QuartzCore/QuartzCore.h>
#include "storm_runtime.h"

namespace {
UIColor *Background() { return [UIColor colorWithRed:.035 green:.055 blue:.085 alpha:1]; }
UIColor *Surface() { return [UIColor colorWithRed:.065 green:.09 blue:.135 alpha:1]; }
UIColor *Ink() { return [UIColor colorWithRed:.95 green:.96 blue:.98 alpha:1]; }
UIColor *Muted() { return [UIColor colorWithRed:.60 green:.66 blue:.76 alpha:1]; }
UIColor *Accent() { return [UIColor colorWithRed:1 green:.61 blue:.25 alpha:1]; }
UILabel *Text(NSString *value, UIFontTextStyle style, UIColor *color) {
  UILabel *label = [[UILabel alloc] init];
  label.text = value; label.numberOfLines = 0;
  label.font = [UIFont preferredFontForTextStyle:style];
  label.adjustsFontForContentSizeCategory = YES; label.textColor = color;
  return label;
}
UIStackView *Column(CGFloat spacing) {
  UIStackView *stack = [[UIStackView alloc] init];
  stack.axis = UILayoutConstraintAxisVertical; stack.spacing = spacing;
  return stack;
}
UIStackView *Card(void) {
  UIStackView *stack = Column(14);
  stack.backgroundColor = Surface(); stack.layer.cornerRadius = 24;
  stack.layer.borderWidth = 1;
  stack.layer.borderColor = [UIColor colorWithWhite:1 alpha:.075].CGColor;
  stack.layoutMarginsRelativeArrangement = YES;
  stack.directionalLayoutMargins = NSDirectionalEdgeInsetsMake(22, 20, 22, 20);
  return stack;
}
UILabel *Eyebrow(NSString *value) {
  UILabel *label = Text(value, UIFontTextStyleCaption2, Accent());
  label.font = [UIFont preferredFontForTextStyle:UIFontTextStyleCaption1];
  return label;
}
}

// Allow a vertical drag that starts on a button to become scrolling. Sliders
// and joystick pan recognizers retain their normal interaction semantics.
@interface StormScrollView : UIScrollView
@end
@implementation StormScrollView
- (BOOL)touchesShouldCancelInContentView:(UIView *)view {
  if ([view isKindOfClass:UIButton.class]) return YES;
  return [super touchesShouldCancelInContentView:view];
}
@end

@implementation StormViewController {
  StormRuntime *_runtime;
  StormMetalView *_metal;
  StormControls *_controls;
  StormGameImporter *_importer;
  UIScrollView *_scroll;
  UISegmentedControl *_navigation;
  NSArray<UIStackView *> *_pages;
  UIStackView *_pageHost;
  UIStackView *_importCard;
  UILabel *_status;
  UILabel *_credit;
  BOOL _scrollTestStarted;
  UILabel *_importTitle;
  UILabel *_progressLabel;
  UILabel *_controllerStatus;
  UILabel *_inputStatus;
  UILabel *_diagnosticStatus;
  UITextView *_logs;
  UIProgressView *_progress;
  UIStackView *_progressStack;
  UIButton *_importButton;
  UIButton *_cancelButton;
  UIButton *_launchButton;
  BOOL _identityMatches;
  BOOL _runtimeTestPassed;
  BOOL _smoke;
  BOOL _importing;
  NSUInteger _validationGeneration;
  CFTimeInterval _lastInputDisplay;
}

- (UIStatusBarStyle)preferredStatusBarStyle { return UIStatusBarStyleLightContent; }

- (void)viewDidLoad {
  [super viewDidLoad];
  self.overrideUserInterfaceStyle = UIUserInterfaceStyleDark;
  self.view.backgroundColor = Background();
  self.view.tintColor = Accent();
  _runtime = storm_runtime_create();
  _runtimeTestPassed = storm_runtime_self_test() == 0;
  _smoke = [NSProcessInfo.processInfo.arguments containsObject:@"--smoke-test"];
  _importer = [[StormGameImporter alloc] init];

  _navigation = [[UISegmentedControl alloc] initWithItems:@[@"Biblioteca", @"Controles", @"Ajustes"]];
  _navigation.accessibilityIdentifier = @"storm.navigation";
  _navigation.selectedSegmentTintColor = [UIColor colorWithRed:.18 green:.23 blue:.31 alpha:1];
  [_navigation setTitleTextAttributes:@{NSForegroundColorAttributeName:Muted()} forState:UIControlStateNormal];
  [_navigation setTitleTextAttributes:@{NSForegroundColorAttributeName:Ink()} forState:UIControlStateSelected];
  _navigation.selectedSegmentIndex = 0;
  _navigation.translatesAutoresizingMaskIntoConstraints = NO;
  [_navigation addTarget:self action:@selector(changePage:) forControlEvents:UIControlEventValueChanged];
  [self.view addSubview:_navigation];

  _scroll = [[StormScrollView alloc] init];
  _scroll.canCancelContentTouches = YES; _scroll.delaysContentTouches = YES;
  _scroll.alwaysBounceVertical = YES;
  _scroll.directionalLockEnabled = YES;
  _scroll.accessibilityIdentifier = @"storm.pageScroll";
  _scroll.translatesAutoresizingMaskIntoConstraints = NO;
  _scroll.showsVerticalScrollIndicator = YES;
  [self.view addSubview:_scroll];
  UIView *container = [[UIView alloc] init];
  container.translatesAutoresizingMaskIntoConstraints = NO;
  [_scroll addSubview:container];
  UIStackView *content = Column(24);
  content.translatesAutoresizingMaskIntoConstraints = NO;
  [container addSubview:content];
  NSLayoutConstraint *preferredWidth = [content.widthAnchor constraintEqualToAnchor:_scroll.frameLayoutGuide.widthAnchor constant:-40];
  preferredWidth.priority = 999;
  [NSLayoutConstraint activateConstraints:@[
    [_navigation.leadingAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.leadingAnchor constant:20],
    [_navigation.trailingAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.trailingAnchor constant:-20],
    [_navigation.bottomAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.bottomAnchor constant:-12],
    [_navigation.heightAnchor constraintGreaterThanOrEqualToConstant:44],
    [_scroll.topAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.topAnchor],
    [_scroll.bottomAnchor constraintEqualToAnchor:_navigation.topAnchor constant:-12],
    [_scroll.leadingAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.leadingAnchor],
    [_scroll.trailingAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.trailingAnchor],
    [container.leadingAnchor constraintEqualToAnchor:_scroll.contentLayoutGuide.leadingAnchor],
    [container.trailingAnchor constraintEqualToAnchor:_scroll.contentLayoutGuide.trailingAnchor],
    [container.topAnchor constraintEqualToAnchor:_scroll.contentLayoutGuide.topAnchor],
    [container.bottomAnchor constraintEqualToAnchor:_scroll.contentLayoutGuide.bottomAnchor],
    [container.widthAnchor constraintEqualToAnchor:_scroll.frameLayoutGuide.widthAnchor],
    [content.topAnchor constraintEqualToAnchor:container.topAnchor constant:24],
    [content.bottomAnchor constraintEqualToAnchor:container.bottomAnchor constant:-24],
    [content.leadingAnchor constraintGreaterThanOrEqualToAnchor:container.leadingAnchor constant:20],
    [content.trailingAnchor constraintLessThanOrEqualToAnchor:container.trailingAnchor constant:-20],
    [content.centerXAnchor constraintEqualToAnchor:container.centerXAnchor],
    [content.widthAnchor constraintLessThanOrEqualToConstant:720], preferredWidth
  ]];

  UIStackView *brand = Column(5);
  [brand addArrangedSubview:Eyebrow(@"PROJETO NATIVO · iOS")];
  UILabel *title = Text(@"STORM REVOLUTION", UIFontTextStyleTitle1, Ink());
  title.font = [[UIFontMetrics metricsForTextStyle:UIFontTextStyleTitle1] scaledFontForFont:[UIFont systemFontOfSize:28 weight:UIFontWeightHeavy]];
  title.accessibilityIdentifier = @"storm.brand";
  [brand addArrangedSubview:title];
  [content addArrangedSubview:brand];

  UIStackView *library = [self libraryPage];
  UIStackView *controls = [self controlsPage];
  UIStackView *settings = [self settingsPage];
  _pages = @[library, controls, settings];
  // Keep only the visible page in the stack. Hiding a nested stack would add a
  // zero-height constraint that conflicts with its fixed-height Metal/controls.
  _pageHost = Column(0);
  [content addArrangedSubview:_pageHost];
  UILabel *credit = Text(@"Projeto iOS desenvolvido por Miquéias", UIFontTextStyleFootnote, Muted());
  _credit = credit;
  credit.textAlignment = NSTextAlignmentCenter;
  credit.accessibilityIdentifier = @"storm.developerCredit";
  [content addArrangedSubview:credit];

  __weak StormViewController *weakSelf = self;
  _controls.inputChanged = ^(uint32_t buttons, float lx, float ly, float rx, float ry, float lt, float rt) {
    StormViewController *self = weakSelf;
    if (!self) return;
    if (self->_runtime) storm_runtime_set_input(self->_runtime, buttons, lx, ly, rx, ry, lt, rt);
    CFTimeInterval now = CACurrentMediaTime();
    if (buttons == 0 || now - self->_lastInputDisplay > .08) {
      self->_lastInputDisplay = now;
      self->_inputStatus.text = [NSString stringWithFormat:@"Botões %04X  ·  LT %.0f%%  RT %.0f%%\nL %.2f / %.2f  ·  R %.2f / %.2f", buttons, lt * 100, rt * 100, lx, ly, rx, ry];
    }
  };
  _controls.connectionChanged = ^(NSString *description) {
    StormViewController *self = weakSelf;
    if (!self) return;
    self->_controllerStatus.text = description;
    [self log:description];
  };
  _controllerStatus.text = _controls.connectionDescription;
  _metal.diagnosticCompletion = ^(BOOL passed, NSString *message) {
    StormViewController *self = weakSelf;
    if (!self) return;
    self->_diagnosticStatus.text = passed ? @"Metal respondeu corretamente ao teste." : @"Não foi possível concluir o teste Metal.";
    [self log:message];
    if (self->_smoke) {
      NSDictionary *result = @{@"runtime_self_test":@(self->_runtimeTestPassed), @"metal_command_completed":@(passed),
        @"game_executed":@NO, @"pixel_comparison_performed":@NO, @"zip_import_ui_present":@(self->_importButton != nil),
        @"developer_credit":@"Projeto iOS desenvolvido por Miquéias", @"developed_by":@"Miquéias",
        @"ui_build":@"zip-library-v1", @"controller_ui_present":@(self->_controls != nil)};
      NSURL *documents = [NSFileManager.defaultManager URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject;
      NSError *error = nil;
      NSData *json = [NSJSONSerialization dataWithJSONObject:result options:NSJSONWritingPrettyPrinted error:&error];
      if (![json writeToURL:[documents URLByAppendingPathComponent:@"smoke-result.json"] options:NSDataWritingAtomic error:&error]) [self log:error.localizedDescription];
    }
  };
  _navigation.selectedSegmentIndex = _smoke ? 2 :
      ([NSProcessInfo.processInfo.arguments containsObject:@"--capture-controls"] ? 1 : 0);
  [self changePage:_navigation];
  [self log:_runtimeTestPassed ? @"Autoteste do runtime aprovado. Nenhum código do jogo foi executado." : @"Falha no autoteste do runtime."];
  if (!_runtime) [self log:@"Falha ao criar o runtime."];
  [NSNotificationCenter.defaultCenter addObserver:self selector:@selector(suspend:) name:UIApplicationWillResignActiveNotification object:nil];
  [NSNotificationCenter.defaultCenter addObserver:self selector:@selector(resume:) name:UIApplicationDidBecomeActiveNotification object:nil];
  [NSNotificationCenter.defaultCenter addObserver:self selector:@selector(thermal:) name:NSProcessInfoThermalStateDidChangeNotification object:nil];
  [self validateInstalled];
}

- (void)viewDidAppear:(BOOL)animated {
  [super viewDidAppear:animated];
  [_scroll flashScrollIndicators];
  if (!_scrollTestStarted && [NSProcessInfo.processInfo.arguments containsObject:@"--scroll-smoke-test"]) {
    _scrollTestStarted = YES;
    dispatch_async(dispatch_get_main_queue(), ^{ [self checkScrollLayout]; });
  }
}
- (void)checkScrollLayout {
  NSMutableArray *pages = [NSMutableArray array];
  BOOL passed = YES;
  for (NSUInteger index = 0; index < _pages.count; ++index) {
    _navigation.selectedSegmentIndex = index;
    [self changePage:_navigation];
    [self.view setNeedsLayout];
    [self.view layoutIfNeeded];
    const CGFloat maximum = MAX(0, _scroll.contentSize.height - _scroll.bounds.size.height + _scroll.adjustedContentInset.bottom);
    [_scroll setContentOffset:CGPointMake(0, maximum) animated:NO];
    [self.view layoutIfNeeded];
    CGRect credit = [_credit convertRect:_credit.bounds toView:_scroll];
    BOOL visible = CGRectContainsRect(CGRectInset(_scroll.bounds, -1, -1), credit);
    BOOL canScroll = maximum > 1 && _scroll.contentOffset.y > 1;
    BOOL valid = visible && _scroll.scrollEnabled && _scroll.panGestureRecognizer.enabled && canScroll;
    passed = passed && valid;
    [pages addObject:@{@"page":@(index), @"content_height":@(_scroll.contentSize.height),
      @"viewport_height":@(_scroll.bounds.size.height), @"offset_y":@(_scroll.contentOffset.y),
      @"footer_visible":@(visible), @"scrolls":@(canScroll)}];
  }
  BOOL buttonCancellation = [_scroll touchesShouldCancelInContentView:_importButton];
  passed = passed && buttonCancellation;
  NSDictionary *report = @{@"passed":@(passed), @"pages":pages, @"button_touch_cancellation":@(buttonCancellation),
    @"finger_gesture_tested":@NO, @"game_executed":@NO};
  NSURL *documents = [NSFileManager.defaultManager URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject;
  [[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:nil]
    writeToURL:[documents URLByAppendingPathComponent:@"scroll-smoke.json"] atomically:YES];
}

- (UIStackView *)libraryPage {
  UIStackView *page = Column(18);
  page.accessibilityIdentifier = @"storm.library";
  UIStackView *hero = Card();
  _importCard = hero;
  [hero addArrangedSubview:Eyebrow(@"01 / SUA BIBLIOTECA")];
  UILabel *heading = Text(@"Prepare o seu jogo.", UIFontTextStyleTitle1, Ink());
  heading.font = [[UIFontMetrics metricsForTextStyle:UIFontTextStyleTitle1] scaledFontForFont:[UIFont systemFontOfSize:30 weight:UIFontWeightBold]];
  [hero addArrangedSubview:heading];
  [hero addArrangedSubview:Text(@"Escolha o ZIP da sua cópia de Xbox 360. O app extrai, organiza os arquivos e confere a versão do executável.", UIFontTextStyleBody, Muted())];
  _importButton = [self button:@"Selecionar arquivo ZIP" symbol:@"archivebox" action:@selector(importGame) primary:YES];
  _importButton.accessibilityIdentifier = @"storm.importZIP";
  [hero addArrangedSubview:_importButton];
  [hero addArrangedSubview:Text(@"Use uma cópia obtida legalmente. A extração precisa de espaço livre para os arquivos descompactados.", UIFontTextStyleFootnote, Muted())];

  _progressStack = Column(10);
  _progressLabel = Text(@"Preparando importação…", UIFontTextStyleSubheadline, Ink());
  _progressLabel.accessibilityIdentifier = @"storm.importProgressMessage";
  _progress = [[UIProgressView alloc] initWithProgressViewStyle:UIProgressViewStyleDefault];
  _progress.progressTintColor = Accent();
  _progress.accessibilityIdentifier = @"storm.importProgress";
  _cancelButton = [self button:@"Cancelar importação" symbol:@"xmark" action:@selector(cancelImport) primary:NO];
  _cancelButton.accessibilityIdentifier = @"storm.cancelImport";
  [_progressStack addArrangedSubview:_progressLabel];
  [_progressStack addArrangedSubview:_progress];
  [_progressStack addArrangedSubview:_cancelButton];
  [page addArrangedSubview:hero];

  UIStackView *state = Card();
  [state addArrangedSubview:Eyebrow(@"02 / ESTADO DO PROJETO")];
  _importTitle = Text(@"Conferindo biblioteca…", UIFontTextStyleHeadline, Ink());
  _importTitle.accessibilityIdentifier = @"storm.libraryState";
  [state addArrangedSubview:_importTitle];
  _status = Text(@"Esta versão prepara os arquivos e testa o aplicativo. O jogo ainda não inicia.", UIFontTextStyleBody, Muted());
  _status.accessibilityIdentifier = @"storm.gameStatus";
  [state addArrangedSubview:_status];
  _launchButton = [self button:@"Iniciar jogo" symbol:@"play.fill" action:@selector(launchGame) primary:NO];
  _launchButton.enabled = NO;
  _launchButton.accessibilityIdentifier = @"storm.launchGame";
  [state addArrangedSubview:_launchButton];
  [state addArrangedSubview:Text(@"A imagem nativa do jogo ainda está em desenvolvimento. Importar o ZIP não conclui essa etapa.", UIFontTextStyleFootnote, Muted())];
  [page addArrangedSubview:state];
  return page;
}

- (UIStackView *)controlsPage {
  UIStackView *page = Column(18);
  page.accessibilityIdentifier = @"storm.controlsPage";
  UIStackView *connection = Card();
  [connection addArrangedSubview:Eyebrow(@"CONTROLE EXTERNO")];
  [connection addArrangedSubview:Text(@"Conecte. Teste. Personalize.", UIFontTextStyleTitle2, Ink())];
  _controllerStatus = Text(@"Verificando controles conectados…", UIFontTextStyleHeadline, Ink());
  _controllerStatus.accessibilityIdentifier = @"storm.controllerStatus";
  [connection addArrangedSubview:_controllerStatus];
  [connection addArrangedSubview:Text(@"Emparelhe um controle compatível nos Ajustes › Bluetooth do iPhone ou conecte por USB quando houver suporte do iOS. A conexão é reconhecida automaticamente.", UIFontTextStyleBody, Muted())];
  [connection addArrangedSubview:Text(@"O layout segue o Xbox 360. A compatibilidade física depende do modelo e do iOS; controles Xbox 360 originais não são presumidos compatíveis.", UIFontTextStyleFootnote, Muted())];
  [page addArrangedSubview:connection];

  UIStackView *touch = Card();
  [touch addArrangedSubview:Eyebrow(@"LAYOUT XBOX 360")];
  [touch addArrangedSubview:Text(@"Controles na tela", UIFontTextStyleTitle2, Ink())];
  [touch addArrangedSubview:Text(@"Teste os analógicos, gatilhos e botões abaixo. Os comandos são enviados ao runtime; as ações de combate ainda dependem do jogo funcionando.", UIFontTextStyleSubheadline, Muted())];
  _controls = [[StormControls alloc] initWithFrame:CGRectZero];
  _controls.accessibilityIdentifier = @"storm.touchControls";
  _controls.layer.cornerRadius = 18; _controls.clipsToBounds = YES;
  [_controls.heightAnchor constraintEqualToConstant:340].active = YES;
  [touch addArrangedSubview:_controls];
  _inputStatus = Text(@"Toque nos botões ou mova o controle para testar a entrada.", UIFontTextStyleCaption1, Muted());
  _inputStatus.font = [UIFont monospacedSystemFontOfSize:11 weight:UIFontWeightMedium];
  _inputStatus.accessibilityIdentifier = @"storm.inputReadout";
  [touch addArrangedSubview:_inputStatus];
  UISwitch *edit = [[UISwitch alloc] init];
  edit.onTintColor = Accent();
  edit.accessibilityIdentifier = @"storm.editControls";
  [edit addTarget:self action:@selector(changeEdit:) forControlEvents:UIControlEventValueChanged];
  [touch addArrangedSubview:[self row:@"Reposicionar controles" control:edit]];
  for (NSUInteger i = 0; i < 2; ++i) {
    UISlider *slider = [[UISlider alloc] init]; slider.tag = i;
    slider.minimumValue = i == 0 ? .65 : .2;
    slider.maximumValue = i == 0 ? 1.4 : 1;
    NSString *key = i == 0 ? @"controlScale" : @"controlOpacity";
    NSNumber *saved = [NSUserDefaults.standardUserDefaults objectForKey:key];
    slider.value = saved ? saved.floatValue : (i == 0 ? 1 : .9);
    slider.accessibilityLabel = i == 0 ? @"Tamanho dos controles" : @"Opacidade dos controles";
    [slider addTarget:self action:@selector(changeControl:) forControlEvents:UIControlEventValueChanged];
    UIStackView *setting = Column(5);
    [setting addArrangedSubview:Text(slider.accessibilityLabel, UIFontTextStyleSubheadline, Ink())];
    [setting addArrangedSubview:slider];
    [touch addArrangedSubview:setting];
    [self changeControl:slider];
  }
  [page addArrangedSubview:touch];
  return page;
}

- (UIStackView *)settingsPage {
  UIStackView *page = Column(18);
  page.accessibilityIdentifier = @"storm.settingsPage";
  UIStackView *graphics = Card();
  [graphics addArrangedSubview:Eyebrow(@"TESTE GRÁFICO")];
  [graphics addArrangedSubview:Text(@"Diagnóstico Metal", UIFontTextStyleTitle2, Ink())];
  [graphics addArrangedSubview:Text(@"Este triângulo verifica a infraestrutura gráfica. Não é uma cena do jogo nem uma medição de desempenho dele.", UIFontTextStyleBody, Muted())];
  _metal = [[StormMetalView alloc] initWithFrame:CGRectZero];
  _metal.accessibilityIdentifier = @"storm.metalDiagnostic";
  _metal.layer.cornerRadius = 16; _metal.clipsToBounds = YES;
  [_metal.heightAnchor constraintEqualToConstant:180].active = YES;
  [graphics addArrangedSubview:_metal];
  _diagnosticStatus = Text(@"Aguardando o primeiro comando gráfico…", UIFontTextStyleFootnote, Muted());
  [graphics addArrangedSubview:_diagnosticStatus];
  UISegmentedControl *fps = [[UISegmentedControl alloc] initWithItems:@[@"Qualidade · 30 Hz", @"Desempenho · 60 Hz"]];
  fps.selectedSegmentIndex = [NSUserDefaults.standardUserDefaults integerForKey:@"performanceMode"] == 1 ? 1 : 0;
  fps.accessibilityLabel = @"Perfil do diagnóstico gráfico";
  [fps addTarget:self action:@selector(changeMode:) forControlEvents:UIControlEventValueChanged];
  [graphics addArrangedSubview:fps];
  [self changeMode:fps];
  UISwitch *adaptive = [[UISwitch alloc] init];
  adaptive.onTintColor = Accent();
  adaptive.on = [NSUserDefaults.standardUserDefaults boolForKey:@"adaptiveResolution"];
  _metal.adaptiveResolution = adaptive.on;
  [adaptive addTarget:self action:@selector(changeAdaptive:) forControlEvents:UIControlEventValueChanged];
  [graphics addArrangedSubview:[self row:@"Resolução adaptativa" control:adaptive]];
  [page addArrangedSubview:graphics];

  UIStackView *compatibility = Card();
  [compatibility addArrangedSubview:Eyebrow(@"SOBRE ESTA VERSÃO")];
  [compatibility addArrangedSubview:Text(@"Um projeto em construção.", UIFontTextStyleTitle2, Ink())];
  [compatibility addArrangedSubview:Text(@"Importação ZIP, controles e diagnóstico estão disponíveis para teste. O jogo, seus gráficos e áudio ainda não foram integrados. Compatibilidade com iOS 27 e desempenho no iPhone precisam de validação.", UIFontTextStyleBody, Muted())];
  [compatibility addArrangedSubview:Text(@"Projeto independente. Naruto e demais marcas pertencem aos respectivos titulares. Nenhum arquivo do jogo acompanha o aplicativo.", UIFontTextStyleFootnote, Muted())];
  [page addArrangedSubview:compatibility];

  UIStackView *diagnostics = Card();
  [diagnostics addArrangedSubview:Eyebrow(@"DIAGNÓSTICO DO APP")];
  _logs = [[UITextView alloc] init];
  _logs.editable = NO; _logs.selectable = YES;
  _logs.backgroundColor = Background(); _logs.textColor = Muted();
  _logs.font = [UIFont monospacedSystemFontOfSize:11 weight:UIFontWeightRegular];
  _logs.layer.cornerRadius = 12; _logs.textContainerInset = UIEdgeInsetsMake(12, 8, 12, 8);
  _logs.accessibilityIdentifier = @"storm.logs";
  [_logs.heightAnchor constraintEqualToConstant:170].active = YES;
  [diagnostics addArrangedSubview:_logs];
  [diagnostics addArrangedSubview:[self button:@"Compartilhar diagnóstico" symbol:@"square.and.arrow.up" action:@selector(shareLogs:) primary:NO]];
  [page addArrangedSubview:diagnostics];
  return page;
}

- (UIButton *)button:(NSString *)title symbol:(NSString *)symbol action:(SEL)selector primary:(BOOL)primary {
  UIButtonConfiguration *config = primary ? [UIButtonConfiguration filledButtonConfiguration] : [UIButtonConfiguration tintedButtonConfiguration];
  config.title = title; config.image = [UIImage systemImageNamed:symbol];
  config.imagePadding = 10; config.cornerStyle = UIButtonConfigurationCornerStyleMedium;
  config.contentInsets = NSDirectionalEdgeInsetsMake(15, 14, 15, 14);
  config.baseBackgroundColor = Accent();
  config.baseForegroundColor = primary ? Background() : Accent();
  config.titleLineBreakMode = NSLineBreakByWordWrapping;
  UIButton *button = [UIButton buttonWithConfiguration:config primaryAction:nil];
  [button addTarget:self action:selector forControlEvents:UIControlEventTouchUpInside];
  [button.heightAnchor constraintGreaterThanOrEqualToConstant:50].active = YES;
  return button;
}

- (UIStackView *)row:(NSString *)title control:(UIView *)control {
  UILabel *label = Text(title, UIFontTextStyleSubheadline, Ink());
  control.accessibilityLabel = title;
  [control setContentHuggingPriority:UILayoutPriorityRequired forAxis:UILayoutConstraintAxisHorizontal];
  UIStackView *row = [[UIStackView alloc] initWithArrangedSubviews:@[label, control]];
  row.axis = UILayoutConstraintAxisHorizontal; row.spacing = 12; row.alignment = UIStackViewAlignmentCenter;
  return row;
}

- (void)changePage:(UISegmentedControl *)control {
  NSUInteger selected = MIN((NSUInteger)MAX(0, control.selectedSegmentIndex), _pages.count - 1);
  if (_pages[selected].superview != _pageHost) {
    for (UIView *page in [_pageHost.arrangedSubviews copy]) {
      [_pageHost removeArrangedSubview:page];
      [page removeFromSuperview];
    }
    [_pageHost addArrangedSubview:_pages[selected]];
  }
  [_controls resetInput];
  _metal.paused = selected != 2 || UIApplication.sharedApplication.applicationState != UIApplicationStateActive;
  [_scroll setContentOffset:CGPointZero animated:NO];
  UIAccessibilityPostNotification(UIAccessibilityScreenChangedNotification, _pages[selected]);
}

- (void)setImportProgressVisible:(BOOL)visible {
  // Attach/remove instead of hiding this nested stack: its spacing and cancel
  // button must never compete against UIStackView's zero-height hiding rule.
  if (visible && !_progressStack.superview) [_importCard addArrangedSubview:_progressStack];
  else if (!visible && _progressStack.superview) {
    [_importCard removeArrangedSubview:_progressStack];
    [_progressStack removeFromSuperview];
  }
}

- (void)log:(NSString *)message {
  if (!message.length) return;
  NSLog(@"STORM: %@", message);
  NSString *next = [(_logs.text ?: @"") stringByAppendingFormat:@"%@\n", message];
  _logs.text = next.length > 24000 ? [next substringFromIndex:next.length - 24000] : next;
}
- (void)shareLogs:(UIButton *)sender {
  NSString *report = [NSString stringWithFormat:@"Storm Revolution iOS — diagnóstico\nProjeto iOS desenvolvido por Miquéias\nSistema: %@ %@\nJogo executado: não\n\n%@", UIDevice.currentDevice.systemName, UIDevice.currentDevice.systemVersion, _logs.text ?: @""];
  UIActivityViewController *sheet = [[UIActivityViewController alloc] initWithActivityItems:@[report] applicationActivities:nil];
  sheet.popoverPresentationController.sourceView = sender;
  sheet.popoverPresentationController.sourceRect = sender.bounds;
  [self presentViewController:sheet animated:YES completion:nil];
}
- (void)changeMode:(UISegmentedControl *)control {
  BOOL performance = control.selectedSegmentIndex == 1;
  _metal.preferredFramesPerSecond = performance ? 60 : 30;
  _metal.resolutionScale = performance ? .65 : 1;
  [_metal applyResolution];
  [NSUserDefaults.standardUserDefaults setInteger:control.selectedSegmentIndex forKey:@"performanceMode"];
}
- (void)changeAdaptive:(UISwitch *)control { _metal.adaptiveResolution = control.on; [NSUserDefaults.standardUserDefaults setBool:control.on forKey:@"adaptiveResolution"]; }
- (void)changeEdit:(UISwitch *)control { _controls.editingControls = control.on; }
- (void)changeControl:(UISlider *)control {
  if (control.tag == 0) _controls.controlScale = control.value; else _controls.controlOpacity = control.value;
  [NSUserDefaults.standardUserDefaults setFloat:control.value forKey:control.tag == 0 ? @"controlScale" : @"controlOpacity"];
}
- (void)importGame {
  if (_importing) return;
  UIDocumentPickerViewController *picker = [[UIDocumentPickerViewController alloc] initForOpeningContentTypes:@[UTTypeZIP] asCopy:NO];
  picker.delegate = self; picker.allowsMultipleSelection = NO;
  [self presentViewController:picker animated:YES completion:nil];
}
- (void)documentPicker:(UIDocumentPickerViewController *)controller didPickDocumentsAtURLs:(NSArray<NSURL *> *)urls {
  (void)controller;
  NSURL *source = urls.firstObject;
  if (!source || _importing) return;
  _importing = YES;
  ++_validationGeneration;
  _importButton.enabled = _launchButton.enabled = NO;
  _cancelButton.enabled = YES;
  [self setImportProgressVisible:YES]; _progress.progress = 0;
  _progressLabel.text = @"Abrindo o ZIP…";
  _importTitle.text = @"Importação em andamento";
  _status.text = @"Mantenha o app aberto durante a extração. Sua importação anterior é preservada se houver um erro.";
  [self log:@"Importação ZIP iniciada. O arquivo original não será alterado."];
  __weak StormViewController *weakSelf = self;
  [_importer importZIPAtURL:source progress:^(double fraction, NSString *message) {
    StormViewController *self = weakSelf;
    if (!self) return;
    self->_progress.progress = MIN(1, MAX(0, fraction));
    self->_progressLabel.text = message;
    self->_progress.accessibilityValue = [NSString stringWithFormat:@"%.0f por cento", fraction * 100];
  } completion:^(NSDictionary *validation, NSError *error) {
    StormViewController *self = weakSelf;
    if (!self) return;
    self->_importing = NO;
    self->_importButton.enabled = YES;
    self->_cancelButton.enabled = NO;
    [self setImportProgressVisible:NO];
    if (error) {
      [self log:error.localizedDescription];
      if (error.userInfo[@"diagnostic"]) [self log:[NSString stringWithFormat:@"ZIP: %@", error.userInfo[@"diagnostic"]]];
      self->_status.text = error.localizedDescription;
      self->_importTitle.text = @"Importação não concluída";
      [self validateInstalledKeepingMessage:YES];
      UIAccessibilityPostNotification(UIAccessibilityAnnouncementNotification, error.localizedDescription);
    } else {
      self->_identityMatches = [validation[@"reference_matches"] boolValue];
      self->_launchButton.enabled = self->_identityMatches;
      self->_importTitle.text = self->_identityMatches ? @"Arquivos importados" : @"Versão não reconhecida";
      self->_status.text = @"A versão do executável foi conferida. O jogo ainda depende da imagem nativa em desenvolvimento para iniciar.";
      [self log:@"ZIP extraído e executável validado. Isso não valida os recursos do jogo nem permite iniciar uma partida."];
      UINotificationFeedbackGenerator *feedback = [[UINotificationFeedbackGenerator alloc] init];
      [feedback notificationOccurred:UINotificationFeedbackTypeSuccess];
      UIAccessibilityPostNotification(UIAccessibilityAnnouncementNotification, @"Arquivos importados. O jogo ainda não está disponível nesta versão.");
    }
  }];
}
- (void)cancelImport {
  if (!_importing) return;
  _cancelButton.enabled = NO;
  _progressLabel.text = @"Cancelando e removendo os arquivos temporários…";
  [_importer cancel];
}
- (void)validateInstalled { [self validateInstalledKeepingMessage:NO]; }
- (void)validateInstalledKeepingMessage:(BOOL)keepMessage {
  NSUInteger generation = ++_validationGeneration;
  __weak StormViewController *weakSelf = self;
  [StormGameImporter validateInstalledWithCompletion:^(NSDictionary *validation, NSError *error) {
    StormViewController *self = weakSelf;
    if (!self || self->_importing || generation != self->_validationGeneration) return;
    self->_identityMatches = [validation[@"reference_matches"] boolValue];
    self->_launchButton.enabled = self->_identityMatches;
    if (!keepMessage) {
      self->_importTitle.text = self->_identityMatches ? @"Arquivos importados" : @"Nenhum jogo preparado";
      self->_status.text = self->_identityMatches ? @"A versão do executável foi conferida. O jogo ainda depende da imagem nativa em desenvolvimento para iniciar." : @"Selecione seu ZIP para começar. Esta versão prepara os arquivos e testa o aplicativo; o jogo ainda não inicia.";
    }
    if (self->_identityMatches) [self log:@"Executável instalado corresponde à versão de referência."];
    else if (validation || error) [self log:@"Nenhum executável validado disponível na biblioteca."];
  }];
}
- (void)launchGame {
  if (!_runtime) { [self log:@"Runtime indisponível."]; return; }
  if (_importing || !_identityMatches) { [self log:@"Importe e valide o executável antes de iniciar."]; return; }
  int result = storm_runtime_start(_runtime, [StormGameImporter gameURL].fileSystemRepresentation);
  NSString *detail = [NSString stringWithUTF8String:storm_runtime_last_error(_runtime)];
  [self log:[NSString stringWithFormat:@"Runtime start result=%d: %@", result, detail ?: @""]];
  _status.text = result == 0 ? @"O runtime aceitou a solicitação. A execução do jogo ainda precisa ser comprovada." : @"Seus arquivos estão preparados, mas a imagem nativa do jogo ainda não está disponível nesta versão.";
  UIAccessibilityPostNotification(UIAccessibilityAnnouncementNotification, _status.text);
}
- (void)suspend:(NSNotification *)notification {
  (void)notification; _metal.paused = YES; [_controls resetInput];
  if (_runtime) storm_runtime_stop(_runtime);
  if (_importing) [self log:@"App em segundo plano. A extração poderá ser suspensa pelo iOS; mantenha o app aberto para concluir."];
}
- (void)resume:(NSNotification *)notification { (void)notification; _metal.paused = _navigation.selectedSegmentIndex != 2; }
- (void)thermal:(NSNotification *)notification {
  (void)notification;
  if (NSProcessInfo.processInfo.thermalState >= NSProcessInfoThermalStateSerious) {
    _metal.preferredFramesPerSecond = 30; _metal.resolutionScale = .5; [_metal applyResolution];
    [self log:@"Temperatura elevada: diagnóstico limitado a 30 Hz e meia resolução."];
  }
}
- (void)didReceiveMemoryWarning {
  [super didReceiveMemoryWarning];
  _metal.resolutionScale = .5; [_metal applyResolution];
  [self log:@"Pressão de memória: resolução do diagnóstico reduzida."];
}
- (void)dealloc {
  [_importer cancel];
  [NSNotificationCenter.defaultCenter removeObserver:self];
  storm_runtime_destroy(_runtime);
}
@end
