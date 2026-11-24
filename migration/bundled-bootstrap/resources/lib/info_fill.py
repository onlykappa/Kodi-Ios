"""The Info card's description for a title started from Continue Watching (owner, 2026-11-24: "ensure info is being populated correctly for shows"; build 688, an episode's card said
"No description for this video yet.").

Continue Watching plays a remembered link directly (ios_watch_dialog.fast_stream), without TMDb Helper, so the playing item had its title, show, season, episode and art but no plot.
Once such a video plays, the service looks the plot up on TMDb (the season of an episode, the film's page for a movie; the same key and cache as the Library pages), keeps it with the
Continue record (so the next start has it from the start) and puts it in Home property KodiIOS.Plot, which the Info card shows when the playing item has none.
Everything the phone does is injected, so the rules are tested here."""
PROPERTY = 'KodiIOS.Plot'
TMDB = 'https://api.themoviedb.org/3'


def lookup(entry, key, cache, get, library):
    """{'plot': text, 'title': text} for the Continue record `entry`, or {}. `library` is the drivelibrary module (its cached season lookup); `get(url)` returns the page's text."""
    tmdb = str(entry.get('tmdb_id') or '')
    if not key or not tmdb.isdigit():
        return {}
    if entry.get('kind') == 'episode':
        season, episode = str(entry.get('season') or ''), str(entry.get('episode') or '')
        if not (season.isdigit() and episode.isdigit()):
            return {}
        found = (library.season(tmdb, int(season), key, cache, get) or {}).get(str(int(episode))) or {}
        return {'plot': found.get('plot') or '', 'title': found.get('title') or ''}
    if entry.get('kind') == 'movie':
        import json
        try:
            data = json.loads(get('%s/movie/%s?api_key=%s' % (TMDB, tmdb, key)))
        except Exception:
            return {}
        return {'plot': data.get('overview') or '', 'title': data.get('title') or ''}
    return {}


def run(entry, has_plot, key, cache, get, library, put, remember):
    """After a video of `entry` began. Nothing to do when the playing item already has a plot or the record has one (it is shown from the record); otherwise looked up, put in
    the Home property and kept with the record (remember(plot)). Returns the plot written, or ''."""
    if has_plot():
        return ''
    plot = str(entry.get('plot') or '')
    if not plot:
        plot = lookup(entry, key, cache, get, library).get('plot', '')
        if plot:
            remember(plot)
    if plot:
        put(plot)
    return plot
