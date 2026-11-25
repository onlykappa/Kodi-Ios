# Provider archive rights and notice inventory

Date: 2026-11-24. Scope: 28 archive inputs in `migration/provider-fallback/source-lock.json`, retrieved from the existing private release and matched against the current SHA256 lock. The separately licensed Otaku mapping database is outside this archive review. This is a filename/metadata inventory and targeted header review, not a file-by-file rights clearance or legal opinion. A manifest declaration does not establish rights to individual images or bundled third-party code. Counts are archive members by image filename extension; they do not identify owners or licenses.

| Package | Manifest license text | License/notice filenames found | Image files |
| --- | --- | --- | ---: |
| plugin.video.jacktook | GPL-2.0-only | `plugin.video.jacktook/LICENSE` | 51 |
| plugin.video.pov | GNU GENERAL PUBLIC LICENSE. Version 3, 29 June 2007 | None found | 84 |
| script.module.magneto | GNU GENERAL PUBLIC LICENSE. Version 3, 29 June 2007 | None found | 19 |
| plugin.video.otaku | GPL-3.0 | None found | 42 |
| context.otaku | GPL-3.0 | None found | 441 |
| plugin.video.prism | GNU GENERAL PUBLIC LICENSE. Version 3, 29 June 2007 | None found | 394 |
| context.prism | GNU GENERAL PUBLIC LICENSE. Version 3, 29 June 2007 | None found | 4 |
| plugin.video.thecrew | GNU GENERAL PUBLIC LICENSE. Version 3, 29 June 2007 | None found | 8 |
| script.module.thecrew | GNU GENERAL PUBLIC LICENSE. Version 3, 29 June 2007 | None found | 2 |
| script.module.resolveurl | None found | None found | 15 |
| script.module.requests | Apache-2.0 | `script.module.requests/LICENSE.txt` | 1 |
| script.module.routing | GPL-3.0 | `script.module.routing/LICENSE.txt` | 1 |
| script.module.beautifulsoup4 | MIT | `script.module.beautifulsoup4/LICENSE.txt` | 1 |
| script.module.pyqrcode | BSD-3-Clause | `script.module.pyqrcode/LICENSE.md` | 1 |
| script.module.unidecode | GPL-2.0-or-later | `script.module.unidecode/LICENSE.txt` | 1 |
| script.module.myconnpy | GPLv2 | `script.module.myconnpy/LICENSE.txt` | 1 |
| script.module.simplejson | MIT | `script.module.simplejson/LICENSE.txt` | 1 |
| script.module.six | MIT | `script.module.six/LICENSE.txt` | 1 |
| script.module.inputstreamhelper | MIT | `script.module.inputstreamhelper/LICENSE.txt` | 1 |
| script.module.kodi-six | GPL v.3 | `script.module.kodi-six/LICENSE.txt` | 1 |
| script.module.certifi | MPL-2.0 | `script.module.certifi/LICENSE.txt` | 1 |
| script.module.chardet | LGPL-2.1 | `script.module.chardet/LICENSE.txt` | 1 |
| script.module.idna | BSD-3-Clause | `script.module.idna/LICENSE.txt` | 1 |
| script.module.urllib3 | MIT | `script.module.urllib3/LICENSE.txt` | 1 |
| script.module.soupsieve | MIT | `script.module.soupsieve/LICENSE.txt` | 1 |
| script.thecrew.artwork | GNU GENERAL PUBLIC LICENSE. Version 3, 29 June 2007 | None found | 436 |
| repository.loop | None found | None found | 2 |
| prism-a4k | None found | `a4kScrapers-3ef39b8a0a185a3c9f1127a2b44f99f830299e2a/LICENSE`; `a4kScrapers-3ef39b8a0a185a3c9f1127a2b44f99f830299e2a/providerModules/a4kScrapers/third_party/aws_requests_auth/LICENSE` | 0 |

## Targeted findings and decisions still needed

- **POV and Magneto:** current archive hashes are owner-selected private release bytes, not the unavailable original commit's verified bytes. The archived manifests declare GPL v3, but neither package includes a separate license or notice file. Magneto's `lib/magneto/modules/dom_parser.py` credits Parsedom authors without separate terms. The 84 POV images and 19 Magneto images lack established per-image provenance. Source origin, modifications, complete corresponding source and artwork rights remain unverified; do not present the archive label as upstream authorship proof.
- **Jacktook:** the archive contains a top-level GPL license but also vendors five Segno files with Lars Heuer copyright/BSD headers and a reported Segno version of 1.6.6. No separate Segno license was found in that archive. All five files differ from the corresponding files at Segno tag 1.6.6 (commit `9b67a3f2914be966c35dd8f00bef19d01b9ec68e`); this is not a claim that the upstream tag is the exact source of the modifications. The upstream tag's BSD text has been added as a separate notice and will be staged by the existing license-text mechanism. The bundled headers retain their own copyright years. Verify the exact origin and changes to the vendored files and review the 51 images separately.
- **Otaku:** the add-on's bundled `resources/lib/ui/pyaes/__init__.py` retains Richard Moore's MIT copyright and permission text; the installer copies retained archive files. The 42 add-on images and 441 context images have no established individual rights in this inventory. Separate mapping database terms remain unresolved and are tracked separately.
- **Prism/a4kScrapers:** the a4k archive contains an MIT license and an additional BSD notice under `providerModules/a4kScrapers/third_party/aws_requests_auth/LICENSE`; the existing selective installer retains both. Its bundled pyparsing file contains an MIT notice, while the bundled cloudscraper subtree lacks an identified separate license file in this scan. Its exact source/version and license need review. Prism's 394 images and context add-on's four images need individual provenance review.
- **Crew/ResolveURL/Loop:** Crew manifests declare GPL v3; `script.module.resolveurl/lib/resolveurl/__init__.py` has a GPL-3-or-later header despite no manifest license text. The Crew artwork package alone contains 436 images and no discovered license/notice filename: its GPL manifest does not settle rights to those images. Loop's small repository package has no manifest license text or notice file found. Identify the owners and terms of included artwork and Loop source before claiming redistribution clearance.
- **Supporting modules:** the inventory lists embedded license files as evidence, not a determination that every embedded file is covered by that text. For reused preexisting add-ons, the installer keeps the preexisting version and its contents rather than copying the locked archive, so any distribution notice audit must also inspect the actual staged copy.

Before a redistribution-ready claim, trace each applicable source and image to an identifiable licensor and terms, retain required notices in the actual distributed package, establish corresponding source for modified copyleft components, and exclude or replace material whose terms cannot be established. The user selected POV/Magneto for use pending review; that selection does not establish third-party rights. No archive or image was newly published by this review.

## Cloudscraper notice follow-up (2026-11-25)

The a4kScrapers vendored cloudscraper declares `__version__ = '1.2.60'`. The upstream 1.2.60 tag resolves to commit `d54abb0fac5743eb7122debe9807eec541613a0b` and its LICENSE is MIT (VeNoMouS and Anorov). Comparing archive members with that exact upstream tree found 10 identical files, 10 differing files, and two not present at the compared paths, including a separately MIT-noticed pyparsing file. The upstream MIT text is retained and staged through the existing notice mechanism; these differences do not establish the origin or license of every added or modified file. Exact modification provenance and complete third-party/image review remain open.
