import requests
from bs4 import BeautifulSoup
import mysql.connector
import time
from requests.exceptions import ChunkedEncodingError

# Database connection
db_source = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="USA"
)

db_target = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="USA"
)

cursor_source = db_source.cursor()
cursor_target = db_target.cursor()

# Filter to only get companies with ID >= 103
query = """
    SELECT NAME, Symbol FROM usa_companies_final WHERE ID >= 103;
"""
cursor_source.execute(query)
companies = cursor_source.fetchall()

# Create target table if it doesn't exist
create_table_query = """
CREATE TABLE IF NOT EXISTS Key_people_info (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(100),
    Ticker VARCHAR(10),
    Designation VARCHAR(250),
    Person_Name VARCHAR(250)
);
"""
cursor_target.execute(create_table_query)

# Yahoo Finance URL template
url_template = "https://finance.yahoo.com/quote/{}/profile/"

# Retry mechanism
def fetch_data_with_retry(url, headers, retries=3, delay=5):
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response
            else:
                print(f"Failed to fetch data for {url} (HTTP Status: {response.status_code})")
        except ChunkedEncodingError as e:
            print(f"Error: {e}. Retrying...")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}. Retrying...")
        
        time.sleep(delay)

    return None

# Main scraping loop
for index, company in enumerate(companies, start=1):
    company_name = company[0]
    ticker = company[1]
    url = url_template.format(ticker)
    print(f"Scraping data for ticker: {ticker} ({company_name})")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    response = fetch_data_with_retry(url, headers)

    if response:
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('div', class_='table-container yf-mj92za')

        if table:
            rows = table.find_all('tr')
            for row in rows[1:]:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    person_name = cols[0].get_text(strip=True)
                    designation = cols[1].get_text(strip=True)

                    insert_query = """
                    INSERT INTO Key_people_info (company_name, Ticker, Designation, Person_Name)
                    VALUES (%s, %s, %s, %s)
                    """
                    cursor_target.execute(insert_query, (company_name, ticker, designation, person_name))
                    db_target.commit()
                    print(f"Inserted: {person_name} - {designation} for {company_name} ({ticker})")
        else:
            print(f"No executive data found for {company_name} ({ticker})")
    else:
        print(f"Failed to fetch data for {company_name} ({ticker}) after retries.")

    if index % 20 == 0:
        print("Pausing for 10 seconds...")
        time.sleep(10)

# Cleanup
cursor_source.close()
cursor_target.close()
db_source.close()
db_target.close()
