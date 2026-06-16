# River FIS UI Map

## Production entrypoint
- `/` is served by `app/server.py` from `ui/index.html`.
- `ui/index.html` is the production app shell and owns the guided flow: Folder → Scan → Recommendation → Storyboard → Preview → Approve → Safety → Execute → Record.

## Legacy/demo files
- `ui/simple.html` is retained as a legacy Story Mode reference until the production shell has been proven by tests and smoke checks.
- Top-level `index.html`, `simple.html`, and JSX demo files are legacy review candidates, not production entrypoints.

## Active CSS files
- `ui/styles/river.css` provides the black/gold River product shell, cards, pills, workbench, and mode layout.
- `ui/styles/storyboard.css` provides storyboard-specific approval and progress rail styling.

## Active components / render helpers
The production app uses vanilla JavaScript render helpers embedded in `ui/index.html`:
- `renderRecipeCard()`
- `renderStoryboard()`
- `renderReviewBlock()`
- `renderActionPlan()`
- `renderSafetyStatus()`
- `renderToast()` behavior via `toast()`
- `renderEmptyState()`

`ui/components/*.jsx` remains as reference component material only and is not loaded by production `ui/index.html`.

## API endpoints by section

### Home / Story
- `POST /api/scan`
- `GET /api/recipes/next?path=`
- `POST /api/storyboard/build`
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
- Uses scanned review blocks and dry-run action plan endpoints.
- No direct execution is exposed from Advanced Mode.

### Plans / History
- Displays client-session action plans, previews, approvals, safety blockers, and execution responses.
- Uses `POST /api/action/preview`, `POST /api/action/approve`, and guarded `POST /api/action/execute`.

### Settings / Diagnostics
- `GET /api/health`
- `GET /api/routes`
- `GET /api/stats`
- `POST /api/project/export-prompt`
