"""Bounded, optional live scores from the existing ESPN scoreboard integration."""
from concurrent.futures import ThreadPoolExecutor
import time
import sports_espn


def fetch_live(codes, clock=time.time, fetch=None):
    """Fetch only the leagues already on screen; failures never block the sports list."""
    selected = [entry for entry in sports_espn.LEAGUES if entry[0] in set(codes)]
    now = int(clock())
    def one(entry):
        code, name, sport, path, joiner, config = entry
        try:
            body = (fetch or (lambda url: sports_espn.fetch_json(url, timeout=3)))(sports_espn.BASE % path)
            return sports_espn.parse(code, name, sport, joiner, config, body, now)[0]
        except Exception:
            return []
    if not selected:
        return []
    with ThreadPoolExecutor(max_workers=min(4, len(selected))) as pool:
        return [game for result in pool.map(one, selected) for game in result]
