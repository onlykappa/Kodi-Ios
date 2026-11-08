"""Desktop Kodi 21.3 rig for checking the portrait pages against the approved mockups (any agent, any Linux box).

Evidence class: **desktop Kodi rig** (APPLE-UI-POLICY §7/§9). It shows real Kodi layout, text fit and the window
logic; it is not the iPhone (no touch, safe areas, SF font, native tab bar or AirPlay). Guide: docs/design/KODI-RIG.md.

Everything it makes lives in KODI_RIG_HOME (default ~/.cache/kodi-rig), never in the repository: the Kodi source and
build, the add-ons taken from a release IPA, the Kodi profile, screenshots and side-by-sides (they show film artwork).

  kodi_rig.py setup [--release build-192]   install packages, build Kodi 21.3 (x11), fetch add-ons + Fuse from the IPA
  kodi_rig.py prepare                        fresh rig profile with this checkout's add-on and portrait folder
  kodi_rig.py start | stop | restart         Xvfb :5 at 603x1167 (the iPhone safe area at 1.5x) + Kodi, JSON-RPC :8089
  kodi_rig.py sync                           copy this checkout's add-on into the running rig, regenerate the pages
  kodi_rig.py scenario NAME [--seconds N]    write a status scenario (kodi_rig_scenarios.SCENARIOS), N s in background
  kodi_rig.py open PAGE [ARGS...]            RunScript(service.kodi.ios.bootstrap,PAGE,ARGS): library_status,
                                             notifications, transfers, tool_pages queue, tool_pages history, ...
  kodi_rig.py click ID | builtin TEXT        SendClick(ID) / any Kodi builtin, run inside Kodi
  kodi_rig.py shot NAME                      screenshot -> KODI_RIG_HOME/shots/NAME.png
  kodi_rig.py mockups                        each approved board -> KODI_RIG_HOME/mockup/boardN.png (Playwright)
  kodi_rig.py side MOCKUP RIG OUT            labelled side-by-side: mockup | desktop Kodi rig
  kodi_rig.py boards [N ...]                 render boards 1-9 with their scenarios and write the side-by-sides
  kodi_rig.py rpc METHOD [JSON]              one JSON-RPC call
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
BOOT = REPO / 'migration/bundled-bootstrap'
MOCKUPS = REPO / 'docs/design/library-status-mockups-r1.html'
RIG = Path(os.environ.get('KODI_RIG_HOME', Path.home() / '.cache/kodi-rig')).expanduser()
SRC, BUILD, MIRROR = RIG / 'kodi-src', RIG / 'kodi-build', RIG / 'kodi-mirror'
ADDONS, FUSE, HOME = RIG / 'addons', RIG / 'fuse-skin', RIG / 'home'
PROFILE = HOME / '.kodi/userdata'
SHOTS, SIDE, MOCK = RIG / 'shots', RIG / 'side', RIG / 'mockup'
BUILTINS = RIG / 'builtins.txt'
DISPLAY, SIZE, RPC = ':5', '603x1167', 'http://127.0.0.1:8089/jsonrpc'
BOOT_ID, FUSE_ID = 'service.kodi.ios.bootstrap', 'skin.arctic.fuse.3'
REPO_URL = 'https://github.com/onlykappa/Kodi-Ios'
KODI_TAG = '21.3-Omega'

# Debian/Ubuntu packages for a Kodi 21.3 x11 build plus the rig's tools (Xvfb, ImageMagick).
PACKAGES = '''cmake nasm autoconf automake libtool gettext autopoint gperf swig default-jre-headless git curl unzip
 libasound2-dev libass-dev libavahi-client-dev libbluray-dev libcap-dev libcdio-dev libcdio++-dev libcec-dev
 libcurl4-openssl-dev libdrm-dev libdvdnav-dev libdvdread-dev libegl1-mesa-dev libfmt-dev libfontconfig-dev
 libfreetype-dev libfribidi-dev libfstrcmp-dev libgif-dev libgl-dev libglu1-mesa-dev libgnutls28-dev libgpg-error-dev
 libgtest-dev libiso9660-dev libjpeg-dev liblcms2-dev libltdl-dev liblzo2-dev libmicrohttpd-dev libnfs-dev
 libpcre2-dev libpcre3-dev libplist-dev libpng-dev libpulse-dev libpython3-dev libshairplay-dev libsmbclient-dev
 libspdlog-dev libsqlite3-dev libssl-dev libtag1-dev libtinyxml-dev libtinyxml2-dev libudev-dev libunistring-dev
 libva-dev libvdpau-dev libxkbcommon-dev libxml2-dev libxrandr-dev libxslt1-dev libxt-dev rapidjson-dev uuid-dev
 zlib1g-dev libflatbuffers-dev flatbuffers-compiler libdav1d-dev libexiv2-dev libxmu-dev libxi-dev libinput-dev
 libgbm-dev libmariadb-dev libcrossguid-dev libdisplay-info-dev libavcodec-dev libavformat-dev libavfilter-dev
 libswscale-dev libswresample-dev libpostproc-dev libavutil-dev libsndio-dev libpipewire-0.3-dev
 xvfb xdotool imagemagick mesa-utils libgl1-mesa-dri'''.split()

CMAKE_FLAGS = ['-DCMAKE_BUILD_TYPE=Release', '-DCORE_PLATFORM_NAME=x11', '-DAPP_RENDER_SYSTEM=gl',
               '-DENABLE_INTERNAL_FLATBUFFERS=OFF', '-DENABLE_INTERNAL_RapidJSON=OFF', '-DENABLE_INTERNAL_CROSSGUID=OFF',
               '-DENABLE_AIRTUNES=OFF', '-DENABLE_UPNP=OFF', '-DENABLE_CEC=OFF', '-DENABLE_BLURAY=OFF', '-DENABLE_DVDCSS=OFF',
               '-DENABLE_OPTICAL=OFF', '-DENABLE_LIRCCLIENT=OFF', '-DENABLE_PULSEAUDIO=OFF', '-DENABLE_ALSA=ON',
               '-DENABLE_VAAPI=OFF', '-DENABLE_VDPAU=OFF', '-DENABLE_TESTING=OFF', '-DENABLE_EVENTCLIENTS=OFF',
               '-DENABLE_PLIST=OFF', '-DENABLE_SMBCLIENT=OFF', '-DENABLE_NFS=OFF', '-DENABLE_MARIADBCLIENT=OFF',
               '-DENABLE_MYSQLCLIENT=OFF']

# Kodi's build downloads these from mirrors.kodi.tv, which some sandboxes block; archive.apache.org has the same
# files (Kodi's cmake checks their hashes), served to it through -DKODI_MIRROR=file://...
APACHE = ['https://archive.apache.org/dist/groovy/4.0.26/distribution/apache-groovy-binary-4.0.26.zip',
          'https://archive.apache.org/dist/commons/lang/binaries/commons-lang3-3.17.0-bin.tar.gz',
          'https://archive.apache.org/dist/commons/text/binaries/commons-text-1.13.0-bin.tar.gz']
# libdvd* come as GitHub archive tarballs, which some proxies refuse; the rig makes them from git tags instead and
# points the (scratch) Kodi checkout's VERSION files at their hashes. Only the rig's own Kodi copy is changed.
DVD = {'libdvdread': '6.1.3-Next-Nexus-Alpha2-2', 'libdvdnav': '6.1.1-Next-Nexus-Alpha2-2', 'libdvdcss': '1.4.3-Next-Nexus-Alpha2-2'}

# Approved boards: (scenario, page to open, control to click after it opens or None). Board 6 is the bell over Home.
BOARDS = {1: ('running', ['library_status'], None), 2: ('airplay', ['library_status'], None),
          3: ('running', ['library_status'], 9005), 4: ('running', ['transfers'], None),
          5: ('airplay', ['notifications'], None), 6: ('running', None, None),
          7: ('running', ['tool_pages', 'queue'], None), 8: ('running', ['tool_pages', 'history'], None),
          9: ('airplay', ['library_status'], 9470)}


def sh(cmd, **kw):
    print('+', cmd if isinstance(cmd, str) else ' '.join(map(str, cmd)), flush=True)
    return subprocess.run(cmd, shell=isinstance(cmd, str), check=True, **kw)


def wait(seconds):
    time.sleep(seconds)


def fetch(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size:
        return dest
    # Large files (the IPA is ~200 MB) can be cut off by a proxy: resume where the last try stopped.
    for attempt in range(6):
        result = subprocess.run(['curl', '-sSfL', '--retry', '3', '-C', '-', '-o', str(dest) + '.part', url])
        if result.returncode == 0:
            os.replace(str(dest) + '.part', dest)
            return dest
        print('download stopped (curl %d), resuming' % result.returncode, flush=True)
        time.sleep(2 ** attempt)
    raise SystemExit('could not download ' + url)


# --- setup ---------------------------------------------------------------------------------------------------------

def install_packages():
    if shutil.which('apt-get') is None:
        print('no apt-get: install the PACKAGES listed in scripts/kodi_rig.py by hand')
        return
    sudo = [] if os.geteuid() == 0 else ['sudo']
    env = dict(os.environ, DEBIAN_FRONTEND='noninteractive')
    subprocess.run(sudo + ['apt-get', 'update', '-qq'], env=env)
    sh(sudo + ['apt-get', 'install', '-y', '-qq', '--no-install-recommends'] + PACKAGES, env=env)


def build_kodi():
    if (BUILD / 'kodi-x11').exists():
        print('Kodi already built:', BUILD / 'kodi-x11')
        return
    if not (SRC / 'CMakeLists.txt').exists():
        shutil.rmtree(SRC, ignore_errors=True)
        sh(['git', 'clone', '-q', '--depth', '1', '--branch', KODI_TAG, 'https://github.com/xbmc/xbmc.git', str(SRC)])
    sources = MIRROR / 'build-deps/sources'
    for url in APACHE:
        fetch(url, sources / url.rsplit('/', 1)[1])
    download = BUILD / 'build/download'
    download.mkdir(parents=True, exist_ok=True)
    work = RIG / 'dvdgit'
    for name, tag in DVD.items():
        folder = '%s-%s' % (name, tag)
        tarball = download / (folder + '.tar.gz')
        if not tarball.exists():
            shutil.rmtree(work / folder, ignore_errors=True)
            sh(['git', 'clone', '-q', '--depth', '1', '--branch', tag, 'https://github.com/xbmc/%s.git' % name, str(work / folder)])
            sh(['tar', '-czf', str(tarball), '-C', str(work), folder])
        digest = subprocess.run(['sha512sum', str(tarball)], capture_output=True, text=True, check=True).stdout.split()[0]
        version = SRC / 'tools/depends/target' / name / (name.upper() + '-VERSION')
        lines = [('SHA512=' + digest) if line.startswith('SHA512=') else line for line in version.read_text().splitlines()]
        version.write_text('\n'.join(lines) + '\n')
    sh(['cmake', '-S', str(SRC), '-B', str(BUILD), '-DKODI_MIRROR=file://' + str(MIRROR)] + CMAKE_FLAGS)
    sh(['cmake', '--build', str(BUILD), '-j', str(os.cpu_count() or 4)])


def release_ipa(tag):
    """The IPA asset of a release (the add-ons and Fuse skin the phone app ships)."""
    api = 'https://api.github.com/repos/onlykappa/Kodi-Ios/releases/tags/' + tag
    try:
        with urllib.request.urlopen(api, timeout=30) as r:
            assets = [a['browser_download_url'] for a in json.load(r).get('assets', []) if a['name'].endswith('.ipa')]
        if assets:
            return assets[0]
    except Exception as error:
        print('release lookup failed (%s); trying the usual asset name' % error)
    return '%s/releases/download/%s/Kodi-iOS-Customized-Touch-r10.ipa' % (REPO_URL, tag)


def fetch_addons(tag):
    """Pure-Python add-ons and the patched Fuse skin from the release IPA (native libraries are left out; the rig's
    bootstrap add-on always comes from this checkout)."""
    ipa = fetch(release_ipa(tag), RIG / 'ipa' / (tag + '.ipa'))
    root = 'Payload/Kodi.app/AppData/AppHome/addons/'
    shutil.rmtree(ADDONS, ignore_errors=True)
    shutil.rmtree(FUSE, ignore_errors=True)
    native = ('.dylib', '.so', '.framework/')
    with zipfile.ZipFile(ipa) as z:
        names = [n for n in z.namelist() if n.startswith(root)]
        skip = {n[len(root):].split('/')[0] for n in names if any(x in n for x in native)}
        for n in names:
            rel = n[len(root):]
            top = rel.split('/')[0]
            if not rel or n.endswith('/') or top in skip or top == BOOT_ID:
                continue
            dest = (FUSE / rel.split('/', 1)[1]) if top == FUSE_ID else ADDONS / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(n) as src, open(dest, 'wb') as out:
                shutil.copyfileobj(src, out)
    print('add-ons from', tag, ':', len(list(ADDONS.iterdir())), 'plus', FUSE_ID)


def setup(args):
    RIG.mkdir(parents=True, exist_ok=True)
    if not args.skip_packages:
        install_packages()
    build_kodi()
    fetch_addons(args.release)
    prepare(None)
    print('rig ready in', RIG, '- next: kodi_rig.py start')


# --- rig -----------------------------------------------------------------------------------------------------------

def bootstrap_copy(dest):
    """This checkout's bootstrap add-on as the rig runs it: its service off (the scenarios own the status files), and
    a rig-only entry that runs the builtins in KODI_RIG_HOME/builtins.txt (RunScript arguments lose commas)."""
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(BOOT, dest, ignore=shutil.ignore_patterns('__pycache__'))
    xml = (dest / 'addon.xml').read_text()
    (dest / 'addon.xml').write_text(xml.replace('<extension point="xbmc.service" library="service.py"/>', ''))
    (dest / 'rig_builtin.py').write_text('import xbmc\nfor line in open(%r).read().splitlines():\n'
                                         ' line.strip() and xbmc.executebuiltin(line.strip())\n' % str(BUILTINS))
    default = (dest / 'default.py').read_text()
    assert "'recover')" in default, 'default.py PAGES changed: update kodi_rig.bootstrap_copy'
    (dest / 'default.py').write_text(default.replace("'recover')", "'rig_builtin','transfers','recover')", 1))


def portrait_rig():
    spec = importlib.util.spec_from_file_location('portrait_rig', REPO / 'scripts/portrait_rig.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(_args):
    if not FUSE.exists():
        raise SystemExit('no add-ons yet: run kodi_rig.py setup first')
    bootstrap_copy(ADDONS / BOOT_ID)
    HOME.mkdir(parents=True, exist_ok=True)
    portrait_rig().prepare(ADDONS, FUSE, HOME)
    print('prepared', HOME)


def sync(_args):
    """This checkout's add-on and regenerated portrait folder into the running rig (no restart needed: Kodi reads a
    window's XML each time it opens)."""
    boot = HOME / '.kodi/addons' / BOOT_ID
    for f in BOOT.rglob('*'):
        if f.is_file() and '__pycache__' not in f.parts and f.name not in ('addon.xml', 'default.py'):
            dst = boot / f.relative_to(BOOT)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
    spec = importlib.util.spec_from_file_location('portrait_sync', BOOT / 'resources/lib/portrait.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    skin = HOME / '.kodi/addons' / FUSE_ID
    files = module.portrait_files(skin, PROFILE)
    module.write(skin, files)
    for path in skin.rglob('*.xml'):
        data = path.read_text(errors='replace')
        if 'System.Platform.IOS' in data:
            path.write_text(data.replace('System.Platform.IOS', 'true'))
    print('synced', len(files), 'portrait files')


def rpc(method, params=None):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}}).encode()
    request = urllib.request.Request(RPC, body, {'Content-Type': 'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=10) as r:
        return json.loads(r.read())


def start(_args):
    if not (BUILD / 'kodi-x11').exists():
        raise SystemExit('no Kodi build: run kodi_rig.py setup first')
    env = dict(os.environ, DISPLAY=DISPLAY, HOME=str(HOME), KODI_HOME=str(BUILD), LIBGL_ALWAYS_SOFTWARE='1')
    for k in ('HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy'):
        env.pop(k, None)
    subprocess.Popen(['Xvfb', DISPLAY, '-screen', '0', SIZE + 'x24', '-nolisten', 'tcp'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    wait(1.5)
    subprocess.Popen([str(BUILD / 'kodi-x11'), '--standalone', '-fs'], env=env, stdout=open(RIG / 'kodi-stdout.log', 'w'),
                     stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(120):
        try:
            rpc('JSONRPC.Ping')
            break
        except Exception:
            wait(1)
    else:
        raise SystemExit('Kodi did not answer JSON-RPC; see %s and %s' % (RIG / 'kodi-stdout.log', HOME / '.kodi/temp/kodi.log'))
    # A fresh profile asks before enabling add-ons it finds on disk and falls back to Estuary; the rig enables them
    # over JSON-RPC, and on that first run writes the profile again and restarts so Kodi opens with Fuse.
    for addon in [p.name for p in ADDONS.iterdir()] + [FUSE_ID]:
        try:
            rpc('Addons.SetAddonEnabled', {'addonid': addon, 'enabled': True})
        except Exception:
            pass
    marker = HOME / '.rig-addons-enabled'
    if not marker.exists():
        if getattr(_args, 'retried', False):
            raise SystemExit('Kodi did not keep the add-ons enabled; see %s' % (HOME / '.kodi/temp/kodi.log'))
        print('first start of this profile: add-ons enabled, restarting with', FUSE_ID, flush=True)
        wait(3)
        stop(_args)
        prepare(_args)
        marker.write_text('add-ons enabled over JSON-RPC\n')
        return start(argparse.Namespace(retried=True))
    print('started: DISPLAY', DISPLAY, SIZE)


def _gone(pattern, seconds=10):
    """Wait until no process matches; then force it. A new Kodi attached to a Xvfb that is still shutting down dies
    with it, so start() must never race the previous stop()."""
    for _ in range(seconds * 2):
        if subprocess.call(['pgrep', '-f', pattern], stdout=subprocess.DEVNULL) != 0:
            return
        wait(0.5)
    subprocess.call(['pkill', '-9', '-f', pattern])
    wait(1)


def stop(_args):
    subprocess.call(['pkill', '-f', 'kodi_rig_scenarios.py'])
    subprocess.call(['pkill', '-f', str(BUILD / 'kodi-x11')])
    _gone(str(BUILD / 'kodi-x11'))
    subprocess.call(['pkill', '-f', 'Xvfb ' + DISPLAY])
    _gone('Xvfb ' + DISPLAY)
    for lock in (Path('/tmp/.X%s-lock' % DISPLAY[1:]), Path('/tmp/.X11-unix/X%s' % DISPLAY[1:])):
        try:
            lock.unlink()
        except OSError:
            pass


def restart(args):
    stop(args)
    start(args)


def run_builtins(*lines):
    BUILTINS.write_text('\n'.join(lines) + '\n')
    rpc('Addons.ExecuteAddon', {'addonid': BOOT_ID, 'params': ['rig_builtin'], 'wait': False})
    wait(1.5)


def open_page(args, settle=7):
    run_builtins('Dialog.Close(all,true)')
    print(rpc('Addons.ExecuteAddon', {'addonid': BOOT_ID, 'params': list(args.page), 'wait': False}))
    wait(settle)


def scenario(args):
    """Write the scenario now; with --seconds keep it fresh in the background (stale after 6 s otherwise)."""
    subprocess.call(['pkill', '-f', 'kodi_rig_scenarios.py'])
    cmd = [sys.executable, '-B', str(REPO / 'scripts/kodi_rig_scenarios.py'), str(PROFILE), args.name]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    if args.seconds:
        subprocess.Popen(cmd + [str(args.seconds)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return json.loads(out)


def shot(name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    out = SHOTS / (name + '.png')
    sh(['import', '-display', DISPLAY, '-window', 'root', str(out)])
    return out


MEASURE_JS = r'''
const {chromium} = require('playwright');
(async () => {
  const [page, out] = process.argv.slice(1);
  const b = await chromium.launch();
  const p = await b.newPage({viewport: {width: 1300, height: 1000}, deviceScaleFactor: 1.5});
  await p.goto('file://' + page);
  await p.waitForTimeout(1500);
  let i = 1;
  for (const f of await p.$$('figure.board')) {
    await (await f.$('.phone')).screenshot({path: out + '/board' + i + '.png'});
    i++;
  }
  await b.close();
})();
'''


def mockups(_args=None):
    """Each approved board at 1.5x (the rig's scale), cropped later to the safe area by `side`."""
    MOCK.mkdir(parents=True, exist_ok=True)
    sh(['node', '-e', MEASURE_JS, str(MOCKUPS), str(MOCK)])


def side(mockup, rig, out, top=88):
    """mockup (status bar cropped to the safe area) | desktop Kodi rig, each labelled with its evidence class."""
    from PIL import Image, ImageDraw
    a = Image.open(mockup).convert('RGB')
    a = a.crop((0, top, 603, top + 1167))
    b = Image.open(rig).convert('RGB')
    w, h = 603 * 2 + 10, max(a.height, b.height) + 40
    canvas = Image.new('RGB', (w, h), (34, 34, 34))
    canvas.paste(a, (0, 40))
    canvas.paste(b, (613, 40))
    draw = ImageDraw.Draw(canvas)
    try:
        from PIL import ImageFont
        font = ImageFont.load_default(size=22)
    except Exception:
        font = None
    for x, label in ((0, 'mockup'), (613, 'desktop Kodi rig')):
        width = draw.textlength(label, font=font)
        draw.text((x + (603 - width) / 2, 8), label, fill=(255, 255, 255), font=font)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    return out


def boards(args):
    """Render the approved boards with their scenarios and write mockup | rig side-by-sides to KODI_RIG_HOME/side."""
    if not (MOCK / 'board1.png').exists():
        mockups()
    sync(args)
    made = []
    for n in args.numbers or sorted(BOARDS):
        name, page, click = BOARDS[n]
        state = scenario(argparse.Namespace(name=name, seconds=120))
        wait(2)
        if page is None:      # board 6: the bell on Home with the model's properties
            run_builtins('Dialog.Close(all,true)', *[('SetProperty(%s,%s,home)' % (k, v)) if v else 'ClearProperty(%s,home)' % k
                                                    for k, v in state['bell'].items()])
            wait(3)
        else:
            open_page(argparse.Namespace(page=page))
            if click:
                run_builtins('SendClick(%d)' % click)
                wait(6)
        made.append(side(MOCK / ('board%d.png' % n), shot('board%d' % n), SIDE / ('board%d.png' % n)))
    run_builtins('Dialog.Close(all,true)')
    subprocess.call(['pkill', '-f', 'kodi_rig_scenarios.py'])
    print('\n'.join(map(str, made)))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('setup')
    s.add_argument('--release', default='build-192', help='release whose IPA supplies the add-ons and Fuse skin')
    s.add_argument('--skip-packages', action='store_true')
    for name in ('prepare', 'start', 'stop', 'restart', 'sync', 'mockups'):
        sub.add_parser(name)
    s = sub.add_parser('scenario')
    s.add_argument('name')
    s.add_argument('--seconds', type=float, default=0)
    s = sub.add_parser('open')
    s.add_argument('page', nargs='+')
    sub.add_parser('click').add_argument('id', type=int)
    sub.add_parser('builtin').add_argument('text')
    sub.add_parser('shot').add_argument('name')
    s = sub.add_parser('side')
    for name in ('mockup', 'rig', 'out'):
        s.add_argument(name)
    sub.add_parser('boards').add_argument('numbers', nargs='*', type=int)
    s = sub.add_parser('rpc')
    s.add_argument('method')
    s.add_argument('params', nargs='?', default='{}')
    a = p.parse_args()
    if a.cmd == 'setup':
        setup(a)
    elif a.cmd in ('prepare', 'start', 'stop', 'restart', 'sync', 'mockups'):
        globals()[a.cmd](a)
    elif a.cmd == 'scenario':
        print(json.dumps(scenario(a)))
    elif a.cmd == 'open':
        open_page(a, settle=0)
    elif a.cmd == 'click':
        run_builtins('SendClick(%d)' % a.id)
    elif a.cmd == 'builtin':
        run_builtins(a.text)
    elif a.cmd == 'shot':
        print(shot(a.name))
    elif a.cmd == 'side':
        print(side(a.mockup, a.rig, a.out))
    elif a.cmd == 'boards':
        boards(a)
    elif a.cmd == 'rpc':
        print(json.dumps(rpc(a.method, json.loads(a.params)))[:4000])


if __name__ == '__main__':
    main()
