"""r48 host test: upscaled copies through the real converter (built for this computer) and the add-on's Native wrapper.

The AI engine exists only on the iPhone (kr_upscale.m); here the stub says so and the Lanczos engine (named "not AI")
exercises everything else: the box fitted to the picture, HEVC out, every audio and subtitle track kept, the copy's
tag, HDR refused, a picture that already fills the box refused, the setting used once, cancel mid-copy, the phone
state JSON. usage: upscale_host.py LIBKODIAIRPLAY.so WORK_DIR   (exit code = failures)"""
import ctypes, json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import driveupload, picture, prepare_downloads as prep  # noqa: E402

failures = []


def check(ok, what):
    print(('PASS ' if ok else 'FAIL ') + what, flush=True)
    if not ok:
        failures.append(what)


def ffmpeg(*args):
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *args], check=True)


def fixtures(work):
    work.mkdir(parents=True, exist_ok=True)
    srt = work / 'subs.srt'
    srt.write_text('1\n00:00:01,000 --> 00:00:03,000\nHello\n\n2\n00:00:05,000 --> 00:00:08,000\nAgain\n')
    sdr = work / 'sdr_640x360.mp4'
    if not sdr.exists():
        # A prepared download: H.264, two AAC tracks (English and Japanese), mov_text subtitles in two languages.
        ffmpeg('-f', 'lavfi', '-i', 'testsrc2=size=640x360:rate=24:duration=12', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=12',
               '-f', 'lavfi', '-i', 'sine=frequency=660:duration=12', '-i', str(srt), '-i', str(srt),
               '-map', '0:v', '-map', '1:a', '-map', '2:a', '-map', '3:s', '-map', '4:s', '-c:v', 'libx264', '-preset', 'ultrafast',
               '-g', '48', '-c:a', 'aac', '-b:a', '64k', '-c:s', 'mov_text', '-metadata:s:a:0', 'language=eng', '-metadata:s:a:1', 'language=jpn',
               '-metadata:s:s:0', 'language=eng', '-metadata:s:s:1', 'language=spa', '-metadata', 'kodi_airplay_prepared=source-resolution-v1',
               '-movflags', '+faststart+use_metadata_tags', str(sdr))
    hdr = work / 'hdr_640x360.mp4'
    if not hdr.exists():
        ffmpeg('-f', 'lavfi', '-i', 'testsrc2=size=640x360:rate=24:duration=3', '-f', 'lavfi', '-i', 'sine=duration=3',
               '-c:v', 'libx265', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p10le', '-x265-params', 'log-level=error',
               '-color_primaries', 'bt2020', '-color_trc', 'smpte2084', '-colorspace', 'bt2020nc', '-tag:v', 'hvc1',
               '-c:a', 'aac', str(hdr))
    return sdr, hdr


class FileSink:
    def __init__(self, path):
        self.path = path
        self.files = {}
        self.sent = 0

    def write(self, track, suffix, data):
        if track not in self.files:
            self.files[track] = open(str(self.path) + ('' if track == 0 else suffix), 'wb')
        self.files[track].write(data)
        self.sent += len(data)

    def close(self):
        for f in self.files.values():
            f.close()


def convert(native, source, out, upscale, stop_after=None):
    sink = FileSink(out)
    calls = [0]

    def going():
        calls[0] += 1
        return stop_after is None or calls[0] < stop_after
    try:
        native.convert_to(str(source), sink, going, lambda *a: None, upscale=upscale)
        return None
    except driveupload.Stop as stop:
        return 'stopped: %s' % stop
    except RuntimeError as error:
        return str(error)
    finally:
        sink.close()


def streams(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def main():
    lib = ctypes.CDLL(sys.argv[1])
    work = Path(sys.argv[2])
    sdr, hdr = fixtures(work)
    lib.kr_video_set_hdr_encoder(b'libx265')   # host: libx265 stands in for Apple's HEVC encoder (as the HDR host tests do)
    native = prep.Native(lib)
    check(native.upscales and native.reads_device, 'r48 exports present (prepare_upscale, upscale_support, upscale_model, device_state)')
    native.set_audio_languages('eng')
    native.set_subtitle_languages('eng')

    support = native.upscale_support(640, 360, '720p')
    check(support.get('engine') == 'none' and support.get('model') == 'none', 'host build: no AI engine, said plainly: %s' % support)
    check(native.upscale_support(1920, 1080, '1080p').get('why') == 'already this size', 'support: a picture that fills the box is refused')
    check(native.upscale_model(640, 360, '720p') == -1, 'host build: no model to download')
    state = native.device_state()
    check(set(state) >= {'battery', 'charging', 'thermal', 'low_power'}, 'device state JSON: %s' % state)

    # AI asked for on a computer: refused with a reason, nothing pretends to be AI.
    error = convert(native, sdr, work / 'ai.mp4', (1280, 720, 0, 0))
    check(error and 'not available' in error, 'AI engine on the host fails honestly: %s' % error)

    # Lanczos 640x360 -> 720p box: 1280x720 HEVC, both audio tracks and both subtitle tracks kept (the language filter
    # is for ordinary preparation, not for a copy of a prepared file), and the copy says what it is.
    out = work / 'up.mp4'
    error = convert(native, sdr, out, (1280, 720, 1, 0))
    check(error is None, 'Lanczos upscaled copy made (%s)' % error)
    info = streams(out)
    video = [s for s in info['streams'] if s['codec_type'] == 'video']
    audio = [s for s in info['streams'] if s['codec_type'] == 'audio']
    subs = [s for s in info['streams'] if s['codec_type'] == 'subtitle']
    check(video and (video[0]['width'], video[0]['height']) == (1280, 720), 'copy is 1280x720: %s' % [(v['width'], v['height']) for v in video])
    check(video and video[0]['codec_name'] == 'hevc', 'copy is HEVC: %s' % [v['codec_name'] for v in video])
    check(len(audio) == 2 and [a['codec_name'] for a in audio] == ['aac', 'aac'], 'both audio tracks copied: %s' % [(a['codec_name'], a.get('tags', {}).get('language')) for a in audio])
    check(len(subs) == 2, 'both subtitle tracks kept: %s' % [s.get('tags', {}).get('language') for s in subs])
    check(abs(float(info['format']['duration']) - 12) < 0.5, 'duration kept: %s' % info['format']['duration'])
    probe = native.probe(str(out))
    check(probe.get('upscaled', '').startswith('1280x720'), 'probe reads the copy tag: %r' % probe.get('upscaled'))
    check(probe.get('audio_tracks') == 2 and probe.get('subtitle_tracks') == 2, 'probe counts tracks: %s/%s' % (probe.get('audio_tracks'), probe.get('subtitle_tracks')))
    check(abs(probe.get('fps', 0) - 24) < 0.1, 'probe frame rate: %s' % probe.get('fps'))
    source_probe = native.probe(str(sdr))
    check(source_probe.get('upscaled') == '', 'an ordinary file has no copy tag')

    # A 1080p box for a 640x360 picture: 1920x1080; a scope picture keeps its shape.
    check(picture.fitted(1920, 800, '4K UHD') == (3840, 1600), 'scope picture fitted in the 4K box: %s' % (picture.fitted(1920, 800, '4K UHD'),))

    # The language filters come back after the copy (the next ordinary preparation keeps English only).
    check(native.audio_languages == 'eng' and native.subtitle_languages == 'eng', 'language filters restored after the copy')

    # The setting is used once: the next conversion with no upscale is an ordinary one (H.264 copied, 640x360).
    plain = work / 'plain.mp4'
    error = convert(native, sdr, plain, None)
    info = streams(plain)
    video = [s for s in info['streams'] if s['codec_type'] == 'video']
    check(error is None and video and (video[0]['width'], video[0]['height'], video[0]['codec_name']) == (640, 360, 'h264'),
          'the next conversion is ordinary again: %s %s' % (error, [(v['width'], v['height'], v['codec_name']) for v in video]))

    # HDR is refused, the original kept as it is.
    error = convert(native, hdr, work / 'hdr_up.mp4', (1280, 720, 1, 0))
    check(error and 'HDR' in error, 'HDR source refused: %s' % error)
    # A picture that already fills the box is refused, not copied.
    error = convert(native, sdr, work / 'same.mp4', (640, 360, 1, 0))
    check(error and 'already this size' in error, 'same size refused: %s' % error)
    # Cancel mid-copy: the converter stops (Stop) and the next one works.
    error = convert(native, sdr, work / 'cancel.mp4', (1280, 720, 1, 0), stop_after=2)
    check(error and error.startswith('stopped'), 'cancel mid-copy stops: %s' % error)
    error = convert(native, sdr, work / 'after_cancel.mp4', (1280, 720, 1, 0))
    check(error is None, 'a copy after a cancelled one works: %s' % error)
    print('%d failure(s)' % len(failures))
    return len(failures)


if __name__ == '__main__':
    sys.exit(main())
