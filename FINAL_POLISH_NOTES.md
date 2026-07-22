# Final Polish Notes

## A) Accuracy improvements added
- stronger user classification heuristics
- stronger purpose classification heuristics
- better frugal rules using multiple cost / architecture signals
- confidence bonus when preferred-source retrieval finds relevant project-approved pages

## B) Preferred-source RAG flow added
The tool now follows a more project-aligned order:
1. existing project sheets
2. uploaded UCS data
3. project-provided structured websites / databases
4. project-provided country websites
5. Wikipedia fallback only if needed

It also stores preferred-source retrieval in the evidence log.

## C) Google Sheets workflow polish
Recommended worksheet names:
- `DATA`
- `GPT DATA`
- `Numeric_Tab`
- `Evidence_Log`

If export mode is `Merged into existing project sheets`, the app can now produce original-format merged CSV files that are safer to upload back into the research workflow.

## D) Deliverable workflow guide
See:
- `HOW_TO_USE_FOR_100_SATELLITES.md`

This explains exactly how to use the project audit, queue generation, processing, review, and export workflow.
