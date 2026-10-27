# Optional GitHub Actions

`ci.yml.example` and `release.yml.example` are prepared configurations, not active
workflows. The current OAuth credential does not have GitHub's `workflow` scope;
GitHub rejected the push when these lived in `.github/workflows/`.

An authorized maintainer with that scope can place them in `.github/workflows/`
without the `.example` suffix. They test Python 3.11/3.13 on Windows/Linux, build
from clean Git archives and publish only stable tags whose commit is on master.
Action revisions are pinned to the verified 2026-10-27 upstream release commits.

Until enabled, run the documented local regression and clean build steps. After
the PR is merged, verify the master commit, create its version tag and use
`gh release create --verify-tag` to upload the verified artifacts. Existing
published release assets must not be silently replaced with different contents.
