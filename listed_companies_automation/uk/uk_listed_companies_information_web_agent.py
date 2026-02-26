import yfinance as yf
import mysql.connector
import time

# Connect to MySQL Databases
try:
    db_import = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="UK"
    )

    db_export = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="UK"
    )
except mysql.connector.Error as err:
    print(f"Error establishing connection with the database: {err}")
    exit(1)

cursor_import = db_import.cursor()
cursor_export = db_export.cursor()

# Fetch all symbols and company names from 'mytable'
cursor_import.execute("SELECT Name, Symbol, country FROM mytable")
companies = cursor_import.fetchall()

count = 0  # Counter to track number of processed entries

# Loop through each company
for company in companies:
    company_name = company[0]  # Company Name
    ticker_symbol = company[1]  # Symbol
    country = company[2]  # Country

    ticker = yf.Ticker(ticker_symbol)

    try:
        # Fetch company details from Yahoo Finance
        info = ticker.info
        hq_city = info.get("city", "N/A")
        hq_state = info.get("state", "N/A")
        hq_country = info.get("country", country)  # Use country from DB if Yahoo is missing
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        revenue_million = info.get("totalRevenue", 0) / 1_000_000 if info.get("totalRevenue") else 0
        currency = info.get("financialCurrency", "N/A")  # Extract financial currency

        # Extract founding year (falling back to 'N/A' if not available)
        year_founded = info.get("fundingStart", None)  # Some companies might not have this data
        if not year_founded or not isinstance(year_founded, int):  # Validate as an integer
            year_founded = None

        # Print extracted data for verification
        print(f"Processing {ticker_symbol}: {company_name}")
        print(f"Year Founded: {year_founded} | Revenue: {revenue_million:.2f} million {currency} | HQ: {hq_city}, {hq_state}, {hq_country} | Sector: {sector} | Industry: {industry}")

        # Insert/Update data into UK_listed_Companies_Database
        update_query = """
        INSERT INTO UK_listed_Companies_Database 
        (Company_Name, Symbol, Year_Founded, `Revenue ($ Mil)`, Revenue_Currency, HQ_Country, HQ_City, HQ_State, Sector, Industry)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        Year_Founded = VALUES(Year_Founded),
        `Revenue ($ Mil)` = VALUES(`Revenue ($ Mil)`),
        Revenue_Currency = VALUES(Revenue_Currency),
        HQ_Country = VALUES(HQ_Country),
        HQ_City = VALUES(HQ_City),
        HQ_State = VALUES(HQ_State),
        Sector = VALUES(Sector),
        Industry = VALUES(Industry)
        """
        cursor_export.execute(update_query, (company_name, ticker_symbol, year_founded, revenue_million, currency, hq_country, hq_city, hq_state, sector, industry))
        db_export.commit()

        count += 1  # Increment processed count

        # **Introduce a 1-minute delay after every 50 entries**
        if count % 50 == 0:
            print("Pausing for 1 minute to prevent API throttling...")
            time.sleep(60)

    except Exception as e:
        print(f"Error processing {ticker_symbol}: {e}")

    # Introduce a short delay between requests to prevent rapid API calls
    time.sleep(2)

# Close database connections
cursor_import.close()
cursor_export.close()
db_import.close()
db_export.close()
print("Data import completed successfully!")
