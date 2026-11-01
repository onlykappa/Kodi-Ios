#!/usr/bin/env bash
# Builds KodiAirPlay.framework: Apple's AirPlay route button (AVRoutePickerView) placed over Kodi's top-right corner.
# Kodi's skin cannot draw a native control, so the setup add-on loads this library with ctypes and calls
# kodi_airplay_show(1/0) during playback, kodi_airplay_open() from the iPhone menu, and kodi_airplay_play(url,
# title) to hand a stream to Apple's player for real AirPlay video (MP4/HLS). Needs macOS with Xcode.
# Usage: build-airplay.sh OUT_DIR
set -euo pipefail
[[ "$(uname -s)" == Darwin ]] || { echo 'BLOCKED: macOS with the iPhoneOS SDK is required.' >&2; exit 2; }
OUT="$(mkdir -p "${1:?output directory}" && cd "$1" && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/kodi-airplay.XXXXXX")"
MIN_IOS=14.0
SDK="$(xcrun --sdk iphoneos --show-sdk-path)"
cat > "$WORK/KodiAirPlay.m" <<'OBJC'
#import <UIKit/UIKit.h>
#import <AVKit/AVKit.h>
#import <AVFoundation/AVFoundation.h>

static AVRoutePickerView *picker;
static AVPlayerViewController *airplayController;

static UIWindow *kodiWindow(void) {
    for (UIScene *scene in UIApplication.sharedApplication.connectedScenes) {
        if (![scene isKindOfClass:UIWindowScene.class]) continue;
        for (UIWindow *window in ((UIWindowScene *)scene).windows) {
            if (window.isKeyWindow) return window;
        }
    }
    return UIApplication.sharedApplication.windows.firstObject;
}

static AVRoutePickerView *ensurePicker(void) {
    UIWindow *window = kodiWindow();
    if (!window) return nil;
    if (!picker) {
        picker = [[AVRoutePickerView alloc] initWithFrame:CGRectZero];
        picker.tintColor = UIColor.whiteColor;
        picker.activeTintColor = UIColor.systemBlueColor;
        picker.prioritizesVideoDevices = YES;
        picker.translatesAutoresizingMaskIntoConstraints = NO;
        picker.hidden = YES;
    }
    if (picker.superview != window) {
        [picker removeFromSuperview];
        [window addSubview:picker];
        UILayoutGuide *safe = window.safeAreaLayoutGuide;
        [NSLayoutConstraint activateConstraints:@[
            [picker.topAnchor constraintEqualToAnchor:safe.topAnchor constant:6],
            [picker.trailingAnchor constraintEqualToAnchor:safe.trailingAnchor constant:-10],
            [picker.widthAnchor constraintEqualToConstant:44],
            [picker.heightAnchor constraintEqualToConstant:44],
        ]];
    }
    [window bringSubviewToFront:picker];
    return picker;
}

// Shows or hides the button in the top-right corner. Safe to call from any thread.
__attribute__((visibility("default"))) void kodi_airplay_show(int visible) {
    dispatch_async(dispatch_get_main_queue(), ^{
        AVRoutePickerView *view = ensurePicker();
        view.hidden = !visible;
    });
}

static void openSheet(AVRoutePickerView *view) {
    for (UIView *subview in view.subviews) {
        if ([subview isKindOfClass:UIButton.class]) {
            [(UIButton *)subview sendActionsForControlEvents:UIControlEventTouchUpInside];
            return;
        }
    }
}

// Real AirPlay video: Apple's player with external playback, then the device sheet. The TV keeps playing while
// Kodi is in the background (playback audio session). Apple's player handles MP4/MOV/HLS, not MKV.
__attribute__((visibility("default"))) void kodi_airplay_play(const char *url, const char *title) {
    NSString *link = url ? [NSString stringWithUTF8String:url] : nil;
    NSString *name = title ? [NSString stringWithUTF8String:title] : @"";
    dispatch_async(dispatch_get_main_queue(), ^{
        NSURL *address = link ? [NSURL URLWithString:link] : nil;
        UIViewController *root = kodiWindow().rootViewController;
        if (!address || !root) return;
        [[AVAudioSession sharedInstance] setCategory:AVAudioSessionCategoryPlayback mode:AVAudioSessionModeMoviePlayback options:0 error:nil];
        [[AVAudioSession sharedInstance] setActive:YES error:nil];
        AVPlayer *player = [AVPlayer playerWithURL:address];
        player.allowsExternalPlayback = YES;
        player.usesExternalPlaybackWhileExternalScreenIsActive = YES;
        if (airplayController) [airplayController dismissViewControllerAnimated:NO completion:nil];
        airplayController = [[AVPlayerViewController alloc] init];
        airplayController.player = player;
        airplayController.title = name;
        airplayController.allowsPictureInPicturePlayback = YES;
        UIViewController *top = root;
        while (top.presentedViewController) top = top.presentedViewController;
        [top presentViewController:airplayController animated:YES completion:^{
            [player play];
            AVRoutePickerView *sheet = [[AVRoutePickerView alloc] initWithFrame:CGRectMake(0, 0, 1, 1)];
            sheet.prioritizesVideoDevices = YES;
            [airplayController.view addSubview:sheet];
            openSheet(sheet);
        }];
    });
}

// Opens the "AirPlay & Bluetooth devices" sheet as if the button had been tapped.
__attribute__((visibility("default"))) void kodi_airplay_open(void) {
    dispatch_async(dispatch_get_main_queue(), ^{
        AVRoutePickerView *view = ensurePicker();
        for (UIView *subview in view.subviews) {
            if ([subview isKindOfClass:UIButton.class]) {
                [(UIButton *)subview sendActionsForControlEvents:UIControlEventTouchUpInside];
                return;
            }
        }
    });
}
OBJC
FW="$OUT/KodiAirPlay.framework"; rm -rf "$FW"; mkdir -p "$FW"
xcrun --sdk iphoneos clang -arch arm64 -isysroot "$SDK" -miphoneos-version-min=$MIN_IOS -fobjc-arc -O2 -dynamiclib \
  -install_name @rpath/KodiAirPlay.framework/KodiAirPlay -framework UIKit -framework AVKit -framework AVFoundation -framework CoreGraphics \
  -o "$FW/KodiAirPlay" "$WORK/KodiAirPlay.m"
cat > "$FW/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>KodiAirPlay</string>
<key>CFBundleIdentifier</key><string>org.kodi-ios.airplay</string>
<key>CFBundleName</key><string>KodiAirPlay</string>
<key>CFBundlePackageType</key><string>FMWK</string>
<key>CFBundleShortVersionString</key><string>1.0</string>
<key>CFBundleVersion</key><string>1</string>
<key>CFBundleSupportedPlatforms</key><array><string>iPhoneOS</string></array>
<key>MinimumOSVersion</key><string>$MIN_IOS</string>
</dict></plist>
PLIST
nm -gU "$FW/KodiAirPlay" | grep -E ' _kodi_airplay_(show|open|play)$'
lipo -info "$FW/KodiAirPlay"
(cd "$OUT" && zip -qry KodiAirPlay.framework.zip KodiAirPlay.framework && shasum -a 256 KodiAirPlay.framework.zip | tee KodiAirPlay.framework.zip.sha256)
