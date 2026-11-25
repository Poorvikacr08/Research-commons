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
plain lexical TF-IDF baseline, duplicate precision/recall/F1 against labeled
pairs, and a leave-one-out recommendation hit@10 comparison between co-save
recommendations and most-popular papers. Recommendation metrics need real `saves`
rows and at least two distinct saved papers per evaluated user. Search and
duplicate metrics are skipped until their reviewed labels are supplied.

For duplicate pairs, use the stable paper UUIDs in the database. DOI or arXiv
matches count as duplicates even when their titles differ. Title-only matches
use the configured MinHash/Jaccard threshold.
