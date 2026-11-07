---
name: apple-liquid-glass
description: Apple Liquid Glass guidance for native UIKit code (vendored, pinned v1.1.0). Use only for the native KodiGlassBar tab bar/search field or another native iOS view, for UIGlassEffect, glass containers, reduce-transparency behaviour or glass decisions. Not for Kodi skin XML, which cannot render Liquid Glass; read docs/design/APPLE-UI-POLICY.md first.
---

# Apple Liquid Glass (Claude Code pointer)

The vendored, unmodified skill lives at `.agents/skills/apple-liquid-glass/` (repository root). Treat that
directory as the skill root. Read `.agents/skills/apple-liquid-glass/SKILL.md` and its routed `references/` files.

Project adaptations (they override the upstream instructions in this repository):
- Read `docs/design/APPLE-UI-POLICY.md` first. Only `migration/glassbar-ios/` uses real Liquid Glass. Kodi-drawn
  frosted textures are "glass-styled surfaces" and must never be described as Liquid Glass.
- The project has no Swift sources and no local Xcode, and native builds run in macOS Actions workflows. Report
  native visual checks (light/dark, Reduce Transparency, Increase Contrast, Reduce Motion) as pending until run on a device.
