# Tasks Document

- [x] 1.0 Tooling and skeleton
  - [x] 1.1 MkDocs Material deps, mkdocs.yml, gitignore site/
    - Files: `pyproject.toml`, `mkdocs.yml`, `.gitignore`
    - Add `mkdocs-material` to uv dev group; configure site_name, theme, markdown_extensions, plugins, nav skeleton matching design IA; ignore `site/`
    - Purpose: Docs toolchain boots locally
    - _Leverage: design.md mkdocs.yml sketch_
    - _Requirements: 1.1–1.5_
    - _Prompt: Implement the task for spec user-docs, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Docs/DevEx engineer | Task: Wire MkDocs Material + mkdocs.yml + gitignore | Restrictions: Dev-only deps; no runtime CLI dependency; no Sphinx | Success: `uv sync` + `uv run mkdocs build` succeeds once stub pages exist (or create minimal stubs in this task) | Log with log-implementation then mark [x] in tasks.md_

  - [x] 1.2 Create docs directory tree with stub pages
    - Files: `docs/index.md`, `docs/getting-started/*`, `docs/concepts/*`, `docs/commands/*`, `docs/development/*`
    - Create all nav-linked Markdown files with H1 titles + short placeholders if content comes later; keep existing `docs/roadmap.md`
    - Purpose: Nav resolves without missing files
    - _Leverage: design file tree_
    - _Requirements: 2.1_
    - _Prompt: Implement the task for spec user-docs, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer | Task: Create full docs/ tree matching mkdocs nav | Restrictions: Do not delete roadmap.md; English only | Success: `uv run mkdocs build --strict` green | Log + mark complete_

- [x] 2.0 Content migration
  - [x] 2.1 Getting started + concepts
    - Files: `docs/index.md`, `docs/getting-started/`, `docs/concepts/`
    - Write overview, install, first project; layout, Docker, multitenancy, Celery guides (from README + accurate CLI)
    - Purpose: Learning path without command dump
    - _Leverage: README.md, design admonitions_
    - _Requirements: 2.1–2.4, 4.3–4.4_
    - _Prompt: Implement the task for spec user-docs, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer | Task: Author getting-started and concepts pages | Restrictions: MDX-safe; Celery Beat warning; opt-ins clearly optional | Success: Pages are copy-paste accurate; build --strict still green | Log + mark complete_

  - [x] 2.2 Command reference pages
    - Files: `docs/commands/*.md`
    - One page per shipped command with examples, key flags, files changed, next steps (migrate from README)
    - Purpose: Curated command docs
    - _Leverage: README.md, commands/*.py help text_
    - _Requirements: 2.2, 4.1–4.2_
    - _Prompt: Implement the task for spec user-docs, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer / CLI specialist | Task: Author all commands/*.md pages | Restrictions: No verbatim Typer dump; match current flags | Success: All shipped commands covered; build --strict green | Log + mark complete_

  - [x] 2.3 Development pages + slim README
    - Files: `docs/development/contributing.md`, `docs/development/releases.md`, `README.md`, `docs/roadmap.md` as needed
    - Move pytest/Ruff/Spec/release how-tos into development docs; slim README to front door with docs links; note docs DoD for future features
    - Purpose: Scannable GitHub landing + maintainer docs
    - _Leverage: README Development/Release sections_
    - _Requirements: 3.1–3.4, 4.5, 6.1–6.3_
    - _Prompt: Implement the task for spec user-docs, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer | Task: Write development docs and slim README | Restrictions: Do not leave detailed command catalog in README; keep license + install | Success: README short; links to docs; build --strict green | Log + mark complete_

- [x] 3.0 Publish and polish
  - [x] 3.1 GitHub Actions docs build + Pages deploy
    - Files: `.github/workflows/docs.yml` (and/or deploy workflow), `mkdocs.yml` `site_url`
    - PR/push: `mkdocs build --strict`; master: deploy `site/` to GitHub Pages via official actions; document Settings → Pages if needed
    - Purpose: Online docs + CI link check
    - _Leverage: design CI notes, existing release.yml style_
    - _Requirements: 1.3–1.4, 5.1–5.3_
    - _Prompt: Implement the task for spec user-docs, first run spec-workflow-guide to get the workflow guide then implement the task: Role: DevOps engineer | Task: Add docs CI and Pages deploy workflows | Restrictions: No secrets in docs; do not break release.yml | Success: Workflow files valid; local build --strict still green | Log + mark complete_

  - [x] 3.2 Steering touch-up + roadmap shipped
    - Files: `.spec-workflow/steering/structure.md` (and tech.md Docs line if needed), `docs/roadmap.md`
    - Point Documentation Standards at MkDocs + slim README; mark user-docs shipped on roadmap
    - Purpose: Repo conventions match reality
    - _Leverage: design steering note_
    - _Requirements: 6.1–6.3_
    - _Prompt: Implement the task for spec user-docs, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Maintainer | Task: Update steering docs standards + roadmap shipped table | Restrictions: Tiny steering edits only; English | Success: Roadmap lists user-docs; structure mentions MkDocs | Log + mark complete_
