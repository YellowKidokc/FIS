# FIS Consolidation — Codex Prompt

## Context

The File Intelligence System (FIS) at `D:\GitHub\FIS` has two parallel backend systems that need to be unified, legacy files that need archiving, and a rename from "River" to "File Intelligence System" throughout.

## The Production UI

The production HTML is in `files/`:
- `files/river-fis-1-scan-pick.html` — Scan/folder picker
- `files/river-fis-2-intelligence-mode.html` — Intelligence mode (guided, preview-first)
- `files/river-fis-3-advanced-mode.html` — Advanced workbench (dry-run only)

These talk to the `file-intelligence-system-master/fis/api.py` endpoints:
- `POST /api/scan`
- `GET /api/scan/{scan_id}`
- `POST /api/plan/simple`
- `POST /api/plan/custom`
- `POST /api/plan/advanced`
- `POST /api/simulate`
- `POST /api/execute`

## The Two Systems — Unify Into One

**System A** (`app/server.py` + `core/` + `engines/`): Has orchestrator, safety, executor, models, recipes, storyboards, action plans, review blocks, 14 pytest files passing, smoke tests. Its UI (`ui/index.html`) has a 5-mode production shell.

**System B** (`file-intelligence-system-master/fis/`): Has planner layer (`fis/planner/`) with action_schema, safety_rules, executor, simulator, simple_strategies (A/B/C recommendations), custom_intent ("Ask FIS"), scan_summary. Its UI is the `files/river-fis-*.html` pages.

**Task:** Merge the best of both into ONE system. The production HTML is the `files/` pages. The production backend should be a single unified server that:
1. Keeps System A's `core/` modules (orchestrator, safety, executor, models, recipes, storyboards, review blocks) — these are tested and working
2. Harvests System B's planner concepts INTO System A's `core/` — specifically: simulation, simple strategies A/B/C, custom intent "Ask FIS", scan summary
3. Serves the `files/river-fis-*.html` pages
4. Exposes ONE set of API endpoints (resolve the overlap between `app/server.py` routes and `fis/api.py` routes)
5. All tests continue to pass after merge

## NLP / Preference / Learning Engine

The learning layer (`learning/preference.py`, `learning/markov.py`) and NLP bridge (`engines/nlp_bridge.py`) are what make this system intelligent rather than just a file scanner. They are currently partially harvested and some are lazy-loaded stubs. 

**Task:** Document what the NLP/preference layer does, what's wired, what's stubbed, and what needs to be connected. Do NOT remove these modules. They are the intelligence layer. Flag what needs testing but keep them in the pipeline.

## Rename: River → File Intelligence System

Throughout all code, HTML, CSS, docs, and comments:
- "River" → "File Intelligence System" or "FIS"
- "River FIS" → "File Intelligence System"
- Keep the black/gold aesthetic, just update the branding text

## Archive Plan

After unification, move these to `_archive/`:

**`_archive/legacy_ui/`:**
- `ui/index.html` (replaced by files/ pages)
- `ui/simple.html`
- `ui/components/*.jsx`
- Root-level: `index.html`, `simple.html`, `2index.html`, `2simple.html`
- Root-level: `fis_flow_prototype*.html`, `fis_simple_v2.html`
- Root-level: `file-sorter-gui-v2.jsx`, `file-sorter-v3.jsx`
- Root-level duplicates: `river-fis-1/2/3-*.html` (copies of files/ versions)

**`_archive/old_scripts/`:**
- `api_server.py`
- `sorter_cache.py`
- `hub_engines.py`
- `manual_sort.py`
- `auto_sort.py`
- `naming_engine.py`
- `nlp_bridge.py` (root-level copy; `engines/nlp_bridge.py` stays)
- `fingerprint.py` (root-level copy; `engines/fingerprint.py` stays)
- `preference_engine.py`
- `chi_classifier.py`
- `cluster_engine.py`
- `background_inventory.py`, `background_inventory_course.py`, `background_enrich.py`
- `nameit.py`

**`_archive/external/`:**
- `Local-File-Organizer-main/`
- `Project2Prompt-master/`
- `file-intelligence-system-master/` (after planner concepts are harvested into core/)

**`_archive/screenshots/`:**
- All root-level `.png`, `.jpg` files
- `advanced/` screenshot folder
- `Simple/` screenshot folder
- `Manual/` screenshot folder

**Delete:**
- `__pycache__/` everywhere
- `*.pyc`
- `.pytest_cache/`
- `files.zip`

## After Consolidation — Clean Root Should Be:

```
D:\GitHub\FIS\
├── app/           # Server + routes
├── core/          # Orchestrator, safety, executor, models, recipes, storyboards, action plans, planner
├── engines/       # Scanner, fingerprint, duplicates, classifier, naming, folderbrain, NLP bridge
├── learning/      # Preference engine, Markov chain
├── workers/       # Background inventory, enrichment
├── files/         # Production HTML (rename to ui/ if desired)
├── scripts/       # start.py, smoke tests, diagnostics
├── tests/         # All pytest files
├── docs/          # UI_MAP, PURGE_PLAN, SCRIPT_INVENTORY, RUNBOOK
├── tools/         # project2prompt
├── _archive/      # Everything archived
├── pytest.ini
└── README.md
```

## Evidence Gates

Before committing:
1. `python -m pytest -q` passes
2. `python -m compileall app core engines learning scripts workers tests` passes
3. `python scripts/smoke_api_flow.py` passes
4. Production HTML pages load and connect to unified API
5. NLP/preference modules documented (what works, what's stubbed)

## Priority Order

1. Archive the obvious debris (screenshots, root HTML dupes, external projects)
2. Harvest System B planner concepts into core/
3. Unify the API endpoints
4. Wire files/ HTML to unified API
5. Rename River → File Intelligence System
6. Run all evidence gates
7. Document NLP/preference status
