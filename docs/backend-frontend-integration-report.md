# Backend / Frontend Integration Test Report

**Project:** Chanakya ScholarSphere (Research Commons)
**Checked:** 25 November 2026
**Revision checked:** `main` at `9c66081`
**Runtime check:** 25 November 2026, using the local Docker Compose database

## Summary

The React production bundle builds successfully. An automated static contract check confirms that the frontend API calls map to registered FastAPI routes and that the `/api` proxy targets the expected local and Compose backend addresses. The confirmed Member 2/Member 3 evaluation-label mismatch is fixed with an adapter that accepts both schemas; the evaluator now defaults to the shared synthetic ground-truth file. Five focused regression tests, Python source compilation, ground-truth JSON parsing, and isolated duplicate/ranking metric checks pass.

The user subsequently ran the stack locally. The paper catalog import and synthetic generator completed, and the evaluator successfully queried the Docker PostgreSQL database. This confirms database connectivity for those jobs. The measured ranking and deduplication results are mixed: search aliases tied the lexical baseline, co-save recommendations trailed popularity, and duplicate precision was very low against the three planted pairs. Browser-to-API flows (sign-in, save, search page, recommendations, and admin UI) still need a manual check in the user's browser. There is no frontend `npm test` script. A local FastAPI import attempt in the coding environment failed under Python 3.14.7 while building SQLModel models; the project's Dockerfile targets Python 3.12, so that host result does not establish a failure in the intended container runtime.

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
| Database-backed generator / evaluator | Pass | The synthetic generator and evaluation command ran inside the backend container and queried the local PostgreSQL database successfully. |
| HTTP API / full UI integration | Not verified | No browser-to-API flow (sign-in, save, search, recommendation, trends, Ask, or admin UI) was confirmed in this run. |
| Local live UI access | Blocked | Vite announced `http://localhost:5173/`, but laptop Edge could not connect; the execution environment does not expose this dev-server port to the desktop browser. |
| Frontend automated tests | Not configured | `frontend/package.json` provides `dev`, `build`, and `preview`, but no `test` script. |
| Paper catalog import | Pass | The local database contains 500 `papers`, 1,061 `paper_authors`, and 500 `paper_sources` rows after an additive schema migration and seed import. |
| Synthetic data generator | Pass | Container run completed: 50 users, 600 posts, 1,600 comments, 14,125 events, 300 saves, 750 upvotes, 150 user follows, 175 topic follows, and three planted duplicate pairs. |
| Database-backed evaluator | Pass (execution) | Evaluator ran in the backend container against the local database and current ground truth. Metric quality is summarized below; execution success does not mean the methods beat their baselines. |

## Measured evaluation results

| Metric | Result |
| --- | ---: |
| TF-IDF + aliases Precision@10 | 0.1333 |
| TF-IDF + aliases MRR | 1.0000 |
| Lexical TF-IDF baseline Precision@10 | 0.1333 |
| Lexical TF-IDF baseline MRR | 1.0000 |
| Initial detector planted-pair matches / unreviewed candidates / planted pairs missed | 2 / 186 / 1 |
| Initial detector recall against the three planted pairs | 0.6667 |
| Co-save recommendation hit@10 | 0.0638 |
| Popular recommendation hit@10 | 0.1064 |
| Recommendation users evaluated | 47 |

Search placed a relevant result first for every labeled query (MRR 1.0), but only about 1.33 relevant items appeared per top ten on average; aliases did not improve these labels over plain lexical TF-IDF. Co-save recommendations performed below the popularity baseline. Member 2 confirmed the synthetic saves only test feature population, not realistic preferences, so these recommendation values should not be interpreted as evidence about real users. Member 2 also confirmed the 186 pairs outside the three planted pairs are unreviewed candidates, not validated false positives; precision/F1 therefore cannot be claimed from this incomplete ground truth. The missed planted pair has identical 777-character abstracts but no DOI/arXiv identifier. The detector now checks exact normalized abstracts as well as identifiers and title similarity, and the evaluator suppresses precision/F1 unless the duplicate labels are explicitly complete. Rerun evaluation to record results from the updated detector.

## Findings and follow-up

1. **Re-evaluate deduplication.** The detector now uses exact normalized abstract matches, which should catch the title-variant pair with identical abstracts. Rerun against the live database. Ask Member 2 to review more candidates before reporting precision/F1.
2. **Recommendation evaluation.** Synthetic saves populate the feature and are not validated behavior. Do not interpret co-save hit@10 (0.0638) versus popularity (0.1064) as real preference performance; describe it as a synthetic-data smoke comparison or collect reviewed interaction labels.
3. **Manual browser integration.** In the local browser, sign in, search for a seeded paper, save/unsave it, check recommendations and the library, then exercise trends, Ask, and admin-only pages. The evaluator and generator validate backend/database access, not these UI flows.
4. **Frontend bundle-size warning.** Vite reports the generated JavaScript bundle at 614 kB minified, above its 500 kB advisory threshold. Build succeeds; code splitting could reduce initial download size.

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

**Route wiring: contract-tested. Production build and focused backend tests: pass. Paper catalog and synthetic data: loaded locally. Evaluation: executed; search matches baseline, duplicate precision and co-save recommendations need improvement. Manual browser integration remains to be checked.**
