# Requirements Document

## Introduction

django-octave’s README has become a long command catalog. Solo developers need a **proper user guide**: install → first project → day-to-day generators → concepts (layout, Docker, tenancy, Celery) → contributing/releases — with the **README as a short front door** that links into docs.

This feature adds a **MkDocs Material** documentation site under `docs/`, thins the README, and (optionally) publishes via GitHub Pages so usage docs live outside chat history and a single scrolling Markdown file.

## Alignment with Product Vision

- Steering **product.md** lists a **docs site** under Potential Enhancements and calls out “adoption clarity” as a success metric.
- Solo-dev ergonomics: discoverable how-tos without reading the whole README or Typer `--help` alone.
- Opinionated stack: docs encode the same opinions as the generators (layout, flags, opt-ins).
- Does **not** change generator behavior; documentation and packaging of docs only.

## Requirements

### Requirement 1 — Documentation site and tool chain

**User Story:** As a solo developer, I want browsable HTML docs for django-octave, so that I can learn the tool without scanning a huge README.

#### Acceptance Criteria

1. WHEN the repo is set up for docs THEN the project SHALL use **MkDocs** with the **Material** theme, configured via `mkdocs.yml` at the repo root.
2. WHEN a contributor installs docs dependencies THEN they SHALL be available via a uv **dev** (or dedicated docs) dependency group (e.g. `mkdocs-material`), not as a runtime dependency of the CLI package.
3. WHEN a contributor runs the documented serve command THEN MkDocs SHALL serve the site locally (e.g. `uv run mkdocs serve`).
4. WHEN MkDocs builds THEN output SHALL land under `site/` and `site/` SHALL be gitignored.
5. The docs toolchain SHALL NOT require Sphinx or a separate docs package layout outside this repo.

### Requirement 2 — Information architecture

**User Story:** As a new user, I want a clear path from “what is this?” to “generate my API,” so that I am not dumped into a flat command dump.

#### Acceptance Criteria

1. Docs SHALL include at least these sections (names may vary slightly in nav):
   - **Home / overview** (`docs/index.md`)
   - **Getting started** (install generator, `new`, first `uv sync` / migrate / run, OpenAPI)
   - **Project layout** (generated `config/`, `apps/`, `core`, settings, tests)
   - **Commands** — one page (or tight cluster) per major CLI surface: `new`, `add`, `add-model`, `add-serializer`, `add-viewset`, `add-permission`, `add-action`, `add-admin`, `add-test`, `add-celery` / `add-task`
   - **Guides** for optional stacks: Docker, multitenancy, Celery/workers/Beat
   - **Development** (contributing to the generator: pytest, Ruff, Spec Workflow, releases)
   - **Roadmap** — retain `docs/roadmap.md` content, linked from nav (not deleted)
2. Command pages SHALL emphasize **examples**, flags that matter, and **what files change** — not a verbatim dump of Typer help.
3. Docs SHALL use relative links between pages; broken internal links are a defect.
4. Content SHALL remain MDX-safe / plain Markdown suitable for MkDocs (no unescaped `{` JSX pitfalls in prose where avoidable; fence code normally).

### Requirement 3 — Slim README as front door

**User Story:** As a GitHub visitor, I want a short README that tells me what the tool is and where to go next, so that the repo landing page stays scannable.

#### Acceptance Criteria

1. WHEN docs ship THEN `README.md` SHALL be reduced to roughly: pitch, feature bullets, install, one quick-start `new` example, link to the docs (local path and/or published URL), requirements, license — **not** the full per-command catalog.
2. README SHALL link clearly to `docs/` (and to the published site URL once Pages is enabled).
3. Detailed command how-tos that today live only in README SHALL move into the docs pages (content may be adapted, not merely cut).
4. Generator packaging (`pyproject.toml` `readme = "README.md"`) SHALL continue to point at the slim README.

### Requirement 4 — Accuracy and coverage of shipped CLIs

**User Story:** As a user following the docs, I want instructions that match the current CLI, so that copy-paste examples work.

#### Acceptance Criteria

1. Docs SHALL cover every **shipped** user-facing command listed in the roadmap “Already shipped” table (excluding internal CI-only notes as primary how-tos).
2. Examples SHALL match current flag names (`--database`, `--docker/--no-docker`, `--celery/--no-celery`, field DSL, etc.).
3. Opt-in features (Docker, multitenancy, Celery) SHALL be documented as optional, not required for `new`.
4. Celery docs SHALL warn that `worker --beat` is not for production (separate Beat process).
5. WHEN a future generator lands THEN updating the matching docs page SHALL be part of that feature’s Definition of Done (stated in Development docs / contributing note).

### Requirement 5 — Publish (GitHub Pages)

**User Story:** As a user who does not clone the repo, I want online docs, so that I can read the guide from a browser.

#### Acceptance Criteria

1. The design SHALL include publishing docs to **GitHub Pages** (MkDocs `gh-deploy` or a `workflow` that builds and deploys `site/`).
2. IF Pages is enabled in this spec’s implementation THEN README and docs home SHALL use the stable published URL; IF Pages is deferred to a follow-up task within the same spec THEN local `mkdocs serve` remains the minimum shippable, and the Pages task remains explicit and completable without rewriting IA.
3. Deployed docs SHALL NOT commit secrets; build uses public repo content only.

### Requirement 6 — Steering / structure alignment

**User Story:** As a maintainer, I want docs layout to match project structure conventions, so that the repo stays navigable.

#### Acceptance Criteria

1. User-facing Markdown for the site SHALL live under `docs/` (plus `mkdocs.yml` at root).
2. Spec / steering artifacts SHALL remain under `.spec-workflow/` and SHALL NOT be the primary end-user docs.
3. Structure/steering docs MAY be updated lightly to point at MkDocs instead of “README-only” as the documentation standard.

## Non-Functional Requirements

### Code Architecture and Modularity

- Docs content is separate from generator runtime code; no docs build required to run `django-octave`.
- Prefer small focused Markdown pages over one mega-file.
- Nav in `mkdocs.yml` is the source of truth for IA.

### Performance

- Cold `mkdocs build` should complete in seconds on a developer machine.
- No heavy plugin stack beyond Material (and optional search already in Material) for v1 — **no** mkdocstrings Python API dump required unless cheap and useful later.

### Security

- No credentials in docs examples; use placeholders for secrets.
- Do not document committing `.env`.

### Reliability

- Docs examples should be copy-pasteable against the current CLI on Linux.
- CI MAY add a `mkdocs build --strict` job (recommended in design) so broken links fail the build.

### Usability

- Material theme defaults are fine; avoid purple-on-white “AI slop” custom brand overload — keep a clean, readable theme (neutral primary is fine).
- Prefer concrete commands over abstract prose.
- German/English: keep docs in **English** to match the README and CLI.

## Out of Scope (this spec)

- Rewriting Spec Workflow / steering as the user manual
- Auto-generating command pages solely from Typer introspection (manual curated pages are OK)
- Video tutorials
- Documenting unshipped Vue frontend in depth (short “planned” note OK)
- Changing CLI behavior or adding new generators
