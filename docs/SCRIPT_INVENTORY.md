# River FIS Script Inventory, Migration Status, and UI Contract

## Scaffold audit status

| File | Status | Notes |
|---|---|---|
| `core/models.py` | complete enough for now | Shared dataclasses plus JSON conversion. |
| `core/orchestrator.py` | needs continued harvest / now functional | Runs real scan, FolderBrain, advisor engines, warnings, timing. |
| `core/cache.py` | duplicate of old logic / compatibility adapter | Real `sorter_cache.py` copied for compatibility; not yet fully adapted to new models. |
| `core/review_blocks.py` | complete enough for now | Groups real findings and adds the required 12 review surfaces. |
| `core/action_plans.py` | complete enough for now | Builds real dry-run/unapproved steps from decisions. |
| `core/safety.py` | complete enough for now | Strict execution gate for deletes, protected paths, DBs, overwrites, missing paths. |
| `core/executor.py` | complete enough for now | Preview + safe executor; unimplemented operations return `not_implemented`. |
| `engines/inventory.py` | real harvested code | Read-only robust scanner based on old manual/background inventory behavior. |
| `engines/fingerprint.py` | real harvested code | Content hash, name normalization, text fingerprints from fingerprint/manual references. |
| `engines/duplicates.py` | real harvested code | Exact hash, same-name/same-size, and near-text duplicate findings only. |
| `engines/classifier.py` | partially_harvested | Extension/keyword domain classifier from `auto_sort.py` ideas; more rules can be moved later. |
| `engines/naming.py` | partially_harvested | Uses `naming_engine.py` slug/presets when available and adds rename-candidate rules. |
| `engines/router.py` | complete enough for now | Review-only route recommendations. |
| `engines/similarity.py` | partially_harvested | Folder-name similarity findings; deeper cluster logic later. |
| `engines/folderbrain.py` | real harvested code | Builds schema-like FolderBrain payload without auto-writing. |
| `learning/preference.py` | duplicate of old logic / compatibility adapter | Lazy wrapper around existing preference engine. |
| `app/server.py` | compatibility wiring | Real pipeline endpoints plus preview-only wrappers for legacy UI routes. |
| `app/routes/*.py` | placeholder / stub | Marker modules for future framework split; dispatch currently lives in `app/server.py`. |
| `ui/index.html`, `ui/simple.html`, `ui/components/*.jsx` | preserved | No redesign this pass; API contract documented below. |
| `ui/styles/*.css` | complete enough for now | River black/gold helper styles preserved. |

## Source script migration table

| Source path | Useful functions/classes found | Destination module | Migration status | Notes | Tests that cover it |
|---|---|---|---|---|---|
| `api_server.py` | HTTP routes, folder composition, cache/rename/manual/hub endpoints | `app/server.py`, `app/routes/*` | partially_harvested | Real scan/review/action endpoints are wired; old UI endpoints have preview-only compatibility wrappers. | `test_api_scan_and_review_blocks` |
| `sorter_cache.py` | `init_db`, scan/action/decision/FolderBrain cache helpers | `core/cache.py` | partially_harvested | Full file copied as compatibility foundation; orchestrator currently works in memory if cache is unavailable. | compileall |
| `hub_engines.py` | baseline rename, organizer preview, manual scan/status | `engines/hub_preview.py`, `engines/naming.py`, `engines/inventory.py` | partially_harvested | Preview concepts harvested; destructive execution remains blocked outside executor. | orchestrator/API tests |
| `preference_engine.py` | `record_decision`, `predict_domain`, stats | `learning/preference.py`, `learning/markov.py` | partially_harvested | Lazy compatibility wrapper; API records preview decisions in memory this pass. | API tests |
| `fingerprint.py` | content hashes, minhash/text duplicate ideas, text extraction | `engines/fingerprint.py`, `engines/duplicates.py` | partially_harvested | Exact hash, same-name/size, and lightweight text near-duplicate logic are wired. | `test_duplicates_create_findings` |
| `naming_engine.py` | `NamingEngine`, `slugify`, presets | `engines/naming.py` | partially_harvested | Slug/preset compatibility plus real rename-candidate findings and previews. | `test_naming_creates_rename_candidates` |
| `auto_sort.py` | keyword classification, domain rules, organize/rename danger refs | `engines/classifier.py`, `engines/router.py` | partially_harvested | Safe classifier/router harvested; direct organize/rename intentionally not imported. | `test_low_confidence_classification_needs_review` |
| `manual_sort.py` | scan, size formatting, md5 dupes, direct sort/flatten/dedup | `engines/inventory.py`, `engines/duplicates.py`, `core/action_plans.py` | partially_harvested | Safe scan/duplicate ideas harvested; direct file ops remain reference only. | inventory/duplicates/action tests |
| `chi_classifier.py` | CHI vectors/frontmatter/domain helpers | `engines/domain_chi.py` | archived_reference | Optional lazy module; not default startup. | compileall |
| `cluster_engine.py` | token features and clustering | `engines/clusters.py`, `engines/similarity.py` | partially_harvested | Similar folder-name findings wired; deeper clustering later. | compileall/orchestrator |
| `nlp_bridge.py` | lazy model resolver/classifiers/summarizer | `engines/nlp_bridge.py` | archived_reference | Optional no-op analyze unless NLP explicitly enabled later; startup safe. | compileall |
| `background_inventory.py` | background inventory runner | `workers/inventory_worker.py`, future `scripts/scan_background.py` | partially_harvested | Worker import points at real inventory scanner; not auto-run. | compileall |
| `background_enrich.py` | summary/enrichment runner | `workers/enrich_worker.py`, future `scripts/enrich_background.py` | partially_harvested | Worker import points at FolderBrain builder; not auto-run. | compileall |
| `background_inventory_course.py` | course scan runner | `workers/inventory_worker.py` | partially_harvested | Accounted as background reference only. | compileall |
| `file-sorter-v3.jsx` | React GUI calls scan/stats/decide/nlp | `ui/components/intelligent-mode.jsx` | partially_harvested | Preserved; endpoints have compatibility wrappers. | UI contract review |
| `file-sorter-gui-v2.jsx` | Legacy/alternate React GUI | `ui/components/review-blocks.jsx` | partially_harvested | Preserved for next GUI pass. | UI contract review |
| `index.html` | Main active River command-center UI | `ui/index.html` | partially_harvested | Preserved as served entrypoint candidate; backend wrappers added. | UI contract review |
| `simple.html` | Simple guided UI | `ui/simple.html` | partially_harvested | Preserved; backend wrappers added. | UI contract review |
| `.sortconfig.yaml` | naming/sort presets | `config/sortconfig.yaml` | partially_harvested | Used by legacy naming engine when available. | compileall |
| `nameit.py` | naming primitive/reference | `engines/naming.py` | not_started | Kept out of startup due Windows escape parse issue. | none |
| `file-intelligence-system-master/` | pipeline/api/renamer/watcher/NLP/db references | `_archive/external/` later | archived_reference | Not moved yet; not collected by pytest. | pytest config |
| `Local-File-Organizer-main/` | file readers and metadata processors | `_archive/external/` later | archived_reference | Not moved yet; not collected by pytest. | pytest config |
| `Project2Prompt-master/` | scanner/processor/utils/exporter | `scripts/export_project_prompt.py`, `tools/project2prompt/` | partially_harvested | Lightweight safe exporter added. | compileall |

## UI API contract

| UI file | Function/component | Endpoint called | Method | Expected request | Expected response | Backend route status |
|---|---|---|---|---|---|---|
| `ui/index.html` | scanner pages | `/api/rename/baseline-plan`, `/api/rename/preview`, `/api/manual/scan`, `/api/organizer/preview` | GET | `path`, `max` query | preview JSON | compatibility wrapper needed / exists |
| `ui/index.html` | intent form | `/api/intent` | POST | JSON intent payload | structured JSON | compatibility wrapper needed / exists |
| `ui/index.html` | advanced tools | `/api/fingerprint`, `/api/folders/compare`, `/api/folders/composition` | GET | query params | tool result JSON | compatibility wrapper needed / exists |
| `ui/index.html` | roots/actions | `/api/roots`, `/api/actions` | GET | optional query | roots/actions JSON | compatibility wrapper needed / exists |
| `ui/index.html` | cache browser | `/api/cache/files`, `/api/cache/scan`, `/api/cache/folder`, `/api/cache/clusters`, `/api/cache/folderbrain`, `/api/cache/classify` | GET | `root`/`path` query | cache/inventory JSON | compatibility wrapper needed / exists |
| `ui/index.html` | hub/status/stats | `/api/hub/status`, `/api/cache/status`, `/api/stats` | GET | none | status JSON | exists or compatibility wrapper exists |
| `ui/index.html` | legacy scan | `/api/scan?path=...&top=...` | GET | query path/top | scan result JSON | exists |
| `ui/index.html` | decide/nlp | `/api/decide`, `/api/nlp-classify` | POST | decision/files JSON | recorded/preview JSON | compatibility wrapper exists |
| `ui/simple.html` | guided flows | `/api/cache/summary`, `/api/findings`, `/api/cache/rename-sample`, `/api/cache/scan` | GET | path/root query | summary/findings JSON | exists or compatibility wrapper exists |
| `ui/simple.html` | create/intent | `/api/create/folder`, `/api/intent` | POST | JSON | preview-only JSON | compatibility wrapper exists |
| `ui/simple.html` | cache classify/rename/findings | `/api/cache/classify`, `/api/cache/rename-plan`, `/api/cache/findings` | GET | root query | cache JSON | exists or compatibility wrapper exists |
| `ui/simple.html` | decisions | `/api/findings/decide`, `/api/decide` | POST | decision JSON | recorded JSON | compatibility wrapper exists |
| `ui/components/intelligent-mode.jsx` | intelligent React mode | `/api/stats`, `/api/scan`, `/api/decide`, `/api/nlp-classify` | GET/POST | path/decision/files | status/scan/record JSON | exists or compatibility wrapper exists |

No UI endpoint performs destructive file operations directly in the new server; compatibility wrappers return preview-only structured responses where legacy behavior has not been fully harvested.
