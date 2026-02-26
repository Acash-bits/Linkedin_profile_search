# Pipeline Execution Guide — USA

This document describes the correct execution order, dependencies, and resume instructions for the USA intelligence pipeline.

---

## Execution Order

| Step | Script | Reads From | Writes To | Can Skip? |
|------|--------|-----------|----------|-----------|
| 1 | `usa_companies_data_fetcher.py` | `usa_companiesmarketcap` | `usa_companies_final` | No — foundation for all other scripts |
| 2 | `usa_companies_website_fetcher.py` | `usa_companies_final` | `usa_companies_final.Company_Website` | No — required by email finder |
| 3 | `usa_executives_scraper.py` | `usa_companies_final` | `Key_people_info` | No — required by LinkedIn and email finders |
| 4a | `usa_executives_linkedin_finder.py` | `Key_people_info` | `LinkedIn_Profiles` | Yes — optional enrichment |
| 4b | `usa_executives_email_finder.py` | `Key_people_info` + `usa_companies_final` | `usa_top_companies_key_people_email` | Yes — final deliverable |
| 5a | `usa_companies_link_builder.py` | `usa_companiesmarketcap` | `USA_companies_link` | Yes — only needed for sector data |
| 5b | `usa_companies_sector_scraper.py` | `USA_companies_link` | `usa_companies_sector` | Yes — only needed for sector data |

Steps 4a and 4b can run in parallel after step 3. Steps 5a and 5b are fully independent and can run any time after step 1.

---

## Dependency Tree

```
usa_companiesmarketcap  (seed — must be populated manually)
        │
        ├──► usa_companies_data_fetcher.py
        │           │
        │           └──► usa_companies_final
        │                       │
        │                       ├──► usa_companies_website_fetcher.py
        │                       │           (updates usa_companies_final)
        │                       │
        │                       └──► usa_executives_scraper.py
        │                                   │
        │                                   └──► Key_people_info
        │                                               │
        │                                   ┌───────────┴───────────┐
        │                                   │                       │
        │                    usa_executives_linkedin_finder    usa_executives_email_finder
        │                                   │                  (also needs usa_companies_final)
        │                                   │
        │                            LinkedIn_Profiles    usa_top_companies_key_people_email
        │
        └──► usa_companies_link_builder.py
                    │
                    └──► USA_companies_link
                                │
                                └──► usa_companies_sector_scraper.py
                                            │
                                            └──► usa_companies_sector
```

---

## Resuming Interrupted Runs

Every long-running script has a built-in resume mechanism. Locate the variable listed below, update it to the last successfully processed point, and rerun the script.

### `usa_companies_website_fetcher.py`

```python
last_processed_id = 1592  # Update to last successfully updated row ID
```

Find the correct value:
```sql
SELECT MAX(ID) FROM usa_companies_final WHERE Company_Website IS NOT NULL;
```

---

### `usa_executives_linkedin_finder.py`

```python
start_id = 1360  # Update to last successfully processed Person_ID + 1
```

Find the correct value:
```sql
SELECT MAX(Person_ID) FROM LinkedIn_Profiles;
-- Set start_id = result + 1
```

---

### `usa_companies_sector_scraper.py`

```python
specific_company = "Rapport Therapeutics"  # Script resumes AFTER this company
```

Find the correct value:
```sql
SELECT Company_Name FROM usa_companies_sector ORDER BY ID DESC LIMIT 1;
```

---

### `usa_companies_link_builder.py`

```python
specific_company = "Viking Therapeutics"  # Script resumes AFTER this company
```

Find the correct value:
```sql
SELECT Name FROM USA_companies_link ORDER BY ID DESC LIMIT 1;
```

---

## Standalone Utility

| Script | Purpose | Output |
|--------|---------|--------|
| `sector_categories_exporter.py` | Audit all available sector categories on companiesmarketcap.com | `~/Desktop/categories.xlsx` |

Run this independently at any time. It does not interact with the database.

```bash
python sector_categories_exporter.py
```