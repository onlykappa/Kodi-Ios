# Proposed isolated GitHub Actions test executor

Status: APPROVED by owner for the capped GitHub Actions test job. Workflow prepared for publication; execution result pending. The current session denies local sockets. This would rerun the unchanged pinned upstream suite on an ephemeral Linux runner, with no repository checkout, secrets, Google account or personal media, and a five-minute job timeout. Existing GitHub plan allowances/billing apply; no free-minute balance has been verified. It does not deploy a media host or begin Phase 4.

Owner approved installing the following as `.github/workflows/drive-upstream.yml` on the existing PR branch only. Retain the original failed run. Inspect resulting check logs before claiming any upstream test passes. If workflow permissions or Actions access are unavailable, retain the blocker and report it without changing the default branch or merging.

```yaml
name: Pinned Drive upstream validation
on:
  pull_request:
    types: [opened, synchronize, reopened]
    paths:
      - '.github/workflows/drive-upstream.yml'
      - 'migration/google-drive/**'
permissions: {}
concurrency:
  group: kodi-drive-upstream-tests
  cancel-in-progress: true
jobs:
  upstream:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Fetch pinned public source without credentials
        env:
          GIT_TERMINAL_PROMPT: '0'
        run: |
          git init common
          git -C common remote add origin https://github.com/cguZZman/script.module.clouddrive.common.git
          git -C common fetch --depth=1 origin 7d22102557bb95b89abcd2f055597db6f54da05c
          git -C common checkout --detach FETCH_HEAD
          test "$(git -C common rev-parse HEAD)" = 7d22102557bb95b89abcd2f055597db6f54da05c
      - name: Run all upstream tests, including loopback streaming cases
        working-directory: common
        run: |
          python3 --version
          python3 -B -m unittest discover -s tests -v
```

No third-party Actions are executed; this uses only the hosted runner's Git/Python and the reviewed pinned public upstream source. No failure suppression or continue-on-error is configured. The workflow uses no credential/token environment variables and grants no GitHub token permissions. Running it would consume a small amount of hosted compute, capped by the configured timeout, subject to GitHub's actual billing rules.
