# Bundled source resilience: owner-controlled backup roadmap

Date: 2026-11-23. Initial baseline: main cf42c63.
Status: steps 1–2 available-source inventory and controlled rig baseline complete; 2/16 roadmap steps complete.
Phone parity gaps remain explicit in docs/SOURCE-DEPENDENCY-INVENTORY.md.

## Goal and authorization

Maintain an owner-controlled backup inside this repository and the signed Kodi iOS IPA:
search -> identify the correct page/torrent -> resolve -> acquire a fresh playable
address/magnet -> use existing Kodi/Elementum playback. Activate it when the primary
provider has a confirmed failure or no acceptable sources, without replacing the
normal picker or launching competing playback sessions.

The owner requests this detailed investigation/roadmap draft PR, not implementation,
a build, framework publication or merge. "Start 1" authorizes step 1; subsequent
numbers refer to the stable steps below. Report concrete blockers rather than
quietly expanding scope. No separate repository or hosted control service is planned.

Preserve installed working versions and existing provider behavior. Reuse only
properly licensed source, retain attribution and meet source-distribution obligations.
Do not impersonate add-ons, bypass authorization/DRM/paywalls/bans, decode protected
code, or copy account state. A provider refusal is a failure category, not permission
to defeat it. Authorized controlled media is used for tests.

## Initial evidence, not a completed dependency audit

- `migration/bundled-bootstrap/resources/lib/provider_fallback.py` already coordinates
  bounded movie/episode backup searches. It lists Jacktook, POV, Otaku, Crew and Prism.
- `provider_adapters/` bridges installed upstream modules; those adapters are not yet
  proof of an independently maintained source engine.
- `provider_adapters/thecrew.py` delegates search and resolution to Crew's Sources.
- Jacktook's adapter defaults include Torrentio and Comet discovery services. Locally
  preserving the adapter cannot preserve those remote services.
- `migration/provider-fallback/source-lock.json` records upstream package provenance,
  hashes, licenses and packaging policy. It references remote assets; this alone does
  not establish that a clean build can run with all upstream repositories unavailable.
- `migration/elementum-ios/source-lock.json` pins Elementum, Burst and supporting
  modules. Its historical device-status fields must not be treated as current proof.
- Crew's supported service and remote proxy dependency are documented in DEC-064;
  preserve native identity and investigate their exact dependencies.
- Sports uses ESPN for schedules and Crew for sources (DEC-065). Do not assume the
  movie/TV fallback can be applied unchanged to time-sensitive live events.

These observations are source inspection only. No new live search, playable source,
shutdown-resilience result, phone validation or complete endpoint inventory is claimed.

## Packaging and dependency boundaries

Keep a small Kodi-facing integration around the existing coordinator. Maintain
licensed backup adapters in the existing provider-adapter tree or a narrowly scoped
module selected after inventory. Bundle exact approved code/data versions and their
necessary dependencies into the IPA; no mandatory GitHub fetch or new server at
runtime. Keep native Elementum as the torrent transport, not another torrent engine.
Separate metadata, search/discovery, resolution, debrid/account APIs, content delivery,
trackers/peer discovery, update repositories and optional telemetry in the inventory.

Distinguish four outages: update repository gone; installed primary add-on unavailable;
remote discovery/configuration backend gone; content/peers unavailable. Each requires
its own test. No code snapshot can guarantee an external site, swarm, live broadcaster,
account service or future iOS compatibility forever. An alternate domain under the
same operator/backend is not automatically an independent fallback.

## Ordered steps and acceptance gates

Every step starts NOT STARTED. Tick only after its deliverable and acceptance checks
are recorded with the commit, commands, results and remaining limitations. A failed
experiment stays recorded. Later work can expose a need to revisit earlier steps.

### 1. Inventory the actual working stack

- [x] Record exact app/add-on/engine versions, hashes, dependency closure, install
  locations and available source for Elementum, Burst, Umbrella, CocoScrapers, Crew,
  ResolveURL, existing fallback modules and their required services.
- Trace each network call family and dynamic code/configuration/feed fetch. Record
  hostnames and roles only where safe, never signed URLs, credentials or user state.
- Deliver a dependency matrix with local/remote, required/optional, account needs,
  replaceability, license, source location and evidence confidence for each component.
- Acceptance: trace representative search and resolve paths from entry point to
  playback handoff. Mark missing phone-only files explicitly; repository pins are
  not evidence of the installed phone version. No blind extraction of private profiles.

### 2. Establish an isolated baseline rig

- [x] Inspect scripts/kodi_rig.py and docs/design/KODI-RIG.md; preserve private profiles.
  Record Kodi, Python, add-on and engine versions and differences from the phone.
- Stage copies of working files in a private profile with no account migration.
  Produce deterministic authorized search/resolve/playback fixtures plus optional
  permitted live checks. Record current failures before any repair.
- Acceptance: normal primary selection plays the controlled fixture; cancel and stop
  work. Capture actual player start and advancing playback time. Clearly separate
  fixtures, real external-source checks and phone evidence.

### 3. Preserve a reproducible licensed source baseline

- [ ] Determine what can be stored directly, what requires accompanying source/notices,
  and what cannot be redistributed. Preserve exact eligible source and build inputs.
- Extend existing locks/manifests, avoid duplicate engines and unlicensed data dumps.
  Specify a trusted backup location for necessary artifacts not suitable for Git.
- Acceptance: clean staging can restore the approved baseline without relying on
  mutable upstream branches. If an asset cannot be mirrored or licensed, list the
  unresolved dependency instead of claiming preservation. Test repository outage.

### 4. Define the independent backup contract

- [ ] Specify search requests (media IDs, titles/aliases, year, season/episode), source
  results (identity, provenance, transport, quality, size/seeds when known), resolver
  handles, expiry, capability flags and typed outcomes using existing code where possible.
- Distinguish empty, offline, timeout, unsupported, account-required, refused, expired
  and canceled. Keep secrets out of persistent candidates and diagnostic output.
- Acceptance: deterministic contract tests prevent wrong-title/episode matches,
  malformed payloads, ambiguous matches and unsupported results reaching playback.

### 5. Implement the smallest independent search adapter

- [ ] Choose one maintained, licensed source implementation from step 1 with useful
  coverage and a permissible ordinary request path. Prefer a reusable local scraper
  over a remote aggregator when independence is the goal.
- Preserve required sessions, pagination and parsing with bounded concurrency/timeouts.
  Do not assume copying Burst/Crew wrapper code removes underlying backend dependencies.
- Acceptance: search works with the primary add-on absent and its discovery service
  blocked; fixtures cover valid/empty/changed/error responses. Record authorized live
  checks separately. Code whose meaningful operation still requires the failed provider
  remains an adapter, not an independent replacement.

### 6. Build and verify fresh resolution

- [ ] Resolve opaque candidates immediately before use using normal supported provider
  flows. Preserve applicable cookies, redirects and required headers; use established
  ResolveURL/native resolvers when appropriate and record that dependency.
- Test expired tokens and fresh resolution without saving signed playback URLs to Git
  or general logs. Respect authorization; do not manufacture session credentials.
- Acceptance: a controlled server requires legitimate session/header continuity;
  master, variant, segment and key requests succeed where applicable. HTTP 403/429,
  inaccessible content and unsupported protections become honest typed failures.

### 7. Connect existing transport and playback

- [ ] Send valid magnet/torrent candidates to the existing Elementum engine and supported
  HTTP/HLS candidates to current Kodi playback. Preserve resume and inputstream behavior.
- Coordinate with VPN work in PR #55; do not add unverified VPN detection or silently
  enable direct torrent traffic. Respect the app's established network/privacy policy.
- Acceptance: generated torrent content hash matches, controlled HTTP/HLS starts and
  time advances, cancel prevents late starts, stop closes work, no duplicate player.
  Host success does not prove the iOS native engine or receiver behavior.

### 8. Integrate fallback into the existing picker

- [ ] Extend provider_fallback and existing hooks rather than create another picker.
  Invoke backups only for confirmed primary failure/empty/unsuitable results according
  to a documented policy. Preserve user-selected sources and manual cancellation.
- Bound total search/resolve time, deduplicate results across providers and reject
  stale search generations. Do not launch fallback while native playback is uncertain.
- Acceptance: failure -> backup -> one actual playback; healthy primary avoids extra
  work; cancellation/no-source states are safe. Test movie and episode paths.

### 9. Add independently useful source coverage

- [ ] Expand adapters incrementally across applicable Burst/torrent, Umbrella-style
  search/resolution and Crew paths, subject to licensing and step 1 findings.
- Record shared infrastructure and account requirements. Never represent a debrid API
  as locally replaceable or copy a paid account from another installation.
- Acceptance: documented coverage matrix by source family and transport; fail one
  backend at a time and prove alternatives do not call the disabled dependency.
  Commit each adapter with focused regression tests, not one unreviewable bulk fork.

### 10. Handle Sports as a separate source capability

- [ ] Retain ESPN event identity, time/status and scores. Map only unique, current
  game matches to available source routes; preserve supported native Crew handling.
- Reuse backup contracts where appropriate while retaining live-specific expiry and
  cancellation. No guessed matches or permanent saved live-stream addresses.
- Acceptance: controlled event -> exact source -> advancing playback; stale/ambiguous
  games rejected; owner-authorized real live checks recorded as point-in-time evidence.
  Do not claim future games will remain available because one game worked.

### 11. Add bounded provider health and recovery

- [ ] Track safe local failure categories and cooldowns; allow expiry and deliberate
  retry. Prefer recent actual success without declaring untested sources healthy.
- Retry fresh resolution once where justified, then try another eligible candidate;
  honor rate limits/refusals and avoid repeated popups or aggressive scanning.
- Acceptance: dead/slow source cannot starve alternatives, confirmed failure advances,
  cancellation never advances, expired tokens refresh, successful source selected once.

### 12. Make packaging resilient to upstream shutdown

- [ ] Integrate approved preserved inputs into existing fetch/build scripts. Separate
  build-time retrieval from runtime requirements; verify hashes and reject tampering.
- Keep the bundled last-known-working version usable without update services. Optional
  updates must not execute arbitrary downloaded code or replace known-good data blindly.
  Use the signed app distribution path for executable changes unless separately reviewed.
- Acceptance: clean build/staging with upstream package hosts blocked; fresh staged
  install and restart can search fixtures using bundled inputs. Record any unavoidable
  external build tools, metadata APIs and content-service dependencies.

### 13. Run the outage, correctness and privacy matrix

- [ ] Test unavailable repository, missing primary add-on, dead remote configuration,
  dead aggregator, shared backend failure, DNS/TLS failures, malformed feeds, expired
  links, 403/429, absent peers, missing accounts and complete offline mode.
- Include wrong movie/year/episode, duplicate results, partial success, cancellation,
  profile restart and concurrent jobs. Do not mask attempted forbidden direct traffic
  with a fixture firewall and then claim networking isolation.
- Acceptance: deterministic regression suite plus sanitized failure/evidence matrix;
  bounded completion, honest errors, zero secret-bearing log lines and no abandoned
  background jobs. All-results-empty must remain a valid outcome, not fabricated success.

### 14. Validate performance and the existing UI in Kodi

- [ ] Measure primary/backup search time, resolution, time to first picture, retries,
  request counts and resource usage on identical controlled fixtures before/after.
- Exercise real picker, download, movie/episode and Sports entry points as applicable.
  Follow Apple UI policy before any UI changes; avoid adding new screens unnecessarily.
- Acceptance: desktop Kodi rig evidence includes actual action-to-player flow and
  advancing time, not only API results. If capturing UI, correct portrait rendering;
  screenshots stay private and are labeled desktop rig, never iPhone evidence.
  Set realistic targets from measurements rather than promise universal five-second opens.

### 15. Complete regression review and handoff

- [ ] Every code fix has an ISSUES entry (seen/cause/fix/test), relevant tests registered
  in import-review.yml, and an update to this roadmap/progress/evidence inventory.
- Run python3 -B scripts/check_project.py and all required workflow checks, plus
  relevant provider, build-packaging, playback and rig tests. Remove stray __pycache__.
- Acceptance: exact commit and passing/failing/not-tested results documented; review
  licenses, dependencies, cancellation and secret redaction; preserve remote work and
  keep PR draft until reviewed. Documentation-only planning does not prove these gates.

### 16. Owner-authorized phone acceptance and maintenance plan

- [ ] Only after explicit authorization, build a testing IPA from an identified commit
  and record bundled hashes. Test primary normal, backup after controlled failure,
  actual stream/download, cancel, reopen/resume and appropriate VPN transitions on phone.
- Document adapter fixture refreshes, dependency/security updates, known unavailable
  sources and how to revert a broken update without erasing saved media or account state.
- Acceptance: owner phone evidence supports stated functionality, or unresolved cases
  remain open. No merge/release from roadmap approval alone. Final report distinguishes
  preserved software, independent discovery and unavoidable external content availability.

### Extension (owner request 2026-11-26): fewer third-party single points of failure

Goal restated by the owner: sources may be third-party, but the app should not depend on Umbrella, Burst or Crew discovery, or on one debrid
service, to keep working. Steps 1–16 above are unchanged and keep their numbers; these four are appended and each needs its own owner
authorization ("Start 17" and so on). Prerequisite already done: the AllDebrid key is read from Umbrella first and mirrored into the app's own
profile (`debrid_token.py`, commit 4914392), so removing Umbrella no longer removes the key. First-time sign-in still goes through Umbrella.

### 17. Own the debrid account and detect debrid failure

- [ ] Give the app its own AllDebrid sign-in (the service's PIN/device flow) writing to the profile store of `debrid_token.py`, so a fresh
  install needs no Umbrella. Map AllDebrid's error codes (service unreachable, key rejected, account not premium, magnet not cached, too many
  active torrents) to the `source_contract` outcomes and tell "debrid is gone" (offline/refused across several calls) from "this title is not
  cached". Keep the key out of Git, logs and the IPA.
- Acceptance: sign-in, refresh and sign-out against a controlled fake service; each error code maps to one typed outcome; a circuit state
  ("debrid unavailable") appears only after repeated failures and clears on success. Real AllDebrid only with explicit owner authorization.

### 18. Direct peer-to-peer stream route when debrid is unavailable

- [ ] When step 17 reports debrid unavailable, offer "Stream directly (peer-to-peer)" for a verified torrent candidate and let the bundled
  Elementum engine stream it instead of the debrid/Drive redirect, behind the existing torrent prompt and its VPN hint. Never start silently,
  never turn a Stream into a Drive download, never change VPN or network settings (coordinate with PR #55).
- Acceptance: with the debrid route forced unavailable, a controlled torrent (local seeder and tracker on the rig) starts, time advances,
  cancel and stop close the engine session, no duplicate player. Host and rig success do not prove iOS engine behaviour, background limits or
  real-swarm speed: those need the owner's phone.

### 19. Peer-to-peer start-up, seeder and health rules

- [ ] Rank candidates by seeders and size for direct streaming, show a visible "waiting for peers" state, give up after a bounded time with a
  typed outcome and move to the next candidate, and keep one failed swarm from blocking others. Record per-source results through the step 11
  health mechanism.
- Acceptance: controlled swarms with zero, few and many seeders produce the expected ranking, waiting state, timeout and fallback; no source is
  retried without bound.

### 20. Metadata snapshot for outages of TMDb and ESPN

- [ ] Keep a bounded, expiring local snapshot of the title, alias, year, season/episode and sports schedule data the matching code needs, so the
  strict identity check and sports matching keep working through a temporary outage of TMDb or ESPN. Stale data must be marked and never
  presented as live; sports state older than its limit is rejected (step 10 rules).
- Acceptance: with the metadata services blocked, a title with a prior snapshot still matches strictly, one without a snapshot fails with a typed
  outcome, and an old sports game is rejected. No claim that metadata stays correct without the services.

## Step execution record

| Step | Status | Commit / evidence / blocker |
| --- | --- | --- |
| 1 | COMPLETE (available-source scope) | [Inventory](SOURCE-DEPENDENCY-INVENTORY.md); verified package hashes, manifest imports, dependency roles and traces. Phone version/partial Umbrella/dynamic endpoint gaps explicit. |
| 2 | COMPLETE (controlled baseline) | [Rig baseline](SOURCE-RIG-BASELINE.md); 13 fixture scenarios pass after isolated artwork repair; generated-video picker/start/advancing clock/stop pass. Production engine and phone unverified. |
| 3 | IN PROGRESS — BLOCKED | [Offline staging and license evidence](SOURCE-PRESERVATION-STEP3.md): 29 verified provider inputs restored locally with Python network connects blocked; durable approved backup, license closure, Elementum inputs and actual Kodi runtime closure remain open. |
| 4 | CONTRACT DONE (host tests) | [SOURCE-BACKUP-CONTRACT.md](SOURCE-BACKUP-CONTRACT.md): typed outcomes, expiry, capabilities, redaction and the pre-playback gate, 13 tests. Not yet wired into the search loop. |
| 5 | ADAPTER DONE (host tests, fixtures only) | [SOURCE-INDEPENDENT-SEARCH.md](SOURCE-INDEPENDENT-SEARCH.md): one first-party site adapter, no add-on needed; not wired into the playback loop, no live check. |
| 6 | FRESH RESOLUTION DONE (host tests, loopback server) | [SOURCE-FRESH-RESOLUTION.md](SOURCE-FRESH-RESOLUTION.md): resolve at use, header/cookie continuity through master, variant, key and segment, typed 401/403/429/expired failures. Not wired into playback. |
| 7 | TRANSPORT/PLAYBACK MODULE DONE (host tests) | [SOURCE-BACKUP-PLAYBACK.md](SOURCE-BACKUP-PLAYBACK.md): one-session player hand-off with time-advance check, torrent hash verification and the existing Elementum route. Not yet called by the picker (step 8). |
| 8 | PICKER POLICY DONE (host tests) | [SOURCE-FALLBACK-POLICY.md](SOURCE-FALLBACK-POLICY.md): policy, uncertain-playback and stale-search guards, dedupe, first-party search as last resort. Hooks still use their existing player calls. |
| 9 | FIRST INCREMENT DONE (host tests, fixtures only) | [SOURCE-COVERAGE.md](SOURCE-COVERAGE.md): ten independent site families (apibay, YTS, EZTV, Knaben, Bitsearch, TorrentDownload, LimeTorrents, Kick4ss, Nyaa, 1337x), five parsed from real captures merged by hash, failure isolation proven; Burst/Coco/Umbrella/Crew paths and live checks remain. |
| 10 | SPORTS POLICY DONE (host tests; one live ESPN read) | [SOURCE-SPORTS.md](SOURCE-SPORTS.md): unique current game match, stale/ambiguous rejection, live expiry, duplicate/cancel guards, independent HLS start. No live stream check. |
| 11 | HEALTH DONE (host tests) | [SOURCE-HEALTH.md](SOURCE-HEALTH.md): per-source cooldowns (Retry-After honoured), deliberate retry, recent winners first, cancel never penalised, one calm Notifications line, wired into the add-on chain, the site searches and the Sports routes. Cooldown tables untuned on phone traffic. |
| 12 | PACKAGING DONE (host tests, network-less) | [SOURCE-PACKAGING.md](SOURCE-PACKAGING.md): preserved inputs used by digest before any download (`--preserved` / `KODI_IOS_PRESERVED_INPUTS`), tampering refused, a staged bundle restarts and searches with no network; runtime never runs downloaded code. Unavoidable external build tools listed. |
| 13–16 | NOT STARTED | Do not start until separately authorized. |
| 17 | ACCOUNT + FAILURE DETECTION DONE (host tests, fake service) | [SOURCE-DEBRID-ACCOUNT.md](SOURCE-DEBRID-ACCOUNT.md): PIN sign-in into the app's own store, every documented error code typed, a 3-strike "debrid unavailable" state wired to the download queue. No sign-in screen yet; real AllDebrid not contacted. |
| 18 | DIRECT ROUTE DONE (host tests) | [SOURCE-DIRECT-STREAM.md](SOURCE-DIRECT-STREAM.md): verified torrent, prompt, one-time grant, Elementum plays from peers, wait and cancel rules. Reached only when debrid is marked unavailable; no on-screen choice yet; engine and swarms untested. |
| 19–20 | ADDED, NOT STARTED | Extension for self-reliance (own debrid account and failure detection, peer-to-peer fallback, health rules, metadata snapshot). Prerequisite done: debrid key mirrored into the app profile (4914392). Each needs separate authorization. |

On completing a step, replace its row range with individual rows and record dates,
commands, expected/observed results and links to sanitized reports. Do not renumber
steps when adding subtasks. Next owner commands: "Start 19" (13–16 are the end-of-project testing steps).
