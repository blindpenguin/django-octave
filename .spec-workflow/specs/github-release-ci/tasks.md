# Tasks Document

- [x] 1.0 Distribution smoke script
  - [x] 1.1 Add `scripts/smoke_dist.py`
    - Files: `scripts/smoke_dist.py`
    - Plain `__main__` script (not pytest-collected): import package, assert templates present, run CLI `--help`
    - Purpose: Catch incomplete wheel/sdist before release
    - _Leverage: design smoke checks_
    - _Requirements: 2.1–2.3_
    - _Prompt: Implement the task for spec github-release-ci, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python packaging engineer | Task: Write smoke_dist.py for installed dist | Restrictions: stdlib only; no pytest collection; no editable src assumptions | Success: Local `uv build` + `uv run --isolated --no-project --with dist/*.whl scripts/smoke_dist.py` exits 0 | Log + mark complete_

- [x] 2.0 Release workflow
  - [x] 2.1 Add `.github/workflows/release.yml`
    - Files: `.github/workflows/release.yml`
    - Tag triggers `vX.Y.Z` (+ pre-release forms); version assert vs `pyproject.toml`; `uv build`; smoke wheel + sdist; GitHub Release with `dist/*` via softprops/action-gh-release; `contents: write`
    - Purpose: Automate GitHub Release artifacts
    - _Leverage: astral setup-uv patterns, design Architecture_
    - _Requirements: 1.1–1.4, 3.1–3.2_
    - _Prompt: Implement the task for spec github-release-ci, first run spec-workflow-guide to get the workflow guide then implement the task: Role: GitHub Actions engineer | Task: Implement release.yml without PyPI publish | Restrictions: No PyPI tokens/OIDC; fail on version mismatch or smoke failure | Success: Workflow YAML validates; steps match design | Log + mark complete_

- [x] 3.0 Docs and hygiene
  - [x] 3.1 README release instructions + ensure dist ignored
    - Files: `README.md`, `.gitignore` if needed
    - Document bump version → tag → push; link Actions/Releases; note PyPI out of scope
    - Purpose: Maintainer release runbook
    - _Leverage: existing README_
    - _Requirements: 4.1–4.2_
    - _Prompt: Implement the task for spec github-release-ci, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer | Task: Document cutting a GitHub Release | Restrictions: No Spec Workflow content; no fake PyPI install instructions | Success: Steps match workflow triggers | Log + mark complete_

  - [x] 3.2 Local verification of build + smoke
    - Files: none (run commands)
    - `uv build` then smoke against wheel and sdist; confirm pytest suite still green
    - Purpose: Confidence before first tagged release
    - _Requirements: 2.*, 5-adjacent_
    - _Prompt: Implement the task for spec github-release-ci, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA | Task: Verify build+smoke locally and pytest green | Restrictions: Do not push tags unless user asks | Success: Smoke exits 0 for wheel and sdist; pytest passes | Log + mark complete_
