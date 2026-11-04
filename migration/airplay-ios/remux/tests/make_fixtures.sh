#!/usr/bin/env bash
# Small generated test files for the remuxer host tests (20 s each, 320x180). Needs an ffmpeg with libx264/libx265
# (Ubuntu's apt ffmpeg). Generated, not committed. Usage: make_fixtures.sh OUT_DIR
set -euo pipefail
OUT="$(mkdir -p "${1:?output dir}" && cd "$1" && pwd)"
F=(ffmpeg -nostdin -hide_banner -loglevel error -y)
V=(-f lavfi -i testsrc2=size=320x180:rate=24:duration=20)
A=(-f lavfi -i sine=frequency=440:sample_rate=48000:duration=20)
A6=(-f lavfi -i "sine=frequency=440:sample_rate=48000:duration=20,aformat=channel_layouts=5.1")
cat > "$OUT/subs.srt" <<'SRT'
1
00:00:01,000 --> 00:00:03,000
Hello from SRT

2
00:00:06,500 --> 00:00:07,500
Second line
SRT
cat > "$OUT/subs.ass" <<'ASS'
[Script Info]
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:02.00,0:00:04.00,Default,,0,0,0,,{\b1}Hello from ASS
ASS
X264=(-c:v libx264 -preset ultrafast -g 48 -keyint_min 48 -sc_threshold 0 -pix_fmt yuv420p)
X265=(-c:v libx265 -preset ultrafast -x265-params keyint=48:min-keyint=48:scenecut=0:log-level=error:colorprim=9:transfer=16:colormatrix=9 -pix_fmt yuv420p10le
      -vf setparams=color_primaries=bt2020:color_trc=smpte2084:colorspace=bt2020nc
      -color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc)
"${F[@]}" "${V[@]}" "${A[@]}" -i "$OUT/subs.srt" -map 0 -map 1 -map 2 "${X264[@]}" -c:a aac -c:s srt \
  -metadata:s:a:0 language=eng -metadata:s:s:0 language=eng "$OUT/h264_aac_srt.mkv"
"${F[@]}" "${V[@]}" "${A6[@]}" -i "$OUT/subs.ass" -map 0 -map 1 -map 2 "${X265[@]}" -c:a ac3 -c:s ass "$OUT/hevc_ac3_ass.mkv"
"${F[@]}" "${V[@]}" "${A6[@]}" -map 0 -map 1 "${X264[@]}" -c:a dca -strict -2 -metadata:s:a:0 title="DTS 5.1" "$OUT/h264_dts.mkv"
"${F[@]}" "${V[@]}" "${A[@]}" -map 0 -map 1 "${X264[@]}" -c:a truehd -strict -2 "$OUT/h264_truehd.mkv"
# Two audio tracks: AC-3 (copied) and DTS (bridged to AAC), plus a text subtitle.
"${F[@]}" "${V[@]}" "${A6[@]}" "${A6[@]}" -i "$OUT/subs.srt" -map 0 -map 1 -map 2 -map 3 "${X264[@]}" -c:a:0 ac3 \
  -c:a:1 dca -strict -2 -c:s srt "$OUT/h264_ac3_dts_srt.mkv"
"${F[@]}" "${V[@]}" "${A[@]}" -map 0 -map 1 "${X264[@]}" -c:a aac "$OUT/h264_aac.mp4"
"${F[@]}" "${V[@]}" "${A[@]}" -map 0 -map 1 "${X264[@]}" -c:a ac3 -f mpegts "$OUT/h264_ac3.ts"
# r7: MPEG-2 video (not an AirPlay codec: the remuxer converts the picture by itself).
"${F[@]}" "${V[@]}" "${A[@]}" -map 0 -map 1 -c:v mpeg2video -g 48 -bf 0 -q:v 4 -c:a ac3 "$OUT/mpeg2_ac3.mkv"
# Container/codec coverage and a real 3840x2160 input. The 4K clip is deliberately 6 fps to keep host CI bounded;
# it verifies actual scaling/seeks/timestamps, not phone throughput or VideoToolbox/H.264 output.
"${F[@]}" "${V[@]}" "${A[@]}" -c:v libvpx-vp9 -deadline realtime -cpu-used 8 -g 48 -c:a libopus "$OUT/vp9_opus.webm"
"${F[@]}" "${V[@]}" "${A[@]}" -c:v mpeg4 -g 48 -bf 0 -q:v 4 -c:a libmp3lame "$OUT/mpeg4_mp3.avi"
"${F[@]}" -f lavfi -i testsrc2=size=3840x2160:rate=6:duration=20 -an \
  -c:v libx265 -preset ultrafast -x265-params keyint=12:min-keyint=12:scenecut=0:log-level=error:pools=2 \
  -pix_fmt yuv420p10le "$OUT/hevc_4k.mkv"
ls -l "$OUT"
