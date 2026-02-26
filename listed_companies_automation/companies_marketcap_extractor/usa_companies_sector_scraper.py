import mysql.connector
import requests
from bs4 import BeautifulSoup
import time

# Connect to MySQL databases
try:
    db_import = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="usa"
    )

    db_export = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="usa"
    )
except mysql.connector.Error as err:
    print(f"Error connecting to the database: {err}")
    exit(1)

cursor_import = db_import.cursor()
cursor_export = db_export.cursor()

# Fetch all links and names from the 'USA_companies_link' table
cursor_import.execute("SELECT Name, Link FROM USA_companies_link")
companies = cursor_import.fetchall()

# Set a flag to start processing after a particular company
start_processing = False  # Flag to track when to start processing
specific_company = "Rapport Therapeutics"  # Replace with the company name after which to start

# Loop through each company
for company in companies:
    company_name = company[0]
    full_url = company[1]  # Use the link directly from the database
    
    # Start processing once the specific company is found
    if company_name == specific_company:
        start_processing = True
        print(f"Found '{specific_company}'. Starting processing for subsequent companies.")
        continue  # Skip the current company, start processing from the next
    
    # Skip companies until the specific company is found
    if not start_processing:
        continue

    print(f"Processing: {company_name} - {full_url}")
    
    try:
        # Fetch the page content
        response = requests.get(full_url, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad responses
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract sectors
        sectors = []
        sector_elements = soup.select('div.info-box.categories-box .category-badge')
        
        for element in sector_elements:
            sector = element.text.strip()  # Get the text of the sector
            # Remove emojis and any non-alphanumeric or non-space characters
            sector = ''.join(char for char in sector if char.isalnum() or char.isspace())
            sectors.append(sector)
        
        # Join sectors with a comma separator
        sectors_str = ', '.join(sectors)
        
        # Check if the company already exists in the export table
        cursor_export.execute(""" 
            SELECT COUNT(*) FROM usa_companies_sector WHERE Company_Name = %s
        """, (company_name,))
        exists = cursor_export.fetchone()[0]
        
        if exists == 0:  # Insert only if the company is not already in the table
            cursor_export.execute(""" 
                INSERT INTO usa_companies_sector (Company_Name, Sectors)
                VALUES (%s, %s)
            """, (company_name, sectors_str))
            db_export.commit()
            print(f"Inserted: {company_name}")
        else:
            print(f"Skipped (already exists): {company_name}")
    
    except requests.exceptions.RequestException as req_err:
        print(f"Request error for {company_name}: {req_err}")
    except mysql.connector.Error as db_err:
        print(f"Database error for {company_name}: {db_err}")
    except Exception as err:
        print(f"Unexpected error for {company_name}: {err}")
    
    # Throttle requests to avoid being blocked
    time.sleep(2)

# Close the connections
cursor_import.close()
cursor_export.close()
db_import.close()
db_export.close()

print("Data extraction and insertion complete!")
