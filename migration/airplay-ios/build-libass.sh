#!/usr/bin/env bash
# r10 burned-in subtitles for the AirPlay picture bridge: static libass + FreeType + FriBidi + HarfBuzz, used directly
# from remux/src/kr_subs.c (FFmpeg's libass filter is NOT enabled: FFmpeg stays LGPL with no external libraries).
# Licences: libass ISC, FreeType FTL (chosen of its FTL/GPLv2 dual licence), FriBidi LGPL-2.1+, HarfBuzz MIT.
# No fontconfig: on iOS libass uses its CoreText font provider (the system fonts, loaded at runtime, not shipped);
# on the host the tests pass a font file. Tarballs are pinned and verified by sha256.
# Usage: build-libass.sh ios OUT_DIR | build-libass.sh host OUT_DIR
set -euo pipefail
TARGET="${1:?ios|host}"; OUT="$(mkdir -p "${2:?output directory}" && cd "$2" && pwd)"
WORK="${LIBASS_WORK:-$(mktemp -d "${TMPDIR:-/tmp}/kodi-libass.XXXXXX")}"
FREETYPE_VERSION=2.13.3; FREETYPE_SHA256=0550350666d427c74daeb85d5ac7bb353acba5f76956395995311a9c6f063289
FREETYPE_URL="https://download.savannah.gnu.org/releases/freetype/freetype-${FREETYPE_VERSION}.tar.xz"
FRIBIDI_VERSION=1.0.16; FRIBIDI_SHA256=1b1cde5b235d40479e91be2f0e88a309e3214c8ab470ec8a2744d82a5a9ea05c
FRIBIDI_URL="https://github.com/fribidi/fribidi/releases/download/v${FRIBIDI_VERSION}/fribidi-${FRIBIDI_VERSION}.tar.xz"
HARFBUZZ_VERSION=11.2.1; HARFBUZZ_SHA256=093714c8548a285094685f0bdc999e202d666b59eeb3df2ff921ab68b8336a49
HARFBUZZ_URL="https://github.com/harfbuzz/harfbuzz/releases/download/${HARFBUZZ_VERSION}/harfbuzz-${HARFBUZZ_VERSION}.tar.xz"
LIBASS_VERSION=0.17.4; LIBASS_SHA256=78f1179b838d025e9c26e8fef33f8092f65611444ffa1bfc0cfac6a33511a05a
LIBASS_URL="https://github.com/libass/libass/releases/download/${LIBASS_VERSION}/libass-${LIBASS_VERSION}.tar.xz"

fetch() { # name version sha url
  local tb="$WORK/$1-$2.tar.xz"
  if [[ ! -f "$WORK/$1-$2/.extracted" ]]; then
    [[ -f "$tb" ]] || curl --fail --location --proto '=https' --max-time 300 -o "$tb" "$4"
    echo "$3  $tb" | (command -v sha256sum >/dev/null && sha256sum -c - || shasum -a 256 -c -) >/dev/null
    tar -xf "$tb" -C "$WORK" && touch "$WORK/$1-$2/.extracted"
  fi
}
fetch freetype "$FREETYPE_VERSION" "$FREETYPE_SHA256" "$FREETYPE_URL"
fetch fribidi "$FRIBIDI_VERSION" "$FRIBIDI_SHA256" "$FRIBIDI_URL"
fetch harfbuzz "$HARFBUZZ_VERSION" "$HARFBUZZ_SHA256" "$HARFBUZZ_URL"
fetch libass "$LIBASS_VERSION" "$LIBASS_SHA256" "$LIBASS_URL"

JOBS="$( (command -v nproc >/dev/null && nproc) || sysctl -n hw.ncpu)"
CFG=(--prefix="$OUT" --enable-static --disable-shared --with-pic)
case "$TARGET" in
  ios)
    [[ "$(uname -s)" == Darwin ]] || { echo 'BLOCKED: macOS with the iPhoneOS SDK is required.' >&2; exit 2; }
    SDK="$(xcrun --sdk iphoneos --show-sdk-path)"
    export CC="$(xcrun --sdk iphoneos -f clang)" CXX="$(xcrun --sdk iphoneos -f clang++)"
    export CFLAGS="-arch arm64 -isysroot $SDK -miphoneos-version-min=14.0 -O2" CXXFLAGS="-arch arm64 -isysroot $SDK -miphoneos-version-min=14.0 -O2"
    export LDFLAGS="-arch arm64 -isysroot $SDK -miphoneos-version-min=14.0"
    CFG+=(--host=aarch64-apple-darwin)
    ASS_EXTRA=(--enable-coretext) ;;
  host)
    export CC="${CC:-cc}" CXX="${CXX:-c++}" CFLAGS="${CFLAGS:--O2}" CXXFLAGS="${CXXFLAGS:--O2}"
    ASS_EXTRA=(--disable-coretext) ;;
  *) echo "unknown target $TARGET" >&2; exit 2;;
esac
export PKG_CONFIG_LIBDIR="$OUT/lib/pkgconfig" PKG_CONFIG_PATH=""
mkdir -p "$OUT/lib/pkgconfig" "$OUT/include"
LOG="$OUT/build.log"; : > "$LOG"
run() { "$@" >> "$LOG" 2>&1 || { tail -40 "$LOG" >&2; exit 1; }; }

B="$WORK/build-$TARGET"; rm -rf "$B"; mkdir -p "$B"/{ft,fb,hb,ass}
# FreeType: no zlib/bzip2/png/brotli/harfbuzz (libass only needs outlines).
(cd "$B/ft" && run "$WORK/freetype-$FREETYPE_VERSION/configure" "${CFG[@]}" --with-zlib=no --with-bzip2=no \
   --with-png=no --with-brotli=no --with-harfbuzz=no && run make -j"$JOBS" && run make install)
(cd "$B/fb" && run "$WORK/fribidi-$FRIBIDI_VERSION/configure" "${CFG[@]}" && run make -C lib -j"$JOBS" \
   && run make -C lib install && run make install-pkgconfigDATA)
# HarfBuzz: the single-file amalgamation (src/harfbuzz.cc) with the FreeType integration; no glib/icu/cairo.
(cd "$B/hb" && run $CXX $CXXFLAGS -fPIC -std=c++11 -fno-exceptions -fno-rtti -DHAVE_FREETYPE=1 \
   -I"$OUT/include/freetype2" -c "$WORK/harfbuzz-$HARFBUZZ_VERSION/src/harfbuzz.cc" -o harfbuzz.o \
   && run ar rcs "$OUT/lib/libharfbuzz.a" harfbuzz.o)
mkdir -p "$OUT/include/harfbuzz"; cp "$WORK/harfbuzz-$HARFBUZZ_VERSION"/src/hb*.h "$OUT/include/harfbuzz/"
cat > "$OUT/lib/pkgconfig/harfbuzz.pc" <<EOF
prefix=$OUT
Name: harfbuzz
Description: HarfBuzz (amalgamated static build)
Version: $HARFBUZZ_VERSION
Requires.private: freetype2
Libs: -L\${prefix}/lib -lharfbuzz
Libs.private: -lc++
Cflags: -I\${prefix}/include/harfbuzz
EOF
[[ "$TARGET" == host && "$(uname -s)" != Darwin ]] && sed -i 's/-lc++/-lstdc++ -lm/' "$OUT/lib/pkgconfig/harfbuzz.pc"
(cd "$B/ass" && run "$WORK/libass-$LIBASS_VERSION/configure" "${CFG[@]}" --disable-fontconfig \
   --disable-require-system-font-provider --disable-asm --disable-libunibreak "${ASS_EXTRA[@]}" \
   && run make -j"$JOBS" && run make install)
printf 'libass %s (%s sha256 %s)\nFreeType %s (%s sha256 %s)\nFriBidi %s (%s sha256 %s)\nHarfBuzz %s (%s sha256 %s)\n' \
  "$LIBASS_VERSION" "$LIBASS_URL" "$LIBASS_SHA256" "$FREETYPE_VERSION" "$FREETYPE_URL" "$FREETYPE_SHA256" \
  "$FRIBIDI_VERSION" "$FRIBIDI_URL" "$FRIBIDI_SHA256" "$HARFBUZZ_VERSION" "$HARFBUZZ_URL" "$HARFBUZZ_SHA256" > "$OUT/LIBASS-CONFIG.txt"
echo "libass $LIBASS_VERSION ($TARGET) in $OUT"
