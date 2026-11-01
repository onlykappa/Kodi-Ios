#!/usr/bin/env bash
# Builds KodiGlassBar.framework: the portrait tab bar (Home, Movies, TV, Library, Search) as a native iOS view.
# Kodi draws its skin with OpenGL and cannot blur or refract what is behind a control; this bar uses Apple's own
# Liquid Glass (UIGlassEffect, iOS 26), with a glass lens that slides to the chosen tab, and the system frosted
# material on older iOS. The setup add-on loads it with ctypes (resources/lib/glassbar.py): kodi_glassbar_show,
# kodi_glassbar_select and kodi_glassbar_take_tap. UIGlassEffect is looked up at run time, so any Xcode builds it.
# Usage: build-glassbar.sh OUT_DIR
set -euo pipefail
[[ "$(uname -s)" == Darwin ]] || { echo 'BLOCKED: macOS with the iPhoneOS SDK is required.' >&2; exit 2; }
OUT="$(mkdir -p "${1:?output directory}" && cd "$1" && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/kodi-glassbar.XXXXXX")"
MIN_IOS=14.0
SDK="$(xcrun --sdk iphoneos --show-sdk-path)"
cat > "$WORK/KodiGlassBar.m" <<'OBJC'
#import <UIKit/UIKit.h>
#import <objc/message.h>
#import <stdatomic.h>

static NSString *const kTitles[] = {@"Home", @"Movies", @"TV", @"Library", @"Search"};
static NSString *const kSymbols[] = {@"house.fill", @"film.fill", @"tv.fill", @"square.stack.fill", @"magnifyingglass"};
static const NSInteger kCount = 5;
static atomic_int pendingTap = -1;

// Apple's Liquid Glass when the system has it (iOS 26), otherwise the frosted chrome material.
static UIVisualEffect *glassEffect(BOOL interactive) {
    Class glass = NSClassFromString(@"UIGlassEffect");
    if (glass && [glass respondsToSelector:@selector(effectWithStyle:)]) {
        UIVisualEffect *effect = ((id (*)(id, SEL, NSInteger))objc_msgSend)(glass, @selector(effectWithStyle:), 0);
        if (interactive && [effect respondsToSelector:@selector(setInteractive:)])
            ((void (*)(id, SEL, BOOL))objc_msgSend)(effect, @selector(setInteractive:), YES);
        return effect;
    }
    return [UIBlurEffect effectWithStyle:UIBlurEffectStyleSystemChromeMaterialDark];
}

static BOOL hasGlass(void) { return NSClassFromString(@"UIGlassEffect") != nil; }

static void makeCapsule(UIVisualEffectView *view, CGFloat height) {
    Class corners = NSClassFromString(@"UICornerConfiguration");
    if (corners && [corners respondsToSelector:@selector(capsuleConfiguration)] &&
        [view respondsToSelector:@selector(setCornerConfiguration:)]) {
        id capsule = ((id (*)(id, SEL))objc_msgSend)(corners, @selector(capsuleConfiguration));
        ((void (*)(id, SEL, id))objc_msgSend)(view, @selector(setCornerConfiguration:), capsule);
    } else {
        view.layer.cornerRadius = height / 2;
        view.layer.cornerCurve = kCACornerCurveContinuous;
        view.clipsToBounds = YES;
    }
}

@interface KodiGlassBar : UIView
@property (nonatomic) NSInteger selected;
@end

@implementation KodiGlassBar {
    UIVisualEffectView *_background;
    UIVisualEffectView *_lens;
    UIView *_lensTint;
    NSMutableArray<UIImageView *> *_icons;
    NSMutableArray<UILabel *> *_labels;
    BOOL _dragging;
}

- (instancetype)initWithFrame:(CGRect)frame {
    if (!(self = [super initWithFrame:frame])) return nil;
    _selected = 0;
    _background = [[UIVisualEffectView alloc] initWithEffect:glassEffect(NO)];
    [self addSubview:_background];
    if (!hasGlass()) {
        _background.layer.borderWidth = 0.5;
        _background.layer.borderColor = [UIColor colorWithWhite:1 alpha:0.18].CGColor;
    }
    _lens = [[UIVisualEffectView alloc] initWithEffect:glassEffect(YES)];
    _lens.userInteractionEnabled = NO;
    _lensTint = [[UIView alloc] init];
    _lensTint.backgroundColor = [UIColor colorWithWhite:hasGlass() ? 0.0 : 1.0 alpha:hasGlass() ? 0.28 : 0.12];
    _lensTint.userInteractionEnabled = NO;
    [_background.contentView addSubview:_lensTint];
    [_background.contentView addSubview:_lens];
    _icons = [NSMutableArray array];
    _labels = [NSMutableArray array];
    UIImageSymbolConfiguration *config = [UIImageSymbolConfiguration configurationWithPointSize:21 weight:UIImageSymbolWeightSemibold];
    for (NSInteger i = 0; i < kCount; i++) {
        UIImageView *icon = [[UIImageView alloc] initWithImage:[UIImage systemImageNamed:kSymbols[i] withConfiguration:config]];
        icon.contentMode = UIViewContentModeScaleAspectFit;
        UILabel *label = [[UILabel alloc] init];
        label.text = kTitles[i];
        label.font = [UIFont systemFontOfSize:10.5 weight:UIFontWeightSemibold];
        label.textAlignment = NSTextAlignmentCenter;
        [_background.contentView addSubview:icon];
        [_background.contentView addSubview:label];
        [_icons addObject:icon];
        [_labels addObject:label];
    }
    UILongPressGestureRecognizer *touch = [[UILongPressGestureRecognizer alloc] initWithTarget:self action:@selector(touched:)];
    touch.minimumPressDuration = 0;
    [self addGestureRecognizer:touch];
    self.layer.shadowColor = UIColor.blackColor.CGColor;
    self.layer.shadowOpacity = 0.35;
    self.layer.shadowRadius = 18;
    self.layer.shadowOffset = CGSizeMake(0, 6);
    return self;
}

- (CGFloat)tabWidth { return (self.bounds.size.width - 8) / kCount; }

- (CGRect)lensFrameAt:(CGFloat)centerX {
    CGFloat w = [self tabWidth] + 6, h = self.bounds.size.height - 8;
    CGFloat x = MIN(MAX(centerX - w / 2, 4), self.bounds.size.width - 4 - w);
    return CGRectMake(x, 4, w, h);
}

- (void)layoutSubviews {
    [super layoutSubviews];
    _background.frame = self.bounds;
    makeCapsule(_background, self.bounds.size.height);
    CGFloat tab = [self tabWidth];
    for (NSInteger i = 0; i < kCount; i++) {
        CGFloat x = 4 + i * tab;
        _icons[i].frame = CGRectMake(x + (tab - 28) / 2, 9, 28, 26);
        _labels[i].frame = CGRectMake(x, 37, tab, 16);
    }
    if (!_dragging) [self placeLensAt:4 + (_selected + 0.5) * tab];
    [self updateColors];
}

- (void)placeLensAt:(CGFloat)centerX {
    // bounds + center, not frame: the lens may be scaled while the finger is down.
    CGRect frame = [self lensFrameAt:centerX];
    CGPoint center = CGPointMake(CGRectGetMidX(frame), CGRectGetMidY(frame));
    _lens.bounds = _lensTint.bounds = CGRectMake(0, 0, frame.size.width, frame.size.height);
    _lens.center = _lensTint.center = center;
    makeCapsule(_lens, frame.size.height);
    _lensTint.layer.cornerRadius = frame.size.height / 2;
    _lensTint.layer.cornerCurve = kCACornerCurveContinuous;
}

- (void)updateColors {
    for (NSInteger i = 0; i < kCount; i++) {
        UIColor *color = i == _selected ? UIColor.systemBlueColor : UIColor.whiteColor;
        _icons[i].tintColor = color;
        _labels[i].textColor = color;
    }
}

- (void)setSelected:(NSInteger)selected {
    if (selected < 0 || selected >= kCount || selected == _selected) return;
    _selected = selected;
    [self updateColors];
    [UIView animateWithDuration:0.45 delay:0 usingSpringWithDamping:0.78 initialSpringVelocity:0.4
                        options:UIViewAnimationOptionBeginFromCurrentState
                     animations:^{ [self placeLensAt:4 + (selected + 0.5) * [self tabWidth]]; } completion:nil];
}

// Touch down lifts the lens (it grows a little, like iOS's tab bar), dragging slides it, lifting picks a tab.
- (void)touched:(UILongPressGestureRecognizer *)gesture {
    CGFloat x = [gesture locationInView:self].x;
    NSInteger index = MIN(MAX((NSInteger)((x - 4) / [self tabWidth]), 0), kCount - 1);
    UIGestureRecognizerState state = gesture.state;
    if (state == UIGestureRecognizerStateBegan) {
        _dragging = YES;
        [UIView animateWithDuration:0.25 delay:0 usingSpringWithDamping:0.7 initialSpringVelocity:0.5
                            options:UIViewAnimationOptionBeginFromCurrentState animations:^{
            [self placeLensAt:x];
            self->_lens.transform = CGAffineTransformMakeScale(1.12, 1.18);
            self->_lensTint.transform = self->_lens.transform;
        } completion:nil];
    } else if (state == UIGestureRecognizerStateChanged) {
        [self placeLensAt:x];
    } else if (state == UIGestureRecognizerStateEnded) {
        _dragging = NO;
        [[UISelectionFeedbackGenerator new] selectionChanged];
        _selected = index;
        [self updateColors];
        [UIView animateWithDuration:0.45 delay:0 usingSpringWithDamping:0.72 initialSpringVelocity:0.6
                            options:UIViewAnimationOptionBeginFromCurrentState animations:^{
            self->_lens.transform = CGAffineTransformIdentity;
            self->_lensTint.transform = CGAffineTransformIdentity;
            [self placeLensAt:4 + (index + 0.5) * [self tabWidth]];
        } completion:nil];
        atomic_store(&pendingTap, (int)index);
    } else if (state == UIGestureRecognizerStateCancelled || state == UIGestureRecognizerStateFailed) {
        _dragging = NO;
        [UIView animateWithDuration:0.3 animations:^{
            self->_lens.transform = CGAffineTransformIdentity;
            self->_lensTint.transform = CGAffineTransformIdentity;
            [self placeLensAt:4 + (self->_selected + 0.5) * [self tabWidth]];
        }];
    }
}
@end

static KodiGlassBar *bar;

static UIWindow *kodiWindow(void) {
    for (UIScene *scene in UIApplication.sharedApplication.connectedScenes) {
        if (![scene isKindOfClass:UIWindowScene.class]) continue;
        for (UIWindow *window in ((UIWindowScene *)scene).windows)
            if (window.isKeyWindow) return window;
    }
    return UIApplication.sharedApplication.windows.firstObject;
}

static KodiGlassBar *ensureBar(void) {
    UIWindow *window = kodiWindow();
    if (!window) return nil;
    if (!bar) {
        bar = [[KodiGlassBar alloc] initWithFrame:CGRectZero];
        bar.translatesAutoresizingMaskIntoConstraints = NO;
        bar.hidden = YES;
        bar.alpha = 0;
    }
    if (bar.superview != window) {
        [bar removeFromSuperview];
        [window addSubview:bar];
        UILayoutGuide *safe = window.safeAreaLayoutGuide;
        NSLayoutConstraint *width = [bar.widthAnchor constraintEqualToAnchor:safe.widthAnchor constant:-28];
        width.priority = UILayoutPriorityDefaultHigh;
        [NSLayoutConstraint activateConstraints:@[
            [bar.centerXAnchor constraintEqualToAnchor:safe.centerXAnchor],
            [bar.bottomAnchor constraintEqualToAnchor:safe.bottomAnchor constant:-4],
            [bar.heightAnchor constraintEqualToConstant:62],
            [bar.widthAnchor constraintLessThanOrEqualToConstant:390],
            width,
        ]];
    }
    [window bringSubviewToFront:bar];
    return bar;
}

// Shows (1) or hides (0) the bar with a short fade. Safe to call from any thread.
__attribute__((visibility("default"))) void kodi_glassbar_show(int visible) {
    dispatch_async(dispatch_get_main_queue(), ^{
        KodiGlassBar *view = ensureBar();
        if (!view) return;
        if (visible) view.hidden = NO;
        [UIView animateWithDuration:0.2 animations:^{ view.alpha = visible ? 1 : 0; }
                         completion:^(BOOL done) { if (!visible && done) view.hidden = YES; }];
    });
}

// Marks the tab of the page Kodi is showing (0 Home, 1 Movies, 2 TV, 3 Library, 4 Search).
__attribute__((visibility("default"))) void kodi_glassbar_select(int index) {
    dispatch_async(dispatch_get_main_queue(), ^{ ensureBar().selected = index; });
}

// The tab the owner last tapped, once (-1 if none since the previous call).
__attribute__((visibility("default"))) int kodi_glassbar_take_tap(void) {
    return atomic_exchange(&pendingTap, -1);
}
OBJC
FW="$OUT/KodiGlassBar.framework"; rm -rf "$FW"; mkdir -p "$FW"
xcrun --sdk iphoneos clang -arch arm64 -isysroot "$SDK" -miphoneos-version-min=$MIN_IOS -fobjc-arc -O2 -dynamiclib \
  -install_name @rpath/KodiGlassBar.framework/KodiGlassBar -framework UIKit -framework QuartzCore -framework CoreGraphics \
  -o "$FW/KodiGlassBar" "$WORK/KodiGlassBar.m"
cat > "$FW/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>KodiGlassBar</string>
<key>CFBundleIdentifier</key><string>org.kodi-ios.glassbar</string>
<key>CFBundleName</key><string>KodiGlassBar</string>
<key>CFBundlePackageType</key><string>FMWK</string>
<key>CFBundleShortVersionString</key><string>1.0</string>
<key>CFBundleVersion</key><string>1</string>
<key>CFBundleSupportedPlatforms</key><array><string>iPhoneOS</string></array>
<key>MinimumOSVersion</key><string>$MIN_IOS</string>
</dict></plist>
PLIST
nm -gU "$FW/KodiGlassBar" | grep -E ' _kodi_glassbar_(show|select|take_tap)$'
lipo -info "$FW/KodiGlassBar"
(cd "$OUT" && zip -qry KodiGlassBar.framework.zip KodiGlassBar.framework && shasum -a 256 KodiGlassBar.framework.zip | tee KodiGlassBar.framework.zip.sha256)
