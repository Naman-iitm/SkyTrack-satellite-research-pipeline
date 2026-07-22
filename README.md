# SkyTrack – Satellite Research Pipeline

A Streamlit-based pipeline for enriching satellite datasets using structured public sources and producing standardized, research-ready outputs.

The application streamlines satellite metadata collection, validation, and export for research workflows by combining multiple data sources into a single interface.

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

---

## Features

### Data Input

- CSV upload
- Excel upload
- Manual satellite name entry
- Google Sheets import

### Data Enrichment

Current enrichment sources include:

- UCS Satellite Database
- CelesTrak SATCAT
- Wikipedia (fallback)
- Launch vehicle reference database

### Processing

- Batch processing
- Automatic field mapping
- Confidence scoring
- Manual review support
- Evidence logging

### Export

- Research dataset
- GPT dataset
- Evidence log
- Excel workbook
- Google Sheets export

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
