#import "Import/StormGameImporter.h"
#import <Foundation/Foundation.h>
#include <vector>
#include <cstdio>
#include <zlib.h>

// Own synthetic data only. Runs exclusively under the explicit CI launch flag.
static NSData *Fixture(NSString *name) {
  std::vector<uint8_t> b;
  auto u16=[&](uint16_t v){b.push_back(v&255);b.push_back(v>>8);};
  auto u32=[&](uint32_t v){u16(v&65535);u16(v>>16);};
  NSData *filename=[name dataUsingEncoding:NSASCIIStringEncoding];
  const uint8_t payload[]={'X','E','X','2'};
  uint32_t crc=(uint32_t)crc32(0,payload,sizeof(payload));
  u32(0x04034b50);u16(20);u16(0);u16(0);u16(0);u16(0);u32(crc);u32(4);u32(4);u16(filename.length);u16(0);
  const auto *n=(const uint8_t *)filename.bytes;
  b.insert(b.end(),n,n+filename.length);b.insert(b.end(),payload,payload+4);
  const uint32_t central=(uint32_t)b.size();
  u32(0x02014b50);u16(20);u16(20);u16(0);u16(0);u16(0);u16(0);u32(crc);u32(4);u32(4);u16(filename.length);u16(0);u16(0);u16(0);u16(0);u32(0);u32(0);
  b.insert(b.end(),n,n+filename.length);
  const uint32_t centralSize=(uint32_t)b.size()-central;
  u32(0x06054b50);u16(0);u16(0);u16(1);u16(1);u32(centralSize);u32(central);u16(0);
  return [NSData dataWithBytes:b.data() length:b.size()];
}
@interface StormImportSmoke : NSObject
@property(nonatomic,strong) StormGameImporter *importer;
@property(nonatomic,strong) NSURL *fixture;
@property(nonatomic,strong) NSURL *sentinel;
@property(nonatomic,strong) NSMutableArray<NSNumber *> *results;
@property(nonatomic) NSUInteger step;
@property(nonatomic) BOOL ownsGame;
- (void)start;
- (void)next;
- (void)finish;
@end
@implementation StormImportSmoke
- (void)start {
  std::fprintf(stderr,"IMPORT_SMOKE_START\n");std::fflush(stderr);
  self.results=[NSMutableArray array];self.importer=[[StormGameImporter alloc] init];
  NSFileManager *fm=NSFileManager.defaultManager;
  NSURL *game=[StormGameImporter gameURL];
  if ([fm fileExistsAtPath:game.path]) { [self.results addObject:@NO];[self finish];return; }
  NSError *error=nil;
  self.ownsGame=[fm createDirectoryAtURL:game withIntermediateDirectories:YES attributes:nil error:&error];
  self.sentinel=[game URLByAppendingPathComponent:@"synthetic-existing-import.txt"];
  [@"preserve-me" writeToURL:self.sentinel atomically:YES encoding:NSUTF8StringEncoding error:&error];
  self.fixture=[[NSURL fileURLWithPath:NSTemporaryDirectory() isDirectory:YES] URLByAppendingPathComponent:[NSUUID.UUID.UUIDString stringByAppendingString:@".zip"]];
  if(error){[self.results addObject:@NO];[self finish];return;}
  [self next];
}
- (void)next {
  std::fprintf(stderr,"IMPORT_SMOKE_STEP %lu\n",(unsigned long)self.step);std::fflush(stderr);
  NSString *name=self.step==1 ? @"../default.xex" : @"Folder/Default.xex";
  NSError *writeError=nil;
  if(![Fixture(name) writeToURL:self.fixture options:NSDataWritingAtomic error:&writeError]){[self.results addObject:@NO];[self finish];return;}
  [self.importer importZIPAtURL:self.fixture progress:^(double fraction,NSString *message){
    std::fprintf(stderr,"IMPORT_SMOKE_PROGRESS %lu %.2f %s\n",(unsigned long)self.step,fraction,message.UTF8String);std::fflush(stderr);
    if(self.step==2 && fraction==0)[self.importer cancel];
  } completion:^(NSDictionary *validation,NSError *error){
    std::fprintf(stderr,"IMPORT_SMOKE_CALLBACK %lu %s\n",(unsigned long)self.step,error.description.UTF8String ?: "no error");std::fflush(stderr);
    NSString *saved=[NSString stringWithContentsOfURL:self.sentinel encoding:NSUTF8StringEncoding error:nil];
    BOOL clean=YES;
    NSArray<NSURL *> *children=[NSFileManager.defaultManager contentsOfDirectoryAtURL:[StormGameImporter gameURL].URLByDeletingLastPathComponent includingPropertiesForKeys:nil options:0 error:nil];
    for(NSURL *url in children)if([url.lastPathComponent hasPrefix:@".incoming-"])clean=NO;
    BOOL expected=self.step==0 ? [error.domain isEqualToString:@"StormImport"] : self.step==1 ? [error.userInfo[@"diagnostic"] isEqualToString:@"ZIP_UNSAFE_PATH"] : error.code==NSUserCancelledError;
    [self.results addObject:@(!validation && error && expected && clean && [saved isEqualToString:@"preserve-me"])];
    ++self.step;if(self.step<3)[self next];else[self finish];
  }];
}
- (void)finish {
  BOOL passed=self.results.count==3;
  for(NSNumber *result in self.results)passed=passed&&result.boolValue;
  NSDictionary *report=@{@"passed":@(passed),@"checks":self.results,@"scope":@"synthetic ZIP rejection, rollback and cancellation in actual iOS importer",@"game_executed":@NO,@"full_game_zip_tested":@NO};
  NSURL *documents=[NSFileManager.defaultManager URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject;
  NSError *writeError=nil;
  BOOL written=[[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:&writeError] writeToURL:[documents URLByAppendingPathComponent:@"import-smoke-result.json"] options:NSDataWritingAtomic error:&writeError];
  std::fprintf(stderr,"IMPORT_SMOKE_FINISH passed=%d written=%d error=%s\n",passed,written,writeError.description.UTF8String ?: "none");std::fflush(stderr);
  if(self.ownsGame)[NSFileManager.defaultManager removeItemAtURL:[StormGameImporter gameURL] error:nil];
  if(self.fixture)[NSFileManager.defaultManager removeItemAtURL:self.fixture error:nil];
}
@end
void StormRunImportSmoke(void) {
  StormImportSmoke *test=[[StormImportSmoke alloc] init];
  [test start]; // Each pending completion owns the test until the next step.
}
