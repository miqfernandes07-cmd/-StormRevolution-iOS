#import "StormNativeOptions.h"
#import "StormNativePreferences.h"

@implementation StormNativeOptions
- (instancetype)init { return [super initWithStyle:UITableViewStyleInsetGrouped]; }
- (void)viewDidLoad {
  [super viewDidLoad];
  self.title = @"Ajustes";
  self.overrideUserInterfaceStyle = UIUserInterfaceStyleDark;
  self.view.tintColor = [UIColor colorWithRed:.50 green:.81 blue:1 alpha:1];
  self.navigationItem.rightBarButtonItem = [[UIBarButtonItem alloc] initWithBarButtonSystemItem:UIBarButtonSystemItemDone target:self action:@selector(done)];
  self.tableView.keyboardDismissMode = UIScrollViewKeyboardDismissModeOnDrag;
}
- (void)done { [self dismissViewControllerAnimated:YES completion:self.closed]; }
- (NSInteger)numberOfSectionsInTableView:(UITableView *)tableView { return 4; }
- (NSInteger)tableView:(UITableView *)tableView numberOfRowsInSection:(NSInteger)section {
  const NSInteger counts[] = {7, 7, 2, 2}; return counts[section];
}
- (NSString *)tableView:(UITableView *)tableView titleForHeaderInSection:(NSInteger)section {
  return @[@"Seu controle", @"Imagem e desempenho", @"Diagnóstico", @"Créditos"][section];
}
- (NSString *)tableView:(UITableView *)tableView titleForFooterInSection:(NSInteger)section {
  return @[@"✕ confirma e ○ volta. No layout celular, o duplo toque no analógico aciona L3/R3. Pause a luta com OPTIONS antes de ajustar. Na organização, arraste cada botão ou analógico e toque em Concluir.",
    @"O perfil Seguro usa o renderizador tradicional e evita o caminho experimental que apresentou artefatos. Preencher usa toda a tela. Perfil, resolução, escala e FXAA exigem reabrir o aplicativo. Estável espera os shaders ficarem prontos.",
    @"O cache é limpo na próxima abertura. Compartilhar envia apenas os logs e as configurações de diagnóstico.",
    @"Port nativo experimental. Seus arquivos importados e saves são preservados nas atualizações."][section];
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
    cell.textLabel.text = @[@"Botões",@"Disposição",@"Tamanho",@"Opacidade",@"Controles na tela",@"Vibração de toque",@"Organizar / restaurar"][row];
    if (row == 0) cell.accessoryView = [self segments:@[@"PlayStation",@"Xbox"] key:@"playstation" selected:[v[@"playstation"] boolValue] ? 0 : 1];
    if (row == 1) cell.accessoryView = [self segments:@[@"Celular",@"Clássico"] key:@"mobile" selected:[v[@"mobile"] boolValue] ? 0 : 1];
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
  } else if (index.section == 1) {
    cell.textLabel.text = @[@"Tela",@"Perfil gráfico",@"Shaders",@"Modo de vídeo",@"Escala interna",@"Limite de quadros",@"Suavização FXAA"][row];
    if (row == 0) cell.accessoryView = [self segments:@[@"Preencher",@"Original"] key:@"fill" selected:[v[@"fill"] boolValue] ? 0 : 1];
    if (row == 1) cell.accessoryView = [self segments:@[@"Seguro",@"Padrão"] key:@"compatible" selected:[v[@"compatible"] boolValue] ? 0 : 1];
    if (row == 2) cell.accessoryView = [self segments:@[@"Estável",@"Assíncrono"] key:@"async" selected:[v[@"async"] boolValue] ? 1 : 0];
    if (row == 3) cell.accessoryView = [self segments:@[@"480p",@"720p"] key:@"resolution" selected:[v[@"resolution"] isEqual:@"640x480"] ? 0 : 1];
    if (row == 4) cell.accessoryView = [self segments:@[@"1×",@"2×"] key:@"renderScale" selected:[v[@"renderScale"] integerValue] == 2 ? 1 : 0];
    if (row == 5) cell.accessoryView = [self segments:@[@"30",@"60"] key:@"fps" selected:[v[@"fps"] integerValue] == 60 ? 1 : 0];
    if (row == 6) cell.accessoryView = [self toggle:@"fxaa" value:[v[@"fxaa"] boolValue]];
  } else if (index.section == 2) {
    cell.textLabel.text = row == 0 ? @"Limpar cache de shaders" : @"Compartilhar logs";
    cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator;
    cell.selectionStyle = UITableViewCellSelectionStyleDefault;
  } else {
    cell.textLabel.text = row == 0 ? @"Créditos • MiquéiasF07" : @"Mostrar FPS";
    if (row == 0) cell.detailTextLabel.text = @"Storm Revolution para iPhone";
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
  id value = @(i == 0);
  if ([key isEqual:@"async"]) value = @(i == 1);
  else if ([key isEqual:@"resolution"]) value = i == 0 ? @"640x480" : @"1280x720";
  else if ([key isEqual:@"renderScale"]) value = @(i + 1);
  else if ([key isEqual:@"fps"]) value = i == 0 ? @30 : @60;
  [self notify:key value:value];
}
- (void)toggleChanged:(UISwitch *)sender { [self notify:sender.accessibilityIdentifier value:@(sender.on)]; }
- (void)sliderChanged:(UISlider *)sender { [self notify:sender.accessibilityIdentifier value:@(sender.value)]; }
- (void)tableView:(UITableView *)tableView didSelectRowAtIndexPath:(NSIndexPath *)index {
  [tableView deselectRowAtIndexPath:index animated:YES];
  if (index.section == 0 && index.row == 6) {
    UIAlertController *menu = [UIAlertController alertControllerWithTitle:@"Organizar controles" message:@"A disposição é salva neste iPhone." preferredStyle:UIAlertControllerStyleActionSheet];
    [menu addAction:[UIAlertAction actionWithTitle:@"Mover botões e analógicos" style:UIAlertActionStyleDefault handler:^(UIAlertAction *a) { [self dismissViewControllerAnimated:YES completion:self.editControls]; }]];
    [menu addAction:[UIAlertAction actionWithTitle:@"Restaurar disposição" style:UIAlertActionStyleDestructive handler:^(UIAlertAction *a) { if (self.resetControls) self.resetControls(); }]];
    [menu addAction:[UIAlertAction actionWithTitle:@"Cancelar" style:UIAlertActionStyleCancel handler:nil]];
    menu.popoverPresentationController.sourceView = [tableView cellForRowAtIndexPath:index];
    menu.popoverPresentationController.sourceRect = [tableView cellForRowAtIndexPath:index].bounds;
    [self presentViewController:menu animated:YES completion:nil];
  } else if (index.section == 2 && index.row == 0) {
    [self notify:@"clearCache" value:@YES];
    UIAlertController *alert = [UIAlertController alertControllerWithTitle:@"Cache agendado" message:@"O cache será limpo ao reabrir o aplicativo. Seus arquivos do jogo e saves serão preservados." preferredStyle:UIAlertControllerStyleAlert];
    [alert addAction:[UIAlertAction actionWithTitle:@"OK" style:UIAlertActionStyleDefault handler:nil]];
    [self presentViewController:alert animated:YES completion:nil];
  } else if (index.section == 2 && index.row == 1 && self.shareLogs) self.shareLogs(self);
}
@end
