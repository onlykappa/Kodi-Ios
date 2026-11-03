#!/usr/bin/env bash
# Builds KodiAirPlay.framework: Apple's AirPlay route button (AVRoutePickerView) placed over Kodi's top-right corner.
# Kodi's skin cannot draw a native control, so the setup add-on loads this library with ctypes and calls
# kodi_airplay_show(1/0) during playback, kodi_airplay_open() from the iPhone menu, and kodi_airplay_play(url,
# title) to hand a stream to Apple's player for real AirPlay video (MP4/HLS). Needs macOS with Xcode.
# r3: kodi_airplay_state() says whether Apple's player could open the stream (Python falls back to Screen Mirroring
# and resumes Kodi when it could not), kodi_airplay_close() dismisses it, and kodi_background_keep(1/0) keeps Kodi
# running after it leaves the screen while a download or upload has work (silence mixed with other apps' sound).
# r4: Apple's player never turns the phone and Kodi rebuilds its screen when it closes (half-drawn Kodi after AirPlay).
# r5: MKV / AVI / WebM / MPEG-TS over AirPlay. kodi_airplay_play() sends those through the remuxer in remux/ (GMPlayer
# core + Kodi iOS code, FFmpeg 8.1.1 LGPL linked statically, its symbols kept private): an HLS server on the phone's
# Wi-Fi address that the Apple TV reads, video copied, DTS/TrueHD/FLAC/Opus/Vorbis re-encoded to AAC. MP4/MOV/HLS keep
# the direct path. kodi_airplay_message() gives the reason when it cannot play, for the screen. Licences in
# remux/THIRD-PARTY-NOTICES (also inside the framework).
# r6: kodi_airplay_log(buf, len) hands Python what happened for kodi.log: the variant line (CODECS, RESOLUTION,
# VIDEO-RANGE), the receiver's User-Agent, every request (path, status, bytes, ms), remux errors, and Apple's player
# events (ready, failed, its error log, presentation size, external playback). HEVC CODECS carry the stream's real
# constraint bytes (was a fixed B0). An AirPlay TV that takes the audio segments but never a video one (owner
# build-133: TCL Roku TV, HEVC file, sound with a music note) gets "No picture on the TV" with the way out.
# r7: a picture for those TVs. When the TV takes audio segments but no video ones, the stream restarts once in compat
# mode at the same position (kr_remux_start(..., compat=1): the remuxer decodes the video, VideoToolbox when it can,
# and re-encodes it to H.264 High 8-bit SDR at most 1080p with Apple's hardware encoder; CODECS avc1.640028), with
# "Converting the picture for this TV..." on the phone meanwhile; "No picture on the TV" only if that fails too. Files
# whose video AirPlay cannot carry at all (VP9, MPEG-2) convert from the start. Costs battery and warmth (a hardware
# decode + encode while playing; nothing runs once the player closes). HDR is not tone mapped (looks washed out).
# FFmpeg gains video decoders, libswscale and VideoToolbox (LGPL kept), linked with VideoToolbox, CoreMedia, CoreVideo.
# r8: owner build-136, TCL Roku TV: the TV fetched the master itself, read the HEVC init, hung up on the segments and
# AirPlay switched off within ~10 s, so r7's 30 s sound-only check never fired. The remuxer now tells receivers apart
# by User-Agent: a third-party AirPlay TV ("MFi_AirPlay_Device") gets the picture converted to H.264 from its first
# request while the phone and an Apple TV keep the copy (same segment grid). Fallback here: external playback ending
# within 20 s with no video segment served to the TV restarts once in compat mode. Segments come faster: inits and
# recent segments cached, the next two made ahead in the background, audio and video made at the same time (each on
# its own connection). Apple's player holder follows the screen (any orientation but upside down, relaid out on every
# size change) instead of the orientation Kodi had when it opened (controls laid out landscape on a portrait screen).
# Usage: build-airplay.sh OUT_DIR   (REMUX_FFMPEG=DIR reuses an iOS build of build-remux-ffmpeg.sh)
set -euo pipefail
[[ "$(uname -s)" == Darwin ]] || { echo 'BLOCKED: macOS with the iPhoneOS SDK is required.' >&2; exit 2; }
OUT="$(mkdir -p "${1:?output directory}" && cd "$1" && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/kodi-airplay.XXXXXX")"
HERE="$(cd "$(dirname "$0")" && pwd)"; REMUX="$HERE/remux"
FF="${REMUX_FFMPEG:-$WORK/ffmpeg-ios}"
[[ -f "$FF/lib/libavformat.a" ]] || bash "$HERE/build-remux-ffmpeg.sh" ios "$FF"
MIN_IOS=14.0
SDK="$(xcrun --sdk iphoneos --show-sdk-path)"
cat > "$WORK/KodiAirPlay.m" <<'OBJC'
#import <UIKit/UIKit.h>
#import <AVKit/AVKit.h>
#import <AVFoundation/AVFoundation.h>

#import <math.h>
#import <stdatomic.h>

#import <objc/message.h>
#import <os/lock.h>

#import "kr_remux.h"

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

// r5: why the current AirPlay stream could not play or stopped (for the alert and kodi_airplay_message()), set from
// any thread.
static char remuxNote[320];
static os_unfair_lock noteLock = OS_UNFAIR_LOCK_INIT;
static NSTimer *stallWatch;

static void setNote(NSString *text) {
    os_unfair_lock_lock(&noteLock);
    snprintf(remuxNote, sizeof remuxNote, "%s", text ? text.UTF8String : "");
    os_unfair_lock_unlock(&noteLock);
}

static UIView *airplayHolderView(void);

// r6: Apple's player events for kodi_airplay_log() (read with the remuxer's request log), latest 64 kept.
static NSMutableArray<NSString *> *playerLines;

static void playerNote(NSString *format, ...) NS_FORMAT_FUNCTION(1, 2);
static void playerNote(NSString *format, ...) {
    va_list ap; va_start(ap, format);
    NSString *line = [[NSString alloc] initWithFormat:format arguments:ap];
    va_end(ap);
    NSLog(@"KodiAirPlay: %@", line);
    os_unfair_lock_lock(&noteLock);
    if (!playerLines) playerLines = [NSMutableArray array];
    [playerLines addObject:[@"player: " stringByAppendingString:line]];
    if (playerLines.count > 64) [playerLines removeObjectAtIndex:0];
    os_unfair_lock_unlock(&noteLock);
}

// r7: the converted stream's source, for the one restart in compat mode (picture converted to H.264).
static char *remuxSource;
static const NSInteger convertingTag = 7707;

static void showConverting(BOOL on) {
    UIView *host = airplayHolderView();
    UIView *old = [host viewWithTag:convertingTag];
    if (!on) { [old removeFromSuperview]; return; }
    if (old || !host) return;
    UILabel *label = [[UILabel alloc] init];
    label.tag = convertingTag;
    label.text = @"Converting the picture for this TV\u2026";
    label.textColor = UIColor.whiteColor;
    label.backgroundColor = [UIColor colorWithWhite:0 alpha:0.7];
    label.textAlignment = NSTextAlignmentCenter;
    label.numberOfLines = 0;
    label.layer.cornerRadius = 10;
    label.clipsToBounds = YES;
    label.translatesAutoresizingMaskIntoConstraints = NO;
    [host addSubview:label];
    [NSLayoutConstraint activateConstraints:@[
        [label.centerXAnchor constraintEqualToAnchor:host.centerXAnchor],
        [label.centerYAnchor constraintEqualToAnchor:host.centerYAnchor],
        [label.widthAnchor constraintLessThanOrEqualToAnchor:host.widthAnchor constant:-40],
        [label.widthAnchor constraintGreaterThanOrEqualToConstant:260],
        [label.heightAnchor constraintGreaterThanOrEqualToConstant:56],
    ]];
}

static NSString *sizeText(CGSize size) { return [NSString stringWithFormat:@"%.0fx%.0f", size.width, size.height]; }

static void stopRemux(void) {
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_UTILITY, 0), ^{ kr_remux_stop(); });
}

@interface KodiAirPlayHolder : UIViewController
@property (nonatomic, weak) UIButton *closeButton;
@end

// r8: the holder follows the screen. r4 pinned the orientation Kodi had when Apple's player opened; Kodi then stopped
// and turned to portrait underneath, and Apple's controls stayed laid out landscape-wide on the portrait screen, cut
// off (owner screenshot, build-136). Any orientation but upside down, and the player view is laid out again on every
// size change. Kodi's screen is still rebuilt when the holder closes (healKodi, ISSUE-081).
@implementation KodiAirPlayHolder
- (UIInterfaceOrientationMask)supportedInterfaceOrientations { return UIInterfaceOrientationMaskAllButUpsideDown; }
- (BOOL)shouldAutorotate { return YES; }
- (UIInterfaceOrientation)preferredInterfaceOrientationForPresentation {
    // Open in the orientation the screen has now (no turn when it appears).
    UIWindowScene *scene = self.view.window.windowScene ?: kodiWindow().windowScene;
    UIInterfaceOrientation now = scene ? scene.interfaceOrientation : UIInterfaceOrientationUnknown;
    return now == UIInterfaceOrientationUnknown || now == UIInterfaceOrientationPortraitUpsideDown ? UIInterfaceOrientationPortrait : now;
}
- (void)layoutPlayer {
    for (UIViewController *child in self.childViewControllers) child.view.frame = self.view.bounds;
}
- (void)viewWillLayoutSubviews {
    [super viewWillLayoutSubviews];
    [self layoutPlayer];
}
- (void)viewWillTransitionToSize:(CGSize)size withTransitionCoordinator:(id<UIViewControllerTransitionCoordinator>)coordinator {
    [super viewWillTransitionToSize:size withTransitionCoordinator:coordinator];
    [coordinator animateAlongsideTransition:^(id<UIViewControllerTransitionCoordinatorContext> context) { [self layoutPlayer]; }
                                 completion:^(id<UIViewControllerTransitionCoordinatorContext> context) { [self layoutPlayer]; }];
}
- (void)viewDidAppear:(BOOL)animated {
    [super viewDidAppear:animated];
    // The screen may have turned while the holder was being presented (Kodi stopping): take the current orientation.
    if (@available(iOS 16.0, *)) [self setNeedsUpdateOfSupportedInterfaceOrientations];
    else [UIViewController attemptRotationToDeviceOrientation];
    [self layoutPlayer];
}
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
        [stallWatch invalidate]; stallWatch = nil;
        playerNote(@"closed at %.1f s", CMTimeGetSeconds(airplayController.player.currentTime));
        stopRemux();  // r5: playback stopped: the server, its sockets and the source connections go too
        // Twice: once now, once after any rotation iOS still runs has settled.
        healKodi();
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.8 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{ healKodi(); });
    }
}
@end

static KodiAirPlayHolder *airplayHolder;
static UIView *airplayHolderView(void) { return airplayHolder.view; }

// Real AirPlay video: Apple's player with external playback, then the device sheet. The TV keeps playing while
// Kodi is in the background (playback audio session). Apple's player handles MP4/MOV/HLS, not MKV.
// r5: never a silent hang: when the converted stream fails or stalls while the remuxer reports an error, say so.
static void showProblem(NSString *text) {
    setNote(text);
    playerNote(@"stopped: %@", text);
    if (!airplayHolder || airplayHolder.presentedViewController) return;
    UIAlertController *alert = [UIAlertController alertControllerWithTitle:@"AirPlay stopped" message:text
                                                            preferredStyle:UIAlertControllerStyleAlert];
    [alert addAction:[UIAlertAction actionWithTitle:@"Close" style:UIAlertActionStyleDefault handler:^(UIAlertAction *a) {
        [airplayController.player pause];
        [airplayHolder dismissViewControllerAnimated:YES completion:nil];
    }]];
    [airplayHolder presentViewController:alert animated:YES completion:nil];
}

// r6: sound but no picture on an AirPlay TV. Closing or carrying on with the sound is the person's choice.
static void showNoPicture(BOOL hevc) {
    NSString *text = hevc
        ? @"This TV's AirPlay can't play HEVC (H.265) video, so it plays only the sound. An Apple TV can. On this TV use "
          @"Play on TV › its Roku / TV app, or Screen Mirroring."
        : @"This TV's AirPlay is playing only the sound: it did not ask for the video. Try Play on TV › its Roku / TV "
          @"app, or Screen Mirroring.";
    setNote(text);
    if (!airplayHolder || airplayHolder.presentedViewController) return;
    UIAlertController *alert = [UIAlertController alertControllerWithTitle:@"No picture on the TV" message:text
                                                            preferredStyle:UIAlertControllerStyleAlert];
    [alert addAction:[UIAlertAction actionWithTitle:@"Keep the sound" style:UIAlertActionStyleCancel handler:nil]];
    [alert addAction:[UIAlertAction actionWithTitle:@"Close" style:UIAlertActionStyleDefault handler:^(UIAlertAction *a) {
        [airplayController.player pause];
        [airplayHolder dismissViewControllerAnimated:YES completion:nil];
    }]];
    [airplayHolder presentViewController:alert animated:YES completion:nil];
}

// r5/r7: Apple's player failing on the converted stream: the remuxer's reason when it has one.
static void watchFailures(AVPlayerItem *item) {
    [[NSNotificationCenter defaultCenter] addObserverForName:AVPlayerItemFailedToPlayToEndTimeNotification
        object:item queue:NSOperationQueue.mainQueue usingBlock:^(NSNotification *note) {
        if (airplayController.player.currentItem != note.object) return;  // the item replaced by the compat restart
        const char *m = kr_remux_message();
        NSError *e = note.userInfo[AVPlayerItemFailedToPlayToEndTimeErrorKey];
        showProblem(m && *m ? @(m) : (e.localizedDescription ?: @"The converted stream stopped."));
    }];
}

static void presentPlayer(NSString *link, NSString *name, BOOL converted) {
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
                playerNote(@"ready, presentation %@, %lu tracks, external %d", sizeText(item.presentationSize),
                           (unsigned long)item.tracks.count, player.externalPlaybackActive);
                atomic_store(&airplayState, 1);
                [timer invalidate];
            } else if (item.status == AVPlayerItemStatusFailed || player.status == AVPlayerStatusFailed) {
                playerNote(@"could not open the stream: %@", item.error ?: player.error);
                atomic_store(&airplayState, -1);
                [timer invalidate];
            }
        }];
        [stallWatch invalidate]; stallWatch = nil;
        if (converted) {
            __block int waiting = 0, ticks = 0, externalTicks = 0, video0 = 0, audio0 = 0, external = 0;
            __block NSUInteger errorsSeen = 0;
            __block BOOL warned = NO, compatTried = kr_remux_compat() != 0, restarting = NO;
            __block double resumeAt = -1;
            // r7: once per stream: restart with the picture converted to H.264 at the same position. NO when it cannot
            // (already tried, or no source to restart).
            BOOL (^restartCompat)(BOOL) = ^BOOL(BOOL hevc) {
                char *source = NULL;
                os_unfair_lock_lock(&noteLock);
                if (!compatTried && remuxSource) source = strdup(remuxSource);
                os_unfair_lock_unlock(&noteLock);
                if (!source) return NO;
                compatTried = YES; restarting = YES;
                double at = CMTimeGetSeconds(player.currentTime);
                if (!isfinite(at) || at < 0) at = 0;
                playerNote(@"restarting in compat mode (picture converted to H.264) at %.1f s", at);
                setNote(@"Converting the picture for this TV\u2026");
                showConverting(YES);
                dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
                    char playlist[512] = "";
                    int r = kr_remux_start(source, 1, 1, playlist, sizeof playlist);
                    free(source);
                    NSString *link = r == KR_READY ? @(playlist) : nil;
                    dispatch_async(dispatch_get_main_queue(), ^{
                        restarting = NO;
                        NSURL *address = link ? [NSURL URLWithString:link] : nil;
                        if (!address) {
                            const char *m = kr_remux_message();
                            playerNote(@"compat restart failed: %s", m ? m : "");
                            showConverting(NO);
                            showNoPicture(hevc);
                            return;
                        }
                        AVPlayerItem *next = [AVPlayerItem playerItemWithURL:address];
                        watchFailures(next);
                        [player replaceCurrentItemWithPlayerItem:next];
                        [player play];
                        resumeAt = at; errorsSeen = 0; waiting = 0; warned = NO;
                        externalTicks = 0; video0 = kr_remux_served(1); audio0 = kr_remux_served(0);
                        setNote(nil);
                    });
                });
                return YES;
            };
            stallWatch = [NSTimer scheduledTimerWithTimeInterval:1.0 repeats:YES block:^(NSTimer *timer) {
                AVPlayerItem *item = player.currentItem;
                ticks++;
                if (restarting) return;  // r7: the compat session is starting
                // r7: the compat stream is ready: back to where the TV was, then play.
                if (resumeAt >= 0 && item.status == AVPlayerItemStatusReadyToPlay) {
                    playerNote(@"compat stream ready, resuming at %.1f s", resumeAt);
                    [player seekToTime:CMTimeMakeWithSeconds(resumeAt, 600) toleranceBefore:kCMTimeZero
                        toleranceAfter:kCMTimePositiveInfinity completionHandler:^(BOOL done) { [player play]; }];
                    resumeAt = -1;
                    showConverting(NO);
                }
                // r6: Apple's player error log (segment / decoder failures it recovered from or not), once each.
                NSArray<AVPlayerItemErrorLogEvent *> *errors = item.errorLog.events;
                for (NSUInteger i = errorsSeen; i < errors.count; i++)
                    playerNote(@"error log: %ld %@ %@ (%@)", (long)errors[i].errorStatusCode, errors[i].errorDomain,
                               errors[i].errorComment ?: @"", errors[i].URI.lastPathComponent ?: @"");
                errorsSeen = errors.count;
                if (player.externalPlaybackActive != external) {
                    int wasOn = external, lasted = externalTicks;
                    external = player.externalPlaybackActive;
                    playerNote(@"external playback %@", external ? @"on (the TV fetches the stream)" : @"off");
                    externalTicks = 0; video0 = kr_remux_served(1); audio0 = kr_remux_served(0);
                    // r8: the TV gave up within seconds without one video segment (owner build-136: a TCL Roku TV read
                    // the HEVC master and init, hung up on the segments, AirPlay off ~10 s later): restart once with
                    // the picture converted instead of waiting for r7's 30 s of sound only. Only when the TV never had
                    // the converted picture (a receiver the remuxer did not recognise) and the video is not H.264.
                    if (wasOn && !external && lasted <= 20 && !compatTried && kr_remux_served_external(1) == 0) {
                        const char *codec = kr_remux_video_codec();
                        BOOL hevc = codec && (!strncmp(codec, "hvc1", 4) || !strncmp(codec, "hev1", 4));
                        if (kr_remux_compat_clients() > 0)
                            playerNote(@"external playback ended after %d s with no video segment served to the TV; it already had the H.264 picture", lasted);
                        else if (codec && !strncmp(codec, "avc1", 4))
                            playerNote(@"external playback ended after %d s with no video segment served to the TV (already H.264)", lasted);
                        else {
                            playerNote(@"external playback ended after %d s with no video segment served to the TV (%s): converting the picture", lasted, codec ? codec : "");
                            if (restartCompat(hevc)) return;
                        }
                    }
                }
                if (external) externalTicks++;
                if (ticks == 5 || ticks == 15 || ticks % 60 == 0)
                    playerNote(@"%ds: at %.1f s, rate %.1f, presentation %@, external %d, segments served video %d audio %d",
                               ticks, CMTimeGetSeconds(player.currentTime), player.rate, sizeText(item.presentationSize),
                               external, kr_remux_served(1), kr_remux_served(0));
                // r6: an AirPlay TV that cannot decode the video (many TVs' built-in AirPlay: no HEVC) takes the audio
                // segments and never a video one, plays the sound with a music note, and Apple's player looks fine.
                if (!warned && external && externalTicks >= 30 && player.timeControlStatus == AVPlayerTimeControlStatusPlaying &&
                    kr_remux_served(0) > audio0 && kr_remux_served(1) == video0) {
                    warned = YES;
                    const char *codec = kr_remux_video_codec();
                    BOOL hevc = codec && (!strncmp(codec, "hvc1", 4) || !strncmp(codec, "hev1", 4));
                    playerNote(@"the TV takes audio segments but no video ones (%s): sound only", codec ? codec : "");
                    if (restartCompat(hevc)) return;
                    showNoPicture(hevc);
                }
                if (item.status == AVPlayerItemStatusFailed) {
                    const char *m = kr_remux_message();
                    showProblem(m && *m ? @(m) : (player.currentItem.error.localizedDescription ?: @"The TV could not play the converted stream."));
                    [timer invalidate]; return;
                }
                waiting = player.timeControlStatus == AVPlayerTimeControlStatusWaitingToPlayAtSpecifiedRate ? waiting + 1 : 0;
                const char *m = kr_remux_message();
                if (waiting >= 20 && m && *m) { showProblem(@(m)); [timer invalidate]; }
            }];
            watchFailures(player.currentItem);
        }
        player.allowsExternalPlayback = YES;
        player.usesExternalPlaybackWhileExternalScreenIsActive = YES;
        if (airplayHolder) [airplayHolder dismissViewControllerAnimated:NO completion:nil];
        airplayController = [[AVPlayerViewController alloc] init];
        airplayController.player = player;
        airplayController.title = name;
        airplayController.allowsPictureInPicturePlayback = YES;
        airplayController.entersFullScreenWhenPlaybackBegins = NO;
        // r4: inside a holder over Kodi rather than in place of it; r8: the holder follows the screen's orientation.
        KodiAirPlayHolder *holder = [[KodiAirPlayHolder alloc] init];
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

// Real AirPlay video: Apple's player with external playback, then the device sheet. The TV keeps playing while
// Kodi is in the background (playback audio session). Apple's player handles MP4/MOV/HLS; r5 converts MKV, AVI,
// WebM and MPEG-TS on the phone first (and links whose bytes turn out not to be MP4).
__attribute__((visibility("default"))) void kodi_airplay_play(const char *url, const char *title) {
    NSString *link = url ? [NSString stringWithUTF8String:url] : nil;
    NSString *name = title ? [NSString stringWithUTF8String:title] : @"";
    atomic_store(&airplayState, 0); // before returning, so a caller polling kodi_airplay_state() never sees the last result
    setNote(nil);
    BOOL direct = !link || kr_remux_kind(url) == KR_DIRECT;
    os_unfair_lock_lock(&noteLock);  // Python calls from its own thread; the player's timer reads it on the main thread
    free(remuxSource); remuxSource = direct ? NULL : strdup(url);
    os_unfair_lock_unlock(&noteLock);
    if (direct) { stopRemux(); presentPlayer(link, name, NO); return; }
    char *copy = strdup(url);
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
        char playlist[512] = "";
        int r = kr_remux_start(copy, 1, 0, playlist, sizeof playlist);
        free(copy);
        if (r == KR_READY) { NSLog(@"KodiAirPlay: converting for AirPlay at %s", playlist); presentPlayer(@(playlist), name, YES); }
        else if (r == KR_NOT_NEEDED) presentPlayer(link, name, NO);
        else {
            const char *m = kr_remux_message();
            NSString *why = m && *m ? @(m) : @"AirPlay could not convert this video.";
            setNote(why);
            NSLog(@"KodiAirPlay: %@", why);
            atomic_store(&airplayState, -1);
        }
    });
}

// r5: why AirPlay could not play the last stream ("" when it could). Returns the length written.
__attribute__((visibility("default"))) int kodi_airplay_message(char *buf, int len) {
    if (!buf || len <= 0) return 0;
    os_unfair_lock_lock(&noteLock);
    snprintf(buf, (size_t)len, "%s", remuxNote);
    os_unfair_lock_unlock(&noteLock);
    return (int)strlen(buf);
}

// r6: what happened since the last call, for kodi.log: Apple's player events, then the remuxer's lines (variant
// CODECS, receiver User-Agent, requests with status, bytes and ms, errors). Newline-separated; what does not fit
// waits for the next call. Returns the length written.
__attribute__((visibility("default"))) int kodi_airplay_log(char *buf, int len) {
    if (!buf || len <= 0) return 0;
    buf[0] = 0;
    size_t used = 0;
    os_unfair_lock_lock(&noteLock);
    while (playerLines.count) {
        const char *line = playerLines.firstObject.UTF8String ?: "";
        size_t n = strlen(line);
        if (used + n + 2 > (size_t)len) break;
        memcpy(buf + used, line, n); used += n; buf[used++] = '\n'; buf[used] = 0;
        [playerLines removeObjectAtIndex:0];
    }
    os_unfair_lock_unlock(&noteLock);
    if ((int)used < len - 1) used += (size_t)kr_remux_log(buf + used, len - (int)used);
    return (int)used;
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
        [stallWatch invalidate]; stallWatch = nil;
        stopRemux();
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
# The remuxer (C) for iPhoneOS, against the remux-only FFmpeg.
CC_IOS=(xcrun --sdk iphoneos clang -arch arm64 -isysroot "$SDK" -miphoneos-version-min=$MIN_IOS -O2 -std=gnu11 -I"$FF/include")
OBJS=()
for c in "$REMUX"/src/*.c "$REMUX"/gmplayer/*.c; do
  o="$WORK/$(basename "${c%.c}").o"; "${CC_IOS[@]}" -c "$c" -o "$o"; OBJS+=("$o")
done
# Only Kodi's entry points are exported: Kodi has its own FFmpeg, these copies stay private to the framework.
printf '_kodi_airplay_show\n_kodi_airplay_open\n_kodi_airplay_play\n_kodi_airplay_state\n_kodi_airplay_close\n_kodi_airplay_message\n_kodi_airplay_log\n_kodi_background_keep\n' > "$WORK/exports"
xcrun --sdk iphoneos clang -arch arm64 -isysroot "$SDK" -miphoneos-version-min=$MIN_IOS -fobjc-arc -O2 -dynamiclib \
  -install_name @rpath/KodiAirPlay.framework/KodiAirPlay -framework UIKit -framework AVKit -framework AVFoundation -framework CoreGraphics -framework CoreMedia \
  -framework VideoToolbox -framework CoreVideo \
  -I"$REMUX/src" -Wl,-exported_symbols_list,"$WORK/exports" \
  -o "$FW/KodiAirPlay" "$WORK/KodiAirPlay.m" "${OBJS[@]}" \
  "$FF/lib/libavformat.a" "$FF/lib/libavcodec.a" "$FF/lib/libswscale.a" "$FF/lib/libswresample.a" "$FF/lib/libavutil.a" \
  -framework Security -framework CoreFoundation -lz -liconv
cp "$REMUX/THIRD-PARTY-NOTICES" "$FW/THIRD-PARTY-NOTICES"; cp "$FF/FFMPEG-CONFIG.txt" "$FW/FFMPEG-CONFIG.txt"
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
nm -gU "$FW/KodiAirPlay" | grep -E ' _kodi_(airplay_(show|open|play|state|close|message|log)|background_keep)$'
[[ "$(nm -gU "$FW/KodiAirPlay" | grep -cE ' _kodi_(airplay_(show|open|play|state|close|message|log)|background_keep)$')" == 8 ]] || { echo 'missing exports' >&2; exit 1; }
! nm -gU "$FW/KodiAirPlay" | grep -E ' _(av|avformat|avcodec|swr|sws|kr|gm)_' || { echo 'FFmpeg symbols exported: they would clash with Kodi' >&2; exit 1; }
# r8: the per-receiver picture and the TV's segment count are linked in (private to the framework, not exported).
[[ "$(nm "$FW/KodiAirPlay" | grep -cE ' [tT] _kr_remux_(third_party_receiver|served_external|compat_clients)$')" == 3 ]] || { echo 'r8 remuxer missing' >&2; exit 1; }
# r7: the picture bridge needs Apple's hardware H.264 encoder in this FFmpeg.
grep -q -- '--enable-encoder=h264_videotoolbox' "$FF/FFMPEG-CONFIG.txt" || { echo 'FFmpeg built without h264_videotoolbox' >&2; exit 1; }
lipo -info "$FW/KodiAirPlay"
(cd "$OUT" && zip -qry KodiAirPlay.framework.zip KodiAirPlay.framework && shasum -a 256 KodiAirPlay.framework.zip | tee KodiAirPlay.framework.zip.sha256)
