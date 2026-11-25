# Backend / Frontend Integration Test Report

**Project:** Chanakya ScholarSphere (Research Commons)
**Checked:** 25 November 2026
**Base revision:** `main` at merge commit `e4722f9` (PR #5)
**Working tree:** local UI and evaluation updates, not committed

## Summary

The React production bundle builds successfully. An automated static contract check confirms that the frontend API calls map to registered FastAPI routes and that the `/api` proxy targets the expected local and Compose backend addresses. The confirmed Member 2/Member 3 evaluation-label mismatch is fixed with an adapter that accepts both schemas; the evaluator now defaults to the shared synthetic ground-truth file. Five focused regression tests, Python source compilation, ground-truth JSON parsing, and isolated duplicate/ranking metric checks pass.

This is **not a complete end-to-end pass**: Docker is unavailable in this environment, so PostgreSQL-backed API calls and browser-to-API behavior could not be exercised. The repository now has focused backend unit tests, though there is still no frontend `npm test` script. A local FastAPI import attempt also fails under this machine's Python 3.14.7 environment while building the SQLModel models; the project's Dockerfile targets Python 3.12, so that result does not establish a failure in the intended container runtime. The Vite server starts in the coding environment, but its port is isolated from the laptop browser session.

## Checks performed

| Check | Result | Notes |
| --- | --- | --- |
| Git revision | Pass | Local `main` fast-forwarded to `e4722f9`; latest Member 2 changes are present. |
| Frontend API base/proxy | Pass by inspection | `frontend/src/api.js` prefixes requests with `/api`; Vite proxies `/api` to the backend. Docker Compose sets the backend service URL. |
| Route alignment | Pass | Added a static contract test: all discovered frontend API paths match backend router paths after route prefixes and dynamic IDs are normalized. |
| React production build | Pass | `npm run build` completed; 660 modules transformed. Bundle is 614 kB minified and Vite reports its advisory size warning. |
| Backend Python syntax | Pass | `compileall` completed for `backend/app` and `backend/generate_synthetic_data.py`. |
| Synthetic ground truth | Pass | `backend/data/synthetic_ground_truth.json` parses as valid JSON. |
| Mining/evaluation helpers | Pass | Isolated checks passed for title duplicate detection, duplicate pair metrics, Precision@K, and MRR. |
| Ground-truth/evaluator contract | Pass after fix | `evaluation_labels.py` maps Member 2's `duplicate_paper_pairs` / `search_relevance_labels[].relevant_documents` to the evaluator format, keeps support for the example format, and evaluation defaults to `data/synthetic_ground_truth.json`. |
| Backend regression/contract tests | Pass | `python -m unittest discover -s tests -v`: 5 tests passed, including the actual synthetic labels and frontend-to-FastAPI route/proxy contracts. |
| FastAPI import / route smoke test | Blocked in this host environment | Python 3.14.7 with SQLModel 0.0.22 / Pydantic 2.14.4 raises `PydanticUserError: Field 'id' requires a type annotation` during model import. The project container uses Python 3.12. |
| Database-backed API / full UI integration | Not run | Docker reports that its Linux engine named pipe is unavailable; no PostgreSQL-backed HTTP or browser-to-API checks were possible. |
| Local live UI access | Blocked | Vite announced `http://localhost:5173/`, but laptop Edge could not connect; the execution environment does not expose this dev-server port to the desktop browser. |
| Frontend automated tests | Not configured | `frontend/package.json` provides `dev`, `build`, and `preview`, but no `test` script. |

## Findings and follow-up

1. **End-to-end integration remains unverified.** Start Docker Desktop and run the stack from the repository folder, then check `/api/health`, log in, and exercise search, save/unsave, recommendations, trends, Ask, and the admin dashboard.
2. **Run backend smoke tests in the intended Python 3.12 container.** The local app import failure occurs under Python 3.14; compare with the Docker runtime before treating it as an application defect.
3. **Frontend bundle-size warning.** Vite reports the generated JavaScript bundle at 614 kB minified, above its 500 kB advisory threshold. Build succeeds; code splitting could reduce initial download size.
4. **Laptop preview.** To see hot reload from your laptop, start Vite from a PowerShell window on the laptop; the coding environment's port is not exposed to Edge.

## Design reference

The welcome and signed-in home mastheads use a restrained editorial layout, university-inspired navy and antique gold accents, and campus photos from the [official Chanakya University Campus Architecture page](https://chanakyauniversity.edu.in/campus-infrastructure/campus-architecture/). Photo captions link back to the source page. The photos load from the university site, with a visual fallback if a remote image is unavailable.

## Local preview

Run these commands in PowerShell on the laptop to get a browser-reachable hot-reload server:

```powershell
Set-Location "C:\Users\maith\Documents\Codex\Research-commons\frontend"
npm run dev -- --host 0.0.0.0
```

Then open `http://localhost:5173/`.

## Overall status

**Frontend/backend route wiring: contract-tested. Ground-truth contract: fixed and regression-tested. Production build and focused backend tests: pass. Full API/database UI verification: pending Docker access.**
