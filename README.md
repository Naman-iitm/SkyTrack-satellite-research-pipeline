# SkyTrack – Satellite Research Pipeline

A Streamlit-based pipeline for enriching satellite datasets using structured public sources and producing standardized, research-ready outputs.

The application streamlines satellite metadata collection, validation, and export for research workflows by combining multiple data sources into a single interface.

<img width="1470" height="803" alt="Screenshot 2026-07-22 at 7 40 47 PM" src="https://github.com/user-attachments/assets/088abf3c-383b-4216-ad3e-f155b3cb4059" />


---

## Overview

SkyTrack supports end-to-end processing of satellite records through:

- Multiple input methods
- Automated metadata enrichment
- Batch processing
- Evidence tracking
- Google Sheets integration
- Structured Excel exports

The project is intended to reduce repetitive manual work while keeping researchers in control of final verification.

<img width="2282" height="1454" alt="image" src="https://github.com/user-attachments/assets/c3e05e94-c553-4a15-a6fe-e62e0bab30e2" />

---

## Features

### Data Input

- CSV upload
- Excel upload
- Manual satellite name entry
- Google Sheets import
<img width="2278" height="1410" alt="image" src="https://github.com/user-attachments/assets/e3889105-de29-4e7a-b470-086f967e1921" />

### Data Enrichment

Current enrichment sources include:

- UCS Satellite Database
- CelesTrak SATCAT
- Wikipedia (fallback)
- Launch vehicle reference database
<img width="2238" height="1142" alt="image" src="https://github.com/user-attachments/assets/161041fd-a4d7-4924-880c-d6c2f910d4c2" />

### Processing

- Batch processing
- Automatic field mapping
- Confidence scoring
- Manual review support
- Evidence logging
<img width="2236" height="1130" alt="image" src="https://github.com/user-attachments/assets/0ad819d1-4155-429a-a6db-43a72a739161" />

### Export

- Research dataset
- GPT dataset
- Evidence log
- Excel workbook
- Google Sheets export
![Uploading image.png…]()

---

## Project Structure

```
.
├── app.py
├── requirements.txt
├── launch_vehicle_reference.csv
├── satellite_app/
│   ├── constants.py
│   ├── gsheets.py
│   ├── helpers.py
│   ├── pipeline.py
│   ├── preferred_rag.py
│   ├── project_audit.py
│   ├── scoring.py
│   ├── sources.py
│   └── websites_catalog.py
├── sample_satellite_input.csv
└── .streamlit/
```

---

## Installation

Clone the repository

```bash
git clone https://github.com/Naman-iitm/SkyTrack-satellite-research-pipeline.git
cd SkyTrack-satellite-research-pipeline
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run the application

```bash
streamlit run app.py
```

---

## Supported Inputs

- CSV
- Excel (.xlsx)
- Google Sheets
- Manual satellite names

---

## Outputs

The application generates:

- Structured research dataset
- GPT dataset
- Evidence log
- Review tables
- Multi-sheet Excel workbook

---

## Google Sheets

Authentication is supported through either:

- Uploaded Service Account JSON
- `GOOGLE_SERVICE_ACCOUNT_JSON` environment variable

---

## Deployment

The project can be deployed directly on Streamlit Cloud.

```bash
streamlit run app.py
```

For Google Sheets support, configure the service account credentials as Streamlit Secrets or environment variables.

---

## Notes

- This tool is designed to assist research workflows.
- Low-confidence records should be manually verified.
- Matching quality improves significantly when the UCS Satellite Database is provided.
- Certain fields, such as launch cost estimates, may require additional validation.

---

## License

This project is intended for research and educational purposes.

---

## Author

**Naman Jha**

Research • Data Engineering • AI Applications
