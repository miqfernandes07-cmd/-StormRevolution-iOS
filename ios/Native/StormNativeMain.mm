// SDL owns the UIKit application delegate. Do not combine with App/main.mm.
#include <SDL3/SDL_main.h>
#import "StormNativeSession.h"
#import "Import/StormGameImporter.h"
#include <rex/app/title_app.h>
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
  rex::Result<void> OnConfigure(rex::SettingsRegistry& settings) override {
    NSURL *support = [NSFileManager.defaultManager URLsForDirectory:NSApplicationSupportDirectory inDomains:NSUserDomainMask].firstObject;
    NSURL *cache = [NSFileManager.defaultManager URLsForDirectory:NSCachesDirectory inDomains:NSUserDomainMask].firstObject;
    NSURL *documents = [NSFileManager.defaultManager URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject;
    const auto path = [&](std::string_view name, NSURL *url) -> rex::Result<void> {
      NSError *error = nil;
      if (![NSFileManager.defaultManager createDirectoryAtURL:url withIntermediateDirectories:YES attributes:nil error:&error])
        return rex::Err(rex::ErrorCategory::kIO, error.localizedDescription.UTF8String);
      return settings.SetText(rex::SettingLayer::kTitle, name, url.path.UTF8String);
    };
    REX_TRY_VOID(path("app.log_root", [documents URLByAppendingPathComponent:@"Logs"]));
    REX_TRY_VOID(path("app.user_root", [support URLByAppendingPathComponent:@"User"]));
    REX_TRY_VOID(path("app.cache_root", [cache URLByAppendingPathComponent:@"Native"]));
    REX_TRY_VOID(settings.SetText(rex::SettingLayer::kTitle, "app.config_file", [support URLByAppendingPathComponent:@"StormNative.toml"].path.UTF8String));
    REX_TRY_VOID(settings.SetText(rex::SettingLayer::kTitle, "title.game_root", StormGameImporter.gameURL.path.UTF8String));
    REX_TRY_VOID(settings.SetText(rex::SettingLayer::kTitle, "hid.shared_pads", "true"));
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
      while (!session.ready && app.RunFrame()) {}
      if (session.ready && !rex::app::IsShutdownRequested()) {
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
