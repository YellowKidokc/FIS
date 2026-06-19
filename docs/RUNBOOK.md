# River FIS Runbook

## Current status

- Scaffold complete.
- Read-only folder intelligence pipeline works.
- API route contracts are live through the stdlib server in `app/server.py`.
- Action plans are dry-run first and stored in the in-memory runtime store.
- Executor is guarded by safety and only low-risk operations are executable now.
- GUI polish is next; current UI is preserved and served as static HTML.

## Start River FIS

```bash
python scripts/start.py
```

Default server:

- Host: `127.0.0.1`
- Port: `61845`
- UI: `http://127.0.0.1:61845/`
- Static directory: `ui/`
- API base: `http://127.0.0.1:61845/api`
- Active served UI: `ui/index.html`; `ui/simple.html` is also available as `/simple.html`.

## Run a scan through the API

```bash
curl -X POST http://127.0.0.1:61845/api/scan \
  -H 'Content-Type: application/json' \
  -d '{"path":"/path/to/folder"}'
```

Every API endpoint returns the envelope:

```json
{"ok": true, "data": {}, "warnings": [], "errors": []}
```

Failures return `ok: false` and human-readable errors.

## Diagnostic CLI

```bash
python scripts/diagnose_pipeline.py "/path/to/folder"
```

Prints FolderBrain summary, inventory counts, finding counts, top review blocks, and a sample dry-run safety result. It does not modify files.

## Manual API smoke flow

```bash
python scripts/smoke_api_flow.py
```

Creates a temporary folder, scans it, builds review blocks, creates an action plan, previews it, approves it, and attempts a guarded execute against the temp folder only.

## Tests

```bash
python -m pytest -q
python -m compileall app core engines learning scripts workers tests
```

## Story / Recipe Mode

Recipe endpoints:

- `GET /api/recipes?path=...` returns ranked guided actions.
- `GET /api/recipes/next?path=...` returns the recommended next action.
- `POST /api/storyboard/build` creates a readable storyboard and links a dry-run plan when appropriate.
- `GET /api/storyboard?id=...` returns a stored storyboard.
- `POST /api/storyboard/decision` records approve/edit/skip/defer without executing files.

Simple Mode now includes a small Story Mode shell that keeps the black/gold River look and lets a user ask for the next recipe before the later visual polish pass.

## Currently executable low-risk operations

- `create_folder`
- `write_folderbrain`
- `copy` when source exists and destination does not overwrite
- `zip_backup` when safety passes
- `protect` as a no-op runtime marker
- `link_hub` as a small hub markdown write

## Guarded / not implemented for execution yet

- `rename`
- `move`
- `archive`
- `tag`

These can be planned and previewed, but execution is blocked or returns `not_implemented` until safety/undo behavior is stronger.

## Blocked

- `delete`
- protected/system paths such as `.git`, `node_modules`, `__pycache__`, Windows system paths, and configured database files
- overwrites without explicit approval
- cross-drive moves/copies without explicit approval
- execution without `confirm_execute=true`

## Still placeholder / compatibility-only

- Legacy compare/fingerprint/composition endpoints return structured preview-only compatibility responses unless already wired to the new pipeline.
- Route modules in `app/routes/` expose route contracts; stdlib dispatch still lives in `app/server.py` until a future framework split.
- GUI visual redesign is intentionally deferred.
