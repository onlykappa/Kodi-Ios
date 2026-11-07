---
name: kodi-ios-ui
description: Mandatory for any Kodi iOS UI work. Use before planning, implementing or reviewing changes to layout, styling, navigation, controls, typography, icons, artwork, animation, player overlays, sheets, settings, notifications, the activity pill or sheet, loading, empty or error states, the native tab bar, or design mockups. Routes to the project's Apple UI policy and the vendored apple-hig and apple-liquid-glass skills.
---

# Kodi iOS UI

This is a project skill (not vendored). It is a thin entry point. The rules live in one place:

1. Read `docs/design/APPLE-UI-POLICY.md` in full (path from the repository root). It is the canonical policy.
2. Follow its §2 to identify which renderer you are in (Kodi skin XML, Fuse 1080i, native UIKit `KodiGlassBar`,
   Kodi C++ patch or HTML mockup). SwiftUI is not used in this project.
3. Load only the references its §3 routing table names:
   - `.agents/skills/apple-hig/SKILL.md` and its `routing-index.md` → `references/hig/*.md` (design rules).
     Route by hand; do not install `/duo` and do not start enforce mode unless the owner asks.
   - `.agents/skills/apple-liquid-glass/SKILL.md` → its `references/` (native UIKit glass only).
4. Reuse the existing helpers and tokens listed in policy §8 before creating anything new.
5. Follow the visual review process in policy §7, and label evidence by class (policy §9). Passing checks or
   builds do not prove visual quality; report device review as pending when it has not happened.

Apple's current documentation outranks every vendored summary. Provenance and update rules are in
`docs/design/apple-ui-resources.md`.
