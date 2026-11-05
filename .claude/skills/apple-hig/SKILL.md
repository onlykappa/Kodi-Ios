---
name: apple-hig
description: Apple Human Interface Guidelines reference (vendored, pinned release 2026-09-27). Use when designing, reviewing or fixing Kodi iOS UI, or for exact HIG rules on components, sizing, typography, colour, materials, motion and accessibility. In this repository read docs/design/APPLE-UI-POLICY.md first; it says which HIG files apply to Kodi skin XML versus native UIKit.
---

# Apple HIG (Claude Code pointer)

The vendored, unmodified skill lives at `.agents/skills/apple-hig/` (repository root). Treat that directory as
the skill root. Read `.agents/skills/apple-hig/SKILL.md` and follow its loading protocol, reading files from
that directory.

Project adaptations (they override the upstream instructions in this repository):
- Read `docs/design/APPLE-UI-POLICY.md` first. Kodi skin XML cannot use SwiftUI/UIKit APIs, live blur or SF Symbols.
- Do not install the `/duo` command anywhere. iPhone Duo is not a target device.
- Route with `routing-index.md` by hand. Do not run the bundled scripts unless the owner asks for enforce mode.
- Apple's live documentation outranks this summary when they conflict.
