import mysql.connector
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Set up Selenium WebDriver for Chrome in headless mode
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Run headless
options.add_argument("--disable-gpu")  # Disable GPU acceleration
options.add_argument("--ignore-certificate-errors")  # Ignore SSL certificate errors

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Function to search company and get top result link
def search_company(company_name):
    # Open the website
    driver.get("https://companiesmarketcap.com/")
    
    # Wait for the search input element to be present on the page
    search_bar = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "search-input"))
    )
    
    # Find the search bar and input the company name
    search_bar.send_keys(company_name)
    search_bar.send_keys(Keys.RETURN)
    
    # Wait for results to load
    time.sleep(3)
    
    # Extract the first link from the dropdown results (from the <a> tag)
    try:
        first_result_link = driver.find_element(By.XPATH, '//*[@id="typeahead-search-results"]/a[1]').get_attribute("href")
        
        # Get the name of the first company in the dropdown
        first_result_name = driver.find_element(By.XPATH, '//*[@id="typeahead-search-results"]/a[1]//div[@class="company-name"]').text
        return first_result_name, first_result_link
    except Exception as e:
        print(f"Error fetching link for {company_name}: {e}")
        return None, None

# Connect to the MySQL database
def connect_db():
    return mysql.connector.connect(
        host="localhost",  # Replace with your host
        user="root",  # Replace with your MySQL username
        password="1234",  # Replace with your MySQL password
        database="usa"  # Replace with your database name
    )

# Fetch all company names from the database
def fetch_company_names():
    db = connect_db()
    cursor = db.cursor()

    cursor.execute("SELECT Name FROM usa_companiesmarketcap")
    companies = cursor.fetchall()

    db.close()
    return companies

# Insert company name and link into the database
def insert_company_link(company_name, company_link):
    db = connect_db()
    cursor = db.cursor()

    insert_query = "INSERT INTO USA_companies_link (Name, Link) VALUES (%s, %s)"
    cursor.execute(insert_query, (company_name, company_link))
    db.commit()

    db.close()

# Main process
def main():
    companies = fetch_company_names()
    start_processing = False  # Flag to start processing after a specific company
    specific_company = "Viking Therapeutics"  # The company after which processing should start

    for company in companies:
        company_name = company[0]  # The company name fetched from the database

        # Check if we have reached the specific company
        if company_name == specific_company:
            start_processing = True
            print(f"Found '{specific_company}'. Starting processing for subsequent companies.")
            continue
        
        # Skip companies until the specific company is found
        if not start_processing:
            continue

        print(f"Processing: {company_name}")
        
        company_name, company_link = search_company(company_name)
        
        if company_name and company_link:
            print(f"Company Name: {company_name}")
            print(f"Company Link: {company_link}")
            
            # Insert the company name and link into the database
            insert_company_link(company_name, company_link)
        else:
            print(f"Could not fetch the link for {company_name}")

# Run the script
if __name__ == "__main__":
    main()

# Close the browser after the task
driver.quit()
