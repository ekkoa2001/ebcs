# Project File Classification

This is an inventory for maintenance. It is **not** a deletion list: files are
only marked as removable after a verified production backup and a clean test run.

| English category | Paths | Runtime status | Maintenance action |
| --- | --- | --- | --- |
| Application source | `server/`, `web/` | Required | Keep and version together. |
| Web entry points | `web/index.html`, `web/login.html`, `web/first-password.html` | Required | Keep. These are the active browser pages. |
| Web styles | `web/assets/css/` | Required | Keep. Consolidate duplicate dialog rules before future UI work. |
| Web modules | `web/assets/js/`, `web/modules/` | Required | Keep. Load feature modules only when their page is opened in a future performance pass. |
| Vendor libraries | `web/vendor/` | Review before removal | Keep unless an import/reference audit proves an asset is unused. |
| Server data | `data/sana_data.sqlite3`, `data/media/` | Required user data | Never delete during cleanup. Back up first. |
| Deployment files | `deploy/`, `Dockerfile`, `docker-compose.yml`, `start.ps1`, `启动团队版.cmd` | Required for deployment/startup | Keep. |
| Tests | `server/tests/`, `tests/` | Development-only, not runtime | Keep; run before releases. |
| Documentation | `README.md`, `docs/` | Development-only, not runtime | Keep; archive obsolete reports rather than deleting. |
| Generated logs | `logs/` | Not runtime source | Cleared. `start.ps1` recreates this folder when the local Python process starts. |
| Generated test output | `tests/output/`, `tests/visual/test-results/` | Not runtime source | Cleared. Keep the Playwright specs in `tests/visual/`. |
| Legacy/inactive Vue prototype | `frontend/` | Removed | Not used by the running site. Do not restore it into this project. |

## Current active architecture

The active product is the `web/` application served by FastAPI in `server/`.
The unused Vue prototype has been removed. `data/` stays in place: it holds the
SQLite fallback, media files, and backups.

Generated files removed in the pre-launch cleanup: `frontend/`, `logs/`,
`tests/output/`, `tests/visual/node_modules/`, `tests/visual/test-results/`,
and Python `__pycache__/` directories. Application source, deployment files,
docs, and `data/` were kept.
