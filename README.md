# 🏢 Listed Companies Intelligence Pipeline — USA

> An end-to-end automated data engineering pipeline that collects, enriches, and stores structured business intelligence on publicly listed US companies — including key executives, LinkedIn profiles, validated email addresses, sector classifications, and financial metadata.

---

## 📌 Table of Contents

- [Project Overview](#project-overview)
- [Pipeline Architecture](#pipeline-architecture)
- [Data Flow](#data-flow)
- [How Company Data Is Extracted](#how-company-data-is-extracted)
- [How Key People Are Extracted](#how-key-people-are-extracted)
- [How LinkedIn Profiles Are Found](#how-linkedin-profiles-are-found)
- [How Emails Are Discovered & Validated](#how-emails-are-discovered--validated)
- [Database Schema](#database-schema)
- [Script Reference](#script-reference)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Running the Pipeline](#running-the-pipeline)
- [Email Rating System](#email-rating-system)
- [Rate Limiting & Anti-Bot Strategy](#rate-limiting--anti-bot-strategy)
- [Resuming Interrupted Runs](#resuming-interrupted-runs)
- [Dependencies](#dependencies)
- [Known Issues & Limitations](#known-issues--limitations)
- [License](#license)

---

## Project Overview

This pipeline automates the collection of actionable business intelligence on publicly listed US companies. It is designed to run sequentially, with each script feeding into the next, ultimately producing a contact-ready database of company executives complete with LinkedIn profiles and validated email addresses.

**What it collects:**
- Company HQ location, sector, industry, and revenue
- Company website URLs
- Key executive names and designations (CEO, CFO, etc.)
- LinkedIn profile URLs per executive
- Best-guess email addresses with confidence ratings
- Sector and category classifications from companiesmarketcap.com

---

## Pipeline Architecture

```mermaid
flowchart TD
    A[(usa_companiesmarketcap)] --> B[usa_companies_data_fetcher.py]
    B --> C[(usa_companies_final)]
    C --> D[usa_companies_website_fetcher.py]
    D --> C

    C --> E[usa_executives_scraper.py]
    E --> F[(Key_people_info)]

    F --> G[usa_executives_linkedin_finder.py]
    G --> H[(LinkedIn_Profiles)]

    F --> I[usa_executives_email_finder.py]
    C --> I
    I --> J[(usa_top_companies_key_people_email)]

    A --> K[usa_companies_link_builder.py]
    K --> L[(USA_companies_link)]
    L --> M[usa_companies_sector_scraper.py]
    M --> N[(usa_companies_sector)]

    style A fill:#1a1a2e,color:#eee,stroke:#4a90d9
    style C fill:#1a1a2e,color:#eee,stroke:#4a90d9
    style F fill:#1a1a2e,color:#eee,stroke:#4a90d9
    style H fill:#1a1a2e,color:#eee,stroke:#4a90d9
    style J fill:#1a1a2e,color:#eee,stroke:#4a90d9
    style L fill:#1a1a2e,color:#eee,stroke:#4a90d9
    style N fill:#1a1a2e,color:#eee,stroke:#4a90d9
```

---

## Data Flow

### Main Pipeline — Executives to Emails

```mermaid
sequenceDiagram
    participant DB as MySQL Database
    participant YF as Yahoo Finance
    participant SE as Search Engines
    participant SMTP as Mail Servers

    Note over DB,SMTP: Stage 1 — Company Enrichment
    DB->>YF: Request ticker info (symbol)
    YF-->>DB: HQ, sector, revenue, website

    Note over DB,SMTP: Stage 2 — Executive Discovery
    DB->>YF: Scrape /quote/ticker/profile/
    YF-->>DB: Person name and designation rows

    Note over DB,SMTP: Stage 3 — LinkedIn Discovery
    DB->>SE: Search Name + Company + Designation + LinkedIn
    SE-->>DB: linkedin.com/in/ URL

    Note over DB,SMTP: Stage 4 — Email Discovery
    DB->>SE: Search Name + Company + email
    SE-->>DB: Emails found on web pages
    DB->>SMTP: SMTP handshake per generated pattern
    SMTP-->>DB: 250 OK = verified / reject = invalid
    DB->>DB: Store best-rated email per person
```

### Sector Pipeline — Independent Branch

```mermaid
sequenceDiagram
    participant DB as MySQL Database
    participant CMC as companiesmarketcap.com
    participant BR as Selenium Browser

    Note over DB,BR: Stage 1 — Build Company Links
    DB->>BR: Open companiesmarketcap.com search
    BR->>CMC: Search each company name
    CMC-->>BR: First dropdown result URL
    BR-->>DB: Store company page URL

    Note over DB,CMC: Stage 2 — Scrape Sector Tags
    DB->>CMC: GET each company page URL
    CMC-->>DB: category-badge elements
    DB->>DB: Store comma-separated sector string
```

---

## How Company Data Is Extracted

This is the first and most foundational step of the pipeline. Before any executive or contact data can be gathered, the pipeline must build a clean, enriched record for each company. This happens across two scripts: `usa_companies_data_fetcher.py` and `usa_companies_website_fetcher.py`.

### Step 1 — Reading the Source Table

The pipeline starts with `usa_companiesmarketcap`, a pre-populated table containing only two things per company: its **name** and its **stock ticker symbol** (e.g. `AAPL`, `MSFT`, `TSLA`). Every other piece of data is derived from this.

```mermaid
flowchart LR
    A["usa_companiesmarketcap
    ────────────────
    Name: Apple Inc.
    Symbol: AAPL"] -->|ticker symbol| B[yfinance Ticker Object]
    B -->|ticker.info returned| C["Extracted Fields
    ────────────────
    address1, city, state
    country, sector, industry
    totalRevenue, website"]
    C --> D["usa_companies_final
    ────────────────
    Full enriched record
    stored per company"]
```

### Step 2 — Calling Yahoo Finance via yfinance

For each row in `usa_companiesmarketcap`, the script instantiates a `yfinance.Ticker` object and calls `.info`. This returns a large Python dictionary containing dozens of fields about the company. Only the fields relevant to the pipeline are extracted.

```mermaid
flowchart TD
    A["yfinance.Ticker - AAPL .info"] --> B{Field Extraction}

    B --> C["address1 → street address"]
    B --> D["city → HQ city"]
    B --> E["state → abbreviation e.g. CA TX NY"]
    B --> F["country → HQ country"]
    B --> G["sector → e.g. Technology"]
    B --> H["industry → e.g. Consumer Electronics"]
    B --> I["totalRevenue → divided by 1000000 → Revenue_million"]
    B --> J["website → fetched separately by website_fetcher.py"]

    E --> K["State Abbreviation Converter
    50-state dictionary
    CA → California
    TX → Texas
    NY → New York"]

    C --> L["Full Address constructed:
    street + city + state + country"]
    K --> L
    D --> L
    F --> L
```

### Step 3 — State Abbreviation Conversion

Yahoo Finance returns US states as two-letter abbreviations (`CA`, `TX`, `NY`). The script contains a hardcoded 50-state dictionary that converts every abbreviation to its full name before storing. If an unrecognized abbreviation is encountered, the original abbreviation is stored as-is rather than failing.

```mermaid
flowchart LR
    A["Raw from Yahoo Finance
    state = CA"] --> B{Lookup in 50-state dictionary}
    B -->|Found| C["California"]
    B -->|Not found| D["CA stored as-is"]
    C --> E["Stored in usa_companies_final.State"]
    D --> E
```

### Step 4 — Website Fetching (Separate Pass)

Website URLs are fetched in a dedicated second script (`usa_companies_website_fetcher.py`) rather than in the same pass as the other fields. This is because Yahoo Finance rate-limits API calls, and separating the website fetch into its own script with its own backoff logic allows the pipeline to be more resilient. The script only processes rows where `Company_Website IS NULL`, so it is safe to re-run multiple times without overwriting existing data.

```mermaid
flowchart TD
    A["usa_companies_final rows
    WHERE Company_Website IS NULL
    AND ID > last_processed_id"] --> B["yfinance.Ticker - ticker.info website"]

    B --> C{Website Returned?}
    C -->|Yes| D["UPDATE usa_companies_final
    SET Company_Website = url"]
    C -->|No - field missing| E["Log: No website found - Skip row"]
    C -->|HTTP 429 Rate Limited| F["Exponential Backoff
    10s → 20s → 40s → 80s
    up to 5 retries"]
    F --> B

    style F fill:#3a1a1a,color:#eee,stroke:#9a4a4a
```

### What a Completed Company Record Looks Like

After both scripts complete, a single company entry in `usa_companies_final` looks like this:

| Field | Example Value |
|-------|--------------|
| Name | Apple Inc. |
| Symbol | AAPL |
| City | Cupertino |
| State | California |
| Full_Address | One Apple Park Way, Cupertino, California, United States |
| Country | United States |
| Sector | Technology |
| Industry | Consumer Electronics |
| Revenue_million | 385,706.00 |
| Company_Website | https://www.apple.com |

---

## How Key People Are Extracted

Once the company records are enriched, the pipeline moves to discovering who the key executives are at each company. This is handled by `usa_executives_scraper.py`, which scrapes Yahoo Finance's company profile pages.

### Overview of the Scraping Process

```mermaid
flowchart TD
    A["Read usa_companies_final
    Get Name + Symbol per company"] --> B["Construct URL:
    finance.yahoo.com/quote/AAPL/profile/"]

    B --> C["HTTP GET Request
    with browser User-Agent header
    to avoid basic bot detection"]

    C --> D{Response Status?}
    D -->|200 OK| E["Parse HTML with BeautifulSoup"]
    D -->|Non-200 or error| F["Retry Logic
    up to 3 attempts
    5 second delay between retries"]
    F -->|Still failing after 3 tries| G["Log failure - Skip company - Move to next"]
    F -->|Success| E

    E --> H["Find target element:
    div.table-container.yf-mj92za"]
    H --> I{Element Found?}
    I -->|No - Yahoo changed HTML| J["Log: No executive data found - Skip company"]
    I -->|Yes| K["Extract all tr rows - Skip header row"]

    K --> L["For each row:
    cols[0] = Person Name
    cols[1] = Designation"]

    L --> M["INSERT INTO Key_people_info
    company_name, Ticker, Designation, Person_Name"]

    M --> N{Every 20 companies processed?}
    N -->|Yes| O["Pause 10 seconds to avoid rate limiting"]
    N -->|No| A

    style G fill:#3a1a1a,color:#eee,stroke:#9a4a4a
    style J fill:#3a1a1a,color:#eee,stroke:#9a4a4a
    style O fill:#1a2e3a,color:#eee,stroke:#4a90d9
```

### How the Yahoo Finance Profile Page Is Parsed

Yahoo Finance's company profile page contains an executive table in HTML. The script uses BeautifulSoup to locate this table and walk through its rows. The page structure being targeted looks like this:

```
<div class="table-container yf-mj92za">
  <table>
    <thead>
      <tr> [header — skipped] </tr>
    </thead>
    <tbody>
      <tr>
        <td>Tim Cook</td>            ← cols[0] = Person Name
        <td>CEO & Director</td>      ← cols[1] = Designation
        <td>1960</td>                ← cols[2] = Year Born (not stored)
        <td>...</td>                 ← other cols (not stored)
      </tr>
      <tr>
        <td>Luca Maestri</td>
        <td>CFO & Senior VP</td>
        ...
      </tr>
    </tbody>
  </table>
</div>
```

The script skips the first row (header), then reads `cols[0]` and `cols[1]` from every subsequent row, inserting one database record per executive found.

### What Multiple Executives from One Company Look Like

A single company like Apple may produce multiple rows in `Key_people_info`:

```mermaid
flowchart LR
    A["Yahoo Finance - Apple Inc. Profile"] -->|Scrape| B["Tim Cook - CEO and Director"]
    A -->|Scrape| C["Luca Maestri - CFO and Senior VP"]
    A -->|Scrape| D["Jeff Williams - Chief Operating Officer"]
    A -->|Scrape| E["Katherine Adams - SVP General Counsel"]

    B --> F[(Key_people_info)]
    C --> F
    D --> F
    E --> F
```

### Retry Logic in Detail

The scraper is designed to be resilient to transient network issues. If a request fails for any reason, it retries up to 3 times with a 5-second gap between each attempt before giving up and moving on.

```mermaid
flowchart TD
    A[Make HTTP GET request] --> B{Success?}
    B -->|Yes| C[Return response to parser]
    B -->|No| D{Attempt number?}
    D -->|Attempt 1 or 2| E[Wait 5 seconds]
    E --> A
    D -->|Attempt 3 - final| F["Return None - Log failure - Skip company"]

    style F fill:#3a1a1a,color:#eee,stroke:#9a4a4a
```

---

## How LinkedIn Profiles Are Found

After executives are stored in `Key_people_info`, the next stage uses `usa_executives_linkedin_finder.py` to find a LinkedIn profile URL for each person. This is the most complex script in the pipeline — it uses a real browser, rotates user agents, searches multiple search engines, and includes sophisticated anti-detection measures.

### Why a Real Browser Is Used

A standard HTTP request to Google or Bing to search for LinkedIn profiles would be immediately blocked by bot detection. The script uses `undetected_chromedriver`, which is a modified version of Selenium's ChromeDriver that patches the browser to remove all signals that identify it as an automated tool. This makes the browser appear indistinguishable from a real user browsing the web.

### Full LinkedIn Discovery Flow

```mermaid
flowchart TD
    A["Read Key_people_info
    WHERE ID >= start_id
    Get: Person_ID, Name, Company, Designation"] --> B["Launch headless Chrome
    via undetected_chromedriver
    Pick random User Agent from pool of 6"]

    B --> C[For each executive]

    C --> D["Open Bing.com
    Wait 3 seconds for page to load"]

    D --> E["Type into Bing search box:
    Name + Company + Designation + LinkedIn profile"]

    E --> F["Press Enter
    Wait 5 to 8 seconds for results"]

    F --> G["Scan ALL anchor tags on page
    looking for href containing linkedin.com/in/"]

    G --> H{LinkedIn URL found in Bing?}

    H -->|Yes| I[Store LinkedIn URL]
    H -->|No| J["Rephrase query:
    LinkedIn Profile of Name + Company + Designation"]

    J --> K[Search again on Bing]
    K --> L{Found this time?}
    L -->|Yes| I
    L -->|No| M["Switch to Google.com
    Repeat both query variations"]

    M --> N{Found on Google?}
    N -->|Yes| I
    N -->|No| O["Store NULL for this person"]

    I --> P["INSERT INTO LinkedIn_Profiles
    Person_ID, Company_Name, Designation
    LinkedIn_Profile, Person_Name_DB"]
    O --> P

    P --> Q{index divisible by approx 47?}
    Q -->|Yes| R["Take 60-second break
    to reset bot detection timers"]
    Q -->|No| S["Wait 8 to 10 seconds randomly
    before next person"]
    R --> S
    S --> C

    style R fill:#1a2e3a,color:#eee,stroke:#4a90d9
    style S fill:#1a2e3a,color:#eee,stroke:#4a90d9
    style O fill:#3a2d1a,color:#eee,stroke:#9a7a4a
```

### Search Engine Strategy — Why Bing First

The script tries Bing before Google for a deliberate reason: Bing is significantly more lenient with automated searches and less likely to present CAPTCHAs or rate-limit the IP. Google is kept as the fallback because it tends to index LinkedIn more thoroughly, so if Bing misses a profile, Google often finds it.

```mermaid
flowchart LR
    A[Executive to search] --> B["Try BING first
    more bot-tolerant
    less likely to CAPTCHA"]
    B --> C{Found?}
    C -->|Yes| E[Done]
    C -->|No| D["Try GOOGLE
    better LinkedIn index coverage"]
    D --> F{Found?}
    F -->|Yes| E
    F -->|No| G["Store NULL - move on"]
```

### How LinkedIn URLs Are Identified on Results Pages

Once a search results page loads, the script does not try to parse the page structure with CSS selectors or XPath — instead, it collects **every single anchor tag** on the entire page and filters for any `href` attribute that contains the string `linkedin.com/in/`. This approach is resilient to changes in search engine page layouts because it doesn't depend on any specific HTML structure around the result links.

```mermaid
flowchart TD
    A["Search results page loaded in headless Chrome"] --> B["driver.find_elements By.CSS_SELECTOR a
    Collect ALL anchor tags on page"]

    B --> C["For each anchor tag - get href attribute"]

    C --> D{href contains linkedin.com/in/ ?}
    D -->|Yes| E["Return this URL immediately - stop scanning"]
    D -->|No| F["Continue to next anchor tag"]
    F --> C

    E --> G["Stored URL example:
    https://www.linkedin.com/in/tim-cook-1b"]
```

### User Agent Rotation

Every time the Chrome browser is launched (once per full script run), a user agent is selected at random from a pool of 6. This prevents repeated requests all looking identical from a server fingerprinting perspective.

```mermaid
flowchart LR
    A[Script starts] --> B{Randomly pick one user agent}
    B --> C["Windows Chrome 91"]
    B --> D["Mac Chrome 91"]
    B --> E["Windows Firefox 89"]
    B --> F["Mac Firefox 89"]
    B --> G["Linux Chrome 91"]
    B --> H["Linux Firefox 89"]
    C --> I["Set as browser identity for entire run"]
    D --> I
    E --> I
    F --> I
    G --> I
    H --> I
```

### Anti-Detection Timing Strategy

The script uses randomized delays and periodic long pauses to mimic human browsing behavior. A perfectly consistent delay (e.g. exactly 5 seconds every time) is itself a bot signal. Randomization makes the pattern appear human.

```mermaid
gantt
    title Timing Pattern for 50 Consecutive Executive Searches
    dateFormat X
    axisFormat %ss

    section Searches 1 to 47
    Search and extract result     :0, 3
    Random wait 8 to 10s         :3, 13
    Search and extract result     :13, 16
    Random wait 8 to 10s         :16, 26

    section Break at search 47
    60-second cooldown break      :26, 86

    section Searches 48 to 50
    Search and extract result     :86, 89
    Random wait 8 to 10s         :89, 99
```

### What Gets Stored

Each row in `LinkedIn_Profiles` contains:

| Field | Example Value |
|-------|--------------|
| Person_ID | 142 (FK to Key_people_info.ID) |
| Company_Name | Apple Inc. |
| Designation | CEO & Director |
| LinkedIn_Profile | https://www.linkedin.com/in/tim-cook-1b |
| Person_Name_DB | Tim Cook |

If no LinkedIn profile is found after exhausting all search attempts, `LinkedIn_Profile` is stored as `NULL` — the row is still inserted so the pipeline knows this person was processed and does not attempt it again on reruns.

---

## How Emails Are Discovered & Validated

`usa_executives_email_finder.py` combines three techniques to find the best possible email address for each executive: pattern generation from the company domain, Google search scraping, and SMTP verification.

### Full Email Discovery Flow

```mermaid
flowchart TD
    A["Read Key_people_info JOIN usa_companies_final
    Get: Person Name, Company Name, Company Website"] --> B["Extract domain from Company_Website
    using regex:
    https://www.apple.com → apple.com"]

    B --> C{Valid domain extracted?}
    C -->|No - website missing or malformed| D["Skip person - Log: no valid domain"]
    C -->|Yes| E["Generate 6 email pattern candidates
    using first + last name + domain"]

    E --> F["Search Google for: Name + Company + email"]
    F --> G["Scrape result pages for any email matching company domain"]

    E --> H[For each generated pattern candidate]

    H --> I["DNS MX Record Lookup
    Find mail server for this domain"]
    I --> J["Open SMTP connection to mail server"]
    J --> K["Send: HELO → MAIL FROM → RCPT TO: email"]
    K --> L{Server response code?}
    L -->|250 OK| M["SMTP Verified - Rating = 5"]
    L -->|550 or reject| N[SMTP Rejected]
    L -->|Error or timeout| N

    G --> O{Email found in Google scrape?}
    O -->|Yes| P["Web Confirmed - Rating = 4"]
    O -->|No| Q["Pattern Only - Rating = 3"]

    M --> R{Compare all candidates by rating}
    N --> R
    P --> R
    Q --> R

    R --> S["Select single best email - highest rating wins"]

    S --> T["INSERT INTO usa_top_companies_key_people_email
    Company_ID, Person_Name, Email_Id, Rating
    LinkedIn_Name, LinkedIn_Profile"]

    style D fill:#3a1a1a,color:#eee,stroke:#9a4a4a
    style M fill:#1a4a1a,color:#eee,stroke:#5a9a5a
    style P fill:#2d3a1a,color:#eee,stroke:#7a9a4a
    style Q fill:#3a2d1a,color:#eee,stroke:#9a7a4a
```

### The 6 Email Patterns Generated

For a person named **John Smith** at domain **apple.com**, the script generates:

```mermaid
flowchart LR
    A["Name: John Smith
    Domain: apple.com"] --> B["john.smith@apple.com"]
    A --> C["johnsmith@apple.com"]
    A --> D["john@apple.com"]
    A --> E["jsmith@apple.com"]
    A --> F["john_smith@apple.com"]
    A --> G["smith@apple.com"]
```

All 6 are generated simultaneously and each goes through the SMTP check independently. The highest-rated one is stored.

### How SMTP Verification Works

SMTP verification exploits the fact that mail servers must respond to email delivery requests. The script mimics being a mail server trying to deliver a message, and checks whether the target server accepts or rejects the address — without ever actually sending an email.

```mermaid
sequenceDiagram
    participant S as Script
    participant DNS as DNS Resolver
    participant MX as Company Mail Server

    S->>DNS: Resolve MX record for apple.com
    DNS-->>S: mx.apple.com mail server address

    S->>MX: Connect on port 25 SMTP
    MX-->>S: 220 Ready

    S->>MX: HELO test
    MX-->>S: 250 Hello

    S->>MX: MAIL FROM test@example.com
    MX-->>S: 250 OK

    S->>MX: RCPT TO john.smith@apple.com
    MX-->>S: 250 OK - Email accepted

    Note over S,MX: OR if address does not exist

    S->>MX: RCPT TO nobody@apple.com
    MX-->>S: 550 No such user

    S->>MX: QUIT
```

---

## Database Schema

### Entity Relationship Diagram

```mermaid
erDiagram
    usa_companiesmarketcap {
        int ID PK
        varchar Name
        varchar Symbol
    }

    usa_companies_final {
        int ID PK
        varchar Name
        varchar Symbol
        varchar City
        varchar State
        varchar Full_Address
        varchar Country
        varchar Sector
        varchar Industry
        decimal Revenue_million
        varchar Company_Website
    }

    USA_companies_link {
        int ID PK
        varchar Name
        varchar Link
    }

    usa_companies_sector {
        int ID PK
        varchar Company_Name FK
        text Sectors
    }

    Key_people_info {
        int ID PK
        varchar company_name FK
        varchar Ticker
        varchar Designation
        varchar Person_Name
    }

    LinkedIn_Profiles {
        int ID PK
        int Person_ID FK
        varchar Company_Name
        varchar Designation
        varchar LinkedIn_Profile
        varchar Person_Name_DB
    }

    usa_top_companies_key_people_email {
        int ID PK
        int Company_ID FK
        varchar Company_Name
        varchar Person_Name
        varchar Designation
        varchar Email_Id
        tinyint Rating
        varchar LinkedIn_Name
        varchar LinkedIn_Profile
    }

    usa_companiesmarketcap ||--o{ usa_companies_final : "enriched into"
    usa_companiesmarketcap ||--o{ USA_companies_link : "linked via"
    USA_companies_link ||--o{ usa_companies_sector : "sectors scraped from"
    usa_companies_final ||--o{ Key_people_info : "executives found for"
    Key_people_info ||--o{ LinkedIn_Profiles : "LinkedIn found for"
    Key_people_info ||--o{ usa_top_companies_key_people_email : "email found for"
    usa_companies_final ||--o{ usa_top_companies_key_people_email : "domain used from"
```

### Table Descriptions

| Table | Populated By | Purpose |
|-------|-------------|---------|
| `usa_companiesmarketcap` | Manual / external import | Master company list — seed for the entire pipeline |
| `usa_companies_final` | `usa_companies_data_fetcher.py` | Enriched company records with HQ, financials, and website |
| `USA_companies_link` | `usa_companies_link_builder.py` | Company page URLs on companiesmarketcap.com |
| `usa_companies_sector` | `usa_companies_sector_scraper.py` | Sector and category tags per company |
| `Key_people_info` | `usa_executives_scraper.py` | Executive names and designations from Yahoo Finance |
| `LinkedIn_Profiles` | `usa_executives_linkedin_finder.py` | LinkedIn profile URLs matched to executives |
| `usa_top_companies_key_people_email` | `usa_executives_email_finder.py` | Best email per executive with confidence rating |

---

## Script Reference

### `usa_companies_data_fetcher.py`

**Purpose:** Seeds the `usa_companies_final` table with company financial and location data.

**How it works:**
```
For each company in usa_companiesmarketcap:
    → Call yfinance ticker.info
    → Extract: address, city, state, country, sector, industry, revenue
    → Convert state abbreviation to full name (e.g. CA → California)
    → Insert into usa_companies_final
```

Contains a full 50-state abbreviation-to-name mapping dictionary. Falls back gracefully if any field is missing from the Yahoo Finance response.

---

### `usa_companies_website_fetcher.py`

**Purpose:** Fills the `Company_Website` column for rows where it is NULL.

**How it works:**
```
For each company WHERE Company_Website IS NULL AND ID > last_processed_id:
    → Call yfinance ticker.info["website"]
    → On HTTP 429 (rate limit): exponential backoff (10s → 20s → 40s → ...)
    → Update Company_Website column
```

**Resume variable:** `last_processed_id` at the bottom of the script.

---

### `usa_executives_scraper.py`

**Purpose:** Scrapes executive names and designations from Yahoo Finance profile pages.

**How it works:**
```
For each company in usa_companies_final:
    → GET https://finance.yahoo.com/quote/{ticker}/profile/
    → Parse div.table-container.yf-mj92za with BeautifulSoup
    → Extract each row: cols[0] = Person Name, cols[1] = Designation
    → Insert into Key_people_info
    → Retry up to 3 times on failure
    → Pause 10 seconds every 20 companies
```

> ⚠️ Yahoo Finance changes its CSS class names periodically. If scraping stops working, inspect the current profile page HTML and update the `class_` selector.

---

### `usa_executives_linkedin_finder.py`

**Purpose:** Finds LinkedIn profile URLs for each executive using automated browser searches.

**How it works:**
```
For each executive in Key_people_info WHERE ID >= start_id:
    → Open Bing, search: "{Name} {Company} {Designation} LinkedIn profile"
    → Scan all <a> tags for linkedin.com/in/ URLs
    → If not found, try Google with same query
    → If still not found, try alternate query format
    → Insert LinkedIn URL (or NULL) into LinkedIn_Profiles
    → Wait 8–10 seconds between people
    → Take 60-second break every ~47 searches
```

Uses `undetected_chromedriver` to avoid bot detection. Rotates through 6 user agent strings.

**Resume variable:** `start_id` at the bottom of the script.

---

### `usa_executives_email_finder.py`

**Purpose:** Generates, validates, and scores email address candidates for each executive.

**Email patterns generated per person:**
```
firstname.lastname@domain.com
firstnamelastname@domain.com
firstname@domain.com
flastname@domain.com
firstname_lastname@domain.com
lastname@domain.com
```

Each candidate is checked via SMTP and Google search, then rated. The highest-rated email is stored. See the [Email Rating System](#email-rating-system) section for full details.

---

### `usa_companies_link_builder.py`

**Purpose:** Builds the `USA_companies_link` table by finding each company's page on companiesmarketcap.com.

**How it works:**
```
For each company in usa_companiesmarketcap (after specific_company resume point):
    → Open companiesmarketcap.com in headless Chrome
    → Type company name into search bar
    → Capture first dropdown result name + URL
    → Insert into USA_companies_link
```

**Resume variable:** `specific_company` string — script skips all companies up to and including this name.

---

### `usa_companies_sector_scraper.py`

**Purpose:** Scrapes sector and category tags for each company from companiesmarketcap.com.

**How it works:**
```
For each company in USA_companies_link (after resume point):
    → GET the stored company page URL
    → Parse div.info-box.categories-box .category-badge elements
    → Strip emojis and non-alphanumeric characters
    → Join sectors with comma separator
    → Insert into usa_companies_sector if not already present
    → Sleep 2 seconds between requests
```

---

## Setup & Installation

### Prerequisites

- Python 3.9+
- MySQL 8.0+
- Google Chrome (required for `usa_executives_linkedin_finder.py` and `usa_companies_link_builder.py`)
- MySQL database named `usa` pre-created

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/listed-companies-intelligence.git
cd listed-companies-intelligence
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up the Database

```bash
mysql -u root -p < sql/usa_schema.sql
```

### 4. Configure Credentials

```bash
cp config/db_config.example.py config/db_config.py
```

Edit `config/db_config.py`:

```python
USA_DB = {
    "host": "localhost",
    "user": "root",
    "password": "YOUR_PASSWORD",
    "database": "usa"
}
```

> `config/db_config.py` is listed in `.gitignore` and must never be committed.

### 5. Seed the Source Table

Populate `usa_companiesmarketcap` with your company list (Name + Symbol columns) before running any scripts. This is the single entry point for the entire pipeline.

---

## Configuration

### Resume Points

All long-running scripts support resuming from an exact stopping point:

| Script | Variable | Type | Description |
|--------|----------|------|-------------|
| `usa_companies_website_fetcher.py` | `last_processed_id` | `int` | MySQL row ID — resumes from next ID |
| `usa_executives_linkedin_finder.py` | `start_id` | `int` | `Key_people_info` ID — resumes from this ID |
| `usa_companies_sector_scraper.py` | `specific_company` | `str` | Company name — resumes after this entry |
| `usa_companies_link_builder.py` | `specific_company` | `str` | Company name — resumes after this entry |

---

## Running the Pipeline

### Full Execution Order

```bash
# ── Stage 1: Company Foundation ─────────────────────────────────
python usa_companies_data_fetcher.py
python usa_companies_website_fetcher.py

# ── Stage 2: Executive Discovery ────────────────────────────────
python usa_executives_scraper.py

# ── Stage 3: LinkedIn + Email Discovery ─────────────────────────
python usa_executives_linkedin_finder.py
python usa_executives_email_finder.py

# ── Stage 4: Sector Pipeline (independent — run any time) ───────
python usa_companies_link_builder.py
python usa_companies_sector_scraper.py
```

### Script Dependency Map

```mermaid
flowchart LR
    S1[usa_companies_data_fetcher] --> S2[usa_companies_website_fetcher]
    S2 --> S3[usa_executives_scraper]
    S3 --> S4[usa_executives_linkedin_finder]
    S3 --> S5[usa_executives_email_finder]
    S2 --> S5

    S6[usa_companies_link_builder] --> S7[usa_companies_sector_scraper]

    style S6 fill:#2d4a2d,color:#eee,stroke:#5a9a5a
    style S7 fill:#2d4a2d,color:#eee,stroke:#5a9a5a
```

The green branch (sector pipeline) is fully independent and can run in parallel with the main pipeline.

---

## Email Rating System

```mermaid
flowchart TD
    A[Email Candidate] --> B{SMTP MX Handshake Returns 250?}
    B -->|Yes| C[Rating 5 — SMTP Verified]
    B -->|No| D{Found on Web via Google Search?}
    D -->|Yes| E[Rating 4 — Web Confirmed]
    D -->|No| F[Rating 3 — Pattern Generated]

    style C fill:#1a4a1a,color:#eee,stroke:#5a9a5a
    style E fill:#2d3a1a,color:#eee,stroke:#7a9a4a
    style F fill:#3a2d1a,color:#eee,stroke:#9a7a4a
```

| Rating | Meaning | Reliability |
|--------|---------|-------------|
| 5 | SMTP server returned 250 OK during handshake | High — server accepted the address |
| 4 | Email address found on a public web page via Google | Medium — was published somewhere online |
| 3 | Pattern-generated from name + domain, unconfirmed | Low — best guess based on naming convention |

> **Note:** Some mail servers return 250 for all addresses regardless of validity (catch-all configuration). Rating 5 means likely valid, not guaranteed deliverable.

---

## Rate Limiting & Anti-Bot Strategy

Each script implements throttling to avoid IP bans and API rate limits:

| Script | Per-Request Delay | Batch Pause |
|--------|------------------|-------------|
| `usa_companies_data_fetcher.py` | yfinance handles internally | — |
| `usa_companies_website_fetcher.py` | 1–3s random | Exponential backoff on HTTP 429 |
| `usa_executives_scraper.py` | — | 10s every 20 companies |
| `usa_executives_linkedin_finder.py` | 8–10s per person | 60s every ~47 searches |
| `usa_executives_email_finder.py` | 6–9s between Google queries | — |
| `usa_companies_sector_scraper.py` | 2s per page | — |

---

## Resuming Interrupted Runs

If any script is interrupted, find the last successfully processed record and update the resume variable before restarting.

**For ID-based resume:**
```sql
-- usa_executives_linkedin_finder.py
SELECT MAX(Person_ID) FROM LinkedIn_Profiles;
-- Set start_id to this value + 1

-- usa_companies_website_fetcher.py
SELECT MAX(ID) FROM usa_companies_final WHERE Company_Website IS NOT NULL;
-- Set last_processed_id to this value
```

**For name-based resume:**
```sql
-- usa_companies_sector_scraper.py / usa_companies_link_builder.py
SELECT Company_Name FROM usa_companies_sector ORDER BY ID DESC LIMIT 1;
-- Set specific_company to this value
```

---

## Dependencies

```
mysql-connector-python==8.3.0     # MySQL driver
yfinance==0.2.37                  # Yahoo Finance API wrapper
requests==2.31.0                  # HTTP requests
beautifulsoup4==4.12.3            # HTML parsing
selenium==4.18.1                  # Browser automation
undetected-chromedriver==3.5.5    # Anti-detection Chrome driver
webdriver-manager==4.0.1          # Auto ChromeDriver management
dnspython==2.6.1                  # DNS/MX record lookups for SMTP validation
google==3.0.0                     # Google search wrapper
pandas==2.2.1                     # DataFrame handling
openpyxl==3.1.2                   # Excel export
lxml==5.1.0                       # Fast HTML parser for BeautifulSoup
```

---

## Known Issues & Limitations

**Yahoo Finance CSS Changes**
`usa_executives_scraper.py` targets `div.table-container.yf-mj92za`. Yahoo Finance occasionally renames CSS classes. If the scraper returns no results, inspect the current profile page HTML and update the selector.

**SMTP Catch-All Servers**
Some company mail servers accept all addresses and return 250 OK regardless of whether the mailbox exists. Rating 5 means the server did not reject the address, not that it is guaranteed deliverable.

**LinkedIn Anti-Bot Detection**
`undetected_chromedriver` bypasses most detection at the time of writing, but LinkedIn and Google continuously update their systems. If profiles stop being discovered, check whether pages are returning CAPTCHAs.

**Google Search Rate Limits**
`usa_executives_email_finder.py` makes direct HTTP requests via the `googlesearch` library. Google will temporarily block IPs after too many rapid requests. The built-in 6–9 second delay mitigates this but running from a server with rotating proxies is recommended for large datasets.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.