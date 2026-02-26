import mysql.connector
import smtplib
import dns.resolver
import requests
import time
import re
import random
from googlesearch import search

# ✅ Connect to MySQL database
def connect_db():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="1234",
            database="usa"
        )
        print("✅ Database connection successful!")
        return conn
    except mysql.connector.Error as err:
        print(f"❌ Database connection failed: {err}")
        exit(1)

# ✅ Fetch data from MySQL
def fetch_data():
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT k.ID, k.company_name, k.Person_Name, k.Designation, 
               u.ID AS Company_ID, u.Company_Website 
        FROM Key_people_info k
        JOIN usa_companies_final u ON k.company_name = u.NAME
    """
    cursor.execute(query)
    data = cursor.fetchall()

    cursor.close()
    conn.close()
    print(f"✅ Fetched {len(data)} records from database.")
    return data

# ✅ Extract domain from website URL
def extract_domain(website_url):
    if not website_url or website_url.strip() == "":
        return None
    match = re.search(r"https?://(?:www\.)?([^/]+)", website_url)
    return match.group(1) if match else None

# ✅ Generate possible email addresses
def generate_possible_emails(name, domain):
    name_parts = name.lower().split()
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    patterns = [
        f"{first_name}.{last_name}@{domain}",
        f"{first_name}{last_name}@{domain}",
        f"{first_name}@{domain}",
        f"{first_name[0]}{last_name}@{domain}",
        f"{first_name}_{last_name}@{domain}",
        f"{last_name}@{domain}" if last_name else ""
    ]

    return [email for email in patterns if email]

# ✅ Check email validity via SMTP
def check_email_exists(email):
    domain = email.split("@")[1]

    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        mail_server = str(mx_records[0].exchange)

        server = smtplib.SMTP(timeout=5)
        server.connect(mail_server)
        server.helo()
        server.mail('test@example.com')
        code, _ = server.rcpt(email)
        server.quit()

        return code == 250  # True if valid
    except Exception:
        return False

# ✅ Search Google for LinkedIn and Emails
def search_google_for_info(name, company, designation):
    linkedin_query = f'site:linkedin.com/in/ OR site:linkedin.com/pub/ "{name}" "{company}"'
    email_query = f'"{name}" "{company}" email'

    linkedin_profile, linkedin_name = None, None
    found_emails = set()

    try:
        # 🔍 Search for LinkedIn profile
        for url in search(linkedin_query, num_results=5):
            if "linkedin.com/in/" in url or "linkedin.com/pub/" in url:
                linkedin_profile = url
                linkedin_name = url.split("/")[-1].split("?")[0]
                print(f"✅ LinkedIn found: {linkedin_profile}")
                break

        time.sleep(random.uniform(6, 9))

        # 🔍 Search for emails
        for url in search(email_query, num_results=5):
            time.sleep(1)
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    emails = re.findall(r"[a-zA-Z0-9._%+-]+@" + re.escape(company.split()[0].lower()) + r"\.\w+", response.text)
                    found_emails.update(emails)
            except requests.RequestException:
                pass

    except Exception as e:
        print(f"❌ Google Search Error: {e}")

    if linkedin_profile is None:
        print(f"⚠️ No LinkedIn found for {name}.")

    return linkedin_name, linkedin_profile, list(found_emails)

# ✅ Assign rating
def rate_email(email, smtp_status, found_in_google):
    if smtp_status:
        return 5
    elif found_in_google:
        return 4
    else:
        return 3

# ✅ Process and store data
def process_and_store():
    print("🚀 Process started...")
    data = fetch_data()
    print(f"📌 Total entries to process: {len(data)}")
    results = []

    for row in data:
        company_id = row['Company_ID']
        company_name = row['company_name']
        person_name = row['Person_Name']
        designation = row['Designation']
        domain = extract_domain(row['Company_Website'])

        print(f"🔍 Processing {person_name} from {company_name} (Domain: {domain})")

        if not domain:
            print(f"⚠️ No valid domain found for {company_name}. Skipping...")
            continue

        linkedin_name, linkedin_profile, google_emails = search_google_for_info(person_name, company_name, designation)
        possible_emails = generate_possible_emails(person_name, domain)

        best_email = None
        highest_rating = 0

        for email in possible_emails:
            smtp_status = check_email_exists(email)
            found_in_google = email in google_emails
            rating = rate_email(email, smtp_status, found_in_google)

            print(f"📧 Checked email: {email} | Rating: {rating}")

            if rating > highest_rating:
                best_email = email
                highest_rating = rating

        print(f"✅ Best email: {best_email} | Rating: {highest_rating}")
        print(f"🔗 LinkedIn: {linkedin_name} ({linkedin_profile})")

        if best_email:
            results.append((company_id, company_name, person_name, designation, best_email, highest_rating, linkedin_name, linkedin_profile))

    if results:
        insert_results(results)
    else:
        print("⚠️ No valid emails found. Nothing to insert.")

    print("🎉 Process completed!")

# ✅ Insert data into MySQL
def insert_results(results):
    conn = connect_db()
    cursor = conn.cursor()

    insert_query = """
        INSERT INTO usa_top_companies_key_people_email (Company_ID, Company_Name, Person_Name, Designation, Email_Id, Rating, LinkedIn_Name, LinkedIn_Profile)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE Email_Id = VALUES(Email_Id), Rating = VALUES(Rating), LinkedIn_Name = VALUES(LinkedIn_Name), LinkedIn_Profile = VALUES(LinkedIn_Profile)
    """

    cursor.executemany(insert_query, results)
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ {cursor.rowcount} records inserted successfully!")

# ✅ Run the process
if __name__ == "__main__":
    process_and_store()
