# How to Use the Tool for Your 100-Satellite Deliverable

## Goal
Fill **100 satellites that are not already properly completed** in the project sheets, while:
- preserving existing RA work
- filling only missing / weak rows
- keeping source links
- avoiding unsupported guesses

---

## Recommended workflow

### Step 1 — Prepare files
Keep these files ready:
- current `DATA` sheet export
- current `GPT DATA` sheet export
- `Websites.csv`
- optional UCS database file

---

### Step 2 — Open app
Run:

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

---

### Step 3 — Setup tab uploads
In **Setup & Run** tab:

#### A. Existing project sheets
Upload:
- current DATA tab CSV/XLSX
- current GPT DATA tab CSV/XLSX
- Websites mapping CSV

#### B. Optional UCS DB
Upload the UCS database if available.
This improves matching quality.

#### C. Processing options
Recommended:
- `Use CelesTrak SATCAT live data` = ON
- `Use Wikipedia summary fallback` = ON
- `Use preferred-source RAG flow (project websites first)` = ON

---

### Step 4 — Project Audit tab
Go to **Project Audit & Queue**.

This is the most important tab.

Here you can:
- detect complete rows
- detect partial rows
- detect missing GPT rows
- detect missing DATA rows
- see which rows are assigned / unassigned
- generate a work queue

### Best filter for actual work
Use status filters such as:
- `Missing GPT row`
- `Needs GPT fill`
- `Partial / Review`
- `Missing DATA row`
- `Needs DATA fill`

If you need only unclaimed rows:
- turn on `Only unassigned rows`

Set queue size:
- `100`

Then download the queue if needed.

---

### Step 5 — Process only the queue
Go back to **Setup & Run**.

Turn ON:
- `Use work queue generated from Project Audit tab`

Now click:
- `Process All Satellites`

This ensures the app works on the smart queue, not the whole dataset.

---

### Step 6 — Review results
#### Data Tab Output
Check factual fields:
- launch date
- vehicle
- orbit
- mass
- costs
- reusability

#### GPT Tab Output
Check interpretive fields:
- USER
- PURPOSE
- SDG
- FRUGAL
- source links
- review status

#### Evidence Log
Use this to inspect why the tool made a classification.

---

### Step 7 — Focus on low-confidence rows
Rows marked:
- `Needs manual review`

should be manually checked first.

Especially verify:
- cost values
- frugal = yes/no
- military / government / commercial user type
- purpose type if multiple uses exist
- SDG mapping if too generic

---

### Step 8 — Export correctly
In **Export / Sheets** tab:

Choose export mode:
- `Merged into existing project sheets`

Then download:
- merged DATA sheet in original format
- merged GPT sheet in original format

These are the safest files to upload back to the project.

---

## Best practice for accuracy

### Always trust this source order
1. Existing project sheets
2. UCS database
3. Project-provided websites
4. CelesTrak / NSSDC / EO Portal / SatBeams / N2YO / project-listed databases
5. Wikipedia fallback
6. External web only if still unresolved

### Do not guess
If evidence is weak:
- leave blank
- review manually
- add note externally if needed

### Do not overwrite strong existing entries casually
The merged mode is designed to preserve existing non-empty rows.

---

## Suggested delivery workflow for you

### Batch 1
Run 25 rows first.
Review output quality.

### Batch 2–4
Then do the remaining rows in sets of 25.

This is safer than doing all 100 blindly at once.

---

## What to submit finally
- merged DATA sheet
- merged GPT DATA sheet
- evidence / notes if needed
- brief issue summary:
  - missing fields
  - unclear sources
  - inconsistent classifications
  - costs unavailable

---

## Fast strategy if you are short on time
1. Filter `Needs GPT fill`
2. Country filter if required
3. Pick 100 rows
4. Process queue
5. Review only flagged rows
6. Export merged original-format sheets

---

## Final note
This tool is meant to reduce repetitive work and help you focus on:
- missing rows
- weak rows
- verifiable source-backed completion

It is not meant to blindly auto-fill everything without review.
