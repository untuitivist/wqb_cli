# Upgrade

Update the installed CLI from this project's published stable GitHub Releases.
The command runs without BRAIN authentication or registry access.
It uses `GH_TOKEN`/`GITHUB_TOKEN` or an existing `gh auth` login when available
to avoid GitHub's anonymous API limit. It never starts an interactive login.
That token is sent only to `api.github.com`, never to release CDNs or BRAIN,
and is not included in update receipts.

```powershell
wqb upgrade --check
wqb upgrade --dry-run
wqb upgrade
wqb upgrade --version 0.6.3
wqb upgrade --version 0.6.3 --reinstall
wqb upgrade --version 0.6.1 --allow-downgrade
wqb upgrade --check --output update.json
```

- The default selects the latest stable release. If that release is older than
  the installed package, the command reports `installed_newer_than_latest` and
  keeps the installation. Exact versions require published releases, not just tags.
- `--check` and `--dry-run` read metadata only; they do not download/install a
  wheel. Download verification happens during an actual update.
- `--reinstall` permits installing the same version. A downgrade requires both
  an exact `--version` and `--allow-downgrade`.
- The wheel and `SHA256SUMS.txt` must belong to the selected upstream release.
  Downloads use HTTPS with bounded redirects, sizes and waits. Wheel SHA-256,
  GitHub asset digests when present, package identity, Python compatibility and
  installed dependencies are checked before pip runs. Checksums provide transfer
  integrity within the trusted repository; they are not independent signatures.
- Installation uses the running interpreter's pip, without a shell, package
  index or dependency changes. Missing/incompatible dependencies are reported as
  `dependency_requirements_not_met`. Install those dependencies in the intended
  environment before retrying.
- Run the installed CLI from the research workspace. Editable/source checkouts
  and externally managed system environments are not self-updated. Use a virtual
  environment or the original environment manager for those installations.
- Credentials, private local data, simulation databases and queue settings are
  not migrated or rewritten. Running workers are not restarted; already loaded
  modules keep their old code until the process is restarted deliberately.
- pip output and a fresh interpreter's version verification are returned as
  JSON. A failed/timed-out install is not success or an automatic rollback:
  inspect the reported installer result and `python -I -m wqb_cli --version`
  before retrying. On Windows, the updater uses normal pip launcher replacement.
- `--output` saves the JSON receipt; it suppresses stdout like other CLI commands.

This command does not run automatically in the background or publish a release.
