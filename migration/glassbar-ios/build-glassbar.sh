#!/usr/bin/env bash
# Builds KodiGlassBar.framework: the portrait tab bar (Home, Movies, TV, Library, Search) as a native iOS view.
# Kodi draws its skin with OpenGL and cannot blur or refract what is behind a control; this bar uses Apple's own
# Liquid Glass (UIGlassEffect, iOS 26), with a glass lens that slides to the chosen tab, and the system frosted
# material on older iOS. The setup add-on loads it with ctypes (resources/lib/glassbar.py): kodi_glassbar_show,
# kodi_glassbar_select and kodi_glassbar_take_tap. UIGlassEffect is looked up at run time, so any Xcode builds it.
# r3: the Search page's field as a native iOS search field at the top of the screen (kodi_search_show, _focus, _take,
# _set): typing happens in iOS's own keyboard while Kodi lists the results under it as you type (searchbar.py).
# r5: Kodi itself can drive the bar (Kodi executable r22, xbmc/application/Application.cpp): it dlopens this
# framework when its frame loop starts, calls kodi_glassbar_set_native_owner(1) and then show/select/take_tap from
# its own thread, so the bar is up as Home opens instead of when Python starts (2-4.5 s later on the phone). The
# setup add-on reads kodi_glassbar_native_owner() and then leaves the bar alone (no second owner). The first show
# appears at once, without the fade.
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
static atomic_int nativeOwner = 0; // r5: 1 once the Kodi executable drives the bar

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

// r2: the bar owns the whole strip from just above the glass to the bottom edge of the screen, edge to edge, like
// iOS's own tab bar. Kodi draws its rows behind and around the capsule (14 pt each side, the home indicator area
// below), so a tap that missed the glass by a little opened the Continue Watching item under it. A touch in the
// strip picks the tab under the finger's x (clamped to the end tabs) and never reaches Kodi.
- (BOOL)pointInside:(CGPoint)point withEvent:(UIEvent *)event {
    if ([super pointInside:point withEvent:event]) return YES;
    UIView *window = self.window;
    if (!window || self.hidden || self.alpha < 0.01) return NO;
    CGPoint inWindow = [self convertPoint:point toView:window];
    CGFloat top = CGRectGetMinY([self convertRect:self.bounds toView:window]) - 12;
    return inWindow.y >= top && inWindow.y <= CGRectGetMaxY(window.bounds) &&
           inWindow.x >= CGRectGetMinX(window.bounds) && inWindow.x <= CGRectGetMaxX(window.bounds);
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
        static BOOL everShown = NO;
        KodiGlassBar *view = ensureBar();
        if (!view) return;
        if (visible && !everShown) {
            // r5: at launch the bar is there with Home's first frame, not faded in after it.
            everShown = YES;
            view.hidden = NO;
            view.alpha = 1;
            return;
        }
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

// r5: the Kodi executable claims the bar (1) before driving it; the setup add-on then only keeps the Search field.
__attribute__((visibility("default"))) void kodi_glassbar_set_native_owner(int owner) {
    atomic_store(&nativeOwner, owner ? 1 : 0);
}

// r5: 1 when the Kodi executable drives the bar, 0 when the setup add-on must (older Kodi executable).
__attribute__((visibility("default"))) int kodi_glassbar_native_owner(void) {
    return atomic_load(&nativeOwner);
}

// ---- r3: Search page field ----------------------------------------------------------------------------------------
// A dark band across the top of the screen with a rounded search field (magnifier, clear button) and a round X
// button, as in the Apple TV app. Python reads what was typed with kodi_search_take() and lists the results below.
enum { SearchChanged = 1, SearchSubmitted = 2, SearchClosed = 4 };
static UIView *searchBand;
static UITextField *searchField;
static NSLayoutConstraint *searchTop, *settingsSearchTop, *searchBottom;
static int searchContext=0;
static NSString *searchText = @"";
static atomic_int searchEvents = 0;

@interface KodiSearchHandler : NSObject <UITextFieldDelegate, UIGestureRecognizerDelegate>
@end

@implementation KodiSearchHandler
- (void)store:(NSString *)text {
    @synchronized (KodiSearchHandler.class) { searchText = [text copy] ?: @""; }
    atomic_fetch_or(&searchEvents, SearchChanged);
}
- (void)changed:(UITextField *)field { [self store:field.text]; }
- (BOOL)textFieldShouldReturn:(UITextField *)field {
    [field resignFirstResponder];
    atomic_fetch_or(&searchEvents, SearchSubmitted);
    return YES;
}
- (BOOL)textFieldShouldClear:(UITextField *)field {
    [self store:@""]; // the clear button sends no editing-changed event
    return YES;
}
- (void)closeTapped {
    searchField.text = @"";
    [self store:@""];
    [searchField resignFirstResponder];
    atomic_fetch_or(&searchEvents, SearchClosed);
}
// Dragging the results lowers the keyboard, as in iOS's own search pages.
- (void)dragged:(UIPanGestureRecognizer *)pan {
    if (pan.state == UIGestureRecognizerStateBegan) [searchField resignFirstResponder];
}
- (BOOL)gestureRecognizerShouldBegin:(UIGestureRecognizer *)gesture {
    return searchField.isFirstResponder && !searchBand.hidden;
}
- (BOOL)gestureRecognizer:(UIGestureRecognizer *)gesture shouldReceiveTouch:(UITouch *)touch {
    return ![touch.view isDescendantOfView:searchBand];
}
- (BOOL)gestureRecognizer:(UIGestureRecognizer *)gesture shouldRecognizeSimultaneouslyWithGestureRecognizer:(UIGestureRecognizer *)other {
    return YES;
}
@end

static KodiSearchHandler *searchHandler;

static UIView *ensureSearch(void) {
    UIWindow *window = kodiWindow();
    if (!window) return nil;
    if (!searchBand) {
        searchHandler = [KodiSearchHandler new];
        searchBand = [[UIView alloc] initWithFrame:CGRectZero];
        searchBand.translatesAutoresizingMaskIntoConstraints = NO;
        searchBand.backgroundColor = [UIColor colorWithWhite:0.07 alpha:1];
        searchBand.hidden = YES;

        searchField = [[UITextField alloc] initWithFrame:CGRectZero];
        searchField.translatesAutoresizingMaskIntoConstraints = NO;
        searchField.backgroundColor = [UIColor colorWithWhite:0.2 alpha:1];
        searchField.layer.cornerRadius = 23;
        searchField.layer.cornerCurve = kCACornerCurveContinuous;
        searchField.textColor = UIColor.whiteColor;
        searchField.tintColor = UIColor.systemBlueColor;
        searchField.font = [UIFont systemFontOfSize:19 weight:UIFontWeightMedium];
        searchField.attributedPlaceholder = [[NSAttributedString alloc] initWithString:@"Shows, Movies, and More"
            attributes:@{NSForegroundColorAttributeName: [UIColor colorWithWhite:0.55 alpha:1]}];
        searchField.returnKeyType = UIReturnKeySearch;
        searchField.keyboardAppearance = UIKeyboardAppearanceDark;
        searchField.autocorrectionType = UITextAutocorrectionTypeNo;
        searchField.autocapitalizationType = UITextAutocapitalizationTypeNone;
        searchField.clearButtonMode = UITextFieldViewModeWhileEditing;
        searchField.delegate = searchHandler;
        [searchField addTarget:searchHandler action:@selector(changed:) forControlEvents:UIControlEventEditingChanged];
        UIImageSymbolConfiguration *glyph = [UIImageSymbolConfiguration configurationWithPointSize:19 weight:UIImageSymbolWeightBold];
        UIImageView *magnifier = [[UIImageView alloc] initWithImage:[UIImage systemImageNamed:@"magnifyingglass" withConfiguration:glyph]];
        magnifier.tintColor = UIColor.whiteColor;
        magnifier.contentMode = UIViewContentModeCenter;
        // r4: the glyph in its own 56 pt slot (16 pt in from the edge, 12 pt before the text); as a bare left view it
        // sat on the field's edge and against the typed text (owner screenshot).
        magnifier.frame = CGRectMake(16, 0, 28, 46);
        UIView *slot = [[UIView alloc] initWithFrame:CGRectMake(0, 0, 56, 46)];
        slot.userInteractionEnabled = NO;
        [slot addSubview:magnifier];
        searchField.leftView = slot;
        searchField.leftViewMode = UITextFieldViewModeAlways;

        UIButton *close = [UIButton buttonWithType:UIButtonTypeSystem];
        close.translatesAutoresizingMaskIntoConstraints = NO;
        [close setImage:[UIImage systemImageNamed:@"xmark" withConfiguration:glyph] forState:UIControlStateNormal];
        close.tintColor = UIColor.whiteColor;
        close.backgroundColor = [UIColor colorWithWhite:0.2 alpha:1];
        close.layer.cornerRadius = 23;
        [close addTarget:searchHandler action:@selector(closeTapped) forControlEvents:UIControlEventTouchUpInside];

        [searchBand addSubview:searchField];
        [searchBand addSubview:close];
        [NSLayoutConstraint activateConstraints:@[
            [close.trailingAnchor constraintEqualToAnchor:searchBand.safeAreaLayoutGuide.trailingAnchor constant:-16],
            [close.widthAnchor constraintEqualToConstant:46], [close.heightAnchor constraintEqualToConstant:46],
            [close.centerYAnchor constraintEqualToAnchor:searchField.centerYAnchor],
            [searchField.leadingAnchor constraintEqualToAnchor:searchBand.safeAreaLayoutGuide.leadingAnchor constant:16],
            [searchField.trailingAnchor constraintEqualToAnchor:close.leadingAnchor constant:-10],
            [searchField.heightAnchor constraintEqualToConstant:46],
            [searchField.bottomAnchor constraintEqualToAnchor:searchBand.bottomAnchor constant:-10],
        ]];
    }
    if (searchBand.superview != window) {
        [searchBand removeFromSuperview];
        [window addSubview:searchBand];
        searchTop=[searchBand.topAnchor constraintEqualToAnchor:window.topAnchor];
        settingsSearchTop=[searchBand.topAnchor constraintEqualToAnchor:window.safeAreaLayoutGuide.topAnchor constant:116.5];
        searchBottom=[searchBand.bottomAnchor constraintEqualToAnchor:window.safeAreaLayoutGuide.topAnchor constant:60];
        [NSLayoutConstraint activateConstraints:@[
            searchContext?settingsSearchTop:searchTop,
            [searchBand.leadingAnchor constraintEqualToAnchor:window.leadingAnchor],
            [searchBand.trailingAnchor constraintEqualToAnchor:window.trailingAnchor],
            // The band ends 60 pt below the top of the safe area: the Search page starts its results under it.
            searchBottom,
        ]];
        UIPanGestureRecognizer *drag = [[UIPanGestureRecognizer alloc] initWithTarget:searchHandler action:@selector(dragged:)];
        drag.cancelsTouchesInView = NO;
        drag.delaysTouchesBegan = NO;
        drag.delaysTouchesEnded = NO;
        drag.delegate = searchHandler;
        [window addGestureRecognizer:drag];
    }
    [window bringSubviewToFront:searchBand];
    return searchBand;
}

// Shows (1) or hides (0) the Search page field; hiding also lowers the keyboard. Any thread.
__attribute__((visibility("default"))) void kodi_search_show(int visible) {
    dispatch_async(dispatch_get_main_queue(), ^{
        UIView *band = ensureSearch();
        if (!band) return;
        if (!visible) [searchField resignFirstResponder];
        band.hidden = !visible;
        if (visible) [band.window bringSubviewToFront:band];
    });
}

// r6: reuse the native field in Settings, below its large title, without Kodi's keyboard page.
__attribute__((visibility("default"))) void kodi_search_context(int context) {
    dispatch_async(dispatch_get_main_queue(), ^{
        if(!ensureSearch())return;
        searchContext=context?1:0;
        searchTop.active=NO;settingsSearchTop.active=NO;
        if(searchContext)settingsSearchTop.active=YES;else searchTop.active=YES;
        searchBottom.constant=searchContext?182.5:60;
        NSString *hint=searchContext?@"Search":@"Shows, Movies, and More";
        searchField.attributedPlaceholder=[[NSAttributedString alloc] initWithString:hint attributes:@{NSForegroundColorAttributeName:UIColor.secondaryLabelColor}];
        searchField.accessibilityLabel=searchContext?@"Search Settings":@"Search movies and shows";
        [searchBand.window layoutIfNeeded];
    });
}

// Raises (1) or lowers (0) the keyboard for the field. Any thread.
__attribute__((visibility("default"))) void kodi_search_focus(int on) {
    dispatch_async(dispatch_get_main_queue(), ^{
        if (!ensureSearch()) return;
        if (on && !searchBand.hidden) [searchField becomeFirstResponder];
        else [searchField resignFirstResponder];
    });
}

// Puts text in the field (a search to show again). Any thread.
__attribute__((visibility("default"))) void kodi_search_set(const char *text) {
    NSString *value = text ? [NSString stringWithUTF8String:text] : @"";
    dispatch_async(dispatch_get_main_queue(), ^{
        if (!ensureSearch()) return;
        searchField.text = value;
        @synchronized (KodiSearchHandler.class) { searchText = value ?: @""; }
    });
}

// What happened since the last call (1 text changed, 2 Search key, 4 X tapped; or-ed) and the field's text as UTF-8
// in buffer (cut to size - 1 bytes, always terminated). Any thread.
__attribute__((visibility("default"))) int kodi_search_take(char *buffer, int size) {
    int events = atomic_exchange(&searchEvents, 0);
    if (buffer && size > 0) {
        NSString *text;
        @synchronized (KodiSearchHandler.class) { text = searchText; }
        const char *utf8 = text.UTF8String ?: "";
        strncpy(buffer, utf8, (size_t)size - 1);
        buffer[size - 1] = 0;
    }
    return events;
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
nm -gU "$FW/KodiGlassBar" | grep -E ' _kodi_(glassbar_(show|select|take_tap|set_native_owner|native_owner)|search_(show|focus|set|take|context))$'
lipo -info "$FW/KodiGlassBar"
(cd "$OUT" && zip -qry KodiGlassBar.framework.zip KodiGlassBar.framework && shasum -a 256 KodiGlassBar.framework.zip | tee KodiGlassBar.framework.zip.sha256)
