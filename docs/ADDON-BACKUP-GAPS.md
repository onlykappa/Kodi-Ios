# Backing up the add-ons: what is missing (owner request 2026-11-26)

Facts come from the owner's phone log (build 722, 2026-11-26: 143 installed add-ons, ids and versions only), compared with the build-679 IPA and the source locks in this repository. `reports/phone-addon-inventory.json` has every row. Evidence class: log read plus host comparison; nothing was run on the phone.

## What the log shows
* **Umbrella 6.8.02** is installed from **repository.umbrella 2.2.6**, and Umbrella runs its own update check at every start ("Addon checking available updates"). It is not part of the IPA.
* Other repositories installed: repository.cocoscrapers, repository.jurialmunkey, repository.loop, repository.xbmc.org. Kodi can update add-ons from these on its own.
* Of 143 add-ons, 124 are inside the build-679 IPA and 19 exist only on the phone. Of those 19, two are covered by a lock (script.module.cocoscrapers, and plugin.video.umbrella since this change). **17 are in neither the IPA nor any lock:** plugin.video.the-loop 8.4, plugin.video.looptv, plugin.video.loopguide, plugin.video.jetproxy, script.module.jetextractors 3.3.34, plugin.video.youtube 7.4.4a, plugin.video.dailymotion_com, repository.umbrella 2.2.6, script.kodi.loguploader, and eight helper modules (script.module.go, pyamf, pyjsparser, pytz, tzdata, tzlocal, defusedxml, backports.zoneinfo).
* Version drift: eight add-ons on the phone are newer than the IPA's copy (TMDb metadata scrapers, music metadata, versioncheck): the phone updated them from a repository.

## Umbrella: pinned
`migration/umbrella/source-lock.json` pins the exact upstream package for 6.8.02: commit `ba0d5e2a8fec793ffe90c6c1248e873f9f84dae3` of `umbrellaplug/umbrellaplug.github.io`, the zip `omega/zips/plugin.video.umbrella/plugin.video.umbrella-6.8.02.zip` (14,249,945 bytes, 1,782 files, GPL-3.0, no native code), SHA-256 `30a437e8...a5a5`. `scripts/fetch_umbrella.py` re-fetches and verifies it with git, or uses a preserved copy by digest (tested against a local git repository; the real fetch was run once and matched). Not yet done for it: a preserved copy in your private release (I cannot upload there from this session), a rights review, and a byte-for-byte comparison with the files on your phone (Umbrella can update itself, so the phone could differ; the version number matches).

## Gaps, in order
| # | Gap | Needed |
| --- | --- | --- |
| 1 | Umbrella and repository.umbrella: pinned, no preserved copy | upload `plugin.video.umbrella-6.8.02.zip` (run the fetch script) and repository.umbrella 2.2.6 to the private release; rights note |
| 2 | The Loop add-ons, JetExtractors, JetProxy, YouTube, Dailymotion and their eight helper modules: not locked, not in the IPA | decide which you use; pin and preserve those; note that JetExtractors' access checks are not to be bypassed |
| 3 | Updates from repositories | turn off add-on auto-update for the pinned add-ons and Umbrella's own update check, so a known-good copy cannot be swapped; keep a last-known-good version to roll back to |
| 4 | The 124 add-ons inside the IPA are preserved only as release IPAs, not hash-locked one by one | generate a per-add-on lock from the IPA (ids, versions, digests) |
| 5 | Crew's remote modules, Elementum's native build inputs, Kodi's own source and dependency mirrors, build hosting, rebuild drill | as listed in the gap analysis already given (roadmap steps 21 to 26) |

## What I need from you
Which of the Loop, Jet, YouTube and Dailymotion add-ons you actually use; whether you want add-on and Umbrella auto-updates turned off; and permission to store the preserved zips in the private release (or tell me to use Git LFS in the repository instead, which I can do from here).


## Update 2026-11-26 (later): what you actually use, from your logs
Seventeen uploaded phone logs, counted by add-on activity (not just the startup list):
* **In real use:** Umbrella, Elementum (thousands of lines), Crew (Sports: "Crew NCAAF 19 games, 19 streams" and similar), Google Drive, CocoScrapers.
* **YouTube: not used.** Its only log lines are its background service starting and a warning; there is no playback. It is only an *optional* dependency of Umbrella, so it is not pinned.
* **The Loop family: no activity in the logs, but the Sports code needs it.** `sports_jet.py` plays through Crew when Crew is installed, and falls back to The Loop's routes when it is not; it also imports `script.module.jetextractors` and plays through `plugin.video.jetproxy`. The Loop 8.4 hard-requires looptv, loopguide and dailymotion_com (that is why those three are installed), plus jetextractors and the helper modules. So these are kept as the Sports fallback, not as things you use by hand.
* **Not pinned on purpose:** YouTube, and the log uploader (Kodi's own component).

Pinned now, `migration/loop-addons/source-lock.json`: 14 add-ons (The Loop 8.4, Loop TV, Loop Guide, Dailymotion 2.4.5, JetExtractors 3.3.34, JetProxy 1.1.0 and eight helper modules), 8.25 MB. Every version is identical to your phone's. All 14 were downloaded live and passed the digest, manifest and safe-archive checks of the existing provider fetcher; every non-optional dependency is pinned in one of the locks or ships in the IPA (a test checks it). Sources: loopaddon.uk (it answers Kodi's client only, fetched the way Kodi does, as you approved on 2026-11-15) and Kodi's official add-on mirror.

`migration/umbrella/source-lock.json` now also pins repository.umbrella 2.2.6 (its address list follows the upstream `master` branch, a moving target; the package pin is by commit).

Still to do: store preserved copies (Umbrella 14.2 MB, repository 0.2 MB, Loop/Jet set 8.3 MB: about 23 MB), review rights, stop silent updates (the Loop and Umbrella repositories both feed Kodi's updater), and the Loop repository itself remains a third-party host that serves only Kodi's client.
