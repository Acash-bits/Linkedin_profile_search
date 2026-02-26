import yfinance as yf
import mysql.connector

# Dictionary to map state abbreviations to full state names
state_abbreviations = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", 
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", 
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", 
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", 
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", 
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", 
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", 
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", 
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", 
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", 
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", 
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", 
    "WI": "Wisconsin", "WY": "Wyoming"
}

# Connect to MySQL Databases
try:
    db_import = mysql.connector.connect(
        host = "localhost",
        user = "root",
        password = "1234",
        database = "usa"
    )

    db_export = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="usa"
    )
except mysql.connector.Error as err:
    print(f"Error establishing connection with the database: {err}")
    exit(1)

cursor_import = db_import.cursor()
cursor_export = db_export.cursor()

# Fetch all symbols (tickers) for the 'usa_companiesmarketcap' table
cursor_import.execute("SELECT Name, Symbol FROM usa_companiesmarketcap")
companies = cursor_import.fetchall()


# Loop through each company
for company in companies:
    company_name = company[0]
    ticker_symbol = company[1]  # Use the ticker directly from the database

    

    # Fetch stock data using yfinance
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        # Extract required details
        address = info.get("address1", "N/A")
        city = info.get("city", "N/A")
        state_abbr = info.get("state", "N/A")
        country = info.get("country", "N/A")
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        revenue_million = info.get("totalRevenue", 0) / 1_000_000 if info.get("totalRevenue") else 0

        # Convert state abbreviation to full state name
        state_full_name = state_abbreviations.get(state_abbr, state_abbr)  # Defaults to abbreviation if not found

        # Construct full address
        full_address = f"{address}, {city}, {state_full_name}, {country}" if address != "N/A" else "N/A"

        # Print data for verification
        print(f"Processing {company_name} ({ticker_symbol}):")
        print(f"City: {city}")
        print(f"State: {state_full_name}")
        print(f"Country: {country}")
        print(f"Sector: {sector}")
        print(f"Industry: {industry}")
        print(f"Revenue: {revenue_million:.2f} million")

        # Insert data into the export database
        insert_query = """
        INSERT INTO usa_companies_final (Name, Symbol, City, State, Full_Address, Country, Sector, Industry, Revenue_million)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor_export.execute(insert_query, (company_name, ticker_symbol, city, state_full_name, full_address, country, sector, industry, revenue_million))
        db_export.commit()

    except Exception as e:
        print(f"Error processing {company_name} ({ticker_symbol}): {e}")

# Close database connections
cursor_import.close()
cursor_export.close()
db_import.close()
db_export.close()
