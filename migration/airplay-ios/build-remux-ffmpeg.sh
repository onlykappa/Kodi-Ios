#!/usr/bin/env bash
# FFmpeg for the AirPlay MKV remuxer (migration/airplay-ios/remux): remux plus the audio bridge AirPlay needs
# (DTS / TrueHD / FLAC / Opus / Vorbis decoded and re-encoded to AAC) and, r7, the picture bridge for TVs whose AirPlay
# cannot decode the video (HEVC / VP9 / MPEG-2 / MPEG-4 decoded, VideoToolbox when available, scaled with libswscale
# and encoded to H.264 by Apple's hardware encoder h264_videotoolbox on iOS). LGPL-2.1+ only: no --enable-gpl, no
# --enable-nonfree, no external libraries (no libx264/openh264: VideoToolbox is a system framework). Static libraries for linking into KodiAirPlay.framework.
# Configuration derived from GMPlayer's Scripts/build-ffmpeg.sh (MIT, (c) 2026 Gaston Morixe).
# Usage: build-remux-ffmpeg.sh ios OUT_DIR     (macOS, iPhoneOS arm64)
#        build-remux-ffmpeg.sh host OUT_DIR    (Linux/macOS host, for the host tests)
set -euo pipefail
TARGET="${1:?ios|host}"; OUT="$(mkdir -p "${2:?output directory}" && cd "$2" && pwd)"
FFMPEG_VERSION="8.1.1"
FFMPEG_SHA256="b6863adde98898f42602017462871b5f6333e65aec803fdd7a6308639c52edf3"
FFMPEG_URL="https://ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.xz"
WORK="${FFMPEG_WORK:-$(mktemp -d "${TMPDIR:-/tmp}/kodi-remux-ffmpeg.XXXXXX")}"
SRC="$WORK/ffmpeg-${FFMPEG_VERSION}"
if [[ ! -f "$SRC/configure" ]]; then
  curl --fail --location --proto '=https' --max-time 300 -o "$WORK/ffmpeg.tar.xz" "$FFMPEG_URL"
  echo "$FFMPEG_SHA256  $WORK/ffmpeg.tar.xz" | (command -v sha256sum >/dev/null && sha256sum -c - || shasum -a 256 -c -)
  tar -xf "$WORK/ffmpeg.tar.xz" -C "$WORK"
fi
FLAGS=(
  --disable-everything --disable-programs --disable-doc --disable-debug
  --disable-shared --enable-static --enable-pic --enable-small --disable-autodetect
  --enable-avformat --enable-avcodec --enable-swresample
  --enable-swscale --disable-avdevice --disable-avfilter
  --enable-demuxer=matroska --enable-demuxer=mov --enable-demuxer=mpegts --enable-demuxer=avi
  --enable-muxer=mov --enable-muxer=mp4 --enable-muxer=webvtt
  --enable-parser=hevc --enable-parser=h264 --enable-parser=aac --enable-parser=aac_latm --enable-parser=ac3
  --enable-parser=av1 --enable-parser=mpegaudio --enable-parser=flac --enable-parser=opus --enable-parser=vorbis
  --enable-parser=dca --enable-parser=mlp --enable-parser=vp9
  --enable-bsf=hevc_mp4toannexb --enable-bsf=h264_mp4toannexb --enable-bsf=aac_adtstoasc
  --enable-bsf=extract_extradata --enable-bsf=dump_extradata --enable-bsf=setts
  # Audio bridge: codecs Apple's player cannot carry, decoded and re-encoded to AAC.
  --enable-decoder=dca --enable-decoder=truehd --enable-decoder=mlp --enable-decoder=flac
  --enable-decoder=opus --enable-decoder=vorbis --enable-encoder=aac
  # Text subtitles as WebVTT.
  --enable-decoder=subrip --enable-decoder=srt --enable-decoder=ass --enable-decoder=ssa
  --enable-decoder=movtext --enable-decoder=webvtt --enable-decoder=text --enable-encoder=webvtt
  # r7 picture bridge: video decoders (AV1 needs dav1d, an external library: not included).
  --enable-decoder=hevc --enable-decoder=h264 --enable-decoder=vp9 --enable-decoder=vp8 --enable-decoder=mpeg2video
  --enable-decoder=mpeg1video --enable-decoder=mpeg4 --enable-parser=mpegvideo --enable-parser=mpeg4video
  --enable-parser=vp8
  --enable-protocol=file --enable-network --enable-protocol=http --enable-protocol=tcp
)
case "$TARGET" in
  ios)
    [[ "$(uname -s)" == Darwin ]] || { echo 'BLOCKED: macOS with the iPhoneOS SDK is required.' >&2; exit 2; }
    SDK="$(xcrun --sdk iphoneos --show-sdk-path)"; CC="$(xcrun --sdk iphoneos -f clang)"
    FLAGS+=(--enable-protocol=https --enable-protocol=tls --enable-securetransport
            --enable-cross-compile --target-os=darwin --arch=arm64 --cc="$CC"
            --sysroot="$SDK" --extra-cflags="-arch arm64 -miphoneos-version-min=14.0"
            --extra-ldflags="-arch arm64 -miphoneos-version-min=14.0")
    ;;
  # No hand-written assembly needed for tests (and no nasm on CI). FFmpeg has no LGPL H.264 encoder and the host has no
  # VideoToolbox, so the host tests drive the picture bridge with the built-in MPEG-4 Part 2 encoder (tests only).
  host) FLAGS+=(--disable-x86asm --enable-encoder=mpeg4) ;;
  *) echo "unknown target $TARGET" >&2; exit 2;;
esac
BUILD="$WORK/build-$TARGET"; mkdir -p "$BUILD"; cd "$BUILD"
"$SRC/configure" --prefix="$OUT" "${FLAGS[@]}" > "$OUT/configure.log" 2>&1 || { tail -40 "$OUT/configure.log" >&2; exit 1; }
make -j"$( (command -v nproc >/dev/null && nproc) || sysctl -n hw.ncpu)" > "$OUT/make.log" 2>&1 || { tail -40 "$OUT/make.log" >&2; exit 1; }
make install > /dev/null
# The exact configuration goes into THIRD-PARTY-NOTICES (FFmpeg LGPL: say how it was built).
printf 'FFmpeg %s (%s, sha256 %s)\nconfigure %s\n' "$FFMPEG_VERSION" "$FFMPEG_URL" "$FFMPEG_SHA256" "${FLAGS[*]}" > "$OUT/FFMPEG-CONFIG.txt"
echo "FFmpeg $FFMPEG_VERSION ($TARGET) in $OUT"
