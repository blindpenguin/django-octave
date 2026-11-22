# django-octave

- Stack: Python **3.14+**, package layout under `src/django_octave/`, managed with **uv** (`pyproject.toml`)
- Run everything via uv: `uv sync`, `uv add <pkg>`, `uv add --dev <pkg>`, `uv run <cmd>`
- Prefer Ruff (lint/format) and pytest once configured in `pyproject.toml`; do not introduce Black/isort/flake8
- Never commit secrets, `.env`, or credentials; read settings from the environment
- Do not edit `.venv/`, build artifacts, or lockfiles unless dependency changes require it
- Match existing project patterns; no drive-by refactors or unrelated files
- For non-trivial features, follow Spec Workflow (see Spec Workflow below) before large implementation

Path-scoped conventions live in `.claude/rules/` (Python, Django, pytest) and load automatically when matching files are touched.

## Spec Workflow

Use the **spec-workflow** MCP (configured in `.mcp.json`) for feature work, refactors, and non-trivial bugs. Do not invent a parallel process.

### Sequence (never skip)

1. Steering (once per project) → product / tech / structure
2. Spec: **requirements** → approval
3. Spec: **design** → approval
4. Spec: **tasks** → review
5. Implement tasks one at a time via MCP tools
6. Mark tasks complete as you finish them

Never write design before approved requirements. Never implement before approved design + reviewed tasks.

### When the user asks for a feature

1. Call `spec-workflow-guide` (or inject guide) if context is missing
2. Prefer MCP tools (`create-spec-doc`, `spec-list`, `spec-status`, `manage-tasks`, approvals) over free-form markdown outside `.spec-workflow/`
3. Spec names: kebab-case (`user-auth`, not `UserAuth`)
4. After creating/updating a doc, request approval and wait — do not advance the phase until approved
5. On implementation: `get-spec-context` + steering context, then implement the next pending task only

### Approvals

- Approvals happen in the Spec Workflow dashboard (`./scripts/spec-dashboard.sh` → http://localhost:5000) or the VS Code extension
- If approval is pending, tell the user to review there; do not pretend approval happened
- On change requests: revise the doc, re-request approval

### Prompt cues

Treat these as workflow triggers: "create a spec for…", "list specs", "implement task X from…", "create steering documents", "refresh tasks".

### Artifacts

All workflow files live under `.spec-workflow/` (steering, specs, approvals). Keep implementation code in the normal project tree (`src/`, etc.).

## Commits

Use **[Conventional Commits](https://www.conventionalcommits.org/)** so `scripts/release-notes.py` can build GitHub Release notes.

### Format

```text
type(scope): short imperative summary

Optional body: why, not a file dump.
```

- **Subject**: ≤72 chars, imperative, no trailing period
- **type** (required): `feat` | `fix` | `docs` | `refactor` | `test` | `chore` | `ci` | `perf`
- **scope** (optional): area touched — e.g. `add`, `add-model`, `celery`, `docs`, `release`, `serializers`
- **Breaking**: `feat(api)!: …` or a footer line `BREAKING CHANGE: …`

### Types → release notes

| type | Appears as |
|------|------------|
| `feat` | Features |
| `fix` | Fixes |
| `docs` | Documentation |
| `perf` | Performance |
| others | skip in user-facing notes (still commit normally) |

Version bumps: `chore(release): 0.2.3` only (no feature narrative in that commit).

### Examples

```text
feat(add): support --model for starter class name
fix(serializers): insert nested helpers before parent class
docs(layout): document shared api/ mount paths
chore(release): 0.2.3
```

### Do not

- Vague subjects: `update`, `fixes`, `wip`, `Release 0.2.2: …` as a grab-bag
- Stack unrelated features in one commit when they should be separate changelog entries
- Skip the type prefix — plain prose breaks release-note extraction
