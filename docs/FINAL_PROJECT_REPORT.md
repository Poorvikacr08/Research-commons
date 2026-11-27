# Chanakya ScholarSphere
## Data Mining and Warehousing Course Project

**Submitted to:** Faculty, Data Mining and Warehousing  
**Team size:** Three members  
**Project repository:** Poorvikacr08/Research-commons  
**Report date:** 27 November 2026

---

## 1. Introduction

Chanakya ScholarSphere is a research community platform for discovering scholarly papers, organizing a personal library, connecting researchers, and discussing research. It combines a React web interface with a FastAPI service, PostgreSQL for relational application and catalog data, and MinIO for source files. The project demonstrates data mining and warehousing ideas through search, recommendation, duplicate-candidate detection, activity analytics, topic trends, and a paper-grounded research assistant.

The work was divided across three team members. Member 1 developed the shared application foundation and community interface; Member 2 developed the paper data platform and analytics; Member 3 developed search and research-intelligence features. The modules were integrated through shared database tables and agreed API response formats.

## 2. System Requirements

### 2.1 Software

- Docker Desktop with Docker Compose.
- A modern browser.
- Windows, macOS, or Linux for local development.
- Python 3.12 in the backend container, Node.js 22 in the frontend container, and PostgreSQL 16 are supplied by the Compose services.
- Internet access is required for OpenAlex and RSS ingestion. Core app functions and local search do not require a paid API or hosted AI service.

### 2.2 Services and local addresses

| Service | Purpose | Local address |
| --- | --- | --- |
| React/Vite | User interface | `http://localhost:5173` |
| FastAPI | Application API and interactive documentation | `http://localhost:8000` and `/docs` |
| PostgreSQL 16 | Application, catalog, and activity records | `localhost:5432` |
| MinIO | Raw ingestion object storage | `http://localhost:9001` console |

### 2.3 Starting the application

From the repository directory, create `.env` from `.env.example`, replace the example values with private local secrets, and start the services:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

The database initialization scripts run on a fresh PostgreSQL volume. For an existing volume, the bundled paper import script can load the catalog if it is empty. `.env` contains local secrets and must not be committed.

## 3. Methodology and Design

### 3.1 Architecture

The React frontend sends `/api` requests through the Vite proxy to FastAPI. FastAPI validates requests, applies JWT-based identity and role checks, and reads or writes PostgreSQL. Paper and news ingestion stores unmodified source payloads in MinIO and normalized metadata in PostgreSQL. Docker Compose provides a reproducible local environment for the four application services.

### 3.2 Data design

PostgreSQL holds users, interests, follows, posts, tags, comments, votes, saves, collections, activity events, papers, paper authors, and paper sources. UUIDs identify records. Activity events capture actions such as views, searches, saves, follows, posts, comments, and upvotes for analytics and mining. Paper authors and source metadata are stored separately from paper records. MinIO stores raw OpenAlex and RSS payloads.

The shared catalog originally included 500 harvested OpenAlex records, and three additional records were planted for duplicate-detection evaluation. A later ingestion run processed more OpenAlex works and RSS stories; the project report recorded 605 paper rows after that run. This is a row count, not a certified unique-work count. The duplicate review labels are provisional, so the project does not claim a final unique-work total or duplicate precision/F1.

### 3.3 Data mining methods

- **Search:** TF-IDF lexical ranking, latent semantic indexing (LSI), and a small research-term alias map. Paper results merge exact DOI/arXiv duplicates and selected high-confidence title duplicates.
- **Recommendations:** Content similarity, co-save signals, shared interests, department context, and popular-item cold-start behavior.
- **Duplicate candidates:** Similarity-based candidate generation with DOI, arXiv, title, and abstract evidence. Human review labels remain provisional.
- **Trends and abuse signals:** Time-window comparisons for topics and rule-based flags for bursty or repetitive activity.
- **Research assistant:** Retrieves passages from stored abstracts and returns an extractive answer with numbered citations. It does not require a paid model API.
- **Analytics:** Aggregated event and content measures with department/topic filtering and drill-down for administrators.

### 3.4 User interface design

The interface uses a university-inspired navy, cream, and gold palette, with the Chanakya ScholarSphere identity. Search is divided into result panels for external papers, the library, people, and posts. The paper detail experience now includes **Knowledge Threads**: a visual path from a paper to detected topic chips and matching papers, researchers, and discussions. Selecting a topic queries the existing search endpoint; the feature does not introduce a separate graph database or paid service.

## 4. Implementation

### 4.1 Features delivered

| Module | Implemented capability |
| --- | --- |
| F1 — Accounts | Registration, login, roles, profiles, interests, people search, and user/topic follows. Passwords use bcrypt and sessions use JWT. |
| F2 — Research community | Posts, tags, attached papers, threaded comments, upvotes, feeds, and topic pages. |
| F3 — Shared library | Save papers by supported identifiers or URL, collections, private notes, and shared save counts. |
| F4 — Data platform | OpenAlex and RSS batch ingestion, normalized paper/author/source records, MinIO raw payloads, and a shared SQL catalog seed. |
| F5 — Search | Four-panel search with lexical and LSI ranking, aliases, and paper-result deduplication. |
| F6 — Recommendations | Paper and people recommendations, co-save suggestions, and cold-start popular results. |
| F7 — Trends and abuse | Topic trend/spike analysis and administrative spam/activity flags. |
| F8 — Research assistant | Abstract-grounded answers with citations and retrieved passages. |
| F9 — Analytics | Admin overview, monthly engagement, topic/department drill-down, cross-department activity, and most-saved/discussed papers. |
| Knowledge Threads | Paper detail visualization that connects the current paper to relevant topics, papers, researchers, and discussions using existing search results. |

### 4.2 Team contributions

**Member 1 — Application and UI**

- Set up the repository and Docker Compose services, shared schema, authentication, and common API error handling.
- Implemented account/profile, social posting, comments, feeds, shared library, collections, and the React application screens.
- Integrated the screen contracts for search, recommendations, trends, Ask, analytics, and admin features with the other members’ APIs.
- Reported an integrated local UI check covering the main screens and administrator dashboard.

**Member 2 — Data platform and analytics**

- Prepared and integrated the original 500-paper OpenAlex catalog with author and source metadata; configured MinIO for raw objects and DuckDB/Parquet exploration.
- Implemented the data ingestion and analytics work, including admin topic/time filters and drill-down functionality.
- Created synthetic activity data for evaluation: 50 users across six departments, 600 posts, 1,600 comments, 14,125 events at generation time, 300 saves, 750 upvotes, 150 user follows, and 175 topic follows. Later checks recorded 14,137 events after additional activity.
- Planted duplicate pairs and activity patterns, produced relevance labels, and reviewed 189 duplicate candidates. Final review labels were 159 not duplicate, 22 likely duplicate pending verification, and 8 ambiguous. Those labels are provisional and were not database edits.
- The ingestion command later completed a batch processing 72 OpenAlex works and inserting 10 RSS stories; raw payloads were reported stored in MinIO.

**Member 3 — Search and intelligence**

- Implemented search, paper and people recommendations, co-save suggestions, topic trends, administrative activity flags, duplicate-candidate detection, and the paper-grounded Ask endpoint.
- Added LSI as a semantic retrieval path and evaluation output for search, planted-pair recall, and leave-one-out recommendation comparison.
- Added **Knowledge Threads** to paper pages, with topic selection and connected search-result sections for related papers, researchers, and discussions.
- Evaluated the features using the project’s synthetic labels and documented limitations where data was insufficient or provisional.

## 5. Evaluation and Verification

### 5.1 Recorded evaluation results

| Metric | Recorded result | Interpretation |
| --- | ---: | --- |
| LSI semantic + aliases Precision@10 | 0.1000 | Equal P@10 to the lexical baselines on the available labeled queries. |
| LSI semantic + aliases MRR | 0.8333 | Lower than the lexical baselines for this query-label set. |
| TF-IDF + aliases Precision@10 / MRR | 0.1000 / 1.0000 | First relevant result ranked first for the labeled queries. |
| Lexical TF-IDF Precision@10 / MRR | 0.1000 / 1.0000 | Baseline performance on the same labels. |
| Planted duplicate pairs detected | 3 of 3 | Recall 1.0 on the deliberately planted evaluation pairs only. |
| Other duplicate candidates | 189 | Reviewed provisionally; not a complete true/false label set. |
| Co-save recommendation hit@10 | 0.1064 | Synthetic leave-one-out result across 47 users. |
| Popular recommendation hit@10 | 0.1702 | Outperformed co-save on this synthetic evaluation set. |

These results do not show that LSI or co-save recommendations outperformed their simple baselines. The synthetic saves were designed to exercise the application and are not validated as real user preferences. Duplicate precision and F1 are not reported because labels are provisional/incomplete.

### 5.2 Build and integration evidence

- A React/Vite production build passed after the Knowledge Threads change (664 modules transformed).
- `git diff --check` passed for the implementation changes before commit.
- The latest feature commit was pushed to `main` as `487f749` (`Add paper knowledge threads`).
- Prior project checks recorded successful Compose startup, backend evaluation against PostgreSQL, OpenAlex/RSS ingestion, and generation of 600 topic-matched links for synthetic posts.
- Prior manual UI checks covered the Home, Library, Search, Ask, Settings, and Admin flows. Those checks reported no browser console errors and verified the admin dashboard and drill-down with data.

The Knowledge Threads feature itself has a successful production build but has not yet been separately confirmed through a manual browser walkthrough after the push. There is no repository automated browser end-to-end suite.

## 6. Limitations and Future Work

- The 605 paper-row count recorded after ingestion is not a deduplicated unique-work count. Candidate review labels are provisional; report duplicate precision/F1 only after a complete verified label set exists.
- Some harvested records may describe proceedings or journal-level entries rather than individual articles.
- The recommendation evaluation is synthetic and co-save hit@10 is below the popularity baseline in the recorded run.
- LSI did not improve MRR over lexical TF-IDF for the available relevance labels. A larger, independently judged search set is needed for stronger conclusions.
- The research assistant is extractive rather than an Ollama-powered generative RAG system. This keeps the prototype free and makes citations traceable, but limits response synthesis.
- Knowledge Threads derives topics from a compact vocabulary/title-term fallback and uses the existing text search API. It is a discovery visualization, not a separately persisted knowledge graph.
- Public deployment still requires production hosting, HTTPS, secure deployment secrets, access controls, backups, and operational monitoring.

## 7. Conclusion

Chanakya ScholarSphere brings together a research-paper catalog, academic community features, analytics, search, recommendations, duplicate review, topic trends, and cited abstract-based assistance in a locally reproducible application. Work was divided across three members and integrated through the shared database and API. The measured results and data limitations are documented without treating synthetic activity or provisional labels as real-world evidence. Knowledge Threads extends the paper page into a connected discovery path using the platform’s existing data and endpoints. The production frontend build passes; a final manual walkthrough of the new thread UI and viva demonstration are the remaining presentation checks.
