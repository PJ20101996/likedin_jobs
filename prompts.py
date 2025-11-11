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
    return f"""You are an expert data extraction assistant. Your task is to analyze raw LinkedIn job posting text and extract structured information into a specific JSON format.

INSTRUCTIONS:
1. Carefully read the entire job posting text provided below.
2. Extract all relevant information and map it to the exact field structure specified.
3. If a field cannot be found in the text, leave it as an empty string "" or empty array [].
4. Return ONLY valid JSON - no additional commentary, explanations, or markdown formatting.
5. Ensure all string fields are properly escaped for JSON.
6. For arrays, use proper JSON array format with square brackets.

FIELD EXTRACTION GUIDELINES:

- application_link: Direct URL to apply for the job (if mentioned)
- application_posted: Date when the job was posted (format: YYYY-MM-DD or as found)
- categories: Array of job categories/tags (e.g., ["Engineering", "Software Development"])
- city: City name where the job is located
- company: Company name
- company_url: Company website URL (if mentioned)
- country: Country name where the job is located
- description: Description about the posted job not about the company.    
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
- created_date: Use current date in YYYY-MM-DD format
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

CRITICAL: 
- The job_description_roles_resp field MUST be a JSON object with "roles" and "responsibilities" as arrays
- All string fields should be strings (use "" for empty, not null)
- All number fields should be numbers (0, not "0")
- Return ONLY valid JSON - no markdown, no code blocks, no explanations
- Ensure proper JSON escaping for special characters

Now, extract the information from the following job posting text and return ONLY the JSON object:

{job_text}

Return the complete JSON object matching the exact structure above. Do not include any text before or after the JSON."""

