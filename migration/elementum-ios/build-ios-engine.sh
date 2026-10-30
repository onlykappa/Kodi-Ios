#!/usr/bin/env bash
# Builds the real pinned Elementum engine for iPhoneOS arm64 as elementum.framework, a dynamic library that the
# Elementum add-on loads in-process with ctypes (its existing "library mode"; iOS apps cannot launch a binary).
# Follows ElementumOrg/libtorrent-go's own recipe (versions and checksums from its Makefile), with Apple's
# iPhoneOS SDK in place of their osxcross toolchain. Needs macOS with Xcode. Usage: build-ios-engine.sh OUT_DIR
set -euo pipefail
[[ "$(uname -s)" == Darwin ]] || { echo 'BLOCKED: macOS with the iPhoneOS SDK is required.' >&2; exit 2; }
OUT="$(mkdir -p "${1:?output directory}" && cd "$1" && pwd)"
WORK="${WORK:-$(mktemp -d "${TMPDIR:-/tmp}/elementum-ios.XXXXXX")}"
PREFIX="$WORK/prefix"; HOST="$WORK/host"; SRC="$WORK/src"
mkdir -p "$PREFIX" "$HOST/bin" "$SRC"
JOBS="$(sysctl -n hw.ncpu)"
MIN_IOS=14.0

ENGINE_COMMIT=cdab7e2ed69122e048be158e2ebea70dbda789ee           # elgatito/elementum (plugin 0.1.114 era)
LIBTORRENT_COMMIT=760f94862ef6b76a13bba0a68d55ca6507aef7c2       # arvidn/libtorrent RC_1_1, as libtorrent-go pins
BOOST_VERSION=1.72.0; BOOST_SHA256=59c9b274bc451cf91a9ba1dd2c7fdcaf5d60b1b3aa83f2c9fa143417cc660722
OPENSSL_VERSION=1.1.1f; OPENSSL_SHA256=186c6bfe6ecfba7a5b48c47f8a1673d0f3b0e5ba2e25602dd23b629975da3f35
SWIG_COMMIT=77323a0f07562b7d90d36181697a72a909b9519a
GO_VERSION=1.21.1

SDK="$(xcrun --sdk iphoneos --show-sdk-path)"
CLANG="$(xcrun --sdk iphoneos --find clang)"; CLANGXX="$(xcrun --sdk iphoneos --find clang++)"
IOS_FLAGS="-arch arm64 -isysroot $SDK -miphoneos-version-min=$MIN_IOS"
step(){ echo "::group::$*"; }
end(){ echo "::endgroup::"; }
fetch(){ # url sha256 dest
  curl --fail --location --retry 3 --proto '=https' -o "$3" "$1"
  echo "$2  $3" | shasum -a 256 -c -
}
# Never let pkg-config or the compiler pick up Homebrew's macOS libraries for the iOS result.
export PKG_CONFIG_PATH='' PKG_CONFIG_LIBDIR="$PREFIX/lib/pkgconfig"

step "Toolchain"
xcodebuild -version; xcrun --sdk iphoneos --show-sdk-version
for tool in autoconf automake libtool pkg-config; do command -v "$tool" >/dev/null || brew install "$tool"; done
end

step "Go $GO_VERSION"
GO_SHA256="$(curl --fail -sSL 'https://go.dev/dl/?mode=json&include=all' | python3 -c "
import json,sys
for r in json.load(sys.stdin):
  if r['version']=='go$GO_VERSION':
    print(next(f['sha256'] for f in r['files'] if f['os']=='darwin' and f['arch']=='arm64' and f['kind']=='archive'))")"
fetch "https://go.dev/dl/go$GO_VERSION.darwin-arm64.tar.gz" "$GO_SHA256" "$SRC/go.tgz"
tar -xzf "$SRC/go.tgz" -C "$HOST"; export PATH="$HOST/go/bin:$HOST/bin:$PATH"; go version
end

step "SWIG (host tool, libtorrent-go's pinned commit)"
# GitHub's generated archives are not byte-stable, so libtorrent-go's archive checksum no longer matches;
# fetch the same pinned commit with git instead (the commit id pins the content).
git init -q "$SRC/swig-$SWIG_COMMIT"; git -C "$SRC/swig-$SWIG_COMMIT" fetch -q --depth=1 https://github.com/swig/swig.git "$SWIG_COMMIT"
git -C "$SRC/swig-$SWIG_COMMIT" checkout -q FETCH_HEAD; test "$(git -C "$SRC/swig-$SWIG_COMMIT" rev-parse HEAD)" = "$SWIG_COMMIT"
(cd "$SRC/swig-$SWIG_COMMIT" && ./autogen.sh >/dev/null && ./configure --prefix="$HOST" --without-pcre >/dev/null && make -j"$JOBS" >/dev/null && make install >/dev/null)
swig -version | head -3
end

step "OpenSSL $OPENSSL_VERSION for iPhoneOS arm64"
fetch "https://www.openssl.org/source/old/1.1.1/openssl-$OPENSSL_VERSION.tar.gz" "$OPENSSL_SHA256" "$SRC/openssl.tgz"
tar -xzf "$SRC/openssl.tgz" -C "$SRC"
(cd "$SRC/openssl-$OPENSSL_VERSION" && CFLAGS="-miphoneos-version-min=$MIN_IOS" ./Configure ios64-xcrun no-shared no-tests no-engine threads --prefix="$PREFIX" >/dev/null \
  && make -j"$JOBS" build_libs >/dev/null && make install_dev >/dev/null)
end

step "Boost $BOOST_VERSION for iPhoneOS arm64"
fetch "https://archives.boost.io/release/$BOOST_VERSION/source/boost_${BOOST_VERSION//./_}.tar.bz2" "$BOOST_SHA256" "$SRC/boost.tbz2"
tar -xjf "$SRC/boost.tbz2" -C "$SRC"
(cd "$SRC/boost_${BOOST_VERSION//./_}" && ./bootstrap.sh --with-toolset=clang >/dev/null \
  && echo "using darwin : iphone : $CLANGXX : <compileflags>\"$IOS_FLAGS -std=c++11\" <linkflags>\"$IOS_FLAGS\" <striper> ;" > user-config.jam \
  && ./b2 -q --user-config=user-config.jam toolset=darwin-iphone target-os=iphone architecture=arm address-model=64 binary-format=mach-o abi=aapcs \
       link=static variant=release threading=multi define=BOOST_SP_USE_PTHREADS \
       --with-system --with-date_time --with-chrono --with-random --with-program_options --prefix="$PREFIX" -j"$JOBS" install >/dev/null)
ls "$PREFIX/lib" | grep boost
end

step "libtorrent RC_1_1 ($LIBTORRENT_COMMIT) for iPhoneOS arm64"
git init -q "$SRC/libtorrent"; git -C "$SRC/libtorrent" fetch -q --depth=1 https://github.com/arvidn/libtorrent.git "$LIBTORRENT_COMMIT"
git -C "$SRC/libtorrent" checkout -q FETCH_HEAD
(cd "$SRC/libtorrent" && ./autotool.sh >/dev/null \
  && sed -i '' 's/$PKG_CONFIG openssl --libs-only-/$PKG_CONFIG openssl --static --libs-only-/' ./configure \
  && CC="$CLANG $IOS_FLAGS" CXX="$CLANGXX $IOS_FLAGS" CFLAGS="-O2" CXXFLAGS="-O2 -std=c++11 -Wno-c++11-extensions -Wno-c++11-long-long -Wno-deprecated-declarations" \
     ./configure --host=aarch64-apple-darwin --enable-static --disable-shared --disable-deprecated-functions \
       --prefix="$PREFIX" --with-boost="$PREFIX" --with-boost-libdir="$PREFIX/lib" --with-openssl="$PREFIX" >/dev/null \
  || { cat config.log | tail -80; exit 1; })
(cd "$SRC/libtorrent" && make -j"$JOBS" >/dev/null && make install >/dev/null)
pkg-config --static --libs libtorrent-rasterbar openssl
end

step "Elementum engine ($ENGINE_COMMIT) as a C archive"
git init -q "$SRC/engine"; git -C "$SRC/engine" fetch -q --depth=1 https://github.com/elgatito/elementum.git "$ENGINE_COMMIT"
git -C "$SRC/engine" checkout -q FETCH_HEAD
test "$(git -C "$SRC/engine" rev-parse HEAD)" = "$ENGINE_COMMIT"
# cgo for ios needs the SDK flags baked into CC/CXX.
printf '#!/bin/sh\nexec "%s" %s "$@"\n' "$CLANG" "$IOS_FLAGS" > "$HOST/bin/ios-cc"
printf '#!/bin/sh\nexec "%s" %s "$@"\n' "$CLANGXX" "$IOS_FLAGS" > "$HOST/bin/ios-cxx"
chmod +x "$HOST/bin/ios-cc" "$HOST/bin/ios-cxx"
(cd "$SRC/engine" && GOOS=ios GOARCH=arm64 CGO_ENABLED=1 CC=ios-cc CXX=ios-cxx \
   CGO_CXXFLAGS="-std=c++11 -I$PREFIX/include -Wno-deprecated-declarations" CGO_CFLAGS="-I$PREFIX/include" \
   go build -mod=readonly -trimpath -buildmode=c-archive -tags shared,go_json -ldflags "-s -w" -o "$WORK/libelementum.a" .)
end

step "Link elementum.framework"
FW="$OUT/elementum.framework"; rm -rf "$FW"; mkdir -p "$FW"
"$CLANGXX" $IOS_FLAGS -dynamiclib -o "$FW/elementum" -install_name @rpath/elementum.framework/elementum \
  -Wl,-force_load,"$WORK/libelementum.a" $(pkg-config --static --libs libtorrent-rasterbar openssl) \
  -L"$PREFIX/lib" -lboost_system -lboost_date_time -lboost_chrono -lboost_random -lboost_program_options \
  -lc++ -lresolv -framework CoreFoundation -framework Security -framework SystemConfiguration
cat > "$FW/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>elementum</string>
<key>CFBundleIdentifier</key><string>org.elementum.engine</string>
<key>CFBundleName</key><string>elementum</string>
<key>CFBundlePackageType</key><string>FMWK</string>
<key>CFBundleShortVersionString</key><string>0.1.114</string>
<key>CFBundleVersion</key><string>1</string>
<key>CFBundleSupportedPlatforms</key><array><string>iPhoneOS</string></array>
<key>MinimumOSVersion</key><string>$MIN_IOS</string>
</dict></plist>
PLIST
# The engine's exported entry points that the add-on calls through ctypes.
nm -gU "$FW/elementum" | grep -E ' _(startWithLogAndArgs|startWithArgs)$'
lipo -info "$FW/elementum"; otool -L "$FW/elementum" | head -20
otool -l "$FW/elementum" | grep -A4 LC_BUILD_VERSION | head -6
(cd "$OUT" && zip -qry elementum.framework.zip elementum.framework && shasum -a 256 elementum.framework.zip | tee elementum.framework.zip.sha256)
end
echo "Built $OUT/elementum.framework (engine $ENGINE_COMMIT, libtorrent $LIBTORRENT_COMMIT). Device testing still pending."
