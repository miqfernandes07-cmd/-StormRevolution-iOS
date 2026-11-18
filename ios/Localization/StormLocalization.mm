#import "StormLocalization.h"
#include "StormTranslations.inc"

NSArray<NSString *> *StormAppLanguages(void) { return @[@"system",@"pt",@"en",@"es",@"fr",@"de",@"it",@"ja"]; }
NSArray<NSString *> *StormAppLanguageNames(void) { return @[SL(@"Automático"),@"Português",@"English",@"Español",@"Français",@"Deutsch",@"Italiano",@"日本語"]; }
NSString *StormAppLanguage(void) {
  NSString *saved = [NSUserDefaults.standardUserDefaults dictionaryForKey:@"StormNativePreferencesV3"][@"appLanguage"];
  if ([StormAppLanguages() containsObject:saved] && ![saved isEqual:@"system"]) return saved;
  for (NSString *preferred in NSLocale.preferredLanguages) {
    NSString *code = [preferred componentsSeparatedByCharactersInSet:[NSCharacterSet characterSetWithCharactersInString:@"-_"]].firstObject;
    if ([StormAppLanguages() containsObject:code] && ![code isEqual:@"system"]) return code;
  }
  return @"en";
}
NSDictionary *StormTranslations(void) {
  static NSDictionary *catalog;
  static dispatch_once_t once;
  dispatch_once(&once, ^{
    NSData *data = [[NSString stringWithUTF8String:StormTranslationJSON] dataUsingEncoding:NSUTF8StringEncoding];
    catalog = [NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
  });
  return catalog;
}
NSString *SL(NSString *key) {
  NSString *language = StormAppLanguage();
  if ([language isEqual:@"pt"]) return key;
  NSDictionary *entry = StormTranslations()[key];
  return entry[language] ?: entry[@"en"] ?: key;
}
