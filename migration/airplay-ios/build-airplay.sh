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
# r9: owner build-138, TCL Roku TV played the H.264 picture but slowly (a converted 6-s segment of a 4K 10-bit HEVC
# source took 5-9 s), stalled after skips and showed no subtitles. VideoToolbox-decoded frames now stay on the GPU
# (VTPixelTransferSession scales 4K P010 to 1080p NV12 into the encoder's own buffers, iOS 16+; threaded libswscale
# otherwise), the TV's first converted segment starts with its master request, a conversion far from a new request
# is cancelled, a dead source connection gives up in seconds and reopens at the offset, subtitles read 10 s back on
# the idle session demuxer instead of 30 s on the audio one, and failed requests carry their reason in kodi.log.
# r10: subtitles on the TV. Third-party AirPlay TVs ignore the master's WebVTT rendition, so the converted picture
# carries them burned in: kodi_airplay_subtitles(ordinal, file, lang) takes Kodi's current subtitle before
# kodi_airplay_play (Kodi's subtitle stream number, -1 off, -2 the file's forced/default; an external .srt/.vtt/.ass
# file such as a4kSubtitles' download), the remuxer draws it into each converted frame with libass (ISC; FreeType FTL,
# FriBidi LGPL-2.1+, HarfBuzz MIT, linked statically, built by build-libass.sh; fonts from iOS through CoreText) on
# the same segment grid, and a third-party TV gets the converted picture even for H.264 sources when subtitles are
# on. FFmpeg's own libass filter is not used (FFmpeg stays LGPL without external libraries).
# r11: audio never waits. r10 read WebVTT cue files on the audio demuxer's lock (5-13 s each on a 4K Drive source) and
# a TV hung up on an audio segment after 5.5 s. Subtitles now have their own connection and lock and answer an empty
# cue file within ~1.5 s when busy; a client whose picture has them burned in gets no SUBTITLES group at all. Audio
# is made 6 segments ahead, video 3 (three background workers), and kodi.log names the conversion path per session
# (GPU transfer or libswscale) with each slow segment's share of realtime. The output stays at most 1080p: the cost
# is decoding the 4K source, which a smaller output does not reduce.
# r14: one-file preparation reads its source from the phone's loopback (http://127.0.0.1, the setup add-on streaming
# the Drive file) instead of a downloaded copy, so a movie needs its prepared size on the phone, not twice that
# (owner, build 157). Loopback only; kodi_airplay_prepare_streams() tells the add-on this build can do it.
# r41 (ISSUE-138, Roku): kodi_airplay_serve_segmented (export 29) gives a Roku's own player (Media Assistant) a
# prepared movie remuxed (picture copied, 6-s segments, audio apart) instead of the muxed byte-range playlist; the
# start of a prepared file is read ahead into the cache (and kept there) as soon as its playlists exist; a TV's AirPlay
# that turns the prepared playlist down before any fragment gets the converted stream once.
# Usage: build-airplay.sh OUT_DIR   (REMUX_FFMPEG=DIR reuses an iOS build of build-remux-ffmpeg.sh, REMUX_LIBASS=DIR
# one of build-libass.sh ios)
set -euo pipefail
[[ "$(uname -s)" == Darwin ]] || { echo 'BLOCKED: macOS with the iPhoneOS SDK is required.' >&2; exit 2; }
OUT="$(mkdir -p "${1:?output directory}" && cd "$1" && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/kodi-airplay.XXXXXX")"
HERE="$(cd "$(dirname "$0")" && pwd)"; REMUX="$HERE/remux"
FF="${REMUX_FFMPEG:-$WORK/ffmpeg-ios}"
[[ -f "$FF/lib/libavformat.a" ]] || bash "$HERE/build-remux-ffmpeg.sh" ios "$FF"
ASS="${REMUX_LIBASS:-$WORK/libass-ios}"
[[ -f "$ASS/lib/libass.a" ]] || bash "$HERE/build-libass.sh" ios "$ASS"
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
// r34: a canceled source probe must never present a late player over a newer attempt.
static atomic_uint playGeneration;
static atomic_uint remuxTicket;
static atomic_int playbackActive;
// r37 (owner's build-200 log): an H.264 restart for a TV that took the sound only is starting; the old item's failure
// must not reach Kodi as the outcome (it closed the player and cancelled the restart half a second in).
static atomic_int compatBusy;
// r38 (owner's build-201 log): Kodi's Play on TV card watches the start by polling kodi_airplay_state(). While it does,
// a problem goes to that card (state -1) instead of Apple's "AirPlay stopped" alert, which hid what went wrong.
static _Atomic double kodiPolledAt;
// r39 (owner, build 202: "if i stop airplay it restarts the movie"): where Kodi was, so the TV starts there
// (kodi_airplay_start_at before kodi_airplay_play; taken by the next player).
static _Atomic double pendingStart;
// A generation check and its native reservation/cancel are one operation, including compat restarts.
static os_unfair_lock ownershipLock = OS_UNFAIR_LOCK_INIT;
static NSTimer *routeWatch;
static NSMutableArray<id> *playbackObservers;
static const NSInteger convertingTag = 7707;
static void keepUpdate(void);

static BOOL playbackStateFor(unsigned generation,int state,int active) {
    os_unfair_lock_lock(&ownershipLock);
    BOOL owned=generation==atomic_load(&playGeneration);
    if(owned){atomic_store(&airplayState,state);atomic_store(&playbackActive,active);}
    os_unfair_lock_unlock(&ownershipLock);
    return owned;
}

static void clearPlaybackObservers(void) {
    for(id observer in playbackObservers)[NSNotificationCenter.defaultCenter removeObserver:observer];
    [playbackObservers removeAllObjects];
}

static void showConverting(BOOL on) {
    UIView *host = airplayHolderView();
    UIView *old = [host viewWithTag:convertingTag];
    if (!on) { [old removeFromSuperview]; return; }
    if (old || !host) return;
    // r38 (owner's build-201 photo): centred, the text ran across Apple's skip-10 s buttons. A pill at the top,
    // between Apple's top-left and top-right buttons, clear of the centre and bottom controls.
    UIView *pill = [[UIView alloc] init];
    pill.tag = convertingTag;
    pill.backgroundColor = [UIColor colorWithWhite:0.17 alpha:0.92];
    pill.layer.cornerRadius = 18;
    pill.userInteractionEnabled = NO;
    pill.translatesAutoresizingMaskIntoConstraints = NO;
    UILabel *label = [[UILabel alloc] init];
    label.text = @"Converting the picture for this TV\u2026";
    label.textColor = UIColor.whiteColor;
    label.font = [UIFont preferredFontForTextStyle:UIFontTextStyleSubheadline];
    label.adjustsFontForContentSizeCategory = YES;
    label.textAlignment = NSTextAlignmentCenter;
    label.numberOfLines = 0;
    label.translatesAutoresizingMaskIntoConstraints = NO;
    [pill addSubview:label];
    [host addSubview:pill];
    UILayoutGuide *safe = host.safeAreaLayoutGuide;
    [NSLayoutConstraint activateConstraints:@[
        [label.leadingAnchor constraintEqualToAnchor:pill.leadingAnchor constant:16],
        [label.trailingAnchor constraintEqualToAnchor:pill.trailingAnchor constant:-16],
        [label.topAnchor constraintEqualToAnchor:pill.topAnchor constant:8],
        [label.bottomAnchor constraintEqualToAnchor:pill.bottomAnchor constant:-8],
        [pill.centerXAnchor constraintEqualToAnchor:safe.centerXAnchor],
        [pill.topAnchor constraintEqualToAnchor:safe.topAnchor constant:12],
        [pill.leadingAnchor constraintGreaterThanOrEqualToAnchor:safe.leadingAnchor constant:120],
        [pill.trailingAnchor constraintLessThanOrEqualToAnchor:safe.trailingAnchor constant:-120],
        [pill.heightAnchor constraintGreaterThanOrEqualToConstant:36],
    ]];
}

static NSString *sizeText(CGSize size) { return [NSString stringWithFormat:@"%.0fx%.0f", size.width, size.height]; }

static dispatch_queue_t remuxQueue(void) {
    static dispatch_queue_t queue;static dispatch_once_t once;
    dispatch_once(&once, ^{ queue=dispatch_queue_create("org.kodi.airplay.session",DISPATCH_QUEUE_SERIAL); });
    return queue;
}

static void stopRemuxFor(unsigned ticket) {
    if(!ticket)return;
    // Interrupt now, before queued cleanup. A blocked open must not hold Cancel behind itself.
    os_unfair_lock_lock(&ownershipLock);
    if(ticket==atomic_load(&remuxTicket))kr_remux_cancel(ticket);
    os_unfair_lock_unlock(&ownershipLock);
    dispatch_async(remuxQueue(), ^{ kr_remux_stop_for(ticket); });
}

static BOOL retirePlaybackFor(unsigned generation) {
    os_unfair_lock_lock(&ownershipLock);
    BOOL owned=generation==atomic_load(&playGeneration);
    unsigned ticket=owned ? atomic_load(&remuxTicket) : 0;
    if(owned){atomic_fetch_add(&playGeneration,1);atomic_store(&playbackActive,0);atomic_store(&airplayState,0);}
    os_unfair_lock_unlock(&ownershipLock);
    if(owned)stopRemuxFor(ticket);
    return owned;
}

static BOOL tvRoute(AVPlayer *player) {
    if(player.externalPlaybackActive)return YES;
    for(AVAudioSessionPortDescription *output in AVAudioSession.sharedInstance.currentRoute.outputs)
        if([output.portType isEqualToString:AVAudioSessionPortAirPlay])return YES;
    return NO;
}

@interface KodiAirPlayHolder : UIViewController <AVRoutePickerViewDelegate>
@property (nonatomic, weak) UIButton *closeButton;
@property (nonatomic) unsigned generation;
@property (nonatomic) unsigned ticket;
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
    if(self.generation!=atomic_load(&playGeneration))return;
    [airplayController.player pause];
    [self dismissViewControllerAnimated:YES completion:nil];
}
- (void)routePickerViewDidEndPresentingRoutes:(AVRoutePickerView *)view {
    if(self.generation==atomic_load(&playGeneration))kr_remux_player(self.ticket,tvRoute(airplayController.player));
}
- (void)viewDidDisappear:(BOOL)animated {
    [super viewDidDisappear:animated];
    if ((self.isBeingDismissed || self.presentingViewController == nil) && retirePlaybackFor(self.generation)) {
        [routeWatch invalidate];routeWatch=nil;
        [airplayWatch invalidate];airplayWatch=nil;
        [stallWatch invalidate]; stallWatch = nil;
        clearPlaybackObservers();
        playerNote(@"closed at %.1f s", CMTimeGetSeconds(airplayController.player.currentTime));
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
    if (NSProcessInfo.processInfo.systemUptime - atomic_load(&kodiPolledAt) < 2.0) {
        // r38: Kodi is watching: its card says what happened (and closes this player); no second alert here.
        playerNote(@"problem left to Kodi's card");
        playbackStateFor(atomic_load(&playGeneration), -1, 0);
        return;
    }
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
static void watchPlayback(AVPlayer *player,AVPlayerItem *item,unsigned generation) {
    clearPlaybackObservers();
    if(!playbackObservers)playbackObservers=[NSMutableArray array];
    __weak AVPlayer *weakPlayer=player;
    id ended=[[NSNotificationCenter defaultCenter] addObserverForName:AVPlayerItemDidPlayToEndTimeNotification
        object:item queue:NSOperationQueue.mainQueue usingBlock:^(NSNotification *note) {
        AVPlayer *current=weakPlayer;
        if(!current || current.currentItem!=note.object)return;
        if(playbackStateFor(generation,0,0))playerNote(@"finished");
    }];
    [playbackObservers addObject:ended];
    id failed=[[NSNotificationCenter defaultCenter] addObserverForName:AVPlayerItemFailedToPlayToEndTimeNotification
        object:item queue:NSOperationQueue.mainQueue usingBlock:^(NSNotification *note) {
        AVPlayer *current=weakPlayer;
        if(!current || current.currentItem!=note.object)return;
        if(atomic_load(&compatBusy))return;   // r37: the H.264 restart replaces this item
        BOOL wasReady=atomic_load(&airplayState)==1;
        if(!playbackStateFor(generation,-1,0))return;
        const char *m = kr_remux_message();
        NSError *e = note.userInfo[AVPlayerItemFailedToPlayToEndTimeErrorKey];
        if(wasReady)showProblem(m && *m ? @(m) : (e.localizedDescription ?: @"The stream stopped."));
    }];
    [playbackObservers addObject:failed];
}

static void presentPlayer(NSString *link, NSString *name, BOOL converted, unsigned generation, unsigned ticket) {
    dispatch_async(dispatch_get_main_queue(), ^{
        if (generation != atomic_load(&playGeneration)) return;
        NSURL *address = link ? [NSURL URLWithString:link] : nil;
        if (!address) playbackStateFor(generation,-1,0);
        UIViewController *root = kodiWindow().rootViewController;
        if (!address || !root) return;
        [[AVAudioSession sharedInstance] setCategory:AVAudioSessionCategoryPlayback mode:AVAudioSessionModeMoviePlayback options:0 error:nil];
        [[AVAudioSession sharedInstance] setActive:YES error:nil];
        AVPlayer *player = [AVPlayer playerWithURL:address];
        if (@available(iOS 15.0, *)) player.audiovisualBackgroundPlaybackPolicy=AVPlayerAudiovisualBackgroundPlaybackPolicyContinuesIfPossible;
        const double startAt = atomic_exchange(&pendingStart, 0.0);
        __block BOOL initialSeekAllowed = YES;
        if(!playbackStateFor(generation,0,1))return;
        keepUpdate();
        [routeWatch invalidate];
        routeWatch=nil;
        watchPlayback(player,player.currentItem,generation);
        [airplayWatch invalidate];
        // r3: Apple's player opens MP4/MOV/HLS only (no MKV) and needs the link to answer on the Wi-Fi address.
        __block int openFailedSeen=0;
        airplayWatch = [NSTimer scheduledTimerWithTimeInterval:0.5 repeats:YES block:^(NSTimer *timer) {
            if(generation!=atomic_load(&playGeneration)){[timer invalidate];return;}
            AVPlayerItem *item = player.currentItem;
            // r37 (owner's build-200 log): "could not open the stream" set -1 in the same second the H.264 restart began,
            // so Kodi closed the player and cancelled it. A failure counts after 1.5 s and never while a restart runs.
            BOOL openFailed = item.status == AVPlayerItemStatusFailed || player.status == AVPlayerStatusFailed;
            openFailedSeen = openFailed && !atomic_load(&compatBusy) ? openFailedSeen + 1 : 0;
            if (item.status == AVPlayerItemStatusReadyToPlay) {
                playerNote(@"ready, presentation %@, %lu tracks, external %d", sizeText(item.presentationSize),
                           (unsigned long)item.tracks.count, player.externalPlaybackActive);
                // r39: start where Kodi was, and show the subtitle the stream marks DEFAULT (the one Kodi showed).
                if (initialSeekAllowed && startAt > 1 && isfinite(startAt)) {
                    initialSeekAllowed = NO;
                    playerNote(@"starting at %.1f s (where Kodi was)", startAt);
                    [player seekToTime:CMTimeMakeWithSeconds(startAt, 600) toleranceBefore:kCMTimeZero toleranceAfter:kCMTimeZero];
                }
                void (^pick)(AVMediaSelectionGroup *) = ^(AVMediaSelectionGroup *legible) {
                    if (!legible.defaultOption) return;
                    [item selectMediaOption:legible.defaultOption inMediaSelectionGroup:legible];
                    playerNote(@"subtitles on: %@", legible.defaultOption.displayName ?: @"");
                };
                if (@available(iOS 15.0, *)) {
                    [item.asset loadMediaSelectionGroupForMediaCharacteristic:AVMediaCharacteristicLegible completionHandler:^(AVMediaSelectionGroup *legible, NSError *error) {
                        dispatch_async(dispatch_get_main_queue(), ^{ if (generation == atomic_load(&playGeneration)) pick(legible); });
                    }];
                } else {
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
                    pick([item.asset mediaSelectionGroupForMediaCharacteristic:AVMediaCharacteristicLegible]);
#pragma clang diagnostic pop
                }
                playbackStateFor(generation,1,1);
                [timer invalidate];
            } else if (openFailedSeen >= 3) {
                playerNote(@"could not open the stream: %@", item.error ?: player.error);
                playbackStateFor(generation,-1,0);
                [timer invalidate];
            }
        }];
        [stallWatch invalidate]; stallWatch = nil;
        if (converted) {
            __block int waiting = 0, ticks = 0, externalTicks = 0, video0 = 0, audio0 = 0, external = 0, soundOnlyTicks = 0;
            __block NSUInteger errorsSeen = 0;
            // r36: a prepared movie may restart once in compat mode too, but only when the TV takes the sound only (below);
            // the older segment-based triggers stay off for it (it has no segments).
            const BOOL preparedLink = [link hasSuffix:@"/prepared.mp4"] || [link hasSuffix:@"/prepared.m3u8"];   // r38: HLS over the prepared file
            __block BOOL warned = NO, compatTried = kr_remux_compat() != 0, restarting = NO, everExternal = NO;
            __block double resumeAt = -1;
            // r7: once per stream: restart with the picture converted to H.264 at the same position. NO when it cannot
            // (already tried, or no source to restart).
            BOOL (^restartCompat)(BOOL) = ^BOOL(BOOL hevc) {
                char *source = NULL;
                unsigned restartTicket=0;
                os_unfair_lock_lock(&ownershipLock);
                os_unfair_lock_lock(&noteLock);
                if(generation==atomic_load(&playGeneration) && !compatTried && remuxSource)source=strdup(remuxSource);
                os_unfair_lock_unlock(&noteLock);
                if(source){restartTicket=kr_remux_begin(1);atomic_store(&remuxTicket,restartTicket);}
                os_unfair_lock_unlock(&ownershipLock);
                if (!source) return NO;
                compatTried = YES; restarting = YES; atomic_store(&compatBusy,1);
                double at = CMTimeGetSeconds(player.currentTime);
                if (!isfinite(at) || at < 0) at = 0;
                // ReadyToPlay may have fired before the initial seek completed. Preserve Kodi's requested
                // position, and give the replacement timer sole ownership of the seek on the new item.
                if (at < 1 && isfinite(startAt) && startAt > 1) at = startAt;
                initialSeekAllowed = NO;
                playerNote(@"restarting in compat mode (picture converted to H.264) at %.1f s", at);
                setNote(@"Converting the picture for this TV\u2026");
                showConverting(YES);
                dispatch_async(remuxQueue(), ^{
                    if(generation!=atomic_load(&playGeneration) || restartTicket!=atomic_load(&remuxTicket)){free(source);return;}
                    char playlist[512] = "";
                    int r = kr_remux_start_for(restartTicket,source, 1, 1, playlist, sizeof playlist);
                    if(r==KR_READY)r=kr_remux_prime_for(restartTicket,at);
                    free(source);
                    NSString *link = r == KR_READY ? @(playlist) : nil;
                    dispatch_async(dispatch_get_main_queue(), ^{
                        if(generation!=atomic_load(&playGeneration))return;
                        restarting = NO; atomic_store(&compatBusy,0);
                        NSURL *address = link ? [NSURL URLWithString:link] : nil;
                        if (!address) {
                            const char *m = kr_remux_message();
                            playerNote(@"compat restart failed: %s", m ? m : "");
                            showConverting(NO);
                            showNoPicture(hevc);
                            return;
                        }
                        AVPlayerItem *next = [AVPlayerItem playerItemWithURL:address];
                        watchPlayback(player,next,generation);
                        [player replaceCurrentItemWithPlayerItem:next];
                        airplayHolder.ticket=restartTicket;
                        kr_remux_player(restartTicket,tvRoute(player));
                        [player play];
                        resumeAt = at; errorsSeen = 0; waiting = 0; warned = NO;
                        externalTicks = 0; video0 = kr_remux_served(1); audio0 = kr_remux_served(0);
                        setNote(nil);
                    });
                });
                return YES;
            };
            stallWatch = [NSTimer scheduledTimerWithTimeInterval:1.0 repeats:YES block:^(NSTimer *timer) {
                if(generation!=atomic_load(&playGeneration)){[timer invalidate];return;}
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
                    if (external) everExternal = YES;   // r41: the TV had the route, even if it is off again by the failure
                    playerNote(@"external playback %@", external ? @"on (the TV fetches the stream)" : @"off");
                    externalTicks = 0; video0 = kr_remux_served(1); audio0 = kr_remux_served(0);
                    // r8: the TV gave up within seconds without one video segment (owner build-136: a TCL Roku TV read
                    // the HEVC master and init, hung up on the segments, AirPlay off ~10 s later): restart once with
                    // the picture converted instead of waiting for r7's 30 s of sound only. Only when the TV never had
                    // the converted picture (a receiver the remuxer did not recognise) and the video is not H.264.
                    if (!preparedLink && wasOn && !external && lasted <= 20 && !compatTried && kr_remux_served_external(1) == 0) {
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
                // r36 (owner's build-198 log and photo: a TCL Roku TV showed a music note; the player reported external 0
                // and every request came from the phone itself): a TV that cannot take this picture (third-party AirPlay,
                // HEVC) gets the AirPlay route as sound only and never fetches the video. Restart once with the H.264
                // picture; a TV that takes the video turns external playback on within a second or two.
                soundOnlyTicks = (!external && tvRoute(player)) ? soundOnlyTicks + 1 : 0;
                if (!compatTried && soundOnlyTicks >= 4) {
                    const char *codec = kr_remux_video_codec();
                    BOOL hevc = codec && (!strncmp(codec, "hvc1", 4) || !strncmp(codec, "hev1", 4));
                    if (!(codec && !strncmp(codec, "avc1", 4))) {
                        playerNote(@"the TV took the sound only (%s, no external playback): converting the picture", codec ? codec : "");
                        if (restartCompat(hevc)) return;
                    }
                }
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
                    // r36: Apple's player gave up ("Cannot Complete Action") while the TV only had the sound: convert the
                    // picture once before reporting a problem.
                    if (!compatTried && !external && tvRoute(player)) {
                        const char *codec = kr_remux_video_codec();
                        if (!(codec && !strncmp(codec, "avc1", 4))) {
                            playerNote(@"the player failed while the TV had the sound only (%s): converting the picture", codec ? codec : "");
                            if (restartCompat(codec && (!strncmp(codec, "hvc1", 4) || !strncmp(codec, "hev1", 4)))) return;
                        }
                    }
                    // r41 (ISSUE-138, owner's build-211 log: a Roku TV's AirPlay read prepared.m3u8 and nothing else; the
                    // player stopped 0.5 s later, "The operation could not be completed"): a third-party receiver that
                    // turns down the prepared playlist (fragments with audio and video together, up to 70 s, HEVC) gets
                    // the converted stream once: demuxed 6-s segments, H.264, the one this TV took in builds 138 and 201.
                    if (!compatTried && preparedLink && everExternal && kr_remux_served_external(1) == 0) {
                        const char *codec = kr_remux_video_codec();
                        playerNote(@"the TV turned down the prepared playlist (%s) before any fragment: converting the picture", codec ? codec : "");
                        if (restartCompat(codec && (!strncmp(codec, "hvc1", 4) || !strncmp(codec, "hev1", 4)))) return;
                    }
                    const char *m = kr_remux_message();
                    showProblem(m && *m ? @(m) : (player.currentItem.error.localizedDescription ?: @"The TV could not play the converted stream."));
                    [timer invalidate]; return;
                }
                waiting = player.timeControlStatus == AVPlayerTimeControlStatusWaitingToPlayAtSpecifiedRate ? waiting + 1 : 0;
                const char *m = kr_remux_message();
                if (waiting >= 20 && m && *m) { showProblem(@(m)); [timer invalidate]; }
            }];
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
        holder.generation=generation;holder.ticket=ticket;
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
            if(generation!=atomic_load(&playGeneration))return;
            __block int failedSeen=0;
            routeWatch=[NSTimer scheduledTimerWithTimeInterval:0.5 repeats:YES block:^(NSTimer *timer) {
                if(generation!=atomic_load(&playGeneration)){[timer invalidate];return;}
                AVPlayerItem *item=player.currentItem;
                BOOL failed=item.status==AVPlayerItemStatusFailed || player.status==AVPlayerStatusFailed;
                failedSeen=failed && !atomic_load(&compatBusy) ? failedSeen+1 : 0;
                // r37: a failure is final after 1.5 s, so the player's 1 s timer can first restart with the H.264 picture.
                if(failedSeen>=3)playbackStateFor(generation,-1,0);
                else if(atomic_load(&airplayState)>=0 && player.timeControlStatus==AVPlayerTimeControlStatusPlaying && player.rate>0) {
                    BOOL resuming=!atomic_load(&playbackActive);
                    if(playbackStateFor(generation,1,1) && resuming) {
                        [AVAudioSession.sharedInstance setCategory:AVAudioSessionCategoryPlayback mode:AVAudioSessionModeMoviePlayback options:0 error:nil];
                        [AVAudioSession.sharedInstance setActive:YES error:nil];
                        keepUpdate();
                    }
                }
                kr_remux_player(holder.ticket,tvRoute(player));
            }];
            kr_remux_player(ticket,tvRoute(player));
            [player play];
            AVRoutePickerView *sheet = [[AVRoutePickerView alloc] initWithFrame:CGRectMake(0, 0, 1, 1)];
            sheet.prioritizesVideoDevices = YES;
            sheet.delegate=holder;
            [holder.view addSubview:sheet];
            openSheet(sheet);
        }];
    });
}

// Real AirPlay video: Apple's player with external playback, then the device sheet. The TV keeps playing while
// Kodi is in the background (playback audio session). Apple's player handles MP4/MOV/HLS; r5 converts MKV, AVI,
// WebM and MPEG-TS on the phone first (and links whose bytes turn out not to be MP4).
__attribute__((visibility("default"))) int kodi_airplay_startup_budget(void) { return KR_STARTUP_SECONDS; }
__attribute__((visibility("default"))) void kodi_airplay_play(const char *url, const char *title) {
    os_unfair_lock_lock(&ownershipLock);
    unsigned generation=atomic_fetch_add(&playGeneration,1)+1;
    atomic_store(&playbackActive,0);atomic_store(&compatBusy,0);
    NSString *link = url ? [NSString stringWithUTF8String:url] : nil;
    NSString *name = title ? [NSString stringWithUTF8String:title] : @"";
    atomic_store(&airplayState, 0); // before returning, so a caller polling kodi_airplay_state() never sees the last result
    setNote(nil);
    BOOL direct = !link || kr_remux_kind(url) == KR_DIRECT;
    unsigned previous=atomic_load(&remuxTicket);
    unsigned ticket=kr_remux_begin(direct ? 0 : 1);atomic_store(&remuxTicket,ticket);
    os_unfair_lock_lock(&noteLock);  // Python calls from its own thread; the player's timer reads it on the main thread
    free(remuxSource); remuxSource = direct ? NULL : strdup(url);
    os_unfair_lock_unlock(&noteLock);
    os_unfair_lock_unlock(&ownershipLock);
    if (direct) { stopRemuxFor(previous); presentPlayer(link, name, NO, generation,ticket); return; }
    char *copy = strdup(url);
    dispatch_async(remuxQueue(), ^{
        if(generation!=atomic_load(&playGeneration)){free(copy);return;}
        char playlist[512] = "";
        int r = kr_remux_start_for(ticket,copy, 1, 0, playlist, sizeof playlist);
        if(r==KR_READY)r=kr_remux_prime_for(ticket,atomic_load(&pendingStart));
        free(copy);
        if (generation != atomic_load(&playGeneration)) return;
        if (r == KR_READY) { playerNote(@"stream ready (see server endpoint)"); presentPlayer(@(playlist), name, YES, generation,ticket); }
        else if (r == KR_NOT_NEEDED) presentPlayer(link, name, NO, generation,ticket);
        else {
            const char *m = kr_remux_message();
            NSString *why = m && *m ? @(m) : @"AirPlay could not convert this video.";
            setNote(why);
            NSLog(@"KodiAirPlay: %@", why);
            playbackStateFor(generation,-1,0);
        }
    });
}

// r10: the subtitles the next kodi_airplay_play burns into the picture a TV gets converted: Kodi's subtitle stream
// number (ordinal >= 0; past the file's own subtitles it is Kodi's external one, `file`), -1 none, -2 automatic (the
// file's forced / default text subtitle, else language `lang`, ISO 639-2). Changing them means playing again.
__attribute__((visibility("default"))) void kodi_airplay_subtitles(int ordinal, const char *file, const char *lang) {
    kr_remux_set_subtitles(ordinal, file, lang);
}

// r40 (owner, build 203: "work on any tv thats connected to the same wifi"): the phone's server for a TV that plays
// links itself (Roku with Media Assistant, Chromecast / Google TV, DLNA): the same playlist the Apple TV gets
// (prepared movies as byte ranges, other files remuxed), on the Wi-Fi address, without Apple's player. Drive's and
// Elementum's own helpers answer on 127.0.0.1 only, so a TV could never open Kodi's link. Blocks while the source
// opens (a few seconds); returns KR_READY with the link in out, KR_NOT_NEEDED (an HLS source: use it as it is) or
// KR_FAILED (kodi_airplay_message says why). compat 1: the picture as H.264 (for a TV without HEVC). The server
// runs until kodi_airplay_close or the next play/serve.
__attribute__((visibility("default"))) int kodi_airplay_serve(const char *url, int compat, char *out, int outlen) {
    if (out && outlen > 0) *out = 0;
    if (!url || !*url) return KR_FAILED;
    os_unfair_lock_lock(&ownershipLock);
    atomic_fetch_add(&playGeneration,1);   // an open Apple player from an earlier AirPlay stops counting
    atomic_store(&playbackActive,0);atomic_store(&compatBusy,0);atomic_store(&airplayState,0);
    unsigned ticket=kr_remux_begin(1);atomic_store(&remuxTicket,ticket);
    os_unfair_lock_lock(&noteLock);free(remuxSource);remuxSource=NULL;os_unfair_lock_unlock(&noteLock);
    os_unfair_lock_unlock(&ownershipLock);
    setNote(nil);
    int r = kr_remux_start_for(ticket, url, 1, compat == KR_COMPAT_ROKU_SAFE ? KR_COMPAT_ROKU_SAFE : compat ? 1 : 0, out, outlen);
    if(r==KR_READY && compat==KR_COMPAT_ROKU_SAFE)r=kr_remux_prime_for(ticket,0);
    if(r!=KR_READY && out && outlen>0)*out=0;
    playerNote(@"served for a TV's own player: result %d", r);
    return r;
}

// r41 (ISSUE-138, owner's build-209 log: a Roku with Media Assistant read the prepared playlists and the init, then
// nothing): the same server for a Roku's own player, but a prepared movie is remuxed instead of served as-is: the
// picture copied (no conversion), 6-s segments, the audio as its own rendition. Roku's streaming specifications do
// not support CMAF HLS with audio and video muxed together and recommend 4-6 s chunks; the prepared fragments carry
// both and run up to 70 s. Same results as kodi_airplay_serve.
__attribute__((visibility("default"))) int kodi_airplay_serve_segmented(const char *url, char *out, int outlen) {
    if (out && outlen > 0) *out = 0;
    if (!url || !*url) return KR_FAILED;
    os_unfair_lock_lock(&ownershipLock);
    atomic_fetch_add(&playGeneration,1);
    atomic_store(&playbackActive,0);atomic_store(&compatBusy,0);atomic_store(&airplayState,0);
    unsigned ticket=kr_remux_begin(1);atomic_store(&remuxTicket,ticket);
    os_unfair_lock_lock(&noteLock);free(remuxSource);remuxSource=NULL;os_unfair_lock_unlock(&noteLock);
    os_unfair_lock_unlock(&ownershipLock);
    setNote(nil);
    int r = kr_remux_start_for(ticket, url, 1, KR_COMPAT_SEGMENTED, out, outlen);
    if(r==KR_READY)r=kr_remux_prime_for(ticket,0);
    if(r!=KR_READY && out && outlen>0)*out=0;
    playerNote(@"served in segments for a TV's own player: result %d", r);
    return r;
}

// r39: Kodi's position in seconds; the next kodi_airplay_play starts the TV there (0: from the start).
__attribute__((visibility("default"))) void kodi_airplay_start_at(double seconds) {
    atomic_store(&pendingStart, isfinite(seconds) && seconds > 0 ? seconds : 0.0);
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
    atomic_store(&kodiPolledAt, NSProcessInfo.processInfo.systemUptime);
    return atomic_load(&airplayState);
}

__attribute__((visibility("default"))) int kodi_airplay_active(void) { return atomic_load(&playbackActive); }

__attribute__((visibility("default"))) int kodi_airplay_network(char *buf, int len) {
    return kr_remux_network(buf,len);
}

__attribute__((visibility("default"))) void kodi_airplay_settings(void) {
    dispatch_async(dispatch_get_main_queue(), ^{
        NSURL *url=[NSURL URLWithString:UIApplicationOpenSettingsURLString];
        [UIApplication.sharedApplication openURL:url options:@{} completionHandler:^(BOOL opened) {
            NSLog(@"KodiAirPlay: app Settings %@",opened ? @"opened" : @"could not open");
        }];
    });
}

// r3: closes Apple's player (after it failed, so Kodi can carry on).
__attribute__((visibility("default"))) void kodi_airplay_close(void) {
    os_unfair_lock_lock(&ownershipLock);
    unsigned generation=atomic_fetch_add(&playGeneration,1)+1;
    unsigned ticket=atomic_load(&remuxTicket);
    atomic_store(&playbackActive,0);
    atomic_store(&airplayState,0);
    os_unfair_lock_unlock(&ownershipLock);
    stopRemuxFor(ticket);
    dispatch_async(dispatch_get_main_queue(), ^{
        if (generation != atomic_load(&playGeneration)) return;
        [airplayWatch invalidate];
        airplayWatch = nil;
        [stallWatch invalidate]; stallWatch = nil;
        [routeWatch invalidate];routeWatch=nil;
        clearPlaybackObservers();
        [airplayController.player pause];
        [airplayHolder dismissViewControllerAnimated:YES completion:nil];
        airplayHolder = nil;
        airplayController = nil;
    });
}

// r3: background downloads. iOS suspends an app a few seconds after it leaves the screen unless it plays sound
// (Kodi's Info.plist has the audio background mode). While Python says a download or upload has work and the app is
// in the background, play one second of silence on a loop, mixed with other apps so their sound carries on.
static AVAudioPlayer *keepPlayer;
static BOOL keepWanted, keepInBackground, keepSaved;
static BOOL keepInterrupted=NO;
static atomic_int keepState=0;
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
    if(atomic_load(&playbackActive)) {
        // AVPlayer's playback/movie session owns AirPlay through lock/background. A download's silent-audio
        // helper must never replace it with a mixable/default session or restore a previous category over it.
        [keepPlayer stop];keepSaved=NO;atomic_store(&keepState,3);return;
    }
    if(keepInterrupted){atomic_store(&keepState,-2);return;}
    const BOOL run = keepWanted && keepInBackground;
    if(!keepInBackground)atomic_store(&keepState,keepWanted?1:0);
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
        atomic_store(&keepState,playing?2:-1);
        NSLog(@"KodiAirPlay: staying awake in the background for a download or upload: %@", playing ? @"yes" : error);
    } else if (!run && (keepPlayer.playing || keepSaved)) {
        atomic_store(&keepState,keepWanted?1:0);
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
            // r28 (build-181 log: "audio interrupted by iOS" at 17:45 and the silence never came back): iOS often sends
            // no "interruption ended", so leaving or reopening Kodi tries the silence again instead of waiting for it.
            [center addObserverForName:UIApplicationDidEnterBackgroundNotification object:nil queue:NSOperationQueue.mainQueue
                            usingBlock:^(NSNotification *note) { keepInBackground = YES; keepInterrupted = NO; keepUpdate(); }];
            [center addObserverForName:UIApplicationWillEnterForegroundNotification object:nil queue:NSOperationQueue.mainQueue
                            usingBlock:^(NSNotification *note) { keepInBackground = NO; keepInterrupted = NO; keepUpdate(); }];
            // A phone call or another app's sound stops the silence; start it again when that ends.
            [center addObserverForName:AVAudioSessionInterruptionNotification object:nil queue:NSOperationQueue.mainQueue
                            usingBlock:^(NSNotification *note) {
                if ([note.userInfo[AVAudioSessionInterruptionTypeKey] unsignedIntegerValue] == AVAudioSessionInterruptionTypeBegan) {
                    keepInterrupted=YES;[keepPlayer stop];atomic_store(&keepState,-2);
                } else if ([note.userInfo[AVAudioSessionInterruptionTypeKey] unsignedIntegerValue] == AVAudioSessionInterruptionTypeEnded) {
                    keepInterrupted=NO;
                    [keepPlayer stop];
                    if(atomic_load(&playbackActive) && ([note.userInfo[AVAudioSessionInterruptionOptionKey] unsignedIntegerValue]&AVAudioSessionInterruptionOptionShouldResume)) {
                        [AVAudioSession.sharedInstance setActive:YES error:nil];
                        [airplayController.player play];
                    }
                    keepUpdate();
                }
            }];
        });
        keepWanted = on != 0;
        keepUpdate();
    });
}

__attribute__((visibility("default"))) int kodi_background_state(void) { return atomic_load(&keepState); }

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
CC_IOS=(xcrun --sdk iphoneos clang -arch arm64 -isysroot "$SDK" -miphoneos-version-min=$MIN_IOS -O2 -std=gnu11 -I"$FF/include" -I"$ASS/include")
OBJS=()
for c in "$REMUX"/src/*.c "$REMUX"/gmplayer/*.c; do
  o="$WORK/$(basename "${c%.c}").o"; "${CC_IOS[@]}" -c "$c" -o "$o"; OBJS+=("$o")
done
# Only Kodi's entry points are exported: Kodi has its own FFmpeg, these copies stay private to the framework.
printf '_kodi_airplay_show\n_kodi_airplay_open\n_kodi_airplay_play\n_kodi_airplay_state\n_kodi_airplay_close\n_kodi_airplay_message\n_kodi_airplay_log\n_kodi_airplay_subtitles\n_kodi_background_keep\n_kodi_background_state\n_kodi_airplay_prepare\n_kodi_airplay_probe\n_kodi_airplay_prepare_streams\n_kodi_airplay_prepare_keep_image_subs\n_kodi_airplay_prepare_to\n_kodi_airplay_verify\n_kodi_airplay_prepare_hdr\n_kodi_airplay_probe_ex\n_kodi_airplay_prepare_audio_languages\n_kodi_airplay_prepare_background\n_kodi_airplay_prepare_subtitle_languages\n_kodi_airplay_prepare_marks\n_kodi_airplay_prepare_resume\n_kodi_airplay_start_at\n_kodi_airplay_serve\n_kodi_airplay_serve_segmented\n' > "$WORK/exports"
printf '_kodi_airplay_network\n_kodi_airplay_settings\n_kodi_airplay_active\n' >> "$WORK/exports"
xcrun --sdk iphoneos clang -arch arm64 -isysroot "$SDK" -miphoneos-version-min=$MIN_IOS -fobjc-arc -O2 -dynamiclib \
  -install_name @rpath/KodiAirPlay.framework/KodiAirPlay -framework UIKit -framework AVKit -framework AVFoundation -framework CoreGraphics -framework CoreMedia \
  -framework VideoToolbox -framework CoreVideo -framework CoreText \
  -I"$REMUX/src" -Wl,-exported_symbols_list,"$WORK/exports" \
  -o "$FW/KodiAirPlay" "$WORK/KodiAirPlay.m" "${OBJS[@]}" \
  "$ASS/lib/libass.a" "$ASS/lib/libharfbuzz.a" "$ASS/lib/libfribidi.a" "$ASS/lib/libfreetype.a" -lc++ \
  "$FF/lib/libavformat.a" "$FF/lib/libavcodec.a" "$FF/lib/libdav1d.a" "$FF/lib/libswscale.a" "$FF/lib/libswresample.a" "$FF/lib/libavutil.a" \
  -framework Security -framework CoreFoundation -lz -liconv
cp "$REMUX/THIRD-PARTY-NOTICES" "$FW/THIRD-PARTY-NOTICES"; cp "$FF/FFMPEG-CONFIG.txt" "$FW/FFMPEG-CONFIG.txt"
cp "$REMUX/LICENSE-LGPL-2.1" "$FW/LICENSE-LGPL-2.1"
cp "$ASS/LIBASS-CONFIG.txt" "$FW/LIBASS-CONFIG.txt"
cp "$FF/DAV1D-CONFIG.txt" "$FF/DAV1D-LICENSE.txt" "$FF/ffmpeg-mov-pts.patch" "$FW/"
cp "$FF/ffmpeg-dovi-padding.patch" "$FF/ffmpeg-mov-trun-cts.patch" "$FW/"
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
nm -gU "$FW/KodiAirPlay" | grep -E ' _kodi_(airplay_(show|open|play|state|close|message|log|network|settings|active|subtitles|prepare|probe|prepare_streams|prepare_keep_image_subs|prepare_to|verify|prepare_hdr|probe_ex|prepare_audio_languages|prepare_background|prepare_subtitle_languages|prepare_marks|prepare_resume)|background_(keep|state))$'
# r14: prepare_streams is what tells the setup add-on it may stream from Drive instead of downloading first.
# r15: prepare_keep_image_subs keeps Blu-ray picture subtitles in .sup files beside the MP4 (Interstellar, build 160).
[[ "$(nm -gU "$FW/KodiAirPlay" | grep -cE ' _kodi_(airplay_(show|open|play|state|close|message|log|network|settings|active|subtitles|prepare|probe|prepare_streams|prepare_keep_image_subs|prepare_to|verify|prepare_hdr|probe_ex|prepare_audio_languages|prepare_background|prepare_subtitle_languages|prepare_marks|prepare_resume|start_at|serve|serve_segmented)|background_(keep|state))$')" == 29 ]] || { echo 'missing exports' >&2; exit 1; }
! nm -gU "$FW/KodiAirPlay" | grep -E ' _(av|avformat|avcodec|swr|sws|kr|gm|ass|FT|hb|fribidi)_' || { echo 'FFmpeg symbols exported: they would clash with Kodi (libass too)' >&2; exit 1; }
# r10: libass and the burn-in path are linked in (private).
[[ "$(nm "$FW/KodiAirPlay" | grep -cE ' [tT] _(ass_render_frame|kr_subs_blend|kr_video_burn|kr_remux_set_subtitles|hb_shape|FT_Init_FreeType|fribidi_get_par_embedding_levels_ex)$')" == 7 ]] || { echo 'r10 libass burn-in missing' >&2; exit 1; }
# r8: the per-receiver picture and the TV's segment count are linked in (private to the framework, not exported).
[[ "$(nm "$FW/KodiAirPlay" | grep -cE ' [tT] _kr_remux_(third_party_receiver|served_external|compat_clients)$')" == 3 ]] || { echo 'r8 remuxer missing' >&2; exit 1; }
[[ "$(nm "$FW/KodiAirPlay" | grep -cE ' [tT] _(kr_dovi_convert|kr_source_set_interrupt|kr_video_subtitle_scan_end)$')" == 3 ]] || { echo 'AirPlay RPU/seek source fixes missing' >&2; exit 1; }
# r7: the picture bridge needs Apple's hardware H.264 encoder in this FFmpeg.
grep -q -- '--enable-encoder=h264_videotoolbox' "$FF/FFMPEG-CONFIG.txt" || { echo 'FFmpeg built without h264_videotoolbox' >&2; exit 1; }
lipo -info "$FW/KodiAirPlay"
(cd "$OUT" && zip -qry KodiAirPlay.framework.zip KodiAirPlay.framework && shasum -a 256 KodiAirPlay.framework.zip | tee KodiAirPlay.framework.zip.sha256)
