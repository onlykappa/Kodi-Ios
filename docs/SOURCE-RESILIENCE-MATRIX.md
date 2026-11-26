# Outage, correctness and privacy matrix (roadmap step 13)

Code: `scripts/resilience_matrix.py` (scenarios), `scripts/test_resilience_matrix.py` (runs it and checks the committed report), sanitized result: `reports/source-resilience-matrix.json` (refresh with `python3 scripts/resilience_matrix.py --write`). **Host checks only: injected failures, a loopback server, real DNS and TLS failures, and one network-less namespace; nothing here is phone, rig or live-service evidence.**

Every scenario runs the real modules. During the run a tripwire records any connection to a non-loopback address (none occurred, and none of these paths is allowed to), a fake log records every line, and thread counts must return to baseline (no abandoned background jobs). The offline scenario uses a real network-less namespace rather than a fixture firewall; the DNS and TLS scenarios use the real resolver and a real handshake against a self-signed local server (the certificate is refused).

## Outage

| Scenario | Expected | Observed | Result |
| --- | --- | --- | --- |
| unavailable package repository: preserved copy used, tampered copy refused, no copy fails typed | build finishes from preserved bytes; tamper and missing are errors | preserved build ok; tampered and missing raise OSError | pass |
| missing primary add-on and every add-on backup: first-party searches take over | results from the ten site searches, add-ons never launched | 3 candidates from site searches; 0 add-on calls | pass |
| dead remote configuration / all sites down: typed offline, not empty | typed offline outcome and no results | offline | pass |
| dead aggregator (Knaben) while others answer | others answer; aggregator reported offline and cooled down | ok; knaben offline, cooling | pass |
| shared backend failure: two add-on providers fail for the same reason | chain continues to a third provider; both cool down | thecrew answered; jacktook, pov cooling | pass |
| DNS failure (real resolver, .invalid host) | typed offline | offline | pass |
| TLS failure (real handshake against a self-signed local server) | typed offline; certificate is not accepted | offline (certificate verification failed) | pass |
| complete offline mode (network-less namespace, real sockets) | typed offline for every request; staged bundle still imports and searches fixtures | offline | pass |
| malformed feeds and pages for every site family | every family: layout changed, never a fabricated result | 10 families reject malformed input | pass |
| expired link: re-resolved once, second expiry returns expired | one re-resolve, then expired; no loop | expired after 2 resolutions | pass |
| 403/429 from a site and from the debrid service | typed refused; cooldown honours Retry-After; debrid circuit needs three service failures | refused; retry-after honoured | pass |
| absent peers: no swarm starts | timeout within the total bound; player stopped; each swarm cooled | timeout after 3 swarms in 211 s | pass |
| missing accounts: no AllDebrid key and no Google sign-in path | typed account-required; direct route offered only behind the prompt | account-required; direct plan allowed (prompt still required) | pass |

## Correctness

| Scenario | Expected | Observed | Result |
| --- | --- | --- | --- |
| wrong movie, wrong year, wrong episode, duplicate results | only the exact title/year/episode; duplicates collapse by hash | 3 movie candidates, no wrong-year/title rows, no wrong-episode rows | pass |
| partial success: some families fail, one answers | results kept with a per-site report | ok with apibay timeout | pass |
| all results empty is a valid outcome | empty, never fabricated success | empty | pass |
| cancellation never advances or penalises | canceled outcome; nothing recorded in health; no player start | no advance, no record, no start | pass |
| profile restart: health, token mirror and stale metadata survive | state reloads from the profile files | cooldown, mirrored key and own key persist | pass |
| concurrent jobs: parallel searches share health; same stream starts once | no exception, consistent health, one player start | 8 parallel searches ok; duplicate starts collapsed (1 player starts) | pass |
| sports: stale, ambiguous and ended games rejected | typed unsupported/empty; no launch | unsupported, unsupported, unsupported | pass |
| no direct torrent traffic is attempted by any search or fallback path | zero non-loopback connections recorded by the tripwire | tripwire clean: 0 non-loopback connects | pass |

## Privacy

| Scenario | Expected | Observed | Result |
| --- | --- | --- | --- |
| no secret-bearing line: logs, health file, notices and reports carry no key or link | zero lines contain the key, a URL, a header or a magnet | 6 log lines, 1 notices, health file: clean | pass |
| the repository carries no key, token file or private state from these steps | no secret pattern in the new modules, docs or reports | 11 modules checked | pass |
| the app never runs downloaded code | update flow has no exec/eval/import of downloaded data | updates.py clean | pass |

## Hygiene

| Scenario | Expected | Observed | Result |
| --- | --- | --- | --- |
| no abandoned background jobs after the whole matrix | thread count back to baseline | extra threads: 0 | pass |

## What this does and does not show

* Each listed failure ends in a bounded, typed, honest outcome; all-results-empty stays `empty`, never a fabricated success; cancel never advances or penalises a source; restart keeps state; parallel jobs do not corrupt shared health and the same stream starts once; no log line, notice, health file or report carries a key, link, header or magnet.
* Not covered here: the phone, real Kodi (step 14 on the rig), real AllDebrid, real swarms, the iOS Elementum engine, Crew's own remote modules and their runtime behaviour, and sites changing after 2026-11-26.
* One flake seen while running the whole 240-test suite in parallel: `test_umbrella_recovery.py` printed OK and then the interpreter segfaulted at exit once; it did not reproduce in 16 further runs (8 in parallel with this branch, 8 without it), so it is recorded, not explained.
