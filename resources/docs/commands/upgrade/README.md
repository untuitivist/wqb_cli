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
python -I -m wqb_cli upgrade --status <status_path> --wait
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
  before retrying.
- A running Windows `wqb.exe` locks its launcher. It verifies the download, then
  starts a one-time helper that waits for that exact launcher process to exit
  before invoking pip. The initial receipt is `upgrade_started`, with
  `installed: false`, `status_path` and `log_path`. This is acceptance, not success.
  The helper writes the final receipt and updates `--output` when supplied.
- To inspect or wait for a Windows job, use the Python module command above;
  this avoids holding another `wqb.exe` open during replacement. `--wait` blocks
  on the process handle for at most 60 seconds. Only `status: updated` with
  `installed: true` confirms installation and fresh-process version verification.
  A timed-out wait can still be pending. A helper that exits without a final
  receipt reports an unknown outcome. Keep the verified wheel, log and receipt
  in the reported temporary job directory for diagnosis.
- `--output` saves the JSON receipt; it suppresses stdout like other CLI commands.

This command never schedules recurring updates or publishes a release. The
Windows helper belongs only to the explicit update invocation.
