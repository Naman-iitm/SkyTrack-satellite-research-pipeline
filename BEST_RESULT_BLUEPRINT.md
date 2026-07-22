# SkyTrack / SkyScraper Successor — Best Result Blueprint

## What this tool is supposed to do
This is not just a single-satellite scraper.
It is a **research workflow tool** for the ISRO Satellite Project.

It should:
- read the existing DATA and GPT sheets
- detect which rows are already complete
- detect which rows are partial / low quality / missing
- create a smart work queue (for example: 100 unfinished satellites)
- fill only missing cells
- preserve existing work by RAs
- provide source-backed outputs
- flag low-confidence rows instead of guessing
- export back into the project format

## What has already been improved in the code
- batch processing
- sheet-aware project audit
- work queue generation
- merged outputs into existing sheets
- original-format CSV exports for existing DATA / GPT sheets
- Google Sheets support
- CelesTrak SSL-safe fallback
- Excel export fallback when openpyxl is missing

## Ideal workflow
1. Upload current DATA tab and GPT DATA tab
2. Audit the project status
3. Generate a 100-row work queue
4. Process only that queue
5. Review low-confidence rows
6. Export merged DATA and GPT sheets

## Why this is better than the old tool
Old tool:
- one satellite at a time
- too many manual clicks
- JSON-centric
- unaware of already-filled rows

New tool:
- understands the existing project sheets
- identifies missing / weak rows
- supports batch verification
- reduces duplicate work
- keeps research workflow intact

## Current limits
- not all official sources are deeply scraped yet
- some GPT classifications still rely on heuristics
- final manual verification is still necessary for uncertain rows
- cost fields especially need careful review

## Best next upgrades (future)
- field-level source snippets
- stronger country-specific source routing
- caching of processed satellites
- reviewer comments and approval tracking
- per-field confidence instead of row-level confidence only
- more official space-agency parsers
