import os
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Function to scrape category names using BeautifulSoup
def scrape_categories():
    # Send a GET request to the URL
    url = "https://companiesmarketcap.com/all-categories/"
    response = requests.get(url)
    
    # Parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find all <td> elements containing <a> tags
    td_elements = soup.find_all("td")
    
    categories = []
    
    # Loop through each <td> element to extract the category name
    for td in td_elements:
        a_tag = td.find("a")
        if a_tag:
            category_name = a_tag.text.strip()  # Get the text and clean it
            if category_name:
                # Remove any emoji or non-word characters using regex and strip any leading/trailing spaces
                clean_category = re.sub(r'[^\w\s]', '', category_name).strip()
                categories.append(clean_category)
    
    # Get the path to the Desktop for Windows
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "categories.xlsx")

    # Convert the list of categories to a DataFrame
    df = pd.DataFrame(categories, columns=["Category Name"])

    # Save the DataFrame to the Excel file on the Desktop
    df.to_excel(desktop_path, index=False)

    print(f"Scraping complete and data saved to '{desktop_path}'")

# Run the scraping function
scrape_categories()
