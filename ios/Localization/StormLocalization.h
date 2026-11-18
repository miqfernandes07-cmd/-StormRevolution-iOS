#import <Foundation/Foundation.h>

// App UI only. Never changes the console language or the imported game assets.
FOUNDATION_EXPORT NSString *SL(NSString *key);
FOUNDATION_EXPORT NSString *StormAppLanguage(void);
FOUNDATION_EXPORT NSArray<NSString *> *StormAppLanguages(void);
FOUNDATION_EXPORT NSArray<NSString *> *StormAppLanguageNames(void);
FOUNDATION_EXPORT NSDictionary *StormTranslations(void);
