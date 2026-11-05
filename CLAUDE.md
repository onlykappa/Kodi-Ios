# Claude Code instructions: Kodi iOS

@AGENTS.md

The shared instructions above (imported from [AGENTS.md](AGENTS.md)) apply in full.

## UI work: mandatory

Before planning, implementing or reviewing any UI change, read the canonical policy
**[docs/design/APPLE-UI-POLICY.md](docs/design/APPLE-UI-POLICY.md)**. This is the same policy that AGENTS.md
names. Use the project skills in `.claude/skills/`:

- `kodi-ios-ui`: the entry point for all UI work. It routes to the policy and the two skills below.
- `apple-hig`: the Apple HIG reference. The vendored copy is in `.agents/skills/apple-hig/`.
- `apple-liquid-glass`: native UIKit glass only. The vendored copy is in `.agents/skills/apple-liquid-glass/`.

If a skill is not offered automatically, read those files directly. The policy, not the skill list, is the requirement.
