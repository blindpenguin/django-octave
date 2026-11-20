# Tasks Document

- [x] 1.0 Celery project setup
  - [x] 1.1 Detect + write config/celery.py, __init__ load, settings, env, versions pins
    - Files: `src/django_octave/celery_gen/`, `src/django_octave/rendering/versions.py`
    - Probe existing celery; generate celery app + beat_schedule dict; patch settings/env/pyproject; force/refuse
    - Purpose: Opt-in Celery wiring
    - _Leverage: detect_project, design snippets_
    - _Requirements: 1.1–1.4_
    - _Prompt: Implement the task for spec add-celery, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django/Celery engineer | Task: Implement celery_gen setup writers with unit tests | Restrictions: No CLI yet; Redis-only broker; no django-celery-beat | Success: Unit tests create celery module, settings keys, env lines, refuse without force | Log with log-implementation then mark [x] in tasks.md_

  - [x] 1.2 Compose redis/worker/beat inject
    - Files: `src/django_octave/celery_gen/compose.py`, tests
    - Marker-block inject into docker-compose.yml when present; skip cleanly when absent
    - Purpose: Runnable workers in Docker projects
    - _Leverage: design compose services_
    - _Requirements: 1.3, 2.2_
    - _Prompt: Implement the task for spec add-celery, first run spec-workflow-guide to get the workflow guide then implement the task: Role: DevOps/Compose engineer | Task: Inject redis/worker/beat services with markers | Restrictions: Do not break existing db/web services | Success: Unit tests on sample compose YAML | Log + mark complete_

- [x] 2.0 Task generator + CLI
  - [x] 2.1 `add-task` upsert + beat_schedule merge
    - Files: `src/django_octave/celery_gen/task_gen.py`, tests
    - Gate on celery.py; tasks.py shared_task; --every / --crontab; force/refuse
    - Purpose: Domain task stubs
    - _Leverage: method upsert patterns or text upsert; design crontab parse_
    - _Requirements: 3.1–3.5_
    - _Prompt: Implement the task for spec add-celery, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Celery engineer | Task: Implement add-task generation and schedule merge | Restrictions: Require add-celery first; valid snake_case names | Success: Unit tests for stub, schedule, crontab errors | Log + mark complete_

  - [x] 2.2 `add-celery` / `add-task` commands + optional `new --celery`
    - Files: `commands/add_celery.py`, `commands/add_task.py`, prompts, `cli.py`, `commands/new.py` / prompts
    - Dual UX; wire setup + task_gen; `--celery/--no-celery` on new
    - Purpose: User-facing surface
    - _Leverage: existing command patterns_
    - _Requirements: 1.1, 1.5, 3.1_
    - _Prompt: Implement the task for spec add-celery, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CLI developer | Task: Wire add-celery, add-task, and new --celery | Restrictions: Thin commands | Success: Listed in --help; flag modes work | Log + mark complete_

- [x] 3.0 Docs and tests
  - [x] 3.1 README for Celery + runners
    - Files: `README.md`, `docs/roadmap.md` as needed
    - Document add-celery, worker/beat, Compose, add-task, worker --beat local-only warning
    - Purpose: Discoverability
    - _Requirements: 2.1, 4.1, 4.3_
    - _Prompt: Implement the task for spec add-celery, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer | Task: Document Celery setup in README | Restrictions: MDX-safe | Success: Examples match CLI | Log + mark complete_

  - [x] 3.2 Integration CliRunner matrices
    - Files: `tests/commands/test_add_celery.py`, `tests/commands/test_add_task.py`
    - new→add-celery; add-task; refuse/force; missing celery gate; compose project path
    - Purpose: End-to-end confidence
    - _Requirements: 4.2_
    - _Prompt: Implement the task for spec add-celery, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA | Task: Integration tests for add-celery and add-task | Restrictions: Keep reasonably fast | Success: All cases pass; full pytest green | Log + mark complete_
