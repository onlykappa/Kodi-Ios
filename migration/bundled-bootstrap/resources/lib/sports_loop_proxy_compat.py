"""Version-guarded compatibility patch for Loop's local HLS proxy; no authorization changes."""
import hashlib
from pathlib import Path

MARKER = 'kodi-loop-proxy-compat-v1'
ALIAS = "# kodi-loop-proxy-compat-v1\n# Rig-only candidate inserted after urllib imports, leaving resolver/auth untouched.\n_kodi_quote, _kodi_unquote = quote, unquote\n_kodi_aliases, _kodi_reverse = {}, {}\n_kodi_alias_lock = threading.Lock()\ndef quote(value, safe='/', **kwargs):\n    if safe == '' and isinstance(value, str):\n        with _kodi_alias_lock:\n            if value not in _kodi_reverse:\n                extension = urlparse(value).path.rsplit('.', 1)[-1].lower()\n                if extension not in ('ts','m3u8','mp4','m4s','aac','key','webm'):\n                    extension = 'ts'\n                alias = uuid.uuid4().hex + '.' + extension\n                _kodi_aliases[alias] = value\n                _kodi_reverse[value] = alias\n            return _kodi_reverse[value]\n    return _kodi_quote(value, safe=safe, **kwargs)\ndef unquote(value, **kwargs):\n    with _kodi_alias_lock:\n        if value in _kodi_aliases:\n            return _kodi_aliases[value]\n    return _kodi_unquote(value, **kwargs)\n"
REBASE = '        if "#EXTINF" in child_body:\n            rebased = []\n            for child_line in child_body.splitlines():\n                stripped = child_line.strip()\n                if stripped and not stripped.startswith(\'#\'):\n                    child_line = urljoin(best_variant_url, stripped)\n                elif \'URI=\' in child_line:\n                    child_line = re.sub(r\'URI="([^\\"]+)"\', lambda m: \'URI="\' + urljoin(best_variant_url, m.group(1)) + \'"\', child_line)\n                rebased.append(child_line)\n            child_body = \'\\n\'.join(rebased) + \'\\n\'\n'
# File -> the revisions this patch is known to fit. proxy_server.py changed between older jetextractors builds and 3.3.34 (the Steam Deck's working copy, 2026-11-26,
# byte-identical to migration/addon-preserve/script.module.jetextractors-3.3.34.zip): the same two anchors exist in both, so the same patch applies to either.
EXPECTED = {'proxy_server.py': ('63cd95c9e567e93ef3cd84320f6bba5a9094649aa874992251aa1beed563400d', 'e29d3dcf7ad4a1f3759b3b71d512bbdc2cad624275ef6c39f7f068f5dc8a75b9'),
            'manifest_rewriter.py': ('a68ae3f1ed840be868dab8683c272c60b3ac4f5eb4ea5ffe6da262cc23e4cfb8',)}

def patched(name, data):
    text = data.decode('utf-8')
    if MARKER in text:
        return data
    if hashlib.sha256(data).hexdigest() not in EXPECTED[name]:
        raise ValueError('unsupported Loop proxy revision')
    text = text.replace('\r\n', '\n')
    if name == 'proxy_server.py':
        if text.count('import requests\n') < 1:
            raise ValueError('unsupported Loop proxy revision')
        text = text.replace('import requests\n', ALIAS+'\nimport requests\n', 1)
    else:
        text = text.replace('        if "#EXTINF" in child_body:\n', REBASE, 1)
        text = '# '+MARKER+'\n'+text
    compile(text, name, 'exec')
    return text.encode('utf-8')

def apply(folder):
    folder = Path(folder) / 'lib/jetextractors/util'
    paths = [folder/name for name in EXPECTED]
    changes = [(p, patched(p.name,p.read_bytes())) for p in paths]
    for path,data in changes:
        if path.read_bytes() != data:
            backup=path.with_suffix('.py.kodi-original')
            if not backup.exists():
                backup.write_bytes(path.read_bytes())
            temp=path.with_suffix('.py.kodi-tmp');temp.write_bytes(data);temp.replace(path)
    return True
