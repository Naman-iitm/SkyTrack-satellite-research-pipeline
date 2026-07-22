# Satellite Project Successor Tool

Ye final improved Streamlit app hai jo current one-by-one prototype ko replace karne ke liye banaya gaya hai.

## Kya improve hua hai

### Option 1 — Exact sheet columns
App exact **Data tab** aur **GPT tab** ke required columns generate karta hai.

### Option 2 — Google Sheets integration
- Google Sheet se input read kar sakta hai
- direct multiple worksheets me output likh sakta hai
- overwrite ya append dono modes supported hain

### Option 3 — Official-source enrichment
Current version me ye live / structured sources use hote hain:
- **UCS Satellite Database** (uploaded by user; primary source)
- **CelesTrak SATCAT** live CSV
- **Wikipedia summary fallback**
- **Launch vehicle reference layer** for max LEO mass / reusability / approximate launch cost

### Option 4 — Better UI
- batch processing
- manual column mapping
- editable review tables
- evidence log
- export workbook with multiple sheets
- cleaner tabs and workflow

---

## Files

- `app.py` → main Streamlit app
- `requirements.txt` → dependencies
- `launch_vehicle_reference.csv` → launch vehicle reference layer
- `satellite_app/constants.py` → exact schemas and mappings
- `satellite_app/helpers.py` → utilities
- `satellite_app/sources.py` → file reading + UCS/CelesTrak/Wikipedia source logic
- `satellite_app/scoring.py` → GPT / SDG / Frugal / Numeric heuristics
- `satellite_app/gsheets.py` → Google Sheets read/write helpers
- `satellite_app/pipeline.py` → end-to-end batch processor

---

## Local run

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Input modes supported

1. **Upload local CSV / Excel**
2. **Google Sheet input**
3. **Manual name paste**

---

## Google Sheets setup

### Method 1: Upload credential JSON in the app
Best for easy usage.

### Method 2: Environment variable
Set this in deployment:

- `GOOGLE_SERVICE_ACCOUNT_JSON`

Ye full service-account JSON string hona chahiye.

---

## Deploy on Streamlit Cloud

1. Code GitHub repo me push karo
2. Streamlit Cloud pe new app create karo
3. `app.py` ko main file select karo
4. Agar Google Sheet writing chahiye toh secrets / env me `GOOGLE_SERVICE_ACCOUNT_JSON` add karo

---

## Important notes

- Ye version **workflow successor** hai, not perfect autonomous researcher.
- Low-confidence rows ko manual official-source verification dena chahiye.
- Cost-related rows especially manual validation maang sakte hain.
- Agar UCS database upload karoge toh matching quality kaafi improve hogi.
- Agar local machine par **CelesTrak SSL error** aaye, updated code CelesTrak ko safer requests-based fallback se load karta hai. Emergency workaround: **Use CelesTrak SATCAT live data** toggle off karke bhi processing run kar sakte ho.

---

## Suggested next upgrades (future)

- more official-space-agency scrapers
- source snippet highlighting per field
- cached row history database
- manual reviewer comments + approval tracking
- stronger cost parsers
- direct Google Sheet column sync with existing project tabs
