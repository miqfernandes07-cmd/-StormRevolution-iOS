#import "Localization/StormLocalization.h"
#import "StormNativeOptions.h"
#import "StormNativePreferences.h"

@implementation StormNativeOptions
- (instancetype)init { return [super initWithStyle:UITableViewStyleInsetGrouped]; }
- (void)viewDidLoad {
  [super viewDidLoad];
  self.title = SL(@"Ajustes");
  self.overrideUserInterfaceStyle = UIUserInterfaceStyleDark;
  self.view.tintColor = [UIColor colorWithRed:.50 green:.81 blue:1 alpha:1];
  self.navigationItem.rightBarButtonItem = [[UIBarButtonItem alloc] initWithBarButtonSystemItem:UIBarButtonSystemItemDone target:self action:@selector(done)];
  self.tableView.keyboardDismissMode = UIScrollViewKeyboardDismissModeOnDrag;
}
- (void)done { [self dismissViewControllerAnimated:YES completion:self.closed]; }
- (NSInteger)numberOfSectionsInTableView:(UITableView *)tableView { return 4; }
- (NSInteger)tableView:(UITableView *)tableView numberOfRowsInSection:(NSInteger)section {
  const NSInteger counts[] = {8, 8, 3, 2}; return counts[section];
}
- (NSString *)tableView:(UITableView *)tableView titleForHeaderInSection:(NSInteger)section {
  return @[SL(@"Seu controle"), SL(@"Imagem e desempenho"), SL(@"Diagnóstico"), SL(@"Créditos")][section];
}
- (NSString *)tableView:(UITableView *)tableView titleForFooterInSection:(NSInteger)section {
  return @[SL(@"Controles por ações e atalhos de golpes. Arraste em Organizar. Pause o jogo antes de ajustar."),
    SL(@"Rápido é experimental e pode causar artefatos. Use Seguro se isso ocorrer. Perfil, resolução, escala e FXAA exigem reabrir o aplicativo."),
    SL(@"O cache é limpo na próxima abertura. Os logs incluem FPS, temperatura e memória para investigar falhas."),
    SL(@"Port nativo experimental. Seus arquivos importados e saves são preservados nas atualizações.")][section];
}
- (UISegmentedControl *)segments:(NSArray<NSString *> *)labels key:(NSString *)key selected:(NSInteger)selected {
  UISegmentedControl *control = [[UISegmentedControl alloc] initWithItems:labels];
  control.accessibilityIdentifier = key;
  control.selectedSegmentIndex = selected;
  [control addTarget:self action:@selector(segmentChanged:) forControlEvents:UIControlEventValueChanged];
  return control;
}
- (UISwitch *)toggle:(NSString *)key value:(BOOL)value {
  UISwitch *control = [UISwitch new]; control.on = value; control.accessibilityIdentifier = key;
  [control addTarget:self action:@selector(toggleChanged:) forControlEvents:UIControlEventValueChanged];
  return control;
}
- (UITableViewCell *)tableView:(UITableView *)tableView cellForRowAtIndexPath:(NSIndexPath *)index {
  NSDictionary *v = StormNativePreferences.values;
  UITableViewCell *cell = [[UITableViewCell alloc] initWithStyle:UITableViewCellStyleSubtitle reuseIdentifier:nil];
  cell.selectionStyle = UITableViewCellSelectionStyleNone;
  cell.textLabel.font = [UIFont systemFontOfSize:15 weight:UIFontWeightMedium];
  cell.detailTextLabel.numberOfLines = 0;
  NSInteger row = index.row;
  if (index.section == 0) {
    cell.textLabel.text = @[SL(@"Botões"),SL(@"Disposição"),SL(@"Tamanho"),SL(@"Opacidade"),SL(@"Controles na tela"),SL(@"Vibração de toque"),SL(@"Organizar / restaurar"),SL(@"Idioma do aplicativo")][row];
    if (row == 0) cell.accessoryView = [self segments:@[SL(@"Celular"),@"PlayStation",@"Xbox"] key:@"controlStyle" selected:([v[@"actionControls"] boolValue] && [v[@"mobile"] boolValue]) ? 0 : ([v[@"playstation"] boolValue] ? 1 : 2)];
    if (row == 1) cell.accessoryView = [self segments:@[SL(@"Celular"),SL(@"Clássico")] key:@"mobile" selected:[v[@"mobile"] boolValue] ? 0 : 1];
    if (row == 2 || row == 3) {
      NSString *key = row == 2 ? @"scale" : @"opacity";
      UISlider *slider = [[UISlider alloc] initWithFrame:CGRectMake(0,0,180,34)];
      slider.minimumValue = row == 2 ? .65 : .2; slider.maximumValue = row == 2 ? 1.4 : 1;
      slider.value = [v[key] floatValue]; slider.accessibilityIdentifier = key;
      [slider addTarget:self action:@selector(sliderChanged:) forControlEvents:UIControlEventValueChanged];
      cell.accessoryView = slider;
    }
    if (row == 4 || row == 5) { NSString *key = row == 4 ? @"touch" : @"haptics"; cell.accessoryView = [self toggle:key value:[v[key] boolValue]]; }
    if (row == 6) { cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator; cell.selectionStyle = UITableViewCellSelectionStyleDefault; }
    if (row == 7) {
      cell.accessibilityIdentifier = @"appLanguage";
      NSString *code = v[@"appLanguage"];
      NSUInteger selected = [StormAppLanguages() indexOfObject:code];
      cell.detailTextLabel.text = [NSString stringWithFormat:@"%@\n%@", StormAppLanguageNames()[selected == NSNotFound ? 0 : selected], SL(@"Escolha o idioma dos menus e controles do aplicativo. O idioma do jogo não é alterado.")];
      cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator; cell.selectionStyle = UITableViewCellSelectionStyleDefault;
    }
  } else if (index.section == 1) {
    cell.textLabel.text = @[SL(@"Tela"),SL(@"Perfil gráfico"),SL(@"Shaders"),SL(@"Modo de vídeo"),SL(@"Escala interna"),SL(@"Limite de quadros"),SL(@"Suavização FXAA"),SL(@"Usar memória ampliada")][row];
    if (row == 0) cell.accessoryView = [self segments:@[SL(@"Preencher"),SL(@"Original")] key:@"fill" selected:[v[@"fill"] boolValue] ? 0 : 1];
    if (row == 1) cell.accessoryView = [self segments:@[SL(@"Seguro"),SL(@"Rápido"),SL(@"Padrão")] key:@"graphicsProfile" selected:[v[@"compatible"] boolValue] ? ([v[@"fastReadback"] boolValue] ? 1 : 0) : 2];
    if (row == 2) cell.accessoryView = [self segments:@[SL(@"Estável"),SL(@"Assíncrono")] key:@"async" selected:[v[@"async"] boolValue] ? 1 : 0];
    if (row == 3) cell.accessoryView = [self segments:@[@"480p",@"720p"] key:@"resolution" selected:[v[@"resolution"] isEqual:@"640x480"] ? 0 : 1];
    if (row == 4) cell.accessoryView = [self segments:@[@"1×",@"2×"] key:@"renderScale" selected:[v[@"renderScale"] integerValue] == 2 ? 1 : 0];
    if (row == 5) cell.accessoryView = [self segments:@[@"30",@"60"] key:@"fps" selected:[v[@"fps"] integerValue] == 60 ? 1 : 0];
    if (row == 6) cell.accessoryView = [self toggle:@"fxaa" value:[v[@"fxaa"] boolValue]];
    if (row == 7) {
      cell.accessoryView = [self toggle:@"expandedMemory" value:[v[@"expandedMemory"] boolValue]];
      cell.detailTextLabel.text = SL(@"Remove o limite do orçamento de alocação do runtime. O iOS continua limitando a RAM disponível. Exige reabrir o aplicativo.");
    }
  } else if (index.section == 2) {
    cell.textLabel.text = @[SL(@"Limpar cache de shaders"),SL(@"Compartilhar logs e desempenho"),SL(@"Arquivos do jogo")][row];
    if (row == 2) cell.detailTextLabel.text = SL(@"Arquivos → No Meu iPhone → Storm Native → Game. A instalação anterior é movida automaticamente, sem duplicar o jogo.");
    cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator;
    cell.selectionStyle = UITableViewCellSelectionStyleDefault;
  } else {
    cell.textLabel.text = row == 0 ? SL(@"Créditos • MiquéiasF07") : SL(@"Mostrar FPS");
    if (row == 0) cell.detailTextLabel.text = SL(@"Storm Revolution para iPhone");
    else cell.accessoryView = [self toggle:@"stats" value:[v[@"stats"] boolValue]];
  }
  return cell;
}
- (void)notify:(NSString *)key value:(id)value {
  [StormNativePreferences setValue:value forKey:key];
  if (self.changed) self.changed(key);
}
- (void)segmentChanged:(UISegmentedControl *)sender {
  NSString *key = sender.accessibilityIdentifier; NSInteger i = sender.selectedSegmentIndex;
  if ([key isEqual:@"controlStyle"]) {
    [StormNativePreferences setValue:@(i == 0) forKey:@"actionControls"];
    if (i == 0) [StormNativePreferences setValue:@YES forKey:@"mobile"];
    [self notify:@"playstation" value:@(i != 2)];
    [self.tableView reloadData]; return;
  }
  if ([key isEqual:@"graphicsProfile"]) {
    [StormNativePreferences setValue:@(i != 2) forKey:@"compatible"];
    [self notify:@"fastReadback" value:@(i == 1)]; return;
  }
  if ([key isEqual:@"mobile"] && i == 1) [StormNativePreferences setValue:@NO forKey:@"actionControls"];
  id value = @(i == 0);
  if ([key isEqual:@"async"]) value = @(i == 1);
  else if ([key isEqual:@"resolution"]) value = i == 0 ? @"640x480" : @"1280x720";
  else if ([key isEqual:@"renderScale"]) value = @(i + 1);
  else if ([key isEqual:@"fps"]) value = i == 0 ? @30 : @60;
  [self notify:key value:value];
  if ([key isEqual:@"mobile"]) [self.tableView reloadData];
}
- (void)toggleChanged:(UISwitch *)sender { [self notify:sender.accessibilityIdentifier value:@(sender.on)]; }
- (void)sliderChanged:(UISlider *)sender { [self notify:sender.accessibilityIdentifier value:@(sender.value)]; }
- (void)tableView:(UITableView *)tableView didSelectRowAtIndexPath:(NSIndexPath *)index {
  [tableView deselectRowAtIndexPath:index animated:YES];
  if (index.section == 0 && index.row == 7) {
    UIAlertController *menu = [UIAlertController alertControllerWithTitle:SL(@"Idioma do aplicativo") message:SL(@"Escolha o idioma dos menus e controles do aplicativo. O idioma do jogo não é alterado.") preferredStyle:UIAlertControllerStyleActionSheet];
    for (NSUInteger i = 0; i < StormAppLanguages().count; ++i) {
      NSString *code = StormAppLanguages()[i];
      [menu addAction:[UIAlertAction actionWithTitle:StormAppLanguageNames()[i] style:UIAlertActionStyleDefault handler:^(UIAlertAction *a) {
        [self notify:@"appLanguage" value:code]; self.title = SL(@"Ajustes"); [self.tableView reloadData];
      }]];
    }
    [menu addAction:[UIAlertAction actionWithTitle:SL(@"Cancelar") style:UIAlertActionStyleCancel handler:nil]];
    menu.popoverPresentationController.sourceView = [tableView cellForRowAtIndexPath:index];
    menu.popoverPresentationController.sourceRect = [tableView cellForRowAtIndexPath:index].bounds;
    [self presentViewController:menu animated:YES completion:nil];
  } else if (index.section == 0 && index.row == 6) {
    UIAlertController *menu = [UIAlertController alertControllerWithTitle:SL(@"Organizar controles") message:SL(@"A disposição é salva neste iPhone.") preferredStyle:UIAlertControllerStyleActionSheet];
    [menu addAction:[UIAlertAction actionWithTitle:SL(@"Mover botões e analógicos") style:UIAlertActionStyleDefault handler:^(UIAlertAction *a) { [self dismissViewControllerAnimated:YES completion:self.editControls]; }]];
    [menu addAction:[UIAlertAction actionWithTitle:SL(@"Restaurar disposição") style:UIAlertActionStyleDestructive handler:^(UIAlertAction *a) { if (self.resetControls) self.resetControls(); }]];
    [menu addAction:[UIAlertAction actionWithTitle:SL(@"Cancelar") style:UIAlertActionStyleCancel handler:nil]];
    menu.popoverPresentationController.sourceView = [tableView cellForRowAtIndexPath:index];
    menu.popoverPresentationController.sourceRect = [tableView cellForRowAtIndexPath:index].bounds;
    [self presentViewController:menu animated:YES completion:nil];
  } else if (index.section == 2 && index.row == 0) {
    [self notify:@"clearCache" value:@YES];
    UIAlertController *alert = [UIAlertController alertControllerWithTitle:SL(@"Cache agendado") message:SL(@"O cache será limpo ao reabrir o aplicativo. Seus arquivos do jogo e saves serão preservados.") preferredStyle:UIAlertControllerStyleAlert];
    [alert addAction:[UIAlertAction actionWithTitle:@"OK" style:UIAlertActionStyleDefault handler:nil]];
    [self presentViewController:alert animated:YES completion:nil];
  } else if (index.section == 2 && index.row == 1 && self.shareLogs) self.shareLogs(self);
}
@end
