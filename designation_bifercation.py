import mysql.connector
import time

# Connect to MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="UK"
)
cursor = conn.cursor()

# Get company names from UK_LINKEDIN_PROFILE
cursor.execute("SELECT DISTINCT Company_Name FROM uk_linkedin_profile")
companies = cursor.fetchall()  # List of (Company_Name,)

count = 0  # Counter for inserted entries

for (company_name,) in companies:
    # Initialize variables for key roles
    ceo_name, ceo_designation, ceo_linkedin = None, None, None
    cfo_name, cfo_designation, cfo_linkedin = None, None, None
    finance_name, finance_designation, finance_linkedin = None, None, None
    accounting_name, accounting_designation, accounting_linkedin = None, None, None
    legal_name, legal_designation, legal_linkedin = None, None, None

    # Fetch key people for this company
    cursor.execute("SELECT Person_Name_DB, Designation, Linkedin_Profile FROM uk_linkedin_profile WHERE Company_Name = %s", (company_name,))
    key_people = cursor.fetchall()  # List of (Person_Name_DB, Designation, Linkedin_Profile)

    # Categorize key people into respective roles
    for person_name, designation, linkedin_link in key_people:
        if "CEO" in designation or "Chief Executive Officer" in designation:
            ceo_name, ceo_designation, ceo_linkedin = person_name, designation, linkedin_link
        elif "CFO" in designation or "Chief Financial Officer" in designation:
            cfo_name, cfo_designation, cfo_linkedin = person_name, designation, linkedin_link
        elif "General Counsel" in designation or "Chief Legal Officer" in designation or "Legal" in designation:
            legal_name, legal_designation, legal_linkedin = person_name, designation, linkedin_link
        elif "Finance" in designation and not cfo_name:
            finance_name, finance_designation, finance_linkedin = person_name, designation, linkedin_link
        elif "Accounting" in designation and not cfo_name and not finance_name:
            accounting_name, accounting_designation, accounting_linkedin = person_name, designation, linkedin_link

    # Print values before inserting
    print(f"Inserting Data: Company={company_name}, CEO={ceo_name} ({ceo_designation}), CFO={cfo_name} ({cfo_designation}), Finance={finance_name} ({finance_designation}), Accounting={accounting_name} ({accounting_designation}), Legal={legal_name} ({legal_designation})")

    # Insert a single row per company into the new table
    cursor.execute("""
        INSERT INTO key_people_summary (Company_Name, CEO_Name, CEO_Designation, CEO_LinkedIn,
                                        CFO_Name, CFO_Designation, CFO_LinkedIn, 
                                        Finance_Name, Finance_Designation, Finance_LinkedIn,
                                        Accounting_Name, Accounting_Designation, Accounting_LinkedIn,
                                        Chief_Legal_Counsel_Name, Chief_Legal_Counsel_Designation, Chief_Legal_Counsel_LinkedIn)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            CEO_Name = VALUES(CEO_Name), CEO_Designation = VALUES(CEO_Designation), CEO_LinkedIn = VALUES(CEO_LinkedIn),
            CFO_Name = VALUES(CFO_Name), CFO_Designation = VALUES(CFO_Designation), CFO_LinkedIn = VALUES(CFO_LinkedIn),
            Finance_Name = VALUES(Finance_Name), Finance_Designation = VALUES(Finance_Designation), Finance_LinkedIn = VALUES(Finance_LinkedIn),
            Accounting_Name = VALUES(Accounting_Name), Accounting_Designation = VALUES(Accounting_Designation), Accounting_LinkedIn = VALUES(Accounting_LinkedIn),
            Chief_Legal_Counsel_Name = VALUES(Chief_Legal_Counsel_Name), 
            Chief_Legal_Counsel_Designation = VALUES(Chief_Legal_Counsel_Designation),
            Chief_Legal_Counsel_LinkedIn = VALUES(Chief_Legal_Counsel_LinkedIn);
    """, (company_name, ceo_name, ceo_designation, ceo_linkedin, 
          cfo_name, cfo_designation, cfo_linkedin, 
          finance_name, finance_designation, finance_linkedin, 
          accounting_name, accounting_designation, accounting_linkedin, 
          legal_name, legal_designation, legal_linkedin))

    count += 1  # Increment counter
    
    # Pause for 60 seconds after every 75 entries
    if count % 75 == 0:
        print("Pausing for 60 seconds...")
        time.sleep(60)

# Commit changes and close connection
conn.commit()
cursor.close()
conn.close()
print("Data insertion completed.")
