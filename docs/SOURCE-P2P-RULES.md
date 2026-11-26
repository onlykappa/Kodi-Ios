# Peer-to-peer start-up, seeder and health rules (roadmap step 19)

Code: `migration/bundled-bootstrap/resources/lib/p2p_rules.py` on `direct_stream.py` (step 18) and `source_health.py` (step 11); `provider_fallback_hooks.direct` now goes through it. Tests: `scripts/test_p2p_rules.py` (8 tests, host only: fake player, fake clock).

**Ranking.** `rank` keeps verified torrents with at least 2 seeders and a size of at most 30 GB (a phone must start the stream quickly), leaves out any swarm still cooling down, and orders by the asked-for quality, then the usual quality order, then seeders (capped at 200 so a huge count does not beat a sane choice), then smaller size.

**Waiting.** Each attempt shows "Waiting for peers · N s" through the Home property `KodiIOS.DirectStream.Status` (plain wording, no ellipsis; cleared when done), 90 s for the first swarm, 60 s for the next, 240 s for the whole attempt and at most 3 swarms; the player is stopped between tries.

**Failure and health.** Each swarm is recorded as `swarm:<info hash>` in the shared source health: a timeout or failure cools it down (2, 10, 30 minutes), so nothing is retried without bound and one dead swarm never blocks the others; a swarm that started is remembered as recent. A declined prompt or a cancel stops the chain at once and is never recorded; the prompt is asked once per attempt. A wrong-title candidate is skipped without penalty. Nothing viable is `empty`; every try failing is the last typed outcome (`timeout` normally).

**Not done.** The words reach the screen only if a skin element reads `KodiIOS.DirectStream.Status`, which is not added yet (UI work, planned for the end under the Apple UI policy and checked on the rig). The picker still hands over one chosen torrent, so ranking across several candidates is used by the library function but not yet offered as a "try the best swarm" action. Seeder counts are what the source site claims, not measured peers. No real swarm, iOS engine or device evidence.
