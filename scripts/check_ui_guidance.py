#!/usr/bin/env python3
"""Check that the Apple UI guidance is present, unmodified and correctly wired up.

Detects: vendored skill files that are missing, altered or unexpected (against docs/design/apple-ui-resources.lock.json);
AGENTS.md / CLAUDE.md no longer pointing at the canonical policy; broken links or repository paths in the
project-authored guidance; HIG topics in the policy's routing table that do not exist; helper names listed in the
policy's reuse section that no longer exist in the code; and SKILL.md metadata that agents cannot load.
Standard library only; reads files, writes nothing.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = 'docs/design/APPLE-UI-POLICY.md'
RESOURCES = 'docs/design/apple-ui-resources.md'
LOCK = 'docs/design/apple-ui-resources.lock.json'
SKILLS = ('kodi-ios-ui', 'apple-hig', 'apple-liquid-glass')
AUTHORED = ['AGENTS.md', 'CLAUDE.md', POLICY, RESOURCES, '.agents/skills/kodi-ios-ui/SKILL.md'] + \
           ['.claude/skills/%s/SKILL.md' % s for s in SKILLS]
PATH_PREFIXES = ('.agents/', '.claude/', 'docs/', 'scripts/', 'migration/')
TOPIC_DIRS = ('.agents/skills/apple-hig/references/hig', '.agents/skills/apple-liquid-glass/references',
              '.agents/skills/apple-hig', '.agents/skills/apple-liquid-glass')


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frontmatter(text):
    m = re.match(r'---\n(.*?)\n---\n', text, re.S)
    if not m:
        return None
    fields = {}
    for line in m.group(1).splitlines():
        kv = re.match(r'([A-Za-z_-]+):\s*(.*)', line)
        if kv:
            key, value = kv.groups()
            fields[key] = value.strip()
        elif fields and line.startswith((' ', '\t')):  # folded continuation (e.g. `description: >`)
            last = list(fields)[-1]
            fields[last] = (fields[last].lstrip('>|').strip() + ' ' + line.strip()).strip()
    return fields


def check():
    problems = []
    def problem(path, rule, detail=''):
        problems.append({'path': path, 'rule': rule, 'detail': detail})

    for rel in AUTHORED + [LOCK]:
        if not (ROOT / rel).is_file():
            problem(rel, 'missing-required-file')

    # Vendored files: exact membership and hashes.
    vendored = 0
    if (ROOT / LOCK).is_file():
        lock = json.loads((ROOT / LOCK).read_text(encoding='utf-8'))
        for entry in lock['vendored']:
            base = ROOT / entry['imported_to']
            if not entry.get('commit') or not re.fullmatch(r'[0-9a-f]{40}', entry['commit']):
                problem(entry['imported_to'], 'unpinned-upstream')
            actual = {p.relative_to(base).as_posix() for p in base.rglob('*') if p.is_file() or p.is_symlink()} if base.is_dir() else set()
            for rel, digest in entry['files'].items():
                path = base / rel
                vendored += 1
                if not path.is_file():
                    problem(entry['imported_to'] + '/' + rel, 'vendored-file-missing')
                elif path.is_symlink():
                    problem(entry['imported_to'] + '/' + rel, 'vendored-file-is-symlink')
                elif sha256(path) != digest:
                    problem(entry['imported_to'] + '/' + rel, 'vendored-file-modified')
            for rel in sorted(actual - set(entry['files'])):
                problem(entry['imported_to'] + '/' + rel, 'unexpected-file-in-vendored-skill',
                        'project adaptations belong outside vendored folders')
            for required in ('SKILL.md', 'LICENSE'):
                if required not in entry['files']:
                    problem(entry['imported_to'], 'vendored-skill-lacks-' + required.lower())

    # Both instruction files must name the canonical policy; CLAUDE.md must import AGENTS.md.
    for rel in ('AGENTS.md', 'CLAUDE.md'):
        p = ROOT / rel
        if p.is_file() and '](%s)' % POLICY not in p.read_text(encoding='utf-8'):
            problem(rel, 'does-not-link-canonical-policy')
    if (ROOT / 'CLAUDE.md').is_file() and not re.search(r'^@AGENTS\.md\s*$', (ROOT / 'CLAUDE.md').read_text(encoding='utf-8'), re.M):
        problem('CLAUDE.md', 'does-not-import-AGENTS.md')

    # Links and repository paths in project-authored guidance.
    for rel in AUTHORED:
        p = ROOT / rel
        if not p.is_file():
            continue
        text = p.read_text(encoding='utf-8')
        for target in re.findall(r'\]\(([^)\s]+)\)', text):
            if re.match(r'[a-z]+:', target):
                continue
            path, _, anchor = target.partition('#')
            dest = (p.parent / path).resolve() if path else p
            if not dest.exists():
                problem(rel, 'broken-link', target)
            elif anchor and dest.suffix == '.md':
                slugs = {re.sub(r'[^\w\- ]', '', h.lower()).strip().replace(' ', '-')
                         for h in re.findall(r'^#+\s+(.*)', dest.read_text(encoding='utf-8'), re.M)}
                if anchor not in slugs:
                    problem(rel, 'broken-anchor', target)
        for token in re.findall(r'`([^`\s]+)`', text):
            if token.startswith(PATH_PREFIXES) and not any(c in token for c in '*<>…'):
                if not (ROOT / token.rstrip('/')).exists():
                    problem(rel, 'missing-repository-path', token)

    # Routing table: every topic file it names must exist in a vendored skill.
    policy = (ROOT / POLICY).read_text(encoding='utf-8') if (ROOT / POLICY).is_file() else ''
    routing = policy.split('## 3.', 1)[-1].split('\n## ', 1)[0]
    for name in sorted(set(re.findall(r'`(?:references/(?:hig/)?)?([a-z0-9-]+\.md)`', routing))):
        if not any((ROOT / d / name).is_file() for d in TOPIC_DIRS):
            problem(POLICY, 'routing-topic-missing', name)

    # Reuse section: helper names must still exist in the named modules.
    reuse = policy.split('## 8.', 1)[-1].split('\n## ', 1)[0]
    lib = ROOT / 'migration/bundled-bootstrap/resources/lib'
    for module, names in re.findall(r'^- `([a-z_]+\.py)`: (.*(?:\n  .*)*)', reuse, re.M):
        source = lib / module
        if not source.is_file():
            continue  # unmerged modules (e.g. PR #9) are listed by name only
        code = source.read_text(encoding='utf-8')
        for name in re.findall(r'`([A-Za-z_]+)`', names):
            if not re.search(r'(?m)^(?:def %s\(|%s\s*=|.*;%s=)' % (name, name, name), code) and \
               not re.search(r'(?m)^[A-Z_]+=.*\b%s=' % name, code):
                problem(POLICY, 'reuse-helper-missing', '%s.%s' % (module, name))

    # Skill metadata: name and description present, name matches folder; Claude pointers reach canonical copies.
    for folder in ('.agents/skills', '.claude/skills'):
        for skill_md in sorted((ROOT / folder).glob('*/SKILL.md')):
            rel = skill_md.relative_to(ROOT).as_posix()
            meta = frontmatter(skill_md.read_text(encoding='utf-8'))
            if meta is None:
                problem(rel, 'missing-frontmatter')
                continue
            if meta.get('name') != skill_md.parent.name:
                problem(rel, 'skill-name-does-not-match-folder', str(meta.get('name')))
            if not meta.get('description'):
                problem(rel, 'skill-description-missing')
            elif len(meta['description']) > 1536:
                problem(rel, 'skill-description-truncated-by-claude-code', str(len(meta['description'])))
    for skill in SKILLS:
        pointer = ROOT / '.claude/skills' / skill / 'SKILL.md'
        if pointer.is_file() and '.agents/skills/%s/' % skill not in pointer.read_text(encoding='utf-8'):
            problem(pointer.relative_to(ROOT).as_posix(), 'pointer-does-not-name-canonical-copy')

    return {'passed': not problems, 'vendored_files_verified': vendored, 'authored_files_checked': len(AUTHORED),
            'problems': problems}


if __name__ == '__main__':
    result = check()
    print(json.dumps(result, indent=1))
    sys.exit(0 if result['passed'] else 1)
