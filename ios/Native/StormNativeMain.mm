// SDL owns the UIKit application delegate. Do not combine with App/main.mm.
#include <SDL3/SDL_main.h>
#import "StormNativeSession.h"
#import "Import/StormGameImporter.h"
#import "StormNativePreferences.h"
#import "StormNativeSaveProfiles.h"
#import "StormNativeCheats.h"
#include <rex/app/title_app.h>
#include <rex/gpu/graphics_system.h>
#include <rex/hid/input_system.h>
#include <rex/ui/ui_system.h>
#if defined(STORM_NATIVE_INTERFACE_CHECK)
// Syntax checking only; this declaration cannot produce an executable.
extern const rex::ppc::PPCImage kPPCImageConfig;
#else
#include "StormProbe_init.h"
#endif

class StormNativeApp final : public rex::app::TitleApp {
 public:
  StormNativeApp() : TitleApp("StormNative", kPPCImageConfig) {}
 protected:
  rex::platform::CrashReporterOptions GetCrashOptions() override {
    return {.app_name = "StormNative", .show_dialog = false};
  }
  rex::Result<void> OnConfigure(rex::SettingsRegistry& settings) override {
    [StormNativePreferences prepareForLaunch];
    NSError *profileError = nil;
    if (![StormNativeSaveProfiles selectCheats:[StormNativePreferences.values[@"cheatMode"] boolValue] error:&profileError])
      return rex::Err(rex::ErrorCategory::kIO, profileError.localizedDescription.UTF8String);
    NSError *migrationError = nil;
    if (![StormGameImporter prepareGameDirectory:&migrationError])
      return rex::Err(rex::ErrorCategory::kIO, migrationError.localizedDescription.UTF8String);
    NSURL *support = [NSFileManager.defaultManager URLsForDirectory:NSApplicationSupportDirectory inDomains:NSUserDomainMask].firstObject;
    NSURL *cache = [NSFileManager.defaultManager URLsForDirectory:NSCachesDirectory inDomains:NSUserDomainMask].firstObject;
    NSURL *documents = [NSFileManager.defaultManager URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject;
    if ([StormNativePreferences.values[@"clearCache"] boolValue]) {
      NSURL *shaderCache = [cache URLByAppendingPathComponent:@"Native"];
      NSError *clearError = nil;
      if (![NSFileManager.defaultManager fileExistsAtPath:shaderCache.path] ||
          [NSFileManager.defaultManager removeItemAtURL:shaderCache error:&clearError])
        [StormNativePreferences setValue:@NO forKey:@"clearCache"];
      else NSLog(@"StormNative cache: %@", clearError.localizedDescription);
    }
    const auto path = [&](std::string_view name, NSURL *url) -> rex::Result<void> {
      NSError *error = nil;
      if (![NSFileManager.defaultManager createDirectoryAtURL:url withIntermediateDirectories:YES attributes:nil error:&error])
        return rex::Err(rex::ErrorCategory::kIO, error.localizedDescription.UTF8String);
      return settings.SetText(rex::SettingLayer::kRuntime, name, url.path.UTF8String);
    };
    REX_TRY_VOID(path("app.log_root", [documents URLByAppendingPathComponent:@"Logs"]));
    REX_TRY_VOID(settings.SetText(rex::SettingLayer::kRuntime, "app.user_root", StormNativeSaveProfiles.activeURL.path.UTF8String));
    REX_TRY_VOID(path("app.cache_root", [cache URLByAppendingPathComponent:@"Native"]));
    REX_TRY_VOID(settings.SetText(rex::SettingLayer::kTitle, "app.config_file", [support URLByAppendingPathComponent:@"StormNative.toml"].path.UTF8String));
    REX_TRY_VOID(settings.SetText(rex::SettingLayer::kTitle, "title.game_root", StormGameImporter.gameURL.path.UTF8String));
    REX_TRY_VOID(settings.SetText(rex::SettingLayer::kTitle, "hid.shared_pads", "true"));
    // Upstream's Apple default is Cocoa; this application uses SDL's UIKit driver.
    REX_TRY_VOID(settings.SetText(rex::SettingLayer::kTitle, "ui.sdl.video_driver", "uikit"));
    NSDictionary<NSString *,NSString *> *graphics = StormNativePreferences.runtimeValues;
    for (NSString *key in graphics)
      REX_TRY_VOID(settings.SetText(rex::SettingLayer::kRuntime, key.UTF8String, graphics[key].UTF8String));
    return rex::Ok();
  }
};

static int RunStormNative(StormNativeApp& app, const rex::CLIArgList& args) {
  if (app.Init(args)) {
    auto native = app.GetUI().GetNativeWindow();
    if (!native || native->type != rex::NativeWindow::Type::kUIKit || !native->window) {
      NSLog(@"StormNative: janela UIKit indisponível");
      rex::app::RequestShutdown(1);
    } else {
      StormNativeSession *session = [[StormNativeSession alloc] initWithWindow:(__bridge UIWindow *)native->window];
      // The copied pointer stays valid until invalidate clears both callbacks, before Shutdown.
      StormNativeApp *application = &app;
      session.overlayChanged = ^(BOOL visible) {
        if (visible) application->GetInput().AcquireUIBlock();
        else application->GetInput().ReleaseUIBlock();
      };
      session.frameStatistics = ^NSDictionary * {
        auto stats = application->GetGraphics().GetFrameStats();
        return @{@"fps":@(stats.fps), @"frames":@(stats.frame_count), @"frameTimeMs":@(stats.frame_time_ms)};
      };
      while (!session.launchRequested && app.RunFrame()) {}
      if (session.ready && !rex::app::IsShutdownRequested()) {
        StormNativeSetCheatsEnabled([StormNativePreferences.values[@"cheatMode"] boolValue]);
        if ([session attachControls]) {
          auto launch = app.LaunchTitle();
          if (launch) app.Run();
          else {
            [session showFailure:[NSString stringWithUTF8String:launch.error().GetDescription().c_str()]];
            while (app.RunFrame()) {}
          }
        } else while (app.RunFrame()) {}
      }
      [session invalidate];
    }
  }
  return app.Shutdown();
}
REX_TITLE_APP_MAIN(StormNativeApp, RunStormNative)
