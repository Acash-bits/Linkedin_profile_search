import undetected_chromedriver as uc
import time
import random
import mysql.connector
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import logging

# 🔧 CONFIGURATIONS
HEADLESS = True
SEARCH_DELAY_RANGE = (5, 8)
PERSON_DELAY_RANGE = (8, 10)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/89.0.2",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0"
]

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ✅ Establish a persistent database connection
def connect_db():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="1234",
            database="usa"
        )
        logging.info("Database connection successful.")
        return conn
    except mysql.connector.Error as err:
        logging.error(f"Database connection failed: {err}")
        return None

# ✅ Fetch data from MySQL
def fetch_data(start_id):
    conn = connect_db()
    if not conn:
        return []

    try:
        cursor = conn.cursor(dictionary=True)
        query = f"SELECT ID, company_name, Designation, Person_Name FROM Key_people_info WHERE ID >= {start_id}"
        cursor.execute(query)
        data = cursor.fetchall()
        cursor.close()
        conn.close()

        logging.info(f"Fetched {len(data)} records from database starting from ID {start_id}.")
        return data
    except mysql.connector.Error as err:
        logging.error(f"Error fetching data: {err}")
        return []

# ✅ Open Search Engine
def open_search_engine(driver, engine):
    urls = {
        "google": "https://www.google.com",
        "bing": "https://www.bing.com"
    }

    logging.info(f"Opening {engine.capitalize()}...")
    try:
        driver.get(urls[engine])
        time.sleep(3)  # Wait for page to load
    except Exception as e:
        logging.error(f"Error opening search engine: {e}")

# ✅ Perform Search
def perform_search(driver, query):
    logging.info(f"Searching: {query}")

    try:
        search_box = driver.find_element(By.NAME, "q")  # Works for Google, Bing
        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)
        time.sleep(random.uniform(*SEARCH_DELAY_RANGE))  # Wait for results to load
        return True
    except Exception as e:
        logging.error(f"Error performing search: {e}")
        return False

# ✅ Extract LinkedIn Profile (No validation)
def extract_linkedin_profile(driver):
    try:
        results = driver.find_elements(By.CSS_SELECTOR, "a")
        for result in results:
            url = result.get_attribute("href")
            if url and "linkedin.com/in/" in url:
                logging.info(f"Found LinkedIn Profile: {url}")
                return url
        logging.warning("No LinkedIn profile found.")
        return None
    except Exception as e:
        logging.error(f"Error extracting LinkedIn profile: {e}")
        return None

# ✅ Insert LinkedIn profile into MySQL
def insert_result(conn, person_id, company_name, designation, linkedin_profile, person_name_from_db):
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO LinkedIn_Profiles (Person_ID, Company_Name, Designation, LinkedIn_Profile, Person_Name_DB)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            LinkedIn_Profile = VALUES(LinkedIn_Profile),
            Person_Name_DB = VALUES(Person_Name_DB)
        """
        cursor.execute(query, (person_id, company_name, designation, linkedin_profile if linkedin_profile else None, person_name_from_db))
        conn.commit()
        cursor.close()
        logging.info(f"LinkedIn profile saved: {person_id} -> {linkedin_profile if linkedin_profile else 'NULL'}")
    except mysql.connector.Error as err:
        logging.error(f"Error inserting result: {err}")

# ✅ Process and store LinkedIn profiles
def process_and_store(start_id):
    logging.info("Process started...")
    data = fetch_data(start_id)
    if not data:
        logging.warning("No data found. Exiting...")
        return

    conn = connect_db()
    if not conn:
        return

    logging.info(f"Total entries to process: {len(data)}")

    options = uc.ChromeOptions()
    options.headless = HEADLESS
    options.user_agent = random.choice(USER_AGENTS)  # Rotate User Agents
    driver = uc.Chrome(options=options)

    search_engines = ["bing", "google"]

    for index, row in enumerate(data):
        person_id = row['ID']
        company_name = row['company_name']
        person_name_from_db = row['Person_Name']
        designation = row['Designation']

        queries = [
            f"{person_name_from_db} {company_name} {designation} LinkedIn profile",
            f"LinkedIn Profile of {person_name_from_db} {company_name} {designation}"
        ]

        linkedin_profile = None

        for engine in search_engines:
            open_search_engine(driver, engine)

            for query in queries:
                if perform_search(driver, query):
                    linkedin_profile = extract_linkedin_profile(driver)
                    if linkedin_profile:
                        break  # Stop searching once a LinkedIn profile is found

            if linkedin_profile:
                break  # Stop searching through other search engines once a profile is found

        insert_result(conn, person_id, company_name, designation, linkedin_profile, person_name_from_db)

        logging.info("-----------------------------")  # Separator line
        
        if (index + 1) % random.randint(45, 50) == 0:
            logging.info("Taking a 1-minute break...")
            time.sleep(60)
        
        person_wait_time = round(random.uniform(*PERSON_DELAY_RANGE), 2)
        logging.info(f"Waiting {person_wait_time} seconds before next person...\n")
        time.sleep(person_wait_time)

    logging.info("Process completed!\n")
    conn.close()
    driver.quit()

if __name__ == "__main__":
    start_id = 1360
    process_and_store(start_id)
