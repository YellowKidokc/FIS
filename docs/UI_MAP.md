# River FIS UI Map

## Production entrypoint
- `/` is served by `app/server.py` from `ui/index.html`.
- `ui/index.html` is the final production entrypoint and owns the guided flow: Folder → Scan → Recommendation → Storyboard → Preview → Approve → Safety → Execute → Record.

## Production modes
The main UI exposes exactly five production modes:
1. Home / Story
2. Intelligence
3. Advanced
4. Plans / History
5. Diagnostics

Classic Legacy is retained only as a hidden fallback button and is not a main production mode.

## Active CSS files
- `ui/styles/river.css` provides the stable app shell, left navigation, black/gold visual system, cards, status rail, diagnostics, and Advanced workbench layout.
- `ui/styles/storyboard.css` provides storyboard-specific approval, progress rail, change table, safety, and subtle pulse styling.
- `ui/styles/intelligent.css` is not referenced by production `ui/index.html` and should be reviewed before archive.

## Active JS/component files
The production app uses vanilla JavaScript embedded in `ui/index.html`; no frontend framework is loaded.
Active render/helpers include:
- `apiFetch()`
- `renderRecipeCard()`
- `renderStoryboard()`
- `renderReviewBlock()`
- `renderActionPlan()`
- `renderSafetyStatus()`
- `toast()`
- `renderEmptyState()`

`ui/components/*.jsx` remains reference material only. It is not loaded by production `ui/index.html`.

## API endpoints by mode

### Home / Story
- `GET /api/health`
- `POST /api/scan`
- `GET /api/recipes?path=`
- `GET /api/recipes/next?path=`
- `POST /api/storyboard/build`
- `GET /api/storyboard?id=`
- `POST /api/storyboard/decision`
- `POST /api/action/plan`
- `POST /api/action/preview`
- `POST /api/action/approve`
- `POST /api/action/execute`
- `POST /api/preferences/record`

### Intelligence
- `GET /api/folderbrain?path=`
- `GET /api/review/blocks?path=`
- `GET /api/recipes?path=`

### Advanced
- Uses scanned FolderBrain/review block/recipe data.
- Creates or previews dry-run plans through `POST /api/action/plan` and `POST /api/action/preview`.
- Advanced does not execute directly.

### Plans / History
- Shows client-session plans, previews, approvals, decisions, safety blockers, and executor logs.
- Uses `POST /api/action/preview`, `POST /api/action/approve`, guarded `POST /api/action/execute`, and `POST /api/preferences/record`.

### Diagnostics
- `GET /api/health`
- `GET /api/routes`
- `GET /api/cache/status`
- `GET /api/preferences/stats`
- `POST /api/project/export-prompt`

## Legacy files
- `ui/simple.html` stays in LEGACY_KEEP until production UI click-through and tests remain stable.
- Top-level `index.html`, top-level `simple.html`, `file-sorter-gui-v2.jsx`, and `file-sorter-v3.jsx` are legacy/demo review candidates.

## Safe to archive later after tests
- Unreferenced component files under `ui/components/` after confirming no production import/reference.
- `ui/styles/intelligent.css` if no future production view uses it.
- Old manual/demo pages after `docs/PURGE_PLAN.md` evidence gates pass.
