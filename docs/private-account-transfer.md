# Preserve saved keys and logins privately

The owner requires saved keys and login state to be carried forward wherever possible. The full local backup preserves all original Flatpak app-state files unchanged. A second local-only archive provides the account-state subset without add-on executable code.

Location on the source Deck:

```text
${HOME}/Kodi-iOS-Backups/20261029T180632Z/
  kodi-private-account-state.tar.zst
  ACCOUNT-SHA256SUMS
  account-state-verification.private.json
  PRIVATE-ACCOUNT-TRANSFER.txt
```

The account archive contains all 28 original add-on data directories, including saved settings, keys, tokens, account databases and associated state, plus the active core GUI, source and profile XML files. Any active `passwords.xml` or `advancedsettings.xml` would also be included; neither was present in this source. It contains 3,179 regular files, 620,869,762 bytes before compression, and 341,663,663 bytes compressed. Every archived file matched the full backup's original hashes, and selected source files remained unchanged.

The archive is credential-bearing and must never be uploaded to GitHub, including private repositories, releases, PR attachments or issues. It is outside the Git project and protected by local filesystem permissions; it is not an encrypted archive. The repository contains only these instructions and sanitized verification metadata.

## Later transfer procedure

1. Keep both the original full backup and the account archive on the Deck. Verify the latter with `sha256sum -c ACCOUNT-SHA256SUMS` from its private directory.
2. Transfer a copy through a trusted private channel to a device or computer used to manage the iPhone. Do not use a public sharing link or GitHub.
3. Install the selected iOS-compatible add-ons first and stop Kodi. Locate the actual target profile and back it up before writing any files.
4. Extract the archive into a separate private staging directory. For each retained compatible add-on, restore its `userdata/addon_data/<addon-id>/` state to the target profile. Keep associated account databases and settings together. Review platform-specific path settings separately, without printing or committing account values.
5. Do not overwrite the iPhone's entire profile or bulk-replace its GUI, display and source settings with Linux versions. Keep the core XML files as recovery references and apply only the necessary compatible account settings.
6. Exclude Umbrella from the future iOS configuration. Its preservation in a historical private backup does not authorize it for the iOS build.
7. Test account recognition before invoking a fresh login. Record only redacted status/results in GitHub.

The account files are preserved, but their use on iOS is not yet tested. Credentials held outside Kodi's files, such as browser/OS keychain items, are not captured. Services may reject expired, revoked or device-bound sessions and require reauthentication. No process here can promise that every service will accept a copied session. The goal is to reuse all compatible saved state and avoid unnecessary logins.
