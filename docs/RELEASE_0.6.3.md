# 0.6.3 development and release plan

## Purpose and scope

Ship the merged community publication repair and a native `wqb upgrade` command.
The source package is 0.6.2, but the last published GitHub Release is v0.6.1 as
verified on 2026-10-27. A package version, a merged commit and a published release
are separate states; the updater must never silently downgrade between them.

| Work | Implementation | Acceptance evidence |
| --- | --- | --- |
| Community publication | Retain PR #9: identity API CSRF, explicit image brand ID, no automatic write replay | Community authentication/publication regressions; no new public test posts |
| Native updates | `wqb upgrade`, `--check`, `--dry-run`, `--version VERSION`, `--reinstall`, `--allow-downgrade`, `--output`, `--status PATH --wait` | Latest/specified stable release, no-op, downgrade, failure and native Windows launcher tests |
| Update integrity | Fixed upstream GitHub repository, HTTPS allowlisted redirects, bounded downloads, SHA256SUMS and optional GitHub asset digest, wheel identity verification | Tampered bytes/metadata/URLs are rejected before pip runs; BRAIN cookies are never used |
| Environment safety | Install with the running interpreter and verify in a fresh process; reject source/editable execution and externally managed environments | Tests for environment mismatch, pip failure and post-install version verification; no worker/config/database edits |
| Issue #3 | Correct workflow docs paths, document development dependencies, add missing auth/API JSON `--output`, explain simulation timeout recovery, expose returned submit checks | Offline CLI/workflow/submission regression; keep platform errors and never infer missing checks |
| Release quality | Clean-source wheel/sdist, private-file and stale-module checks, SHA256SUMS, Windows/Linux CI configuration examples | Built and installed wheel agrees with source/version/resources; release only from a merged master commit |

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

The current GitHub OAuth credential rejected an attempted branch push containing
new Actions workflows because it lacks `workflow` scope. Keep the ready-to-enable
configurations in `docs/github_actions/`; do not claim remote CI is enabled or
silently change credential permissions. This release can use the tested local
build helper and existing `gh release` permissions after verifying the merged
commit. No workflow-scope escalation is needed for that publication path.

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

The actual Windows launcher test reproduced WinError 32 when pip tried to
uninstall the running `wqb.exe`; pip's script-writing fallback cannot solve an
earlier uninstall lock. Native Windows updates therefore verify/download first,
then return an explicit `upgrade_started` receipt and hand installation to a
one-time helper. It walks the native ancestor chain (including virtualenv Python
redirectors), waits on the exact `wqb.exe` process handle, rechecks the staged
wheel and installs only after that launcher exits. Final success is recorded
only after the fresh interpreter verifies the version. The status command can
block on the helper's handle; it does not poll. Logs, staged wheel and receipts
remain in the reported temporary job directory for diagnosis.

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

## Additional defect and dependency review

The initial audit of the exact installed runtime dependency closure (19 packages)
returned 19 advisory records across six packages. Some records duplicate the
same advisory under different IDs; this is 11 distinct GitHub advisories, not 19
independently demonstrated application vulnerabilities.

| Package | Observed version | New minimum | Evidence and applicability |
| --- | --- | --- | --- |
| certifi | 2026.5.20 | 2026.10.19 | [Compromised CA-chain trust](https://github.com/advisories/GHSA-6q48-6c7w-9gw2); relevant to authenticated HTTPS |
| urllib3 | 2.5.0 | 2.8.0 | Six advisories, including [unbounded chunk-size buffering](https://github.com/advisories/GHSA-vxq7-64xx-v4gw) and [HTTPS proxy TLS configuration](https://github.com/advisories/GHSA-8988-9cw3-xx77); transport exposure depends on server/proxy behavior |
| idna | 3.7 | 3.15 | [Resource exhaustion on crafted hostnames](https://github.com/advisories/GHSA-65pc-fj4g-8rjx); updater additionally restricts exact hosts |
| requests | 2.32.5 | 2.33.0 | [Zip utility temporary-file reuse](https://github.com/advisories/GHSA-gc5v-m9x4-r6x2); ordinary Requests calls are not the affected direct utility usage |
| msgpack | 1.1.2 | 1.2.1 | [Reuse of failed streaming Unpacker](https://github.com/advisories/GHSA-6v7p-g79w-8964); current scope reader uses one-shot unpackb, not this demonstrated trigger |
| jaraco.context | 6.0.1 | 6.1.0 | [Tar extraction traversal](https://github.com/advisories/GHSA-58pv-8j8x-9vj2); keyring dependency, with no direct CLI tarball call found |

The floors remove known vulnerable dependency versions from fresh supported
installs. They do not establish that every advisory was exploitable through the
CLI. Dependency advisories are time-dependent and require future rechecks.

The existing shared WQBRAIN environment also has arxiv 2.2.0 constraining
Requests to 2.32.x and selenium 4.34.2 constraining urllib3 to 2.5.x, plus an
older-than-required tzdata. Do not silently upgrade those unrelated tools or
declare that shared environment dependency-consistent. Test 0.6.3 in a clean
environment. Keep the reinstalled merged 0.6.2 runtime and its active research
workers unchanged until its unrelated dependency conflicts are deliberately
resolved; `upgrade` reports incompatible dependencies rather than changing them.

Also fixed a concrete crash on submission responses containing `is: null`.
Retained the explicit local pickle reader for compatibility and documented that
untrusted pickle loading can execute code; that legacy input is not made safe by
renaming a file or by the transport dependency updates.

## Release boundary

The user authorized development, installation, pushing a PR and release after
merge. This plan adds no research policy, quota gate, Alpha submission, forum
post, automatic background updater or cleanup of existing files.
