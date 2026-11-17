#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN
// Owns one asynchronous, cancellable import. All callbacks run on the main queue.
@interface StormGameImporter : NSObject
+ (NSURL *)gameURL;
// Atomic same-volume move of old imports into Documents/Game. Never copies the
// multi-GB installation or overwrites either directory on conflict.
+ (BOOL)prepareGameDirectory:(NSError **)error;
+ (void)validateInstalledWithCompletion:(void (^)(NSDictionary * _Nullable validation, NSError * _Nullable error))completion;
- (void)importZIPAtURL:(NSURL *)url
             progress:(void (^)(double fraction, NSString *message))progress
           completion:(void (^)(NSDictionary * _Nullable validation, NSError * _Nullable error))completion;
- (void)cancel;
@end
NS_ASSUME_NONNULL_END
