import requests
from bs4 import BeautifulSoup
import mysql.connector
import time
from requests.exceptions import ChunkedEncodingError

# Database connection for the source (usa_companies_final) 
db_source = mysql.connector.connect(
    host="localhost",  # Replace with your DB host
    user="root",       # Replace with your DB username
    password="1234",  # Replace with your DB password
    database="usa"  # Replace with your source DB name
)

# Database connection for the target (salt_lake_key_people_info)
db_target = mysql.connector.connect(
    host="localhost",  # Replace with your DB host
    user="root",       # Replace with your DB username
    password="1234",  # Replace with your DB password
    database="usa"  # Replace with your target DB name
)

cursor_source = db_source.cursor()
cursor_target = db_target.cursor()

# Query to fetch tickers and company names where the city is Salt Lake
query = """
    SELECT `NAME`, Symbol FROM usa_companies_final
    WHERE city = "Salt Lake City";
    """
cursor_source.execute(query)
companies = cursor_source.fetchall()

# Create table if not exists in target database
create_table_query = """
CREATE TABLE IF NOT EXISTS salt_lake_key_people_info (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(100),
    Ticker VARCHAR(10),
    Designation VARCHAR(250),
    Person_Name VARCHAR(250)
);
"""
cursor_target.execute(create_table_query)

# URL template for Yahoo Finance
url_template = "https://finance.yahoo.com/quote/{}/profile/"

# Retry function with delay
def fetch_data_with_retry(url, headers, retries=3, delay=5):
    """Fetching data from given source"""
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)  # Adding a timeout to prevent waiting too long
            if response.status_code == 200:
                return response
            else:
                print(f"Failed to fetch data for {url} (HTTP Status: {response.status_code})")
        except ChunkedEncodingError as e:
            print(f"Error: {e}. Retrying...")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}. Retrying...")
        
        print(f"Retrying in {delay} seconds...")
        time.sleep(delay)  # Delay before retrying

    return None  # Return None if all retries fail

# Loop through companies and scrape data
for index, company in enumerate(companies, start=1):
    company_name = company[0]  # Extract company name from the query
    ticker = company[1]  # Extract ticker symbol from the query
    url = url_template.format(ticker)
    print(f"Scraping data for ticker: {ticker} ({company_name})")

    # Set User-Agent to mimic browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }

    response = fetch_data_with_retry(url, headers)

    if response:
        soup = BeautifulSoup(response.content, 'html.parser')
        # Locate the table containing the executives' data
        table = soup.find('div', class_='table-container yf-1tqxvla')

        if table:
            rows = table.find_all('tr')  # Get all rows in the table
            for row in rows[1:]:  # Skip the header row
                cols = row.find_all('td')  # Get columns
                if len(cols) >= 2:
                    person_name = cols[0].get_text(strip=True)
                    designation = cols[1].get_text(strip=True)

                    # Insert data into database
                    insert_query = """
                    INSERT INTO salt_lake_key_people_info (company_name, Ticker, Designation, Person_Name)
                    VALUES (%s, %s, %s, %s)
                    """
                    cursor_target.execute(insert_query, (company_name, ticker, designation, person_name))
                    db_target.commit()
                    print(f"Inserted: {person_name} - {designation} for {company_name} ({ticker})")
        else:
            print(f"No executive data found for {company_name} ({ticker})")
    else:
        print(f"Failed to fetch data for {company_name} ({ticker}) after retries.")
    
    # Pause for 10 seconds after every 20 companies
    if index % 20 == 0:
        print("Pausing for 10 seconds...")
        time.sleep(10)

# Close database connections
cursor_source.close()
cursor_target.close()
db_source.close()
db_target.close()
