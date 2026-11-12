# Desktop Kodi rig

A real Kodi 21.3 on Linux, under a virtual screen the size of the iPhone 16 Pro's portrait safe area
(402 × 778 pt at 1.5×, 603 × 1167 px), running the portrait skin this checkout generates. Any agent can set it up
with one command and compare a page with its approved mockup.

**Evidence class: desktop Kodi rig** (APPLE-UI-POLICY §9). It shows real Kodi layout, text fit, conditions and the
window scripts. It does **not** show touch, safe areas, the SF font (the rig uses Fuse's Inter, which is wider), the
native tab bar, scaling on the phone or real AirPlay. Device checks stay with the owner.

## Set up (once per machine, about 15–20 minutes)

```
python3 -B scripts/kodi_rig.py setup            # add --release build-NNN to take add-ons from another release
python3 -B scripts/kodi_rig.py start
```

`setup` does, in `KODI_RIG_HOME` (default `~/.cache/kodi-rig`, never the repository):

1. installs the Debian/Ubuntu packages Kodi needs plus Xvfb and ImageMagick (`apt-get`, as root or with sudo);
2. clones Kodi `21.3-Omega` and builds the x11 binary. Two workarounds for sandboxes that block downloads:
   Groovy and Apache Commons come from archive.apache.org through `-DKODI_MIRROR=file://…` (Kodi checks their hashes),
   and libdvdread/nav/css tarballs are made from their git tags with the rig's own Kodi copy pointed at their hashes;
3. downloads the release IPA and takes its pure-Python add-ons and the patched Arctic Fuse 3 skin
   (native libraries are left out);
4. prepares a Kodi profile: this checkout's `service.kodi.ios.bootstrap` (its service turned off, so the scenarios
   own the status files), the generated portrait folder, iOS-only conditions forced on (`scripts/portrait_rig.py`).

Network it needs: `github.com` (Kodi, libdvd*, the release IPA), `api.github.com` (finding the IPA asset),
`archive.apache.org`, and the distribution's package mirror. In a Claude Code cloud session these may need adding
to the environment's allowed hosts.

## Use

```
python3 -B scripts/kodi_rig.py boards           # all nine approved boards -> KODI_RIG_HOME/side/boardN.png
python3 -B scripts/kodi_rig.py boards 3 5       # just some
```

`boards` refreshes the add-on from this checkout (`sync`), shoots the mockups once (Playwright), writes each
board's status scenario, opens its page, taps where the board needs it (board 3: the working card; board 9: a Ready
row), takes a screenshot and writes a labelled side-by-side: **mockup | desktop Kodi rig**.

By hand:

| Command | What it does |
|---|---|
| `sync` | copies this checkout's add-on into the running rig and regenerates the pages (no restart) |
| `scenario NAME [--seconds N]` | writes a status state: `running`, `airplay`, `paused`, `network`, `queued`, `idle`, `stale`, `long` (`scripts/kodi_rig_scenarios.py`; synthetic films only). With `--seconds` it stays fresh in the background (the model calls anything older than 6 s stale) |
| `open PAGE [ARGS]` | `library_status`, `notifications`, `transfers`, `tool_pages queue`, `tool_pages history`, … |
| `click ID` | `SendClick(ID)` in the open window (ids are in the page generators, e.g. `library_page.WORK`) |
| `builtin TEXT` | any Kodi builtin (`SetProperty(Notices.Pct,40,home)`, `Dialog.Close(all,true)`, …) |
| `shot NAME` | screenshot to `KODI_RIG_HOME/shots/NAME.png` |
| `side MOCKUP RIG OUT` | labelled side-by-side of any two images |
| `rpc METHOD [JSON]` | one JSON-RPC call (port 8089) |
| `stop`, `restart`, `prepare` | stop Kodi and Xvfb; restart; rebuild the profile from scratch |

Kodi's own log is `KODI_RIG_HOME/home/.kodi/temp/kodi.log` (script errors from the pages land there).

## Smoke check before an IPA (roadmap 3.4)

```
python3 -B scripts/rig_smoke.py            # starts the rig if needed, syncs this checkout, runs every check (about 4 minutes)
python3 -B scripts/rig_smoke.py --list     # the checks and what is not covered
python3 -B scripts/rig_smoke.py notifications watch_sheet
```

For each page (Notifications, Accounts, Profiles, Favourites, Settings search and sections, Skin settings, the
Navigation menu, Activity, Library status, Transfers, Queue, History, AirPlay settings, the watch / resume / quality
sheets, the show and movies pages) it opens the page in the running rig and fails the check when: the page's own open
line (`ui open`, or the sheet's line) is missing from Kodi's log, Kodi's log gains a traceback, an expression or XML
error or a missing window (a short allow-list with reasons is in the script), or the screenshot is blank. The report
is `KODI_RIG_HOME/smoke/report.json`; the exit status is 1 when anything failed. Run it before asking for an IPA and
put its result line in the PR. It is **desktop Kodi rig** evidence: it does not cover the track menus and video
controls (the rig plays no video), a real Umbrella/Elementum flow, layout against the mockups (use `boards`), or
anything on the phone. It is not wired into CI: that needs a built Kodi on the runner (about 15 minutes), which the
workflows do not have.

## Rules

- Screenshots and side-by-sides stay out of Git: they show film artwork. Attach them to the reply or PR comment and
  label them "desktop Kodi rig".
- Measurements of the approved boards: [build-193-measurements.md](build-193-measurements.md).
- Kodi quirks the rig found (ISSUE-119): a progress control bound to a window property stays empty (set bars from the
  script); a number-only label is read as a string id (`$NUMBER[n]`); `!!X` reads as `!X` (`status_ui.neg`);
  icon PNGs draw their shape in half the canvas (`status_ui.glyph`).
- The rig never replaces the owner's iPhone check.
