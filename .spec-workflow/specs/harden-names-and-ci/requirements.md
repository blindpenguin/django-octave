# Requirements Document

## Introduction

A second, narrower security pass. It closes one finding that the first audit and `harden-generator` **missed**, one small authentication weakness, and the last open audit item (G5), plus the supply-chain basics around it.

| ID | Finding |
|----|---------|
| N1 (new) | **The project name is copied into generated source unescaped.** Reproduced: `django-octave new 'My" + __import__("os").getcwd() + "App'` writes `"TITLE": "My" + __import__("os").getcwd() + "App API"` into `config/settings/base.py` (executed on every start), the same string into `pyproject.toml`'s `description`, and further into `index.html`, Vue templates and the README. This is the same class of bug as G2 (CLI text becoming code). `add-frontend` has a second source: it reads the project title from the **first `# ` heading of `README.md`**. |
| N2 (new) | `RegisterSerializer` calls `validate_password(password)` **without the user**, so Django's `UserAttributeSimilarityValidator` (listed in `AUTH_PASSWORD_VALIDATORS`) never runs: `alice@example.com` can register with the password `alice@example`. |
| G5 | The release workflow publishes without running tests or lint, third-party actions are pinned by mutable tag, and no workflow runs on pull requests. |
| N3 (small) | Documentation gaps for production: CORS origins in `.env.example` are localhost values, Django admin login is not rate limited, JWT refresh tokens are not revocable. |

Out of scope (decided or deferred): pagination of list endpoints (the SPA would silently show only the first page; needs SPA paging first), a CSP for the SPA, token blacklisting, removing the registration enumeration message (accepted risk), the SPA tenant picker, the DRY/refactor items from the audit.

## Alignment with Product Vision

A generator must not turn text typed at the prompt, or found in a README, into executable code. Registration must apply the password rules the project itself declares. A project that publishes releases and tells users to trust its generated defaults should test itself before it ships and pin what it executes.

## Requirements

### Requirement 1 — project names are validated before they reach any template (N1)

**User Story:** As a developer running `new`, I want unsafe project names refused, so that generated files never contain code I did not write.

#### Acceptance Criteria

1. WHEN `new` receives a project name (argument or prompt) THEN the system SHALL accept only names of 1–64 characters that start with a letter or digit and otherwise contain only letters, digits (Unicode allowed), spaces, `.`, `-` and `_`.
2. WHEN the name violates that rule THEN `new` SHALL exit with status 1 (or 2 for a Typer `BadParameter`), print the rule and the offending name, and write nothing.
3. WHEN the name contains quotes, backslashes, angle brackets, braces, `$`, `` ` ``, control characters (including newlines) or other characters outside the allowed set THEN it SHALL be refused (this covers Python, TOML, JSON, HTML, Vue and Markdown contexts).
4. WHEN `add-frontend` derives the project title from the README heading AND that title violates the same rule THEN the system SHALL fall back to the project slug instead of using the heading, without failing the command.
5. WHEN a name is accepted THEN every generated text file SHALL parse in its own format (Python `ast`, TOML, JSON) for a representative set of allowed awkward names (spaces, dots, hyphens, Unicode letters, leading digit).
6. WHEN the existing slug rules apply (directory name, package name) THEN they SHALL be unchanged.

### Requirement 2 — registration applies the user-attribute password rules (N2)

**User Story:** As an operator, I want registration to reject passwords that resemble the account's own email, so that the declared password policy is actually enforced.

#### Acceptance Criteria

1. WHEN a client registers with a password similar to the email THEN the system SHALL reject it with HTTP 400 and the validator's message under `password`.
2. WHEN a client registers with an acceptable password THEN registration SHALL succeed as before.
3. WHEN validation fails THEN no user SHALL be created.
4. The response shape for existing error cases (mismatching confirmation, duplicate email) SHALL be unchanged.

### Requirement 3 — CI, release gate and pinned actions (G5)

**User Story:** As a maintainer, I want every pull request and every release tested, and the actions I run pinned, so that a broken or tampered build cannot be published unnoticed.

#### Acceptance Criteria

1. WHEN a pull request is opened or `master` is pushed THEN a `CI` workflow SHALL run `ruff check`, `pytest` and `mkdocs build --strict`, all of which SHALL pass on the current tree.
2. WHEN `master` is pushed or a release tag is pushed THEN the opt-in end-to-end suites (`OCTAVE_E2E=1` and `OCTAVE_E2E_DOCKER=1`) SHALL run before anything is published.
3. WHEN a release tag is pushed THEN the release job SHALL NOT start unless the unit tests, lint, docs build and both end-to-end suites passed (`needs:`).
4. WHEN workflows reference third-party actions THEN each SHALL be pinned to a full commit SHA with the version in a trailing comment; GitHub-owned actions are pinned too.
5. WHEN a pinned action has a newer release THEN Dependabot SHALL propose the update (a `github-actions` entry in `.github/dependabot.yml`).
6. The CI workflow SHALL use least-privilege permissions (`contents: read`) and SHALL NOT use secrets.
7. WHEN the repository's lint is run THEN the two known auto-fixable errors SHALL be fixed so CI starts green; `ruff format --check` is **not** part of CI in this spec (58-file reformat is a separate chore).
8. WHEN workflows are changed THEN they SHALL be syntax-validated locally and the exact commands CI runs SHALL be run locally.

### Requirement 4 — documentation and repository hygiene (N3)

**User Story:** As an operator, I want the remaining production caveats written down, so that I can decide on them knowingly.

#### Acceptance Criteria

1. WHEN reading `docs/concepts/security.md` THEN it SHALL list: change `CORS_ALLOWED_ORIGINS` from the localhost example for production; Django admin login is not rate limited (suggest network restriction or a package such as django-axes); refresh tokens are valid until expiry and cannot be revoked (suggest short lifetimes or `rest_framework_simplejwt.token_blacklist`); and the project-name rule.
2. WHEN `.gitignore` is read THEN it SHALL ignore `.claude/settings.local.json`.
3. WHEN `docs/commands/new.md` is read THEN it SHALL state the project-name rule.
4. WHEN the work is done THEN `docs/code-audit-2026-11-23.md` SHALL record N1–N3 (new findings) and G5 as fixed.

## Non-Functional Requirements

### Code Architecture and Modularity
- **Single Responsibility Principle**: one function decides whether a name is safe; commands and the README fallback both call it.
- **Modular Design**: workflows share the same verification steps through a reusable workflow or identical job definitions, not three divergent copies.
- **Dependency Management**: no new Python dependencies; no new third-party actions beyond those already in use.
- **Clear Interfaces**: the error for a bad name is a `ValueError` subclass already handled by `new`.

### Performance
- CI uses the uv cache; the unit job should finish in a few minutes, e2e jobs run only on `master` pushes and release tags.

### Security
- Fail closed: anything outside the allowed name set is refused.
- Workflows run with `permissions: {}` by default and grant only what a job needs; actions pinned by SHA; no `pull_request_target`.

### Reliability
- Release publishing cannot be reached when tests fail; a flaky network in e2e jobs fails the release, which is preferable to publishing an untested build.

### Usability
- The name error states the rule in one line and shows the rejected value.
