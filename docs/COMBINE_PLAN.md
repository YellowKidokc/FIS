# Combining FIS + David-OS v3 — "One folder per app" plan

## The problem today

The same work lives in many places, so it is hard to know what is what:

| Thing | Where it lives now |
|---|---|
| FIS (file intelligence) | `D:\GitHub\FIS` (whole repo), `David-OSv3\fis`, `David-OSv3\file-intelligence-system`, `David-OSv3\tools\fis`, `David-OSv3\scripts\fis` |
| Classification | `David-OSv3\03_CLASSIFY` (5,495 .py files, mostly copies/sidecars), `FIS\chi_classifier.py`, `David-OSv3\agents\chi_*` |
| Message Hub / API | `David-OSv3\hub` |
| Engine pieces | `David-OSv3\engine` (70 files, mixed purposes) |
| Launchers | `.bat` files scattered across `gui\`, `01_PROFILE\`, `04_ADAPT\`, `05_TOPIC_COLLECTION\`, FIS root |

## The target: isolated, named apps + one shared kit + one launcher

```
D:\GitHub\David-OS\
├─ LAUNCH.bat                  ← one menu: pick an app, it starts
├─ apps\
│  ├─ profile\                 ← (was 01_PROFILE)
│  │   app.toml  START.bat  README.md  src\  ui\  tests\
│  ├─ inventory\               ← (was 02_INVENTORY + engine\registry)
│  ├─ classify\                ← (FIS chi_classifier + 03_CLASSIFY code, no copied sidecars)
│  ├─ rename\                  ← (FIS naming_engine + 03_CLASSIFY\03_RENAMING)
│  ├─ fingerprint\             ← (FIS fingerprint.py + Rust minhash)
│  ├─ adapt\                   ← (was 04_ADAPT)
│  ├─ topic-collection\        ← (was 05_TOPIC_COLLECTION)
│  ├─ hub\                     ← (message hub / API, was hub\)
│  └─ fis\                     ← the FIS web UI that drives inventory→classify→rename
├─ shared\                     ← code more than one app uses (safety rules, DB access, models)
│  └─ python\  rust\
├─ data\                       ← each app gets its own subfolder: data\classify\, data\hub\ …
└─ archive\                    ← old copies, zips, sidecar dumps (nothing deleted)
```

### Rules for every app

1. **Own folder, own name, own `START.bat`.** Double-click it and only that app runs.
2. **`app.toml`** says: name, what it does, port (if any), what it reads, what it writes.
3. **Apps never import each other.** They may only import `shared\`. If two apps need the same thing, it moves to `shared\`.
4. **Own data folder** under `data\<app>\`. No app writes into another app's data.
5. **Talk through files or HTTP**, not reaching into each other's code. (e.g. classify writes `data\classify\results.json`; rename reads it.)
6. **Rust pieces live inside the app that uses them** (`apps\fingerprint\rust\`) or in `shared\rust\` if more than one app uses them, always with a Python fallback.

## Safe migration order (nothing deleted, each step reversible)

1. Create the new skeleton + `LAUNCH.bat`; leave old folders alone.
2. Move **fingerprint** first (smallest, already has Rust + tests). Old path keeps working via a stub.
3. Then **classify**, **rename**, **inventory** — the core of organising your papers.
4. Then **hub**, **profile**, **adapt**, **topic-collection**.
5. Move duplicate copies / zips / sidecar dumps into `archive\`.
6. Only after everything launches from the new layout, retire the old FIS repo into `archive\`.
