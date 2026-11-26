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
