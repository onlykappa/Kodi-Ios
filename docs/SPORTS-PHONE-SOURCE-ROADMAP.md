# Sports phone source roadmap — build 575 follow-up

## Scope and branch

Owner request: documentation only for this handoff. No implementation, IPA or merge.
Branch: `codex/sports-phone-source-roadmap`, based on `claude/sports-jet` at
`30722ac2714aaaabfb982b4e8e3c5e3cb4ba3f73`. Open its draft PR against
`claude/sports-jet` so the roadmap diff stays separate from PR #43's existing code.
PR #43 stays unmerged. If its base later changes, merge/rebase deliberately with
the owner; do not force-push another agent's work.

## Phone evidence and corrected acceptance status

The supplied phone log identifies build 575, code commit `63b4434`.
ESPN returned 18 live and 51 upcoming games in 1.62 seconds. Four Crew category
roots were discovered; this count is not four playable sources.
NHL visited 19 folders and matched 36 streams in 53.37 seconds. NBA, NCAAB and
Full Live Sites each visited zero folders. Overall discovery completed after
55 seconds, with only one category returning games.

The first Live Now view closed after 29.105 seconds, before NHL results were
published. A second visit lasted 3.466 seconds and also ended before that scan
completed. Sports itself closed immediately before the zero-folder summaries.
The worker runs category tasks behind a shared gate; each traversal checks the
Sports session and playback ownership before entering a folder. Cancellation
of the session while NHL owns the gate is a concrete explanation to reproduce
for the skipped categories, not a proven phone root cause. Do not remove safe
cancellation merely to make those counts nonzero.

The owner reports finding a game manually through Crew after several failed
choices. The screenshot shows Knicks–Raptors and Crew's nested "Found on other
sites" picker. The log later opens an HTTP media stream and creates H.264 video
and AAC audio at 18:40:28. The log alone does not identify the selected provider
or independently prove which game it showed. Earlier direct opens include
unresolved Crew expressions; do not count those as successful playback.

Conclusion: ESPN cards work on the phone; automatic source discovery, game-card
playback and automatic source fallback have not passed phone acceptance.
Desktop Buffalo–Philadelphia playback remains valid desktop evidence only.

## Implementation order for the next agent

1. **Reproduce discovery starvation and lifecycle.** Trace the shared category
   gate, session ticket, pending count, page navigation and result publication
   in `sports_jet.py`, `sports_crew_context.py` and `sports_crew_routes.py`.
   Reproduce leaving/reopening Live Now before a slow first league finishes.
   Distinguish cancelled, skipped, unavailable and genuinely empty categories.
   Find why visible NBA cards get no choices while direct Crew can find them.
   Publish useful matched results incrementally; avoid making another league
   wait for a full first-league crawl. Keep native listing concurrency safe.

2. **Discover the same genuine Crew game/provider routes.** Compare ordinary
   Crew navigation for an ESPN-live matchup with the collector's traversal,
   including "Found on other sites" and any nested feed/HD choices. Determine
   which are directory routes and which are resolver-only native pickers.
   Match both teams uniquely within league/date, preserving the full native
   query and menu ancestry. Keep ESPN authoritative for scores and status.
   Do not invent plugin actions, scrape protected internals, spoof identities,
   or assume a displayed match guarantees a playable stream.

3. **Connect a live game action to an on-demand source search.** Reuse the
   existing Sports pages/buttons and provider door. A card with no cached
   choices must have a defined route to search that specific live game and
   expose the result; do not leave it as a permanently inert score card.
   Keep explicit source choices as recovery. Review UI policy before designing
   the exact control/loading/error behavior; no new layout is approved here.
   Close the Sports modal stack before native playback and refresh Crew's
   genuine menu ancestry immediately before each attempt, retaining ISSUE-371.

4. **Prove safe sequential source selection.** Investigate native supported
   ways to enumerate/select the nested choices observed in step 2. A parent
   route may still open a native chooser; do not claim unattended routing until
   this is resolved. Try ranked candidates one at a time, refreshing each just
   in time. HTTP success alone is insufficient: confirm Kodi video startup and
   advancing playback time. Distinguish definite error from user Cancel/Stop,
   superseded ownership and timeout; never advance after user cancellation.
   Where Kodi cannot distinguish a failed open from Stop, retain conservative
   behavior and report the limitation. Do not defeat provider access decisions.

5. **Validate and record evidence.** Add regression coverage for slow first
   league plus NBA, partial publication, page exit/reopen, unique matchup,
   nested native choices, stale regex cache, failed-first/working-second,
   cancellation, all-failed and replacement requests. Register new suites in
   `.github/workflows/import-review.yml`; run its required checks and
   `python3 -B scripts/check_project.py` before committing. Render changed
   pages in a correct portrait Kodi rig and follow UI policy checks. Test at
   least two actual ESPN-live games through actual Sports controls, plus a
   controlled definite failure followed by successful video and cancellation.
   Treat fixtures, desktop broadcasts and phone results as separate evidence.

## Definition of ready for the next phone test

- A live game's button produces correctly matched Crew choices on a cold open
  and after leaving/reopening Sports, without waiting for unrelated leagues.
- The real Sports button starts video for multiple games in the desktop rig;
  playback time advances and selected-game identity is checked where possible.
- Failed-first/working-next and Cancel/Stop behavior are demonstrated, with
  honest limitations where the native provider reports ambiguous outcomes.
- Timings report schedule, first match, discovery completion and time to video;
  no arbitrary "100% working" claim or universal provider availability claim.
- Issues/progress/handoff reflect the phone failure and each new result.
  No IPA until separately authorized by the owner.

## Fresh-agent starting instructions

Clone `onlykappa/Kodi-Ios` using the fresh agent's own authorized GitHub access,
then check out `codex/sports-phone-source-roadmap`. Read this document first,
then `AGENTS.md`, `ROADMAP.md`, `docs/PROGRESS.md`, `docs/ISSUES.md` (367–371),
`docs/DECISIONS.md` (062–063), `docs/SPORTS-HANDOFF.md`,
`docs/SPORTS-PLAYBACK-PROGRESS.md` and `docs/design/KODI-RIG.md`.
Older handoff text predating build 575 is historical; use this phone checkpoint.
Inspect remote heads before editing/pushing and preserve concurrent work.

Existing private rig, if present: `/workspace/scratch/kodi-rig-20261118`,
container `sports-kodi-rig-20261118`, RPC port 8089. It is Kodi21.2/Python3.13
with a rig-only forced portrait canvas and isolated Home; phone is Kodi21.3/
Python3.11. Do not delete its profile. A fresh account may not have this rig,
the uploaded log or scratch probes; rebuild using the rig guide and request
the owner log again if detailed raw evidence is necessary. All essential
sanitized findings above are in Git; no lost detached commit is required.

Keep raw logs, stream URLs, headers, cookies, provider configuration, account
data and screenshots outside Git and PR text. Do not merge or publish an IPA
without a new explicit request. Do not implement anything in the roadmap-only
turn; this file defines the next coding task when the owner assigns it.
