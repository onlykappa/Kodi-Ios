# Publication boundary

The GitHub repository is private, but privacy does not make raw credentials acceptable to upload. The full backup is local-only. Its verification metadata may be shared; its contents, filename inventory and redaction reverse map may not.

## Included

The snapshot is constructed from a limited file allowlist. It includes skin UI settings, menu/widget JSON, custom player definitions, keymaps, playlists, source placeholders and four GUI settings: skin, language, country and mouse input. Original source bytes used for snapshot creation were checked against the verified backup manifest.

The export removes sensitive setting/key names, generated GUID/hash fields, opaque values, email addresses and network endpoints. It normalizes paths into Kodi `special://` paths when they refer to this profile or application. Other private paths become `${LOCAL_MEDIA_ROOT_NN}` placeholders; network endpoints become `${NETWORK_SOURCE_NN}` placeholders. Source names are anonymized. These placeholders require manual configuration and are not runtime settings.

Umbrella references remain in this sanitized historical snapshot for review. That does not select Umbrella for iOS. No add-on code or binary is distributed in the repository.

## Excluded

Raw add-on account settings, API keys, OAuth data, login information, profiles, favourites, databases, watch history, caches, thumbnails, downloaded add-on packages, logs, executable add-ons, personal media, full backups and the private reverse map are excluded.

## Checks

`scripts/check_project.py` checks every repository working file outside `.git`, enforces file type and size boundaries, parses JSON/XML, verifies snapshot file hashes/coverage, checks playlist references and compares plugin references against the installed manifest inventory. Its optional source-data check compares all candidate private values found in original XML/JSON against all publishable files, without printing any values.

Credential patterns include GitHub, Google API/OAuth, AWS access IDs, Slack, JWTs, private keys, credential-bearing URLs and common assigned secrets. Percent-encoded text is decoded before scanning. Missing plugins and invalid manifests are explicitly recorded as existing issues; new discrepancies fail validation.

After initializing Git, use `--git-history` to scan every historical blob reachable from local refs as well as the working files. `python3 -B scripts/test_checks.py` verifies nine success/rejection cases, including encoded credential URLs, source-value leaks, missing playlists, tampering and symlinks.

The original Deck's shell cannot resolve external hosts, and no external secret scanner is installed. The scanner here uses Python's standard library, not Gitleaks or TruffleHog. Passing results describe these checks and do not prove that every conceivable secret is absent. No raw files are staged as an intermediate step. All commits must pass scanning before publication, and publication must include only reviewed text files.
