import mysql.connector
import yfinance as yf
import time
import random

# Database connection details
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "1234",
    "database": "USA"
}

table_name = "usa_companies_final"  # Replace with your actual table name
last_processed_id = 1592  # Update this to continue from the next ID

def get_tickers(last_id):
    """Fetch tickers from the database where Company_Website is NULL or empty and ID is greater than last_id."""
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
    query = f"SELECT ID, Symbol FROM {table_name} WHERE (Company_Website IS NULL OR Company_Website = '') AND ID > %s"
    cursor.execute(query, (last_id,))
    tickers = cursor.fetchall()
    cursor.close()
    connection.close()
    return tickers

def update_website(company_id, website):
    """Update the company website in the database."""
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
    update_query = f"UPDATE {table_name} SET Company_Website = %s WHERE ID = %s"
    cursor.execute(update_query, (website, company_id))
    connection.commit()
    cursor.close()
    connection.close()

def fetch_with_backoff(symbol, max_retries=5):
    """Fetch website using exponential backoff when rate-limited."""
    delay = 10  # Start with 10 seconds
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(symbol)
            website = stock.info.get("website")

            if website:
                return website
            print(f"⚠️ No website found for {symbol}")
            return None
        except Exception as e:
            if "429" in str(e):  # Detect rate limit
                print(f"🚨 Rate-limited! Waiting {delay} seconds before retrying...")
                time.sleep(delay)
                delay *= 2  # Double the delay each retry
            else:
                print(f"❌ Error processing {symbol}: {e}")
                return None
    print(f"⛔ Max retries reached for {symbol}. Skipping.")
    return None

def fetch_and_update_websites(last_id):
    """Fetch websites from Yahoo Finance and update the database, continuing from the given last ID."""
    tickers = get_tickers(last_id)

    if not tickers:
        print("✅ No more records to update!")
        return

    print("⏳ Waiting for 20 seconds before starting...")
    time.sleep(3)  # Initial wait before fetching data

    for company_id, symbol in tickers:
        website = fetch_with_backoff(symbol)

        if website:
            update_website(company_id, website)
            print(f"✅ Updated {symbol}: {website}")

        # Add a random delay between requests (3-6 seconds)
        wait_time = random.uniform(1, 3)
        print(f"⏳ Waiting {round(wait_time, 2)} seconds before the next request...")
        time.sleep(wait_time)

# Run the function, continuing from ID 1592
fetch_and_update_websites(last_processed_id)
