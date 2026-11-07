# Apple UI resources: selection, provenance and updates

Reviewed **2026-11-05**. The canonical policy is [APPLE-UI-POLICY.md](APPLE-UI-POLICY.md). Exact file hashes are in
[apple-ui-resources.lock.json](apple-ui-resources.lock.json), and `scripts/check_ui_guidance.py` verifies them.

## Selected and vendored

| Skill | Upstream | Pinned commit | Imported paths → repository | Licence |
|---|---|---|---|---|
| `apple-hig` | [justinwetch/HIGAgentSkills](https://github.com/justinwetch/HIGAgentSkills) | `2206ff935b4affa9ad249a5399a3e8e29f5f6edd` (2026-10-17; release 2026-09-27, Apple snapshot 2026-09-12) | The 167 files of its own runtime shipping manifest (`SKILL.md`, `README.md`, `routing-index.md`, `references/`, `commands/duo.md`, the two helper scripts `hig_route.py` and `hig_enforce.py`) + `LICENSE` + `NOTICE` → `.agents/skills/apple-hig/` | MIT. Apple-owned guideline material is excluded by its NOTICE. |
| `apple-liquid-glass` | [DanielJamesTronca/apple-liquid-glass-skill](https://github.com/DanielJamesTronca/apple-liquid-glass-skill) | `324b668c511556df6e5d85b082e2029a6e4ccb5a` (2026-08-14; v1.1.0) | `skills/apple-liquid-glass/` (16 files) + root `LICENSE` → `.agents/skills/apple-liquid-glass/` | MIT |

Files are copied **unchanged**. Upstream SHA-256s of the HIG runtime files were checked against the upstream's own
shipping manifest before import: all matched. Project-specific adaptations are kept separate: this file, the policy,
the `kodi-ios-ui` project skill, and the `.claude/skills/*` pointer files.

**Why these two:**

- **`apple-hig`** is the primary design authority below Apple's own pages. It covers all 157 HIG topics,
  distilled with exact values and recommendation strength kept, and each topic was source-reviewed against a dated
  Apple snapshot. It is actively maintained (15 commits, most recent 2026-10-17). It is plain markdown and needs no
  runtime. Spot-checked against Apple on 2026-11-05: the 44 × 44 pt hit region, 17/11 pt iOS text sizes, the 4.5:1 / 3:1 contrast table, and "Don't use Liquid
  Glass in the content layer" all match.
- **`apple-liquid-glass`** is for the native UIKit surface (`KodiGlassBar`) and any future native view. Its
  "should this be glass?" decision tree and its UIKit API table are directly applicable. Its `UIGlassEffect`
  availability (iOS 26.0) was verified against Apple's documentation on 2026-11-05.

### Scripts reviewed

| File | Review | Status |
|---|---|---|
| `apple-hig/scripts/hig_route.py` (122 lines) | stdlib only (`argparse`, `json`, `re`, `sys`, `pathlib`); reads the request file and skill markdown; no network, subprocess or writes | Included because the upstream SKILL.md references it. **Not executed.** Agents here route by hand (policy §3). |
| `apple-hig/scripts/hig_enforce.py` (562 lines) | stdlib only; reads files and hashes them; writes one JSON result only to a path given on the command line; no network or subprocess | Included unchanged. Only for owner-requested enforce mode. |
| `apple-liquid-glass/scripts/audit_liquid_glass.py` (426 lines) | stdlib only (`argparse`, `json`, `os`, `re`, `sys`, `dataclasses`); read-only scan of `.swift`/plist files; no network, subprocess or writes | Included unchanged. Optional; the project currently has no Swift. |

No upstream installer was run. Nothing is installed outside the repository, and no symlinks are used.

## Deferred

| Candidate | Commit inspected | Reason |
|---|---|---|
| [twostraws/SwiftUI-Agent-Skill](https://github.com/twostraws/SwiftUI-Agent-Skill) (MIT) | `f2920b63995263f57b3e198674e89a602efba6d2` | Good SwiftUI code-review skill, but the project has **no SwiftUI**. Revisit only if a native SwiftUI surface is approved. |
| [AvdLee/SwiftUI-Agent-Skill](https://github.com/AvdLee/SwiftUI-Agent-Skill) (MIT) | `204dba7c67256a8b707ee3fbc5759a824191974f` | Same reason. It overlaps with the one above, and its update skill needs the Sosumi MCP. If SwiftUI arrives, choose one of the two, not both. |
| [getsentry/MobileBuildMCP](https://github.com/getsentry/MobileBuildMCP) (MIT) | `2998ac77ebbca59544e88a27f34bfb830db9d924` | Useful native build/simulator tooling, but it needs macOS + Xcode + Node. Agents here run on Linux, and native builds run in the existing macOS Actions workflows. It is an install, not guidance; reconsider for a local Mac workflow. |

## Rejected

| Candidate | Commit inspected | Reason |
|---|---|---|
| [SudewaJay/apple-design-skill](https://github.com/SudewaJay/apple-design-skill) (MIT) | `57bfab7daf8766a9a45cfc405790e749c71eda30` | Overlaps `apple-hig` but is self-described as "synthesized" with no source review. It is aimed at web/marketing/Figma, and ships a binary `.skill` bundle. Its one useful point (do not bundle SF fonts, use Inter) is already policy. |
| [iAmVishal16/swiftui-microinteractions](https://github.com/iAmVishal16/swiftui-microinteractions) (MIT) | `ced538b0a08ec5e28a9b757d167c7b08ef14b6ac` | SwiftUI-only animation generator (about 24 MB, mostly media). Not usable in Kodi XML. Its "glass morphism" styling conflicts with HIG material rules. |
| [lrfvk/skin.tvOS-X](https://github.com/lrfvk/skin.tvOS-X) | `91083b19a23dbed61baa70de36c2906c408e14eb` (2016-09-01) | Unmaintained since 2016 (Kodi 17 GUI API). Licensed CC BY-SA 3.0, whose share-alike would bind copied code. Imitates Apple TV branding. |

## Kodi implementation reference

**[wyrm65/skin.apptv](https://github.com/wyrm65/skin.apptv)**, Apache-2.0, pinned `695b739496b8c9449cfbf7a83df10d5424c403ad`
(2026-11-02; v1.8.0 Alpha3, Kodi 21 Omega, `xbmc.gui` 5.17.0). It is **referenced, not vendored** (about 58 MB of
skin, media and Apple-TV-styled assets, mostly irrelevant here). It is useful for Kodi XML techniques under the same
renderer limits as this project:

- Rounded artwork with `diffuse` masks (`mask-squ.png`, `mask-rect.png`, `mask-fade.png`) in 28 XML windows.
  This project generates equivalent textures in code (`portrait.rounded()`, `coverage()`).
- Its `xml/DialogExtendedProgressBar.xml`, `DialogSelect.xml` and `DialogContextMenu.xml` are comparable surfaces
  to the activity pill, select card and context menu.
- It uses Inter/Roboto (OFL/Apache), not SF fonts, which confirms the approach.

Rules: read it at the pinned commit; never copy its images, sounds or icons. Copy XML code only with Apache-2.0
attribution, and it must still pass this policy. It is a 10-foot, remote-first skin, so translate its sizes with policy §4.1.

## How agents discover the guidance

| Agent | Discovery | What it gets |
|---|---|---|
| **Claude Code** | Reads `CLAUDE.md` (which imports `AGENTS.md`) automatically, and discovers project skills in `.claude/skills/<name>/SKILL.md` ([docs](https://code.claude.com/docs/en/skills)). | `kodi-ios-ui`, `apple-hig`, `apple-liquid-glass`. The `.claude/skills` files are short pointers to the canonical copies in `.agents/skills/` (one copy of each upstream file, no symlinks). |
| **Codex** (CLI/IDE/app) | Reads `AGENTS.md` automatically and scans `.agents/skills` from the working directory up to the repository root ([docs](https://learn.chatgpt.com/docs/build-skills)). | The same three skills, directly. |
| **Other agents** (Cursor, Copilot, Gemini, Aider, …) | Many read `AGENTS.md`, but skill discovery varies and is **not assumed**. | `AGENTS.md` lists the mandatory files by path: read `docs/design/APPLE-UI-POLICY.md`, then the routed files under `.agents/skills/`. |

No agent is guaranteed to load a skill automatically for every request. The policy is also linked directly from
`AGENTS.md` and `CLAUDE.md`, so a plain file read is always enough.

## Update procedure

Updates are deliberate and reviewed, never automatic:

1. Clone the upstream into a scratch directory outside the repository. Note the new commit, its date, its licence
   and any new NOTICE text.
2. Read the upstream changelog and diff from the pinned commit. Re-review any changed or new script, statically,
   before including it. Do **not** run upstream installers.
3. For `apple-hig`, copy exactly the files listed in the release's shipping manifest plus `LICENSE`/`NOTICE`. Check
   their SHA-256s against that manifest. For `apple-liquid-glass`, copy `skills/apple-liquid-glass/` plus `LICENSE`.
   Replace the whole folder; do not merge.
4. Regenerate the hashes in `apple-ui-resources.lock.json` and update the commit, date and release fields there and
   in this file.
5. Re-run the spot-checks against Apple's live documentation for any value the policy quotes. Update the policy if
   Apple changed it.
6. Run `python3 -B scripts/check_ui_guidance.py` and `python3 -B scripts/check_project.py`, and open a PR. The PR
   description lists the upstream diff summary.

A new candidate resource needs the same evaluation as above (instructions, licence, maintenance, overlap and Apple
verification) and a DECISIONS entry.
