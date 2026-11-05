# Experiments: before and after

Test set: the 10 sample questions (S01 to S10).
Metrics come from `python eval/evaluate.py <expected> <results> --retrieval`.
Hit@5 and MRR are computed over the 5 sample questions that need a document.

| # | Change | Hit@5 | MRR | Right source | Behaviour correct | What we learned |
|---|--------|-------|-----|--------------|-------------------|-----------------|
| 1 | Keyword search only (BM25) | not measured | not measured | | | |
| 2 | + meaning search (hybrid, RRF) | not measured | not measured | | | |
| 3 | + recency boost (newer rules rank higher) | 1.00 (5/5) | 1.00 | 5/5 | 9/10 on the sample file compared with itself (S05 is a scoring artefact) | The full system finds the right document at rank 1 for every document question. |
| 4 | + SQL safety checks and refusal | n/a | n/a | n/a | S10 refused correctly | Write queries are never run. The database opens read-only. |

## Notes
- Old vs new rules: the 2015 file (48/12/4 hours) does not appear in the top 5 for the "12 hours before departure" question. The 2026 documents fill all five slots.
- Timetable answers always say the data is a 2016 snapshot.
- Rows 1 and 2 will be filled with measured numbers if there is time. Until then they stay "not measured".