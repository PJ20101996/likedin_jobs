"""
LLM Extraction Prompt for LinkedIn Job Data
This prompt instructs the LLM to extract structured data from raw LinkedIn job descriptions.
"""

def get_extraction_prompt(job_text):
    """
    Generate the extraction prompt with the job text.
    
    Args:
        job_text (str): Raw LinkedIn job posting text
        
    Returns:
        str: Formatted prompt string
    """
    return f"""You are a professional data extraction assistant. You must analyze the raw LinkedIn job posting text and extract TWO clear JSON objects:.
1️⃣ "job_data" → contains information about the **job post only** (role, position, skills, etc.)
2️⃣ "company_data" → contains information about the **company only** (organization overview, mission, website, etc.)

INSTRUCTIONS:
1. Carefully read the entire job posting text provided below.
2. Extract all relevant information and map it to the exact field structure specified.
3. If a field cannot be found in the text, leave it as an empty string "" or empty array [].
4. Return ONLY valid JSON - no additional commentary, explanations, or markdown formatting.
5. Ensure all string fields are properly escaped for JSON.
6. For arrays, use proper JSON array format with square brackets.

FIELD EXTRACTION GUIDELINES:

application_link MUST be extracted from the text**  
Job postings often embed links like Google Forms, company career URLs, SmartRecruiters, Greenhouse, Taleo, Zoho Recruit, or short links.  
Extract ANY link that appears to be used for applying, including links that appear after phrases like:
- "Apply here"
- "Click the link"
- "Submit your application"
- "Fill this form"
- "Apply now"
- “Use this Google Form”
- “Career page link”

If multiple links exist → choose the one MOST related to applying.  
If none exist → keep application_link as empty string.

- application_link: Direct URL to apply for the job (if mentioned)
- application_posted: Date when the job was posted (format: YYYY-MM-DD). 
  **IMPORTANT**: If the posting mentions relative time like "4 weeks ago", "1 month ago", "2 days ago", etc., you MUST calculate the actual date by subtracting that time from TODAY's date.
  Examples:
  - "4 weeks ago" → Calculate: Today's date minus 28 days (format as YYYY-MM-DD)
  - "1 month ago" → Calculate: Today's date minus 30 days (format as YYYY-MM-DD)
  - "2 weeks ago" → Calculate: Today's date minus 14 days (format as YYYY-MM-DD)
  - "3 days ago" → Calculate: Today's date minus 3 days (format as YYYY-MM-DD)
  Use TODAY's date (current date) as the reference point for all calculations.
  If no date information is found, leave as empty string ""
- categories: Array of job categories/tags (e.g., ["Engineering", "Software Development"])
- city: City name where the job is located
- company: Company name
- company_url: Company website URL (if mentioned)
- country: Country name where the job is located
- description: ← ⚠️ this should describe only the job responsibilities/role, NOT the company details.    
- description_full: Complete job description text
- industry: Industry sector (e.g., "Technology", "Healthcare", "Finance")
- job_description_roles_resp: Object with two arrays:
  - roles: Array of job roles/titles mentioned
  - responsibilities: Array of individual responsibility bullet points
- job_id: Unique job identifier if mentioned, otherwise leave empty
- job_type: Type of employment (e.g., "Full-time", "Part-time", "Contract", "Internship")
- location: Full location string (e.g., "San Francisco, CA, United States")
- position_title: Job title/position name
- remote_in_person: "Remote", "On-site", "Hybrid", or as specified
- required_skills: Comma-separated or array-converted string of required skills
- salary: Salary range or compensation information (if mentioned)
- start_date: Expected start date or "Immediate" if mentioned
- state: State/province name (if applicable)
- created_date: Set to today's date in YYYY-MM-DD format (use the current date, not a date from the job posting)
- logo_url: Leave empty unless specifically mentioned
- number_of_viewed: Set to 0
- number_of_applied: Set to 0
- number_of_saved: Set to 0

REQUIRED JSON STRUCTURE (you must return exactly this structure):

{{
  "application_link": "",
  "application_posted": "",
  "categories": [],
  "city": "",
  "company": "",
  "company_url": "",
  "country": "",
  "description": "",
  "description_full": "",
  "industry": "",
  "job_description_roles_resp": {{
    "roles": [],
    "responsibilities": []
  }},
  "job_id": "",
  "job_type": "",
  "location": "",
  "position_title": "",
  "remote_in_person": "",
  "required_skills": "",
  "salary": "",
  "start_date": "",
  "state": "",
  "created_date": "",
  "logo_url": "",
  "number_of_viewed": 0,
  "number_of_applied": 0,
  "number_of_saved": 0
}}


-----------------------
COMPANY DATA STRUCTURE (store in `companies` collection):
-----------------------
{{
  "name": "",
  "city": "",
  "state": "",
  "industry": "",
  "description": "",
  "url": "",
  "company_domain": "",
  "logo_url": "",
  "company_id": ""
}}

COMPANY DATA EXTRACTION GUIDELINES (MUST EXTRACT ALL FIELDS):

- name: Extract the company name (usually found at the top of the posting or in "About the company" section)

- city: Extract the city where the company is located (from job location or company info)

- state: Extract the state/province where the company is located

- industry: Extract the industry sector (e.g., "IT Services and IT Consulting", "Software Development", "Technology", "Healthcare")

- description: Must include the full company overview text. Look for:
  * The section explicitly titled "About the company" or something similar they will mention about their company stuff
  * Sentences starting with the company name ("Optum is a...", "Infosys is a global leader...", etc.)
  * Paragraphs describing what the company does, its mission, employees, or services.
  * Do NOT include job duties or responsibilities here.

- url: Extract the company website URL if explicitly mentioned. Look for:
  * Company website links (e.g., "www.infosys.com", "https://www.infosys.com", "Visit www.infosys.com")
  * URLs in the "About the company" section or anywhere in the text
  * Include the full URL as found (with or without http/https/www)
  * If not found, leave as empty string ""

- company_domain: Extract ONLY the domain name from the company URL:
  * If url is "www.infosys.com" → extract "infosys.com"
  * If url is "https://www.infosys.com" → extract "infosys.com"
  * If url is "https://infosys.com" → extract "infosys.com"
  * Remove "www.", "http://", "https://", and any paths
  * If URL is not available but email is found (e.g., "hr@animaker.com"), extract domain from email (e.g., "animaker.com")
  * If neither is available, leave as empty string ""

- logo_url: Leave as empty string strictly ""

- company_id: Leave as empty string "" unless a specific company ID is mentioned



{{
  "job_data": {{...}},
  "company_data": {{...}}
}}

⚠️⚠️⚠️ CRITICAL EXTRACTION REQUIREMENTS ⚠️⚠️⚠️

BEFORE EXTRACTING, READ THESE REQUIREMENTS CAREFULLY:

1. COMPANY DESCRIPTION EXTRACTION (MOST IMPORTANT):
   - You MUST search the ENTIRE text for company description paragraphs
   - Look for text that describes the company - usually appears after the company name
   - Common patterns: "CompanyName is a...", "We enable...", "With over X years...", "We do it by..."
   - Extract EVERY sentence and paragraph that describes the company, its services, mission, experience, clients, employees
   - DO NOT skip or leave empty if company description text exists
   - Example from Infosys: "Infosys is a global leader in next-generation digital services and consulting. We enable clients in more than 50 countries to navigate their digital transformation. With over three decades of experience..." - EXTRACT ALL OF THIS
   - The description field MUST contain the full company description text, not be empty

2. COMPANY DOMAIN EXTRACTION:
   - If you find a URL like "www.infosys.com" or "Visit www.infosys.com", extract the domain as "infosys.com"
   - Remove "www.", "http://", "https://" prefixes
   - Remove any paths after the domain
   - If URL is "www.infosys.com" → company_domain should be "infosys.com"
   - DO NOT leave company_domain empty if a URL is found

3. JSON STRUCTURE:
   - The job_description_roles_resp field MUST be a JSON object with "roles" and "responsibilities" as arrays
   - All string fields should be strings (use "" for empty, not null)
   - All number fields should be numbers (0, not "0")
   - Return ONLY valid JSON - no markdown, no code blocks, no explanations
   - Ensure proper JSON escaping for special characters

Now, extract the information from the following job posting text and return ONLY the JSON object:

{job_text}

Return the complete JSON object matching the exact structure above. Do not include any text before or after the JSON."""

