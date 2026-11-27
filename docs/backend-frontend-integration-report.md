# Backend / Frontend Integration Test Report

**Project:** Chanakya ScholarSphere (Research Commons)
**Checked:** 27 November 2026
**Revision checked:** `main` based on `0c87bcf` (PR #7 merge), with this follow-up committed on top
**Runtime check:** 27 November 2026, using the local Docker Compose database and browser

## Summary

The React production bundle builds successfully. An automated static contract check confirms that the frontend API calls map to registered FastAPI routes and that the `/api` proxy targets the expected local and Compose backend addresses. The confirmed Member 2/Member 3 evaluation-label mismatch is fixed with an adapter that accepts both schemas; the evaluator now defaults to the shared synthetic ground-truth file. Thirteen focused backend tests, Python source compilation, ground-truth JSON parsing, and isolated duplicate/ranking metric checks pass.

The local Docker stack is now reachable in the browser. The home feed and Library loaded database-backed content; Search, Ask, and Settings screens rendered; the AI chatbox returned a cited answer to a sample question; and the Admin dashboard loaded after signing in with the shared admin account. The dashboard displayed platform metrics, topic analytics, saved papers, and flagged accounts. The browser reported no console errors during these checks. The admin session was signed out after verification. This was a manual UI smoke check, not a complete exhaustive test of every interaction. The separate candidate-review ledger has provisional labels for all 189 non-planted pairs: 159 not duplicate, 22 likely duplicate pending verification, and 8 ambiguous. These labels are not final evaluator ground truth. There is no frontend `npm test` script. A local FastAPI import attempt in the coding environment failed under Python 3.14.7 while building SQLModel models; the project's Dockerfile targets Python 3.12, so that host result does not establish a failure in the intended container runtime.

## Checks performed

| Check | Result | Notes |
| --- | --- | --- |
| Git revision | Pass | The follow-up changes are committed on `main`, based on `0c87bcf` (PR #7 merge). |
| Frontend API base/proxy | Pass by inspection | `frontend/src/api.js` prefixes requests with `/api`; Vite proxies `/api` to the backend. Docker Compose sets the backend service URL. |
| Route alignment | Pass | Added a static contract test: all discovered frontend API paths match backend router paths after route prefixes and dynamic IDs are normalized. |
| React production build | Pass | `npm run build` completed; 660 modules transformed. Bundle is 614 kB minified and Vite reports its advisory size warning. |
| Backend Python syntax | Pass | `compileall` completed for `backend/app` and `backend/generate_synthetic_data.py`. |
| Synthetic ground truth | Pass | `backend/data/synthetic_ground_truth.json` parses as valid JSON. |
| Mining/evaluation helpers | Pass | Isolated checks passed for title duplicate detection, duplicate pair metrics, Precision@K, and MRR. |
| Ground-truth/evaluator contract | Pass after fix | `evaluation_labels.py` maps Member 2's `duplicate_paper_pairs` / `search_relevance_labels[].relevant_documents` to the evaluator format, keeps support for the example format, and evaluation defaults to `data/synthetic_ground_truth.json`. |
| Backend regression/contract tests | Pass | `python -m unittest discover -s tests -v`: 13 tests passed, including synthetic labels, frontend-to-FastAPI route/proxy contracts, and intelligence helper coverage. |
| FastAPI import / route smoke test | Blocked in this host environment | Python 3.14.7 with SQLModel 0.0.22 / Pydantic 2.14.4 raises `PydanticUserError: Field 'id' requires a type annotation` during model import. The project container uses Python 3.12. |
| Database-backed generator / evaluator | Pass | The synthetic generator and evaluation command ran inside the backend container and queried the local PostgreSQL database successfully. |
| HTTP API / UI smoke check | Pass, partial | Home feed and Library data loaded; Search, Ask, and Settings rendered; AI chat returned a cited answer; Admin dashboard loaded under the shared admin account. Not every control or workflow was exercised. |
| Local live UI access | Pass | Browser opened `http://localhost:5173/`; backend health previously returned `ok` at `/api/health`. |
| Frontend automated tests | Not configured | `frontend/package.json` provides `dev`, `build`, and `preview`, but no `test` script. |
| Paper catalog seed import | Pass | The seed loaded 500 `papers`, 1,061 `paper_authors`, and 500 `paper_sources` rows after an additive schema migration. |
| Current catalog abstract coverage | Pass | A live query returned 503 total paper rows and 503 with non-empty abstracts (the 500-row seed plus three planted duplicate-evaluation copies). The count after duplicate resolution has not been established. |
| Synthetic data generator | Pass | Container run completed: 50 users, 600 posts, 1,600 comments, 14,125 events, 300 saves, 750 upvotes, 150 user follows, 175 topic follows, and three planted duplicate pairs. |
| Database-backed evaluator | Pass (execution) | Evaluator ran in the backend container against the local database and current ground truth. Metric quality is summarized below; execution success does not mean the methods beat their baselines. |

## Measured evaluation results

| Metric | Result |
| --- | ---: |
| TF-IDF + aliases Precision@10 | 0.1000 |
| TF-IDF + aliases MRR | 1.0000 |
| Lexical TF-IDF baseline Precision@10 | 0.1000 |
| Lexical TF-IDF baseline MRR | 1.0000 |
| Detector planted-pair matches / reviewed non-planted candidates / planted pairs missed | 3 / 189 / 0 |
| Candidate review statuses (provisional) | 159 not duplicate / 22 likely duplicate / 8 ambiguous |
| Recall against the three planted pairs | 1.0000 |
| Duplicate precision / F1 | Not reported (ground truth is incomplete) |
| Co-save recommendation hit@10 | 0.1064 |
| Popular recommendation hit@10 | 0.1702 |
| Recommendation users evaluated | 47 |

Search placed a relevant result first for every labeled query (MRR 1.0), with one relevant item per top ten on average; aliases did not improve these labels over plain lexical TF-IDF. The updated detector finds all three planted pairs, including the title variant with an identical 777-character abstract and no DOI/arXiv identifier. The 189 additional candidates have provisional labels (159 not duplicate, 22 likely duplicate pending verification, and 8 ambiguous); they are not final evaluator ground truth, so precision/F1 are withheld. Co-save recommendations remain below the popularity baseline. Member 2 confirmed the synthetic saves only test feature population, not realistic preferences, so these recommendation values should not be interpreted as evidence about real users.

## Findings and follow-up

1. **Finalize duplicate labels.** Verify the 22 likely duplicates and resolve the 8 ambiguous pairs before using the ledger as evaluator ground truth; do not report precision/F1 from provisional labels.
2. **Recommendation evaluation.** Synthetic saves populate the feature and are not validated behavior. Do not interpret co-save hit@10 (0.1064) versus popularity (0.1702) as real preference performance; describe it as a synthetic-data smoke comparison or collect reviewed interaction labels.
3. **Remaining UI checks.** The manual smoke check confirms the app opens and core screens render. Search submission, save/unsave, recommendations, Ask page submission, settings changes, and individual admin drill-down actions were not exercised in this pass.
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

**Route wiring: contract-tested. Production build and earlier focused backend tests: pass. Paper catalog and synthetic data: loaded locally. Manual browser smoke check: pass for the screens and actions listed above. The detector recalls all planted pairs; duplicate precision remains unknown until candidates are reviewed. Search matches baseline; synthetic co-save recommendations trail popularity. Some UI workflows and drill-down actions remain unverified.**
