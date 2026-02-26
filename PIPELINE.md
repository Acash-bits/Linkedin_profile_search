# Pipeline Execution Guide

This document describes the correct execution order for each regional pipeline.

---

## USA Pipeline

### Prerequisites
- `usa` database created and schema applied
- `usa_companiesmarketcap` table populated with company names and ticker symbols

### Execution Order

| Step | Script | Reads From | Writes To |
|------|--------|-----------|----------|
| 1 | `usa_companies_address_library.py` | `usa_companiesmarketcap` | `usa_companies_final` |
| 2 | `website_link_retriever.py` | `usa_companies_final` | `usa_companies_final.Company_Website` |
| 3 | `usa_key_people_web_agent.py` | `usa_companies_final` | `Key_people_info` |
| 4 | `linkedin_profile_finder.py` | `Key_people_info` | `LinkedIn_Profiles` |
| 5 | `email_id_curator.py` | `Key_people_info` + `usa_companies_final` | `usa_top_companies_key_people_email` |
| 6a | `usa_listed_companies_link_aggregator.py` | `usa_companiesmarketcap` | `USA_companies_link` |
| 6b | `sector_content_retriever.py` | `USA_companies_link` | `usa_companies_sector` |

Steps 6a and 6b are **independent** of steps 1–5 and can be run in parallel.

---

## UK Pipeline

### Prerequisites
- `UK` database created and schema applied
- `mytable` populated with UK company names, symbols, and countries

### Execution Order

| Step | Script | Reads From | Writes To |
|------|--------|-----------|----------|
| 1 | `uk_listed_companies_information_web_agent.py` | `mytable` | `UK_listed_Companies_Database` |
| 2 | `uk_companies_linkedin_search.py` | `UK_Key_people_info` | `UK_LinkedIn_Profile` |
| 3 | `designation_analyzer.py` | `uk_linkedin_profile` | `key_people_summary` |

> Note: `UK_Key_people_info` must be populated before step 2. Use a similar Yahoo Finance scraper adapted for UK tickers, or populate it manually.

---

## Standalone / Utility Scripts

| Script | Purpose | Output |
|--------|---------|--------|
| `sector_name_harvestor_to_excelr.py` | Audit all available sector categories | `~/Desktop/categories.xlsx` |

---

## Resuming Interrupted Runs

Every long-running script supports resumption. Update the resume variable before re-running:

```python
# linkedin_profile_finder.py — line at bottom
start_id = 1360  # Change to last successfully processed ID + 1

# website_link_retriever.py
last_processed_id = 1592  # Change to last successfully processed ID

# sector_content_retriever.py / usa_listed_companies_link_aggregator.py
specific_company = "Company Name Here"  # Script resumes AFTER this company
```
