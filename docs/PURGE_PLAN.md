# River FIS Purge and Archive Plan

This plan documents cleanup candidates. Do not permanently delete source scripts until the production UI, API smoke flow, and tests pass and harvested behavior is documented.

## KEEP_ACTIVE
- `app/`
- `core/`
- `engines/`
- `learning/`
- `workers/`
- `scripts/start.py`
- `scripts/smoke_api_flow.py`
- `scripts/diagnose_pipeline.py`
- `scripts/ui_smoke_check.py`
- `tests/`
- `ui/index.html`
- `ui/styles/river.css`
- `ui/styles/storyboard.css`
- production Diagnostics mode and route registry
- `docs/UI_MAP.md`
- `docs/PURGE_PLAN.md`
- `docs/SCRIPT_INVENTORY.md`

## LEGACY_KEEP
- `ui/simple.html` until Story Mode is fully validated inside `ui/index.html`.
- `ui/components/*.jsx` as design/reference components until production parity is confirmed.
- Classic Legacy hidden fallback only; not a production main mode.
- Old manual/advanced workbench artifacts if still useful for operation copy.

## ARCHIVE_AFTER_TESTS
Move only after tests and smoke flows pass:
- top-level `api_server.py`
- top-level `sorter_cache.py`
- top-level `hub_engines.py`
- top-level `manual_sort.py`
- top-level `auto_sort.py`
- top-level `naming_engine.py`
- `file-sorter-gui-v2.jsx`
- `file-sorter-v3.jsx`
- unused demo pages
- external old systems after confirming no live imports

Target archive folders:
- `_archive/legacy_ui/`
- `_archive/old_scripts/`
- `_archive/external/`

## DELETE_GENERATED
- `__pycache__/`
- `*.pyc`
- `*.log`
- `*.err`
- temp files
- `.pytest_cache/`
- build artifacts

## DELETE_DUPLICATE
- Duplicate demo shells only after `docs/UI_MAP.md` is updated with replacement evidence.

## UNKNOWN_REVIEW
- Any top-level script with unclear import/use status.
- External bundled projects until import scans and smoke checks prove they are not used.

## Evidence gates before moving files
1. `python scripts/ui_smoke_check.py` passes.
2. `python scripts/smoke_api_flow.py` passes.
3. `python -m pytest -q` passes.
4. `python -m compileall app core engines learning scripts workers tests` passes.
5. Documentation states what behavior was harvested or replaced.
