# Member 3 evaluation

The metric script lives at `backend/app/evaluate_intelligence.py`. It runs against
the same PostgreSQL database as the application and prints a Markdown table.

1. Ask Member 2 to provide reviewed `search_qrels` and `duplicate_pairs` in the
ground-truth JSON. Do not use the example placeholders as labels.
2. Copy `backend/data/evaluation_ground_truth.example.json` to
`backend/data/evaluation_ground_truth.json` and replace the placeholders.
3. From the repository root, run:

   ```powershell
   docker compose exec backend python -m app.evaluate_intelligence --labels data/evaluation_ground_truth.json
   ```

The output includes Precision@10 and MRR for TF-IDF with query aliases versus a
plain lexical TF-IDF baseline, and a leave-one-out recommendation hit@10
comparison between co-save recommendations and most-popular papers.
Recommendation metrics need `saves` rows and at least two distinct saved papers
per evaluated user. For duplicate detection, report precision/recall/F1 only
when `duplicate_ground_truth_complete` is `true`. With an incomplete list, the
evaluator reports recall against the planted pairs and counts other detections
as unreviewed candidates rather than false positives.

For duplicate pairs, use the stable paper UUIDs in the database. DOI or arXiv
matches, exact normalized abstracts, and exact normalized titles count as
duplicate evidence. Other title-only matches use the configured
MinHash/Jaccard threshold.

To export candidates with both abstracts and identifiers for human review, run
from the repository root:

```powershell
docker compose exec backend python -m app.export_duplicate_candidates
```

The CSV appears at `backend/data/duplicate_candidate_review.csv` on the host.
Pairs outside the planted labels remain unreviewed until someone adjudicates
them; do not count them as false positives before that review.
