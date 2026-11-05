#!/usr/bin/env bash
# FFmpeg for the AirPlay MKV remuxer (migration/airplay-ios/remux): remux plus the audio bridge AirPlay needs
# (DTS / TrueHD / FLAC / Opus / Vorbis decoded and re-encoded to AAC) and, r7, the picture bridge for TVs whose AirPlay
# cannot decode the video (HEVC / VP9 / MPEG-2 / MPEG-4 decoded, VideoToolbox when available, scaled with libswscale
# and encoded to H.264 by Apple's hardware encoder h264_videotoolbox on iOS). LGPL-2.1+ only: no --enable-gpl, no
# --enable-nonfree or GPL libraries. AV1 uses BSD-2-Clause dav1d; VideoToolbox is a system framework.
# Static libraries for linking into KodiAirPlay.framework.
# Configuration derived from GMPlayer's Scripts/build-ffmpeg.sh (MIT, (c) 2026 Gaston Morixe).
# Usage: build-remux-ffmpeg.sh ios OUT_DIR     (macOS, iPhoneOS arm64)
#        build-remux-ffmpeg.sh host OUT_DIR    (Linux/macOS host, for the host tests)
set -euo pipefail
TARGET="${1:?ios|host}"; OUT="$(mkdir -p "${2:?output directory}" && cd "$2" && pwd)"
FFMPEG_VERSION="8.1.1"
FFMPEG_SHA256="b6863adde98898f42602017462871b5f6333e65aec803fdd7a6308639c52edf3"
FFMPEG_URL="https://ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.xz"
WORK="${FFMPEG_WORK:-$(mktemp -d "${TMPDIR:-/tmp}/kodi-remux-ffmpeg.XXXXXX")}"
mkdir -p "$WORK"
HERE="$(cd "$(dirname "$0")" && pwd)"
DAV="${REMUX_DAV1D:-$OUT/dav1d}"
[[ -f "$DAV/lib/libdav1d.a" ]] || bash "$HERE/build-dav1d.sh" "$TARGET" "$DAV"
export PKG_CONFIG_PATH="$DAV/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
SRC="$WORK/ffmpeg-${FFMPEG_VERSION}"
SOURCE_URL="$FFMPEG_URL"; SOURCE_SHA256="$FFMPEG_SHA256"
if [[ ! -f "$SRC/configure" ]]; then
  if curl --fail --location --proto '=https' --max-time 300 -o "$WORK/ffmpeg.tar.xz" "$FFMPEG_URL"; then
    echo "$FFMPEG_SHA256  $WORK/ffmpeg.tar.xz" | (command -v sha256sum >/dev/null && sha256sum -c - || shasum -a 256 -c -)
    tar -xf "$WORK/ffmpeg.tar.xz" -C "$WORK"
  else
    # Same signed upstream release commit, independently pinned archive for site outages.
    SOURCE_URL="https://codeload.github.com/FFmpeg/FFmpeg/tar.gz/239f2c733de417201d7ad3b3b8b0d9b63285b2b1"
    SOURCE_SHA256=ec0aa20fb9f6fd3692ffc04dc12ffa43cfffc4a479e388ccd7910ec6cfe188a2
    curl --fail --location --proto '=https' --max-time 300 -o "$WORK/ffmpeg.tar.gz" "$SOURCE_URL"
    echo "$SOURCE_SHA256  $WORK/ffmpeg.tar.gz" | (command -v sha256sum >/dev/null && sha256sum -c - || shasum -a 256 -c -)
    mkdir -p "$SRC"; tar -xf "$WORK/ffmpeg.tar.gz" --strip-components=1 -C "$SRC"
  fi
  printf '%s\n%s\n' "$SOURCE_URL" "$SOURCE_SHA256" > "$WORK/source-origin.txt"
elif [[ -f "$WORK/source-origin.txt" ]]; then
  SOURCE_URL="$(sed -n '1p' "$WORK/source-origin.txt")"; SOURCE_SHA256="$(sed -n '2p' "$WORK/source-origin.txt")"
else
  SOURCE_URL="pre-existing-source-tree"; SOURCE_SHA256="not-rechecked"
fi

if ! grep -q 'int64_t avpriv_kodi_mov_index_pts' "$SRC/libavformat/mov.c"; then
  patch --batch --forward -d "$SRC" -p1 < "$HERE/ffmpeg-mov-pts.patch"
fi
if ! grep -q 'Kodi iOS: ignore NAL trailing_zero_8bits' "$SRC/libavcodec/dovi_rpudec.c"; then
  patch --batch --forward -d "$SRC" -p1 < "$HERE/ffmpeg-dovi-padding.patch"
fi
FLAGS=(
  --disable-everything --disable-programs --disable-doc --disable-debug
  --disable-shared --enable-static --enable-pic --enable-small --disable-autodetect
  --enable-avformat --enable-avcodec --enable-swresample
  --enable-swscale --disable-avdevice --disable-avfilter
  --enable-demuxer=matroska --enable-demuxer=mov --enable-demuxer=mpegts --enable-demuxer=avi
  --enable-demuxer=mpegvideo --enable-demuxer=mpegps --enable-demuxer=asf --enable-demuxer=flv --enable-demuxer=ogg
  --enable-demuxer=rm --enable-demuxer=wtv --enable-demuxer=nut
  --enable-demuxer=sup --enable-demuxer=vobsub
  --enable-muxer=mov --enable-muxer=mp4 --enable-muxer=webvtt
  --enable-parser=hevc --enable-parser=h264 --enable-parser=aac --enable-parser=aac_latm --enable-parser=ac3
  --enable-parser=av1 --enable-parser=mpegaudio --enable-parser=flac --enable-parser=opus --enable-parser=vorbis
  --enable-parser=dca --enable-parser=mlp --enable-parser=vp9
  --enable-bsf=hevc_mp4toannexb --enable-bsf=h264_mp4toannexb --enable-bsf=aac_adtstoasc
  --enable-bsf=extract_extradata --enable-bsf=dump_extradata --enable-bsf=setts
  # Audio bridge: codecs Apple's player cannot carry, decoded and re-encoded to AAC.
  --enable-decoder=dca --enable-decoder=truehd --enable-decoder=mlp --enable-decoder=flac
  --enable-decoder=opus --enable-decoder=vorbis --enable-encoder=aac
  --enable-decoder=aac --enable-decoder=aac_latm --enable-decoder=mp2float --enable-decoder=mp3float --enable-decoder=ac3 --enable-decoder=eac3
  --enable-decoder=wmav1 --enable-decoder=wmav2 --enable-decoder=wmapro --enable-decoder=wmavoice
  --enable-decoder=wavpack --enable-decoder=alac --enable-decoder=pcm_bluray --enable-decoder=pcm_dvd --enable-decoder=pcm_s16le --enable-decoder=pcm_s16be --enable-decoder=pcm_s24le --enable-decoder=pcm_s32le
  --enable-decoder=pcm_s24be --enable-decoder=pcm_s32be --enable-decoder=pcm_f32le --enable-decoder=pcm_f64le
  # Text subtitles as WebVTT.
  --enable-decoder=pgssub --enable-decoder=dvdsub --enable-decoder=dvbsub --enable-decoder=xsub
  --enable-decoder=subrip --enable-decoder=srt --enable-decoder=ass --enable-decoder=ssa
  --enable-decoder=movtext --enable-decoder=webvtt --enable-decoder=text --enable-encoder=webvtt
  # Picture bridge: native decoders plus pinned dav1d for AV1 fallback on all devices.
  --enable-libdav1d --enable-decoder=libdav1d
  --enable-decoder=hevc --enable-decoder=h264 --enable-decoder=vp9 --enable-decoder=vp8 --enable-decoder=mpeg2video
  --enable-decoder=mpeg1video --enable-decoder=mpeg4 --enable-parser=mpegvideo --enable-parser=mpeg4video
  --enable-parser=vp8
  --enable-decoder=vc1 --enable-decoder=wmv1 --enable-decoder=wmv2 --enable-decoder=wmv3
  --enable-decoder=msmpeg4v1 --enable-decoder=msmpeg4v2 --enable-decoder=msmpeg4v3
  --enable-decoder=h263 --enable-decoder=flv --enable-decoder=theora --enable-decoder=mjpeg
  --enable-decoder=prores --enable-decoder=dnxhd --enable-decoder=ffv1 --enable-decoder=huffyuv
  --enable-decoder=rv10 --enable-decoder=rv20 --enable-decoder=rv30 --enable-decoder=rv40
  --enable-parser=vc1 --enable-parser=h263 --enable-parser=mjpeg --enable-parser=dnxhd
  --enable-protocol=file --enable-network --enable-protocol=http --enable-protocol=tcp
)
case "$TARGET" in
  ios)
    [[ "$(uname -s)" == Darwin ]] || { echo 'BLOCKED: macOS with the iPhoneOS SDK is required.' >&2; exit 2; }
    SDK="$(xcrun --sdk iphoneos --show-sdk-path)"; CC="$(xcrun --sdk iphoneos -f clang)"
    FLAGS+=(--enable-protocol=https --enable-protocol=tls --enable-securetransport
            # r7: VideoToolbox decode (hwaccels) and Apple's hardware H.264 encoder (system frameworks VideoToolbox,
            # CoreMedia, CoreVideo, CoreFoundation; build-airplay.sh links them).
            --enable-videotoolbox --enable-hwaccel=hevc_videotoolbox --enable-hwaccel=h264_videotoolbox
            --enable-hwaccel=mpeg2_videotoolbox --enable-hwaccel=mpeg1_videotoolbox
            --enable-hwaccel=mpeg4_videotoolbox --enable-hwaccel=vp9_videotoolbox
            --enable-decoder=av1 --enable-hwaccel=av1_videotoolbox
            --enable-encoder=h264_videotoolbox
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
cp "$DAV/lib/libdav1d.a" "$OUT/lib/"
cp "$DAV/DAV1D-CONFIG.txt" "$DAV/DAV1D-LICENSE.txt" "$OUT/"
cp "$HERE/ffmpeg-mov-pts.patch" "$HERE/ffmpeg-dovi-padding.patch" "$OUT/"
# The exact configuration goes into THIRD-PARTY-NOTICES (FFmpeg LGPL: say how it was built).
printf 'FFmpeg %s (%s, sha256 %s)\nconfigure %s\n' "$FFMPEG_VERSION" "$SOURCE_URL" "$SOURCE_SHA256" "${FLAGS[*]}" > "$OUT/FFMPEG-CONFIG.txt"
echo "FFmpeg $FFMPEG_VERSION ($TARGET) in $OUT"
