# Blueprint-Dockerfile Boundary Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `Dockerfile` the single source of truth for build/runtime details and remove overlapping fields from `blueprint.yaml`.

**Architecture:** Keep blueprint focused on orchestration metadata (`context`, `dockerfile`, weights, deploy provider, verify). Runtime behavior is simplified by always launching local containers with image default `ENTRYPOINT/CMD`. Validation rejects removed fields to force migration and avoid drift.

**Tech Stack:** Python 3, Typer CLI, PyYAML, pytest, Docker CLI integration

---

### Task 1: Tighten Blueprint Schema and Validation

**Files:**
- Modify: `mdp_cli/blueprint.py`
- Test: `tests/test_blueprint.py`

**Step 1: Write the failing test**

In `tests/test_blueprint.py`, add test cases asserting validation fails when any removed field exists:
- `build.requirements`
- `build.service`
- `build.model.code`
- `deploy.providers[].start_command`

Example test snippet:

```python
def test_validate_blueprint_rejects_removed_fields(tmp_path):
    bp_dir = tmp_path / "bp-removed"
    bp_dir.mkdir()
    (bp_dir / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
    (bp_dir / "blueprint.yaml").write_text(
        """
name: removed-fields
build:
  requirements: requirements.txt
  service: service.py
  model:
    code: model/infer.py
    weights:
      - name: w
        url: https://example.com/a.bin
deploy:
  providers:
    - name: local
      start_command: python service.py
""".strip()
        + "\n",
        encoding="utf-8",
    )
    errs = validate_blueprint_dir(bp_dir)
    assert any("build.requirements is removed" in e for e in errs)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_blueprint.py::test_validate_blueprint_rejects_removed_fields -v`

Expected: FAIL because validator does not yet reject removed fields.

**Step 3: Write minimal implementation**

In `mdp_cli/blueprint.py`:
- Remove fields from dataclasses:
  - `BuildConfig.requirements`
  - `BuildConfig.service`
  - `ModelConfig.code`
  - `LocalDeployConfig.start_command`
- In `load_blueprint`, ignore removed fields.
- In `validate_blueprint_dir`, add explicit removed-field checks against raw YAML and append deterministic error messages.
- Remove file existence checks tied to removed fields.

**Step 4: Run tests to verify they pass**

Run:
- `pytest tests/test_blueprint.py -v`

Expected: PASS for updated schema tests.

**Step 5: Commit**

```bash
git add mdp_cli/blueprint.py tests/test_blueprint.py
git commit -m "refactor(schema): remove overlapping blueprint build/runtime fields"
```

### Task 2: Remove Runtime Command Override in Local Provider

**Files:**
- Modify: `mdp_cli/providers.py`
- Test: `tests/test_pipeline.py`

**Step 1: Write the failing test**

Add a focused unit test that confirms local rollout command does not append `sh -lc ...` override and runs image directly.

Use monkeypatch to capture command passed into `_run`.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline.py::test_local_rollout_uses_image_default_command -v`

Expected: FAIL because provider still appends `start_command` when configured.

**Step 3: Write minimal implementation**

In `mdp_cli/providers.py`:
- Update `LocalProvider.rollout` to always execute:
  - `docker run -d --name <name> -p <host>:<container_port> <image>`
- Remove conditional `cfg.start_command` branch.

**Step 4: Run tests to verify they pass**

Run:
- `pytest tests/test_pipeline.py -v`

Expected: PASS, including new rollout behavior test.

**Step 5: Commit**

```bash
git add mdp_cli/providers.py tests/test_pipeline.py
git commit -m "refactor(local): run container with image default entrypoint"
```

### Task 3: Update Blueprints and Spec Docs

**Files:**
- Modify: `blueprints/example/blueprint.yaml`
- Modify: `blueprints/pai-example/blueprint.yaml`
- Modify: `docs/blueprint-spec.md`
- Modify: `README.md`

**Step 1: Write the failing test**

Add/update tests validating the in-repo example blueprints still lint successfully after removed fields are dropped.

If existing tests already assert this, keep them and use lint commands as acceptance checks.

**Step 2: Run checks to verify current mismatch**

Run:
- `python3 -m mdp_cli.main lint -d ./blueprints/example`
- `python3 -m mdp_cli.main lint -d ./blueprints/pai-example`

Expected: Potential fail until example YAML and docs align with new schema.

**Step 3: Write minimal implementation**

- Remove removed fields from both example blueprint files.
- In `docs/blueprint-spec.md`:
  - Update minimal directory and schema examples.
  - Remove removed fields from required/default sections.
  - State startup command must be defined in Dockerfile.
- In `README.md`:
  - Add breaking change note for removed fields and command ownership.

**Step 4: Run validation checks**

Run:
- `pytest tests/test_blueprint.py -v`
- `python3 -m mdp_cli.main lint -d ./blueprints/example`
- `python3 -m mdp_cli.main lint -d ./blueprints/pai-example`

Expected: PASS with no schema drift.

**Step 5: Commit**

```bash
git add blueprints/example/blueprint.yaml blueprints/pai-example/blueprint.yaml docs/blueprint-spec.md README.md
git commit -m "docs(example): align blueprint spec with Dockerfile-owned runtime"
```

### Task 4: Full Regression Verification

**Files:**
- No code changes expected

**Step 1: Run full test suite**

Run: `pytest -q`

Expected: All tests pass.

**Step 2: Run smoke checks**

Run:
- `python3 -m mdp_cli.main lint -d ./blueprints/example`
- `python3 -m mdp_cli.main plan -d ./blueprints/example`
- `python3 -m mdp_cli.main build -d ./blueprints/example`

Expected: lint/plan/build complete under new schema.

**Step 3: Optional provider smoke**

Run (if environment is ready):
- `bash scripts/smoke_cli.sh`

Expected: local pipeline runs without start-command override path.

**Step 4: Commit verification evidence**

```bash
git add -A
git commit -m "chore: finalize blueprint-dockerfile boundary migration"
```

