# 0.6.3 development and release plan

## Purpose and scope

Ship the merged community publication repair and a native `wqb upgrade` command.
The source package is 0.6.2, but the last published GitHub Release is v0.6.1 as
verified on 2026-10-27. A package version, a merged commit and a published release
are separate states; the updater must never silently downgrade between them.

| Work | Implementation | Acceptance evidence |
| --- | --- | --- |
| Community publication | Retain PR #9: identity API CSRF, explicit image brand ID, no automatic write replay | Community authentication/publication regressions; no new public test posts |
| Native updates | `wqb upgrade`, `--check`, `--dry-run`, `--version VERSION`, `--reinstall`, `--allow-downgrade`, `--output` | Latest/specified stable release, no-op, downgrade, failure and native Windows launcher tests |
| Update integrity | Fixed upstream GitHub repository, HTTPS allowlisted redirects, bounded downloads, SHA256SUMS and optional GitHub asset digest, wheel identity verification | Tampered bytes/metadata/URLs are rejected before pip runs; BRAIN cookies are never used |
| Environment safety | Install with the running interpreter and verify in a fresh process; reject source/editable execution and externally managed environments | Tests for environment mismatch, pip failure and post-install version verification; no worker/config/database edits |
| Issue #3 | Correct workflow docs paths, document development dependencies, add missing auth/API JSON `--output`, explain simulation timeout recovery, expose returned submit checks | Offline CLI/workflow/submission regression; keep platform errors and never infer missing checks |
| Release quality | Clean-source wheel/sdist, private-file and stale-module checks, SHA256SUMS, Windows/Linux CI | Built and installed wheel agrees with source/version/resources; release only from a merged master commit |

## Execution order

1. Fetch and verify merged PR #9; reinstall a clean wheel built from its exact
   merged commit in WQBRAIN, preserving dependencies and private runtime data.
2. Develop on `feat/upgrade-0.6.3`; record scoped issue/security findings and
   implement the command, fixes, documentation and regression coverage.
3. Run offline regressions, dependency advisory checks and clean package checks.
   Keep findings distinct from a claim of a complete security audit.
4. Commit, push and open a reviewable PR against master, with test evidence.
5. After that PR is merged, tag its master commit as v0.6.3 and publish the wheel,
   sdist and SHA256SUMS. Verify the downloaded release and native update path.
   An unmerged branch is never a stable release.

## Command contract

`wqb upgrade` selects the latest published stable GitHub Release. `--version`
selects an exact stable release tag (with or without `v`). `--check` and
`--dry-run` fetch release metadata without installing. An older latest release
is a no-op; an explicit downgrade additionally requires `--allow-downgrade`.
The same version is a no-op unless `--reinstall` is supplied.

The updater installs only a verified universal wheel into the running Python
environment, without changing dependency versions. Missing/incompatible
dependencies are reported before installation. Ordinary pip errors retain the
installer output and a nonzero exit status; partial installation is not called
success. Successful installation is confirmed by a fresh isolated Python process.
Already-running processes retain their loaded code; the updater does not restart
research workers or rewrite queues, credentials, cookies or databases.

## Issue and forum review

Open issue: <https://github.com/untuitivist/wqb_cli/issues/3>, including all three
comments, read on 2026-10-27. Reproduced missing workflow docs nodes and missing
development pytest dependency. The existing simulation docs already distinguish
HTTP acceptance from completion, but recovery and GLB examples need correction.

The configured local community cache last completed synchronization on
2026-10-26 16:54 UTC (less than 24 hours before this review). Native sqlitecom
search for `"CLI" OR "CSRF" OR "upgrade"` returned no matches. No community
endorsement is inferred; PR #9 tests, this repository's issue and official
packaging/release documentation provide the implementation evidence.

Primary references:

- <https://pip.pypa.io/en/stable/cli/pip_install/>
- <https://docs.github.com/en/rest/releases/releases#get-the-latest-release>
- <https://github.com/untuitivist/wqb_cli/pull/9>

## Release boundary

The user authorized development, installation, pushing a PR and release after
merge. This plan adds no research policy, quota gate, Alpha submission, forum
post, automatic background updater or cleanup of existing files.
