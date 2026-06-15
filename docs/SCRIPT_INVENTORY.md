# River FIS Script Inventory and Target Architecture

This inventory accounts for the active River FIS scripts and bundled reference systems before deeper harvesting. Generated/cache/binary artifacts are excluded from the active refactor.

| Current path | Main responsibility | Useful functions/classes | Dangerous functions/classes | Destination module | Decision | Notes |
|---|---|---|---|---|---|---|
| `api_server.py` | HTTP bridge for GUI, scan, cache, rename, NLP, decisions | `folder_composition_scan`, HTTP handlers, template helpers | routes can trigger write operations/templates | `app/server.py`, `app/routes/*` | split | Keep behavior; move business logic into core/engines over time. |
| `sorter_cache.py` | SQLite cache, inventory, actions, FolderBrain persistence | `init_db`, `scan_inventory`, `folderbrain_summary`, `write_folderbrain`, action/decision helpers | writes SQLite and FolderBrain files | `core/cache.py` | keep/rename | Copied as cache foundation for compatibility. |
| `hub_engines.py` | Preview adapters for rename, organizer, status, manual scan | `baseline_rename_plan`, `organizer_preview`, `rename_preview`, `manual_scan` | none direct, but previews may be confused with execution | `engines/hub_preview.py`, `engines/naming.py`, `engines/inventory.py` | split | Active adapter wrapper added; harvest into focused engines later. |
| `preference_engine.py` | Learns approve/reject/override decisions | `record_decision`, `predict_domain`, `get_engine_stats` | writes preference DB | `learning/preference.py`, `learning/markov.py` | keep | Must not execute file operations. |
| `fingerprint.py` | Text extraction, hashes, minhash duplicate groups | `content_hash`, `build_duplicate_groups`, `find_duplicates`, extractors | reads many files; CLI writes output | `engines/fingerprint.py`, `engines/duplicates.py` | promote/split | Wrapper added; duplicate advisor added with no file operations. |
| `naming_engine.py` | Slug and rename preview generation | `NamingEngine`, `slugify`, `clean_filename`, `PRESETS` | none direct | `engines/naming.py` | keep | Active engine returns rename findings only. |
| `auto_sort.py` | Classifies and can organize/rename files | `classify_file`, `classify_directory`, keyword helpers | `organize_files`, `organize_folders`, `rename_in_place` | `engines/classifier.py`, `engines/router.py`, `_archive/old_scripts` | split | Do not preserve direct move/rename in engine path. |
| `manual_sort.py` | Manual scan/sort/flatten/dedup CLI | `scan_directory`, `find_duplicates`, `md5_hash` | `sort_by_extension`, `flatten_directory`, `dedup` | `engines/inventory.py`, `engines/duplicates.py`, `core/action_plans.py` | split/archive reference | Use as primitive reference only. |
| `chi_classifier.py` | Optional CHI/domain classification | `classify_chi_factor`, `build_chi_vector`, `generate_frontmatter` | none direct | `engines/domain_chi.py` | optional keep | Lazy optional domain module. |
| `cluster_engine.py` | Token feature clustering | `cluster_files`, `build_feature_matrix` | none direct | `engines/clusters.py`, `engines/similarity.py` | keep | Wrapper added; similarity engine stubbed. |
| `nlp_bridge.py` | Optional heavy NLP/CLIP bridge | `get_deberta`, `summarize_with_bart`, `classify_image_with_clip` | model loading can break startup | `engines/nlp_bridge.py` | optional keep | Lazy wrapper only; not imported by server startup. |
| `background_inventory.py` | Background inventory runner | `main` | can write cache | `scripts/scan_background.py`, `workers/inventory_worker.py` | convert | Worker destination scaffolded. |
| `background_enrich.py` | Background enrichment | `enrich`, `short_summary`, `main` | writes cache/enrichment | `scripts/enrich_background.py`, `workers/enrich_worker.py` | convert | Worker destination scaffolded. |
| `background_inventory_course.py` | Course-oriented inventory | `run_course`, `main` | writes cache | `workers/inventory_worker.py` | convert | Not auto-run. |
| `file-sorter-v3.jsx` | Advanced GUI component | UI actions and scan controls | buttons may imply actions | `ui/components/intelligent-mode.jsx` | preserve | Copied to UI component destination. |
| `file-sorter-gui-v2.jsx` | GUI component | UI controls | buttons may imply actions | `ui/components/review-blocks.jsx` | preserve | Copied to UI component destination. |
| `index.html` | Main River UI | black/gold layout | none | `ui/index.html` | preserve | Copied unchanged first pass. |
| `simple.html` | Simple UI | lightweight GUI | none | `ui/simple.html` | preserve | Copied unchanged first pass. |
| `.sortconfig.yaml` | Naming/sort config | presets/settings | none | `config/sortconfig.yaml` | keep | Copied when present. |
| `nameit.py` | Filename helper/reference | naming primitives | unknown parse issue from Windows path escapes | `engines/naming.py` | inspect later | Keep outside startup until cleaned. |
| `file-intelligence-system-master/` | Older FIS app | `fis/pipeline.py`, `fis/api.py`, `fis/renamer.py`, NLP extractors | watcher/startup services | `_archive/external/` after harvest | harvest then archive | Reference only for this pass. |
| `Local-File-Organizer-main/` | Older organizer | `file_utils.py`, metadata processors | organizer planning may imply file ops | `_archive/external/` after harvest | harvest then archive | Avoid model-heavy startup deps. |
| `Project2Prompt-master/` | Project prompt exporter | scanner/processor/utils | clipboard/output side effects | `tools/project2prompt/`, `scripts/export_project_prompt.py` | keep as tool | Lightweight exporter added. |

## Target responsibility map

River FIS now has the first-pass guided spine: scan → FolderBrain → advisor findings → review blocks → dry-run action plan → safety gate → executor-only execution.
