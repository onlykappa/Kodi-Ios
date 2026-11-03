#!/usr/bin/env bash
# Builds the remuxer against a host FFmpeg (build-remux-ffmpeg.sh host DIR) and runs the host tests on generated
# fixtures, from files and over HTTP with Range requests. usage: run_host_tests.sh FFMPEG_HOST_DIR WORK_DIR
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; R="$HERE/.."
FF="$(cd "${1:?host ffmpeg dir}" && pwd)"; WORK="$(mkdir -p "${2:?work dir}" && cd "$2" && pwd)"
[[ -f "$WORK/fixtures/mpeg2_ac3.mkv" ]] || "$HERE/make_fixtures.sh" "$WORK/fixtures" > /dev/null
LIBS=("$FF/lib/libavformat.a" "$FF/lib/libavcodec.a" "$FF/lib/libswscale.a" "$FF/lib/libswresample.a" "$FF/lib/libavutil.a")
EXTRA=(-lm -lpthread -lz)
[[ "$(uname -s)" == Darwin ]] && EXTRA+=(-framework Security -framework CoreFoundation -liconv) || EXTRA+=(-ldl)
cc -std=gnu11 -O1 -g -Wall -Wextra -Wno-format-truncation -Wno-unused-parameter -Wno-sign-compare -I"$FF/include" \
  "$HERE/test_remux.c" "$R"/src/*.c "$R"/gmplayer/*.c "${LIBS[@]}" "${EXTRA[@]}" -o "$WORK/test_remux"
python3 -B "$HERE/range_server.py" "$WORK/fixtures" > "$WORK/port" & SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT
for _ in $(seq 50); do [[ -s "$WORK/port" ]] && break; sleep 0.1; done
"$WORK/test_remux" "$WORK/fixtures" "http://127.0.0.1:$(cat "$WORK/port")"
