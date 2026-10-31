#!/usr/bin/env bash
# Build Kodi 21.3-Omega for iPhoneOS with the r11 rotation patch and export only the main executable.
# Usage: build-kodi-ios.sh <work-dir> <out-dir>
set -euo pipefail
WORK=$1; OUT=$2
HERE=$(cd "$(dirname "$0")" && pwd)
TAG=21.3-Omega
COMMIT=$(python3 -c "import json;print(json.load(open('$HERE/source-lock.json'))['commit'])")
mkdir -p "$WORK" "$OUT"
SRC=$WORK/xbmc; DEPS=$WORK/depends; BUILD=$WORK/build
if [ ! -d "$SRC/.git" ]; then
  git clone --quiet --depth 1 --branch "$TAG" https://github.com/xbmc/xbmc.git "$SRC"
fi
test "$(git -C "$SRC" rev-parse HEAD)" = "$COMMIT" || { echo "Kodi tag $TAG moved"; exit 1; }
# A restored cache holds a previously patched tree; start from the pinned tag each time.
git -C "$SRC" checkout --quiet -- xbmc
git -C "$SRC" apply --check "$HERE/kodi-21.3-rotation.patch"
git -C "$SRC" apply "$HERE/kodi-21.3-rotation.patch"
JOBS=$(getconf _NPROCESSORS_ONLN)
cd "$SRC/tools/depends"
[ -f "$DEPS/.depends-built" ] || ./bootstrap
[ -f "$DEPS/.depends-built" ] || ./configure --host=aarch64-apple-darwin --with-platform=ios --prefix="$DEPS" > "$WORK/configure.log" 2>&1 || { tail -50 "$WORK/configure.log"; exit 1; }
if [ ! -f "$DEPS/.depends-built" ]; then
  if ! make -j"$JOBS" > "$WORK/depends.log" 2>&1; then
    grep -n -i -B2 -A8 "error" "$WORK/depends.log" | tail -120; exit 1
  fi
  touch "$DEPS/.depends-built"
fi
make -C "$SRC/tools/depends/target/cmakebuildsys" BUILD_DIR="$BUILD" > "$WORK/cmake.log" 2>&1 || { tail -80 "$WORK/cmake.log"; exit 1; }
cd "$BUILD"
if ! xcodebuild -config Release -target kodi -jobs "$JOBS" -sdk iphoneos CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO > "$WORK/xcode.log" 2>&1; then
  grep -n "error:" "$WORK/xcode.log" | head -60; tail -40 "$WORK/xcode.log"; exit 1
fi
APP=$(find "$BUILD" -path '*Release-iphoneos/Kodi.app' -type d | head -1)
test -n "$APP" && test -f "$APP/Kodi"
cp "$APP/Kodi" "$OUT/Kodi"
otool -L "$OUT/Kodi" > "$OUT/Kodi.dylibs.txt"
lipo -info "$OUT/Kodi"
( cd "$OUT" && shasum -a 256 Kodi > Kodi.sha256 )
shasum -a 256 "$HERE/kodi-21.3-rotation.patch" | cut -d' ' -f1 > "$OUT/patch.sha256"
echo "$COMMIT" > "$OUT/kodi-commit.txt"
cat "$OUT/Kodi.sha256"
