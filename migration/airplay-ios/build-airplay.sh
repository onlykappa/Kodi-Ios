#!/usr/bin/env bash
# Builds KodiAirPlay.framework: Apple's AirPlay route button (AVRoutePickerView) placed over Kodi's top-right corner.
# Kodi's skin cannot draw a native control, so the setup add-on loads this library with ctypes and calls
# kodi_airplay_show(1/0) during playback, kodi_airplay_open() from the iPhone menu, and kodi_airplay_play(url,
# title) to hand a stream to Apple's player for real AirPlay video (MP4/HLS). Needs macOS with Xcode.
# r3: kodi_airplay_state() says whether Apple's player could open the stream (Python falls back to Screen Mirroring
# and resumes Kodi when it could not), kodi_airplay_close() dismisses it, and kodi_background_keep(1/0) keeps Kodi
# running after it leaves the screen while a download or upload has work (silence mixed with other apps' sound).
# r4: Apple's player never turns the phone and Kodi rebuilds its screen when it closes (half-drawn Kodi after AirPlay).
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

#import <stdatomic.h>

#import <objc/message.h>

static AVRoutePickerView *picker;
static AVPlayerViewController *airplayController;
static atomic_int airplayState = 0; // 0 idle or loading, 1 Apple's player has the stream, -1 it could not open it
static NSTimer *airplayWatch;

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

// r4: Apple's player presented full screen turned the phone (it allows landscape) while Kodi's own view was taken
// off the screen; back in Kodi the turn was missed and Kodi drew only the left 46% of the screen with no text (owner
// screenshots). The holder keeps the orientation Kodi has, is presented over Kodi (Kodi's view stays in place), and
// when it closes asks Kodi to rebuild its screen (XBMCController applyRotatedScreen, from the portrait patch).
static void healKodi(void) {
    UIViewController *root = kodiWindow().rootViewController;
    SEL heal = NSSelectorFromString(@"applyRotatedScreen");
    if ([root respondsToSelector:heal]) ((void (*)(id, SEL))objc_msgSend)(root, heal);
}

@interface KodiAirPlayHolder : UIViewController
@property (nonatomic) UIInterfaceOrientationMask mask;
@property (nonatomic, weak) UIButton *closeButton;
@end

@implementation KodiAirPlayHolder
- (UIInterfaceOrientationMask)supportedInterfaceOrientations { return self.mask; }
- (BOOL)shouldAutorotate { return NO; }
- (void)viewDidLoad {
    [super viewDidLoad];
    self.view.backgroundColor = UIColor.blackColor;
    UIButton *close = [UIButton buttonWithType:UIButtonTypeSystem];
    [close setImage:[UIImage systemImageNamed:@"xmark.circle.fill"] forState:UIControlStateNormal];
    close.tintColor = UIColor.whiteColor;
    close.translatesAutoresizingMaskIntoConstraints = NO;
    [close addTarget:self action:@selector(closeTapped) forControlEvents:UIControlEventTouchUpInside];
    [self.view addSubview:close];
    [NSLayoutConstraint activateConstraints:@[
        [close.topAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.topAnchor constant:8],
        [close.leadingAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.leadingAnchor constant:12],
        [close.widthAnchor constraintEqualToConstant:44], [close.heightAnchor constraintEqualToConstant:44],
    ]];
    self.closeButton = close;
}
- (void)closeTapped {
    [airplayController.player pause];
    [self dismissViewControllerAnimated:YES completion:nil];
}
- (void)viewDidDisappear:(BOOL)animated {
    [super viewDidDisappear:animated];
    if (self.isBeingDismissed || self.presentingViewController == nil) {
        // Twice: once now, once after any rotation iOS still runs has settled.
        healKodi();
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.8 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{ healKodi(); });
    }
}
@end

static KodiAirPlayHolder *airplayHolder;

// Real AirPlay video: Apple's player with external playback, then the device sheet. The TV keeps playing while
// Kodi is in the background (playback audio session). Apple's player handles MP4/MOV/HLS, not MKV.
__attribute__((visibility("default"))) void kodi_airplay_play(const char *url, const char *title) {
    NSString *link = url ? [NSString stringWithUTF8String:url] : nil;
    NSString *name = title ? [NSString stringWithUTF8String:title] : @"";
    atomic_store(&airplayState, 0); // before returning, so a caller polling kodi_airplay_state() never sees the last result
    dispatch_async(dispatch_get_main_queue(), ^{
        NSURL *address = link ? [NSURL URLWithString:link] : nil;
        if (!address) atomic_store(&airplayState, -1);
        UIViewController *root = kodiWindow().rootViewController;
        if (!address || !root) return;
        [[AVAudioSession sharedInstance] setCategory:AVAudioSessionCategoryPlayback mode:AVAudioSessionModeMoviePlayback options:0 error:nil];
        [[AVAudioSession sharedInstance] setActive:YES error:nil];
        AVPlayer *player = [AVPlayer playerWithURL:address];
        [airplayWatch invalidate];
        // r3: Apple's player opens MP4/MOV/HLS only (no MKV) and needs the link to answer on the Wi-Fi address.
        airplayWatch = [NSTimer scheduledTimerWithTimeInterval:0.5 repeats:YES block:^(NSTimer *timer) {
            AVPlayerItem *item = player.currentItem;
            if (item.status == AVPlayerItemStatusReadyToPlay) {
                atomic_store(&airplayState, 1);
                [timer invalidate];
            } else if (item.status == AVPlayerItemStatusFailed || player.status == AVPlayerStatusFailed) {
                NSLog(@"KodiAirPlay: Apple's player could not open the stream: %@", item.error ?: player.error);
                atomic_store(&airplayState, -1);
                [timer invalidate];
            }
        }];
        player.allowsExternalPlayback = YES;
        player.usesExternalPlaybackWhileExternalScreenIsActive = YES;
        if (airplayHolder) [airplayHolder dismissViewControllerAnimated:NO completion:nil];
        airplayController = [[AVPlayerViewController alloc] init];
        airplayController.player = player;
        airplayController.title = name;
        airplayController.allowsPictureInPicturePlayback = YES;
        airplayController.entersFullScreenWhenPlaybackBegins = NO;
        // r4: inside a holder that keeps Kodi's orientation, over Kodi rather than in place of it.
        KodiAirPlayHolder *holder = [[KodiAirPlayHolder alloc] init];
        UIWindowScene *scene = kodiWindow().windowScene;
        UIInterfaceOrientation now = scene ? scene.interfaceOrientation : UIInterfaceOrientationPortrait;
        holder.mask = UIInterfaceOrientationIsLandscape(now) ? UIInterfaceOrientationMaskLandscape : UIInterfaceOrientationMaskPortrait;
        holder.modalPresentationStyle = UIModalPresentationOverFullScreen;
        [holder addChildViewController:airplayController];
        airplayController.view.frame = holder.view.bounds;
        airplayController.view.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
        [holder.view insertSubview:airplayController.view atIndex:0];
        [airplayController didMoveToParentViewController:holder];
        if (holder.closeButton) [holder.view bringSubviewToFront:holder.closeButton];
        airplayHolder = holder;
        UIViewController *top = root;
        while (top.presentedViewController) top = top.presentedViewController;
        [top presentViewController:holder animated:YES completion:^{
            [player play];
            AVRoutePickerView *sheet = [[AVRoutePickerView alloc] initWithFrame:CGRectMake(0, 0, 1, 1)];
            sheet.prioritizesVideoDevices = YES;
            [holder.view addSubview:sheet];
            openSheet(sheet);
        }];
    });
}

// r3: 1 once Apple's player has the stream, -1 if it could not open it, 0 before either (or when idle).
__attribute__((visibility("default"))) int kodi_airplay_state(void) {
    return atomic_load(&airplayState);
}

// r3: closes Apple's player (after it failed, so Kodi can carry on).
__attribute__((visibility("default"))) void kodi_airplay_close(void) {
    dispatch_async(dispatch_get_main_queue(), ^{
        [airplayWatch invalidate];
        airplayWatch = nil;
        [airplayController.player pause];
        [airplayHolder dismissViewControllerAnimated:YES completion:nil];
        airplayHolder = nil;
        airplayController = nil;
        atomic_store(&airplayState, 0);
    });
}

// r3: background downloads. iOS suspends an app a few seconds after it leaves the screen unless it plays sound
// (Kodi's Info.plist has the audio background mode). While Python says a download or upload has work and the app is
// in the background, play one second of silence on a loop, mixed with other apps so their sound carries on.
static AVAudioPlayer *keepPlayer;
static BOOL keepWanted, keepInBackground, keepSaved;
static AVAudioSessionCategory keepCategory;
static AVAudioSessionMode keepMode;
static AVAudioSessionCategoryOptions keepOptions;

static NSData *silence(void) {
    // 16-bit mono PCM WAV, 8 kHz, one second of zeros (little-endian, as on every iPhone).
    const uint32_t rate = 8000, bytes = rate * 2, riff = 36 + bytes, fmtSize = 16, byteRate = rate * 2;
    const uint16_t pcm = 1, mono = 1, align = 2, bits = 16;
    NSMutableData *wav = [NSMutableData dataWithLength:44 + bytes];
    uint8_t *b = wav.mutableBytes;
    memcpy(b, "RIFF", 4); memcpy(b + 4, &riff, 4); memcpy(b + 8, "WAVEfmt ", 8); memcpy(b + 16, &fmtSize, 4);
    memcpy(b + 20, &pcm, 2); memcpy(b + 22, &mono, 2); memcpy(b + 24, &rate, 4); memcpy(b + 28, &byteRate, 4);
    memcpy(b + 32, &align, 2); memcpy(b + 34, &bits, 2); memcpy(b + 36, "data", 4); memcpy(b + 40, &bytes, 4);
    return wav;
}

static void keepUpdate(void) {
    // Main thread only.
    AVAudioSession *session = AVAudioSession.sharedInstance;
    const BOOL run = keepWanted && keepInBackground;
    if (run && !keepPlayer.playing) {
        if (!keepSaved) {
            keepCategory = session.category; keepMode = session.mode; keepOptions = session.categoryOptions; keepSaved = YES;
        }
        NSError *error = nil;
        [session setCategory:AVAudioSessionCategoryPlayback mode:AVAudioSessionModeDefault
                     options:AVAudioSessionCategoryOptionMixWithOthers error:&error];
        [session setActive:YES error:&error];
        if (!keepPlayer) {
            keepPlayer = [[AVAudioPlayer alloc] initWithData:silence() error:&error];
            keepPlayer.numberOfLoops = -1;
        }
        BOOL playing = [keepPlayer prepareToPlay] && [keepPlayer play];
        NSLog(@"KodiAirPlay: staying awake in the background for a download or upload: %@", playing ? @"yes" : error);
    } else if (!run && keepPlayer.playing) {
        [keepPlayer stop];
        if (keepSaved) [session setCategory:keepCategory mode:keepMode options:keepOptions error:nil];
        keepSaved = NO;
        NSLog(@"KodiAirPlay: background keep-alive stopped");
    }
}

__attribute__((visibility("default"))) void kodi_background_keep(int on) {
    dispatch_async(dispatch_get_main_queue(), ^{
        static dispatch_once_t once;
        dispatch_once(&once, ^{
            NSNotificationCenter *center = NSNotificationCenter.defaultCenter;
            keepInBackground = UIApplication.sharedApplication.applicationState == UIApplicationStateBackground;
            [center addObserverForName:UIApplicationDidEnterBackgroundNotification object:nil queue:NSOperationQueue.mainQueue
                            usingBlock:^(NSNotification *note) { keepInBackground = YES; keepUpdate(); }];
            [center addObserverForName:UIApplicationWillEnterForegroundNotification object:nil queue:NSOperationQueue.mainQueue
                            usingBlock:^(NSNotification *note) { keepInBackground = NO; keepUpdate(); }];
            // A phone call or another app's sound stops the silence; start it again when that ends.
            [center addObserverForName:AVAudioSessionInterruptionNotification object:nil queue:NSOperationQueue.mainQueue
                            usingBlock:^(NSNotification *note) {
                if ([note.userInfo[AVAudioSessionInterruptionTypeKey] unsignedIntegerValue] == AVAudioSessionInterruptionTypeEnded) {
                    [keepPlayer stop];
                    keepUpdate();
                }
            }];
        });
        keepWanted = on != 0;
        keepUpdate();
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
nm -gU "$FW/KodiAirPlay" | grep -E ' _kodi_(airplay_(show|open|play|state|close)|background_keep)$'
lipo -info "$FW/KodiAirPlay"
(cd "$OUT" && zip -qry KodiAirPlay.framework.zip KodiAirPlay.framework && shasum -a 256 KodiAirPlay.framework.zip | tee KodiAirPlay.framework.zip.sha256)
