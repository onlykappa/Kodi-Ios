#!/usr/bin/env bash
# Builds the remuxer against a host FFmpeg (build-remux-ffmpeg.sh host DIR) and runs the host tests on generated
# fixtures, from files and over HTTP with Range requests. usage: run_host_tests.sh FFMPEG_HOST_DIR WORK_DIR [LIBASS_HOST_DIR]
# r10: LIBASS_HOST_DIR from build-libass.sh host (default: FFMPEG_HOST_DIR/../asshost); KR_TEST_FONT a .ttf (default DejaVu Sans).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; R="$HERE/.."
FF="$(cd "${1:?host ffmpeg dir}" && pwd)"; WORK="$(mkdir -p "${2:?work dir}" && cd "$2" && pwd)"
if [[ ! -f "$WORK/fixtures/mpeg2_ac3.mkv" || ! -f "$WORK/fixtures/vp9_opus.webm" ||
      ! -f "$WORK/fixtures/mpeg4_mp3.avi" || ! -f "$WORK/fixtures/hevc_4k.mkv" || ! -f "$WORK/fixtures/av1_opus.mkv" || ! -f "$WORK/fixtures/h264_10bit.mp4" || ! -f "$WORK/fixtures/h264_pgs.mkv" || ! -f "$WORK/fixtures/prores_pcm.mov" || ! -f "$WORK/fixtures/av1_hdr10.mkv" ]]; then
  "$HERE/make_fixtures.sh" "$WORK/fixtures" > /dev/null
fi
if [[ ! -f "$WORK/fixtures/long.sup" ]]; then
  python3 -B "$HERE/make_pgs.py" "$WORK/fixtures/long.sup" --long
fi
if [[ ! -f "$WORK/fixtures/dvd.idx" || ! -f "$WORK/fixtures/dvd.sub" ]]; then
  python3 -B "$HERE/make_pgs.py" "$WORK/fixtures/dvd.idx" --vobsub
fi
ASS="$(cd "${3:-$FF/../asshost}" && pwd)"
if [[ ! -f "$WORK/fixtures/long-gop.mp4" ]]; then
  ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'testsrc2=size=128x72:rate=24:duration=32' \
    -f lavfi -i 'sine=frequency=440:duration=32' -c:v libx264 -preset ultrafast -g 720 -sc_threshold 0 \
    -c:a aac -b:a 64k -movflags empty_moov+default_base_moof+frag_keyframe -min_frag_duration 30000000 "$WORK/fixtures/long-gop.mp4"
fi
# Match the prepared writer's finite init duration (FFmpeg empty_moov alone leaves these fields zero).
python3 -B - "$WORK/fixtures/long-gop.mp4" <<'PY'
import struct,sys
from pathlib import Path
p=Path(sys.argv[1]);data=bytearray(p.read_bytes())
def walk(start,end):
    at=start
    while at+8<=end:
        size,kind=struct.unpack_from('>I4s',data,at)
        if size<8 or at+size>end:break
        if kind in (b'moov',b'trak',b'mdia'):walk(at+8,at+size)
        if kind in (b'mvhd',b'mdhd') and data[at+8]==0:
            scale=struct.unpack_from('>I',data,at+20)[0]
            struct.pack_into('>I',data,at+24,round(32.023*scale))
        if kind==b'tkhd' and data[at+8]==0:struct.pack_into('>I',data,at+28,32023)
        at+=size
walk(0,len(data));p.write_bytes(data)
PY
if [[ ! -f "$WORK/fixtures/dovi.mkv" ]]; then
  python3 -B "$HERE/make_dovi.py" "$WORK/fixtures/dovi.mkv"
fi
if [[ ! -f "$WORK/fixtures/multi.idx" || ! -f "$WORK/fixtures/multi.sub" ]]; then
  python3 -B "$HERE/make_pgs.py" "$WORK/fixtures/multi.idx" --vobsub --multi
fi
if [[ ! -f "$WORK/fixtures/long_pgs.mkv" ]]; then
  ffmpeg -hide_banner -loglevel error -y -copyts -stream_loop 3 -i "$WORK/fixtures/h264_aac_srt.mkv" -i "$WORK/fixtures/long.sup" \
    -map 0:v -map 0:a -map 1:s -c copy -t 65 -disposition:s:0 default "$WORK/fixtures/long_pgs.mkv"
fi
# r30: a re-encoded HDR picture (AV1 -> HEVC Main10) and audio (AC-3 -> AAC) over two 30-second units, to carry on from.
if [[ ! -f "$WORK/fixtures/resume_av1_hdr.mkv" ]]; then
  ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'testsrc2=size=128x72:rate=4:duration=75' -f lavfi -i 'sine=frequency=440:duration=75' \
    -vf 'format=yuv420p10le,setparams=color_primaries=bt2020:color_trc=smpte2084:colorspace=bt2020nc' -c:v libaom-av1 -cpu-used 8 -crf 30 -row-mt 1 -threads 2 -g 8 \
    -color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc -c:a ac3 -b:a 96k "$WORK/fixtures/resume_av1_hdr.mkv"
fi
# Build 190 end-to-end test (e2e_conversion.py): a 100 MB copy, and a re-encode whose 30 s units span several pieces.
if [[ ! -f "$WORK/fixtures/long_big.mkv" ]]; then
  ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'testsrc2=size=640x360:rate=10:duration=1300' -f lavfi -i 'sine=frequency=440:duration=1300' \
    -c:v libx264 -preset ultrafast -g 20 -b:v 600k -c:a aac -b:a 64k "$WORK/fixtures/long_big.mkv"
fi
# A cue seek far into a large movie must obey the whole-request subtitle deadline.
if [[ ! -f "$WORK/fixtures/long_sub.mkv" ]]; then
  ffmpeg -hide_banner -loglevel error -y -i "$WORK/fixtures/long_big.mkv" -i "$WORK/fixtures/subs.srt" \
    -map 0:v -map 0:a -map 1:s -c copy "$WORK/fixtures/long_sub.mkv"
fi
if [[ ! -f "$WORK/fixtures/resume_av1_hdr_big.mkv" ]]; then
  ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'testsrc2=size=640x360:rate=24:duration=95' -f lavfi -i 'sine=frequency=440:duration=95' \
    -vf 'format=yuv420p10le,setparams=color_primaries=bt2020:color_trc=smpte2084:colorspace=bt2020nc' -c:v libaom-av1 -cpu-used 8 -crf 30 -row-mt 1 -threads 4 -g 24 \
    -color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc -c:a ac3 -b:a 96k "$WORK/fixtures/resume_av1_hdr_big.mkv"
fi
# Long sparse fixture proves an actual twenty-minute MP4 seek without a large test download.
if [[ ! -f "$WORK/fixtures/long_seek.mkv" ]]; then
  ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'testsrc2=size=64x36:rate=1:duration=1300' \
    -an -c:v libx264 -preset ultrafast -g 2 -pix_fmt yuv420p "$WORK/fixtures/long_seek.mkv"
fi
export KR_TEST_FONT="${KR_TEST_FONT:-$(ls /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf /Library/Fonts/Arial.ttf /System/Library/Fonts/Supplemental/Arial.ttf 2>/dev/null | head -1)}"
[[ -f "$KR_TEST_FONT" ]] || { echo "no test font (set KR_TEST_FONT)" >&2; exit 2; }
LIBS=("$ASS/lib/libass.a" "$ASS/lib/libharfbuzz.a" "$ASS/lib/libfribidi.a" "$ASS/lib/libfreetype.a" "$FF/lib/libavformat.a" "$FF/lib/libavcodec.a" "$FF/lib/libdav1d.a" "$FF/lib/libswscale.a" "$FF/lib/libswresample.a" "$FF/lib/libavutil.a")
EXTRA=(-lm -lpthread -lz -lstdc++)
if grep -q -- '--enable-libx265' "$FF/FFMPEG-CONFIG.txt"; then
  read -r -a X265_LIBS <<< "$(pkg-config --libs x265)";EXTRA+=("${X265_LIBS[@]}")
fi
[[ "$(uname -s)" == Darwin ]] && EXTRA+=(-framework Security -framework CoreFoundation -liconv) || EXTRA+=(-ldl)
cc -std=gnu11 -O1 -g -Wall -Wextra -Wno-format-truncation -Wno-unused-parameter -Wno-sign-compare -I"$FF/include" -I"$ASS/include" \
  "$HERE/test_remux.c" "$R"/src/*.c "$R"/gmplayer/*.c "${LIBS[@]}" "${EXTRA[@]}" -o "$WORK/test_remux"
: > "$WORK/port"
python3 -B "$HERE/range_server.py" "$WORK/fixtures" > "$WORK/port" & SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT
for _ in $(seq 50); do [[ -s "$WORK/port" ]] && break; sleep 0.1; done
"$WORK/test_remux" "$WORK/fixtures" "http://127.0.0.1:$(cat "$WORK/port")" "${4:-}"
