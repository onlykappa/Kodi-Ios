# Preserved archive rights review

Date: 2026-11-26. Scope: the 17 archives in `migration/addon-preserve/` (list and digests in `manifest.json`). Method: the license text each package declares in its own `addon.xml`, read from the stored archive, plus the notice file the manifest names. This is a metadata review, not a file-by-file clearance and not a legal opinion. Sibling document: [SOURCE-PROVIDER-RIGHTS-REVIEW.md](SOURCE-PROVIDER-RIGHTS-REVIEW.md) (provider archives).

| Archive | Declared license | Notes |
| --- | --- | --- |
| plugin.video.umbrella 6.8.02 | GPL-3.0 | Notice file `LICENSE.txt` present. Two secret-shaped strings were reviewed in the scanner (public API keys of the add-on itself). |
| repository.umbrella 2.2.6 | none declared | Repository descriptor only. Provider is "Umbrella". |
| plugin.video.dailymotion_com 2.4.5 | GPL-2.0-or-later | Notice present. |
| plugin.video.jetproxy 1.1.0 | none declared | No notice file; only `addon.xml`. Unresolved. |
| plugin.video.loopguide 3.8.4 | GPL-3.0 | Notice is `addon.xml` only. |
| plugin.video.looptv 26+matrix.2 | GPL-3.0 | Notice is `addon.xml` only. |
| plugin.video.the-loop 8.4 | GPL-2.0-or-later | One secret-shaped string reviewed. |
| script.module.backports.zoneinfo, tzdata | Apache-2.0 | Notice present. |
| script.module.defusedxml | PSF | Notice present. |
| script.module.go 1.0.5.1 | "See upstream" (bogdanfinn/tls-client and its dependencies) | Contains native code; the license is not stated in the package. Unresolved. |
| script.module.jetextractors, pyamf, pyjsparser, pytz, tzlocal | MIT | Notice present. |
| crew-remote-modules 936547cf | none declared | Four `.xml` files that the Crew add-on downloads and runs. Upstream `posadka/xmls2` has no stated license in the stored copy, and one JWT-shaped string was reviewed. Unresolved. |

## What this means

- Most archives are GPL, MIT, Apache or PSF. Keeping and redistributing those inside a private repository is ordinary practice, provided the notice stays with the archive (the zips are stored unchanged, so it does).
- Three have no declared license (jetproxy, repository.umbrella, crew-remote-modules) and one points elsewhere (script.module.go). Without a license nobody has granted permission to copy them. They are kept as a private, personal-use backup that is not published. Do not distribute them (for example in a public release or IPA) until the owner decides, or the authors are asked.
- A declared license does not clear individual images, or code bundled inside a package.
- The IPA already contains the add-ons it bundles; this review only concerns the extra backup copies.

## Decision needed from the owner

Keep the four unresolved archives private only (recommended: the repository is private and the app is for personal use), or drop them from the backup. Record the answer in `docs/DECISIONS.md`.

## Own ports of JetExtractors scrapers (DEC-066 follow-up, 2026-11-27)
JetExtractors is MIT-licensed ((c) 2020 t4ils). Scrapers we port keep that notice in their module docstring. Its `jsunpack.py` is GPL v3 (urlresolver) and is NOT copied: `sports_embed.unpack` is our own code. Ported so far: LiveFeeds (`sports_livefeeds.py`, listing and links; stream resolution through `sports_embed.py`). Still read through The Loop: ReedStreams, Embedsport2, EmbedHD API, XYZAlt, 720pStream. The sites themselves remain third parties.
