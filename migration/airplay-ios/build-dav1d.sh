#!/usr/bin/env bash
# Pinned BSD-2-Clause AV1 software decoder, static for host tests or iPhoneOS arm64.
set -euo pipefail
TARGET="${1:?ios|host}"; OUT="$(mkdir -p "${2:?output directory}" && cd "$2" && pwd)"
COMMIT=b546257f770768b2c88258c533da38b91a06f737  # upstream dav1d 1.5.3
SHA256=c5b7428c3f5b28db0aee0c62f6ffb2b42f4b08e7be5ce49d7ad046aaf0dc151d
URL="https://codeload.github.com/videolan/dav1d/tar.gz/$COMMIT"
WORK="${DAV1D_WORK:-$(mktemp -d "${TMPDIR:-/tmp}/kodi-dav1d.XXXXXX")}"; mkdir -p "$WORK"
SRC="$WORK/dav1d-$COMMIT"
if [[ ! -f "$SRC/meson.build" ]]; then
  curl --fail --location --proto '=https' --max-time 300 -o "$WORK/dav1d.tar.gz" "$URL"
  echo "$SHA256  $WORK/dav1d.tar.gz" | (command -v sha256sum >/dev/null && sha256sum -c - || shasum -a 256 -c -)
  tar -xf "$WORK/dav1d.tar.gz" -C "$WORK"
fi
if ! command -v meson >/dev/null || ! command -v ninja >/dev/null; then
  [[ -x "$WORK/tools/bin/meson" && -x "$WORK/tools/bin/ninja" ]] || {
    python3 -m venv "$WORK/tools"
    "$WORK/tools/bin/python" -m pip install --disable-pip-version-check meson==1.8.2 ninja==1.11.1.4
  }
  export PATH="$WORK/tools/bin:$PATH"
fi
ARGS=(--prefix="$OUT" --libdir=lib --default-library=static -Db_staticpic=true -Denable_tools=false -Denable_tests=false)
case "$TARGET" in
  ios)
    [[ "$(uname -s)" == Darwin ]] || { echo 'macOS with iPhoneOS SDK is required' >&2; exit 2; }
    SDK="$(xcrun --sdk iphoneos --show-sdk-path)"
    cat > "$WORK/ios.ini" <<EOF
[binaries]
c = ['xcrun', '--sdk', 'iphoneos', 'clang']
ar = ['xcrun', '--sdk', 'iphoneos', 'ar']
strip = ['xcrun', '--sdk', 'iphoneos', 'strip']
[host_machine]
system = 'darwin'
cpu_family = 'aarch64'
cpu = 'arm64'
endian = 'little'
[properties]
needs_exe_wrapper = true
[built-in options]
c_args = ['-arch', 'arm64', '-isysroot', '$SDK', '-miphoneos-version-min=14.0']
c_link_args = ['-arch', 'arm64', '-isysroot', '$SDK', '-miphoneos-version-min=14.0']
EOF
    ARGS+=(--cross-file="$WORK/ios.ini" -Denable_asm=true) ;;
  host) ARGS+=(-Denable_asm=false) ;;  # bounded, portable tests; phone arm64 keeps optimized assembly
  *) echo "unknown target $TARGET" >&2; exit 2 ;;
esac
BUILD="$WORK/build-$TARGET"
if [[ -f "$BUILD/meson-private/coredata.dat" ]]; then ARGS+=(--reconfigure); fi
meson setup "$BUILD" "$SRC" "${ARGS[@]}" > "$OUT/build.log" 2>&1
meson compile -C "$BUILD" >> "$OUT/build.log" 2>&1
meson install -C "$BUILD" >> "$OUT/build.log" 2>&1
cp "$SRC/COPYING" "$OUT/DAV1D-LICENSE.txt"
printf 'dav1d 1.5.3, commit %s\n%s\narchive sha256 %s\n' "$COMMIT" "$URL" "$SHA256" > "$OUT/DAV1D-CONFIG.txt"
