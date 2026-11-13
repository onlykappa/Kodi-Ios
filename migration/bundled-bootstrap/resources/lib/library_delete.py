"""Library file manager L6 (DEC-043 board D): select several videos, see the space you get back, confirm, delete.

Pure logic plus one runner with the Drive call passed in, so host tests drive it. Items are dicts:
  {'id': Drive file id, 'title', 'line' (grey second line), 'size': bytes, 'ai': {'copy_id', 'size'} or None}
Deleting sends each file to Google Drive's Trash (30 days, as long press › Remove does: drivelibrary.trash), never a
permanent delete; an AI Upscale copy goes too only when the owner ticks it in the alert.
"""
import os

import library_files as lf


def totals(items, picked, with_ai=False):
    """(how many, bytes freed) for the picked ids."""
    chosen = [i for i in items if i['id'] in picked]
    size = sum(int(i.get('size') or 0) for i in chosen)
    if with_ai:
        size += sum(int((i.get('ai') or {}).get('size') or 0) for i in chosen)
    return len(chosen), size


def ai_bytes(items, picked):
    return sum(int((i.get('ai') or {}).get('size') or 0) for i in items if i['id'] in picked and i.get('ai'))


def bar_label(count, size):
    """Board D1's red button: 'Delete 3 · 3.9 GB'."""
    return 'Delete %d · %s' % (count, lf.size_text(size) or '0 MB') if count else ''


def alert(count, noun='episode'):
    """Board D2: (heading, text, yes label)."""
    plural = '%d %s%s' % (count, noun, '' if count == 1 else 's')
    return ('Delete %s?' % plural,
            'They go to Google Drive\'s Trash, where they stay for 30 days. Nothing else is touched.',
            'Delete %s' % plural.title() if count > 1 else 'Delete')


def watched_ids(items, watched):
    """Board D1's "Watched (6)": the picked set for the watched ones."""
    return {i['id'] for i in items if i['id'] in watched or i.get('name') in watched}


def delete(items, picked, with_ai, trash, state_dir, upscale=None, log=lambda text: None):
    """Trash the picked files (and their AI copies when asked). Updates the saved Library listing and the copies
    state so pages drop them at once. Returns (removed ids, failed titles)."""
    import drivelibrary
    removed, failed = [], []
    for item in [i for i in items if i['id'] in picked]:
        try:
            trash(item['id'])
            removed.append(item['id'])
        except Exception as error:
            failed.append(item.get('title') or item['id'])
            log('Kodi iOS delete: %s not trashed (%s)' % (item.get('title') or item['id'], type(error).__name__))
            continue
        copy = item.get('ai') or {}
        if with_ai and copy.get('copy_id'):
            try:
                trash(copy['copy_id'])
            except Exception as error:
                log('Kodi iOS delete: AI copy of %s not trashed (%s)' % (item.get('title'), type(error).__name__))
    path = os.path.join(state_dir, 'drive-library.json')
    cache = drivelibrary.load_json(path, {})
    gone = set(removed)
    for hit in cache.values():
        if isinstance(hit, dict) and isinstance(hit.get('entries'), list):
            hit['entries'] = [e for e in hit['entries'] if str(e.get('id')) not in gone]
    drivelibrary.save_json(path, cache)
    if upscale is not None:
        copies_of = {str(i['id']): str(i['original']) for i in items if i.get('original')}
        for ident in removed:
            if ident in copies_of:   # an AI copy itself (Free Up Space › AI Upscale copies): the original stays
                entry = upscale.get('copies', {}).get(copies_of[ident])
                if entry:
                    entry.update(status='gone', copy_id=None)
                continue
            entry = upscale.get('copies', {}).get(ident)
            if entry:
                entry['status'] = 'gone' if with_ai or not entry.get('copy_id') else entry['status']
                entry['original_gone'] = True
    return removed, failed


def ai_items(upscale, names=None):
    """Free Up Space › AI Upscale copies: each ready copy as an item of its own (the original stays)."""
    out = []
    for original, e in sorted((upscale or {}).get('copies', {}).items(), key=lambda kv: -int(kv[1].get('size') or 0)):
        if e.get('status') != 'ready' or not e.get('copy_id'):
            continue
        name = (names or {}).get(original) or e.get('name') or original
        out.append({'id': str(e['copy_id']), 'original': str(original), 'title': '%s · %s copy' % (_title(name), e.get('label', 'AI')),
                    'line': lf.size_text(int(e.get('size') or 0)) + ' · the original stays', 'size': int(e.get('size') or 0), 'ai': None})
    return out


def _title(name):
    try:
        import drivelibrary
        return drivelibrary.display_title(name) or name
    except Exception:
        return name


def free_up_groups(shows, episodes_by_show, movies, upscale, watched=()):
    """Board F: the suggestions, biggest first, each with the items its Review opens (all ticked):
    [{'key', 'title', 'sub', 'bytes', 'items', 'noun'}]; empty groups are left out."""
    groups = []
    ai = ai_items(upscale)
    if ai:
        size = sum(i['size'] for i in ai)
        groups.append({'key': 'ai', 'title': 'AI Upscale copies', 'sub': '%s · the originals stay' % lf.size_text(size),
                       'bytes': size, 'items': ai, 'noun': 'copy'})
    big = sorted([m for m in movies if m.get('id')], key=lambda r: -int(r.get('size') or 0))[:5]
    if big:
        items = items_from_rows(big, upscale)
        size = sum(i['size'] for i in items)
        names = ' · '.join('%s %s' % (m.get('title'), lf.size_text(int(m.get('size') or 0))) for m in big[:2])
        more = len(big) - 2
        groups.append({'key': 'largest', 'title': 'Largest movies', 'sub': names + (' · %d more' % more if more > 0 else ''),
                       'bytes': size, 'items': items, 'noun': 'movie'})
    seen = []
    for show in shows:
        for f in episodes_by_show.get(show['id']) or []:
            if str(f.get('id')) in watched:
                seen.append(dict(f, title='%s · %s' % (show['title'], _title(f.get('name', '')))))
    if seen:
        items = items_from_rows(seen, upscale)
        size = sum(i['size'] for i in items)
        groups.append({'key': 'watched', 'title': 'Watched episodes', 'sub': '%d episodes · %s' % (len(items), lf.size_text(size)),
                       'bytes': size, 'items': items, 'noun': 'episode'})
    return sorted(groups, key=lambda g: -g['bytes'])


def items_from_rows(rows, upscale=None, title=None):
    """Select-list items from the file manager's rows (episode_rows / movie_rows): only files on Drive (an id); the AI
    copy's Drive id comes from the copies state."""
    copies = (upscale or {}).get('copies', {})
    out = []
    for r in rows:
        if not r.get('id'):
            continue
        copy = copies.get(str(r['id'])) or {}
        ai = {'copy_id': copy.get('copy_id'), 'size': int(copy.get('size') or 0)} if copy.get('status') == 'ready' and copy.get('copy_id') else None
        size = int(r.get('size') or 0)
        bits = [lf.size_text(size) or '']
        if ai:
            bits = ['%s + AI copy %s' % (lf.size_text(size), lf.size_text(ai['size']))]
        if r.get('watched'):
            bits.append('watched')
        name = title(r) if title else (r.get('title') or '')
        out.append({'id': str(r['id']), 'title': name, 'line': ' · '.join(b for b in bits if b), 'size': size, 'ai': ai,
                    'name': r.get('file') or r.get('name') or ''})
    return out


def drive_problems(cache):
    """'Check Drive for problems' (owner, 2026-11-13): what older builds left on Drive, from the saved Library listing
    (drive-library.json, no network), as select-list items with the reason in their grey line:
    - an episode that is really a pack's film ("Naruto Shippūden S01E01 - The Movie.mkv": 'movie' in the name, or more
      than 6x its show's median episode size);
    - the same episode twice in one show (the smaller copy is offered);
    - an empty show folder named after a torrent's info-hash.
    Nothing is removed here; board D's alert comes first."""
    import re
    import statistics
    import drivelibrary
    import prepare_downloads
    from debrid_drive import is_hash
    out = []
    shows = {str(e.get('id')): e for e in (cache.get('tv:') or {}).get('entries') or []}
    for slot, hit in cache.items():
        if not slot.startswith('tv:') or slot == 'tv:' or not isinstance(hit, dict):
            continue
        folder = slot[3:]
        entries = [e for e in hit.get('entries') or [] if e.get('id')]
        show = shows.get(folder, {})
        name = show.get('title') or show.get('name') or ''
        if not entries:
            if is_hash(name):
                out.append({'id': folder, 'title': 'Empty folder %s…' % name[:12], 'line': 'Named after a download, nothing in it',
                            'size': 0, 'ai': None, 'kind': 'folder'})
            continue
        sizes = [int(e.get('size') or 0) for e in entries if int(e.get('size') or 0) > 0]
        median = statistics.median(sizes) if len(sizes) >= 3 else 0
        seen = {}
        for e in entries:
            size = int(e.get('size') or 0)
            label = e.get('name') or ''
            if re.search(r'(?i)\bmovie\b|\bthe[ ._-]movie\b|\bfilm\b', label) or (median and size > 6 * median):
                out.append({'id': str(e['id']), 'title': drivelibrary.display_title(label) or label,
                            'line': '%s · looks like a film, not an episode' % lf.size_text(size), 'size': size, 'ai': None})
                continue
            show_key, season, episode = prepare_downloads.line_key(label)[:3]
            if e.get('season') and e.get('episode'):
                season, episode = int(e['season']), int(e['episode'])
            if not episode:
                continue
            other = seen.get((season, episode))
            if other is None:
                seen[(season, episode)] = e
                continue
            smaller, kept = (e, other) if size <= int(other.get('size') or 0) else (other, e)
            seen[(season, episode)] = kept
            out.append({'id': str(smaller['id']), 'title': drivelibrary.display_title(smaller.get('name') or '') or smaller.get('name'),
                        'line': '%s · S%d E%d is here twice' % (lf.size_text(int(smaller.get('size') or 0)), season, episode),
                        'size': int(smaller.get('size') or 0), 'ai': None})
    return out
