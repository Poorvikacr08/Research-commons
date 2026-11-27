# Chanakya ScholarSphere — technical completion report

**Course:** Data Mining and Warehousing  
**Status reviewed:** 27 November 2026  
**Scope:** Faculty brief F1–F9, implementation, available database evidence, and reproducibility.

## Executive summary

The project implements the social research platform, shared paper library,
analytics dashboard, search, recommendations, trends and spam flags, and a
grounded research assistant. This completion pass added a local latent semantic
indexing (LSI) search path, missing admin analytics for most-discussed papers
and monthly engagement, a reproducible OpenAlex/RSS-to-PostgreSQL/MinIO batch
ingester, and an additive script for linking existing synthetic discussions to
topically matching papers.

The checked project database previously reported 503 paper records with
abstracts (the 500-row harvested catalog plus three planted duplicate test
copies). The 189 candidate review labels remain provisional: 159 not duplicate,
22 likely duplicate pending verification, and 8 ambiguous. Do not claim a final
unique-work count or duplicate precision/F1 until those labels are verified.
The latest database-backed search evaluation reports LSI hybrid P@10 0.10 and
MRR 0.8333, compared with P@10 0.10 and MRR 1.00 for both TF-IDF variants. LSI
did not improve the current labeled query set.

## Faculty criteria coverage

| Brief | Implementation | Status and evidence |
| --- | --- | --- |
| F1 Accounts and profiles | Student/faculty/researcher/admin accounts, profiles, interests and follows | Implemented in FastAPI and React; synthetic dataset contains 50 synthetic accounts across six departments, in addition to the admin. |
| F2 Research community | Posts, tags, paper attachments, comments/replies, upvotes and feed | Implemented. Generator creates 600 posts and 1,600 comments (2,200 combined), plus engagement rows. The additive linker populated 600 topic-matched paper links for existing synthetic posts. |
| F3 Shared library | Save by paper/identifier/URL, collections/private notes, shared save counts | Implemented in the library routes and PostgreSQL schema. Generator inserts real save rows as well as events. |
| F4 External data pipeline | Scholarly metadata and RSS, raw source capture, normalized PostgreSQL records, refresh | Reproducible importer added and run successfully: 72 OpenAlex works processed, 10 new RSS stories inserted, with raw payloads stored in MinIO. Paper, author and source tables are upserted. |
| F5 Search | Four panels, unified deduplicated paper results, keyword and semantic ranking | Hybrid local TF-IDF + LSI with research-term aliases is implemented. Latest evaluation: LSI P@10 0.10, MRR 0.8333; TF-IDF + aliases P@10 0.10, MRR 1.00. |
| F6 Recommendations | Paper and people recommendations, co-save suggestions, cold start | Implemented. Existing synthetic leave-one-out result was 0.1064 hit@10 versus 0.1702 for popularity across 47 users. Synthetic saves were not validated as realistic preferences, so this is a pipeline check, not a claim of recommendation quality. |
| F7 Trends and abuse signals | Topic spikes, admin spam/anomaly flags | Implemented and synthetic burst activity is available. Precision/recall for the flags has not been measured against reviewed labels. |
| F8 Research assistant | Grounded answer, numbered citations and retrieved passages | Implemented as extractive retrieval over stored abstracts, with citations and passage scores. This is the cost-free, explainable baseline; a local Ollama model remains an optional extension. |
| F9 Admin analytics | Topic trends, department drill-down, cross-department activity, most saved/discussed, engagement | Implemented and manually verified in the signed-in local UI. Overview, university→department→topic→member drill-down, cross-department matrix, most-saved and most-discussed papers, monthly engagement, spam flags, and spike alerts rendered with database data. |

## Architecture and data flow

- **Frontend:** React and Vite. `/api` requests are proxied to FastAPI.
- **API:** FastAPI routers use JWT identity and PostgreSQL sessions. Admin
  analytics and flags enforce the admin role.
- **Storage:** PostgreSQL 16 is the shared normalized application/catalog
  database. MinIO retains unmodified ingestion payloads. The repository includes
  the 500-row paper catalog SQL seed for a fresh database.
- **Ingestion:** OpenAlex scholarly articles and MIT News research/AI RSS are
  fetched in batches. Raw responses are stored by run and source; normalized
  catalog and author records are idempotently inserted or backfilled.
- **Search and mining:** TF-IDF lexical scoring is combined with corpus-fitted
  truncated-SVD/LSI cosine similarity and a small transparent alias map. Search
  merges exact DOI/arXiv duplicates and high-confidence title duplicates.
- **Q&A:** The assistant selects relevant abstract passages and composes a
  cited extractive response. It does not claim to generate evidence outside the
  retrieved catalog.

## Reproducing the application and data

From the repository folder in PowerShell:

```powershell
Copy-Item .env.example .env   # set unique local passwords in .env
docker compose up --build -d
```

The UI is at `http://localhost:5173`, API documentation at
`http://localhost:8000/docs`, health at `http://localhost:8000/api/health`, and
MinIO console at `http://localhost:9001`.

If the local database has no catalog, import the bundled seed from the project
folder with `.\db\import_papers.ps1`. Generate the synthetic accounts and
activity only when you intend to replace the previous synthetic dataset; the
generator cleans its own synthetic rows and rewrites its ground-truth file.
To add discussion links to already-generated synthetic data without deleting
or editing any rows:

```powershell
docker compose exec backend python link_synthetic_discussions.py
```

Run one ingestion batch:

```powershell
docker compose run --rm backend python -m app.ingest_external --openalex-limit 100 --rss-limit 20
```

Enable the optional 24-hour ingestion worker:

```powershell
docker compose --profile ingestion up -d --build
```

Run evaluation after the catalog and synthetic dataset are ready:

```powershell
docker compose exec backend python -m app.evaluate_intelligence --labels data/synthetic_ground_truth.json
```

The evaluator prints LSI hybrid, alias-enhanced TF-IDF, lexical TF-IDF,
planted-pair recall, and co-save versus popularity hit@10. Duplicate precision
and F1 remain suppressed unless the duplicate labels are declared complete.

## Evaluation evidence and interpretation

The latest database-backed run reported:

| Measure | Recorded result | Interpretation |
| --- | ---: | --- |
| LSI semantic + aliases P@10 / MRR | 0.1000 / 0.8333 | Same top-ten precision as the lexical baseline, with lower reciprocal rank on this qrel set. |
| TF-IDF + aliases P@10 / MRR | 0.1000 / 1.0000 | First relevant result ranked first for each labeled query. |
| Lexical TF-IDF P@10 / MRR | 0.1000 / 1.0000 | Alias expansion did not change these metrics for this label set. |
| Planted duplicate pairs found | 3 / 3 | Recall 1.0 on the three deliberately planted test pairs. |
| Unreviewed detector candidates | 189 | Not verified true/false positives. |
| Co-save hit@10 vs. popularity | 0.1064 vs. 0.1702 | Synthetic preference signal trails the simple popularity baseline. |
| Users in recommendation evaluation | 47 | Leave-one-out evaluation requires at least two distinct saved works. |

The run was performed after the LSI method was added. The implementation
provides a semantic retrieval path, but these labels do not show an improvement
over the lexical baselines. Describe that result honestly and avoid claiming
that LSI performed better.

## Verification and limits

The earlier integration pass recorded a successful React production build,
Python compilation, ground-truth parsing, 13 backend contract/regression tests,
database-backed synthetic generation/evaluation, and manual browser smoke
checks of the Home, Library, Search, Ask, Settings and Admin screens. The admin
screen and cited assistant response were manually checked. In this pass, the
admin role opened the dashboard and the university→department→topic→member
drill-down was exercised; the most-discussed and engagement panels populated
after synthetic paper links were added. Individual save, settings, and search
workflows were not re-exercised in this pass.

This completion pass changed search dependencies, ingestion, admin analytics,
and generated discussion links. The project owner subsequently rebuilt the
Docker stack and ran the database-backed evaluator successfully. RSS/OpenAlex
ingestion still needs a run with internet access. The repository does not
include an automated browser test suite.

Checks run during this completion pass: Python `compileall` passed; all 13
backend unit/contract tests passed when run from `backend/`; the React Vite
production build passed (662 modules, 628.61 kB main JavaScript bundle); Compose
configuration validation passed; and the ground-truth JSON parsed successfully.
The project owner's console output confirms Docker built the backend image,
started all four services, ran the evaluator against PostgreSQL, completed
OpenAlex/RSS ingestion, and added 600 topic-matched paper links for synthetic
posts.
The first ingestion attempt revealed an obsolete MIT News AI feed URL (HTTP
404). It was replaced with MIT's current `/rss/topic/artificial-intelligence2`
feed; a direct HTTP check returned 200 for that feed and the Research feed. The
subsequent batch completed: 72 OpenAlex works processed and 10 RSS stories
inserted, with the command reporting raw payloads stored in MinIO. The additive
linker then reported 600 rows inserted without deleting or editing existing
posts, papers, or interactions. The refreshed Admin page displayed eight
most-discussed papers (top count 501 comments), six months of engagement
series, and the expected flag and spike panels.

Known data limitations:

- 503 catalog rows and abstracts were observed; three rows are planted
  duplicate-evaluation copies. The final unique-work total is not certified
  while other candidate reviews remain provisional.
- Candidate labels currently comprise 159 not duplicate, 22 likely duplicate
  pending verification, and 8 ambiguous. Precision/F1 is therefore not a valid
  reported result.
- Recommendation interactions are synthetic and were built to exercise the
  feature, not to represent measured student preferences.
- Some harvested catalog records may describe proceedings or journal records
  rather than individual articles; note this catalog-quality limitation in the
  viva/report.
- The assistant is extractive and the search LSI model is trained on the
  current catalog at runtime. A larger or better-labeled corpus can change the
  rankings and evaluation values.

For public deployment, replace the demo credentials and local secrets, use
HTTPS, set access controls and backups, and run ingestion as a monitored job.
