"""
LinkedIn Job Extractor - Streamlit Application
Main application for extracting structured data from LinkedIn job postings.
"""

import streamlit as st
import json
import os
from datetime import datetime, timedelta
import re
from dotenv import load_dotenv
from openai import OpenAI
from prompts import get_extraction_prompt
from utils.db_connection import insert_job_data, insert_company_data, test_connection

# Load environment variables from .env file
load_dotenv()


def validate_job_posting_text(text):
    """
    Validate if the input text appears to be a job posting.
    
    Args:
        text (str): Input text to validate
        
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if not text or len(text.strip()) < 50:
        return False, "⚠️ The input text is too short. Please paste the complete job posting content."
    
    text_lower = text.lower()
    
    # Check for job-related keywords (at least 3 should be present)
    job_keywords = [
        'job', 'position', 'role', 'career', 'opportunity', 'opening',
        'company', 'employer', 'organization', 'hiring', 'recruiting',
        'location', 'city', 'state', 'country', 'remote', 'hybrid', 'on-site',
        'responsibilities', 'requirements', 'qualifications', 'skills',
        'experience', 'years', 'full-time', 'part-time', 'contract',
        'salary', 'compensation', 'benefits', 'apply', 'application',
        'engineer', 'developer', 'manager', 'analyst', 'specialist', 'associate'
    ]
    
    found_keywords = [keyword for keyword in job_keywords if keyword in text_lower]
    
    # Check for common job posting patterns
    job_patterns = [
        'about the job', 'job description', 'job title', 'position title',
        'we are seeking', 'we are looking for', 'join our team',
        'required skills', 'technical skills', 'must have', 'should have'
    ]
    
    found_patterns = [pattern for pattern in job_patterns if pattern in text_lower]
    
    # Need at least 3 keywords OR at least 1 pattern to be considered valid
    if len(found_keywords) < 3 and len(found_patterns) == 0:
        return False, """⚠️ **Invalid Input: This doesn't appear to be a job posting.**
        
Please ensure you paste the **complete job description** from LinkedIn, including:
- ✅ Job title/position name
- ✅ Company name  
- ✅ Location information (city, state, country)
- ✅ Job responsibilities or requirements
- ✅ Skills or qualifications needed
- ✅ Any other job-related details

**Please copy and paste the full job posting content from LinkedIn.**"""
    
    # Check for common non-job content indicators
    invalid_indicators = [
        'lorem ipsum', 'test text', 'sample text', 'placeholder',
        'this is a test', 'dummy data', 'example text', 'random text'
    ]
    
    for indicator in invalid_indicators:
        if indicator in text_lower:
            return False, f"⚠️ **Invalid Input:** The text contains test/placeholder content ('{indicator}').\n\nPlease paste **actual job posting content** from LinkedIn."
    
    # Check if text seems too generic or random (should have reasonable word count)
    word_count = len(text.split())
    if word_count < 20:
        return False, f"⚠️ **Input too short:** The text has only {word_count} words, which is too short for a job posting.\n\nPlease paste the **complete job posting** with all details."
    
    # Additional check: Should contain at least one location indicator
    location_indicators = ['location', 'city', 'state', 'country', 'remote', 'hybrid', 'on-site', 'india', 'bengaluru', 'mumbai', 'delhi', 'pune']
    has_location = any(indicator in text_lower for indicator in location_indicators)
    
    # Additional check: Should contain company or job title indicators
    title_indicators = ['engineer', 'developer', 'manager', 'analyst', 'specialist', 'associate', 'lead', 'senior', 'junior']
    has_title = any(indicator in text_lower for indicator in title_indicators)
    
    if not has_location and not has_title and len(found_keywords) < 5:
        return False, """⚠️ **Input validation failed:** The text doesn't contain enough job posting indicators.
        
Please make sure you're pasting:
- A complete LinkedIn job posting
- Including job title, company name, and location
- With job responsibilities and requirements

**Please copy the entire job posting from LinkedIn and try again.**"""
    
    return True, ""


# Page configuration
st.set_page_config(
    page_title="LinkedIn Job Extractor",
    page_icon="💼",
    layout="wide"
)

# Initialize session state
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'processed_company_data' not in st.session_state:
    st.session_state.processed_company_data = None
if 'insertion_success' not in st.session_state:
    st.session_state.insertion_success = False


def parse_relative_date(text, field_value=""):
    """
    Parse relative date expressions like "4 weeks ago", "1 month ago" from text
    and calculate the actual date.
    
    Args:
        text (str): Raw job posting text to search for relative dates
        field_value (str): The value returned by LLM (might already be calculated)
        
    Returns:
        str: Calculated date in YYYY-MM-DD format, or empty string if not found
    """
    # First, search for relative date patterns in the text (prioritize this)
    text_lower = text.lower()
    
    # Pattern: "X weeks ago", "X week ago"
    week_match = re.search(r'(\d+)\s+weeks?\s+ago', text_lower)
    if week_match:
        weeks = int(week_match.group(1))
        calculated_date = datetime.now() - timedelta(weeks=weeks)
        return calculated_date.strftime("%Y-%m-%d")
    
    # Pattern: "X months ago", "X month ago"
    month_match = re.search(r'(\d+)\s+months?\s+ago', text_lower)
    if month_match:
        months = int(month_match.group(1))
        # Approximate: 1 month = 30 days
        calculated_date = datetime.now() - timedelta(days=months * 30)
        return calculated_date.strftime("%Y-%m-%d")
    
    # Pattern: "X days ago", "X day ago"
    day_match = re.search(r'(\d+)\s+days?\s+ago', text_lower)
    if day_match:
        days = int(day_match.group(1))
        calculated_date = datetime.now() - timedelta(days=days)
        return calculated_date.strftime("%Y-%m-%d")
    
    # Pattern: "X years ago", "X year ago" (usually not relevant for job postings, but handle it)
    year_match = re.search(r'(\d+)\s+years?\s+ago', text_lower)
    if year_match:
        years = int(year_match.group(1))
        calculated_date = datetime.now() - timedelta(days=years * 365)
        return calculated_date.strftime("%Y-%m-%d")
    
    # If no relative date found in text, check if LLM already calculated a valid date
    if field_value and re.match(r'^\d{4}-\d{2}-\d{2}$', field_value):
        try:
            parsed = datetime.strptime(field_value, "%Y-%m-%d")
            # Only use if it's a recent date (not from 2023 or earlier)
            if parsed.year >= 2024:
                return field_value
        except:
            pass
    
    return field_value if field_value else ""


def extract_job_data_with_llm(raw_text):
    """
    Send raw job text to LLM and get structured JSON response.
    
    Args:
        raw_text (str): Raw LinkedIn job posting text
        
    Returns:
        tuple: (job_data: dict, company_data: dict) - Structured job and company data as dictionaries
    """
    # Get API key from environment or Streamlit secrets
    api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", None)
    
    if not api_key:
        st.error("⚠️ OpenAI API key not found! Please set OPENAI_API_KEY environment variable or add it to Streamlit secrets.")
        return None, None
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Get the formatted prompt with the job text
        formatted_prompt = get_extraction_prompt(raw_text)
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4.1-nano",  # Using gpt-4o-mini for cost efficiency, can be changed to gpt-4
            messages=[
                {
                    "role": "system",
                    "content": "You are a data extraction assistant. Extract job information and return ONLY valid JSON, no additional text."
                },
                {
                    "role": "user",
                    "content": formatted_prompt
                }
            ],
              # Low temperature for consistent extraction
            response_format={"type": "json_object"}  # Force JSON response
        )
        
        # Extract JSON from response
        json_text = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if json_text.startswith("```json"):
            json_text = json_text[7:]
        if json_text.startswith("```"):
            json_text = json_text[3:]
        if json_text.endswith("```"):
            json_text = json_text[:-3]
        json_text = json_text.strip()
        
        # Clean up common JSON issues
        # Remove any leading/trailing whitespace or newlines
        json_text = json_text.strip()
        
        # Remove any leading text before the first {
        first_brace = json_text.find('{')
        if first_brace > 0:
            json_text = json_text[first_brace:]
        
        # Remove any trailing text after the last }
        last_brace = json_text.rfind('}')
        if last_brace > 0 and last_brace < len(json_text) - 1:
            json_text = json_text[:last_brace + 1]
        
        # Parse JSON with better error handling
        try:
            extracted_data = json.loads(json_text)
        except json.JSONDecodeError as json_error:
            # Show detailed error information
            error_msg = str(json_error)
            error_position = getattr(json_error, 'pos', None)
            
            st.error(f"❌ JSON Parsing Error: {error_msg}")
            if error_position:
                # Show context around the error
                start = max(0, error_position - 100)
                end = min(len(json_text), error_position + 100)
                st.code(f"...{json_text[start:end]}...", language="text")
            else:
                st.code(json_text[:1000], language="json")
            
            # Try to extract JSON from the response if it's partially valid
            try:
                # Try to find JSON object boundaries
                start_idx = json_text.find('{')
                end_idx = json_text.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_text = json_text[start_idx:end_idx+1]
                    extracted_data = json.loads(json_text)
                    st.warning("⚠️ Attempted to fix JSON by extracting the JSON object. Please verify the data.")
                else:
                    return None, None
            except:
                return None, None
        
        # Extract job_data and company_data from the response
        job_data = extracted_data.get("job_data", {})
        company_data = extracted_data.get("company_data", {})
        
        # DEBUG: Check what LLM returned for created_date
        if job_data and "created_date" in job_data:
            llm_created_date = job_data.get("created_date")
            if llm_created_date and "2023" in str(llm_created_date):
                st.warning(f"⚠️ DEBUG: LLM returned created_date as: '{llm_created_date}' (This will be kept because it exists in the response)")
        
        # If the response doesn't have the nested structure, assume it's all job data
        if not job_data and not company_data:
            # Check if it's the old format (all job data at root level)
            if "position_title" in extracted_data or "company" in extracted_data:
                job_data = extracted_data
                # Try to extract company info from job data
                company_data = {
                    "name": extracted_data.get("company", ""),
                    "city": extracted_data.get("city", ""),
                    "state": extracted_data.get("state", ""),
                    "industry": extracted_data.get("industry", ""),
                    "description": "",  # Company description not in job data
                    "url": extracted_data.get("company_url", ""),
                    "company_domain": "",
                    "logo_url": extracted_data.get("logo_url", ""),
                    "company_id": ""
                }
            else:
                return None, None
        
        # Ensure all required fields are present with defaults for job data
        default_job_structure = {
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
            "job_description_roles_resp": {
                "roles": [],
                "responsibilities": []
            },
            "job_id": "",
            "job_type": "",
            "location": "",
            "position_title": "",
            "remote_in_person": "",
            "required_skills": "",
            "salary": "",
            "start_date": "",
            "state": "",
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "logo_url": "",
            "number_of_viewed": 0,
            "number_of_applied": 0,
            "number_of_saved": 0
        }
        
        # Merge with defaults to ensure all fields exist for job data
        for key, default_value in default_job_structure.items():
            if key not in job_data:
                job_data[key] = default_value
            # Handle nested structure for job_description_roles_resp
            elif key == "job_description_roles_resp":
                if not isinstance(job_data[key], dict):
                    job_data[key] = default_value
                else:
                    if "roles" not in job_data[key]:
                        job_data[key]["roles"] = []
                    if "responsibilities" not in job_data[key]:
                        job_data[key]["responsibilities"] = []
        
        # Ensure all required fields are present with defaults for company data
        default_company_structure = {
            "name": "",
            "city": "",
            "state": "",
            "industry": "",
            "description": "",
            "url": "",
            "company_domain": "",
            "logo_url": "",
            "company_id": ""
        }
        
        # Merge with defaults to ensure all fields exist for company data
        for key, default_value in default_company_structure.items():
            if key not in company_data:
                company_data[key] = default_value
        
        # Parse relative dates for application_posted (e.g., "4 weeks ago" → actual date)
        if job_data and "application_posted" in job_data:
            llm_date = job_data.get("application_posted", "")
            calculated_date = parse_relative_date(raw_text, llm_date)
            if calculated_date and calculated_date != llm_date:
                job_data["application_posted"] = calculated_date
        
        # Force created_date to always be current date (override any LLM-provided date)
        current_date = datetime.now().strftime("%Y-%m-%d")
        job_data["created_date"] = current_date
        
        return job_data, company_data
        
    except json.JSONDecodeError as e:
        # This should not be reached due to inner try-catch, but keeping as backup
        st.error(f"❌ Invalid JSON response from LLM: {str(e)}")
        try:
            st.code(json_text[:1000] if 'json_text' in locals() else "No response received", language="json")
        except:
            pass
        return None, None
    except Exception as e:
        error_details = f"❌ Error calling LLM: {str(e)}"
        st.error(error_details)
        # Show more details in expander for debugging
        with st.expander("🔍 Error Details (Click to expand)"):
            st.exception(e)
            if 'json_text' in locals():
                st.text("Raw LLM Response:")
                st.code(json_text[:2000], language="text")
        return None, None


def main():
    """Main application function."""
    
    # Title and header
    st.title("💼 LinkedIn Job Extractor")
    st.markdown("---")
    st.markdown("Paste raw LinkedIn job posting text below and click 'Process Data' to extract structured information.")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # MongoDB connection test
        st.subheader("Database Status")
        is_connected, status_msg = test_connection()
        if is_connected:
            st.success(status_msg)
        else:
            st.error(status_msg)
            with st.expander("🔧 Troubleshooting"):
                st.markdown("""
                **Common Issues:**
                1. Check your internet connection
                2. Verify MongoDB Atlas IP whitelist (allow all IPs: 0.0.0.0/0)
                3. Verify connection string is correct
                4. Check if MongoDB Atlas cluster is running
                """)
        
        st.markdown("---")
        st.subheader("About")
        st.markdown("""
        This application extracts structured data from LinkedIn job postings using AI.
        
        **Features:**
        - AI-powered data extraction
        - Automatic JSON structuring
        - MongoDB storage
        - Real-time validation
        """)
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📝 Input: Raw Job Data")
        raw_text = st.text_area(
            "Paste LinkedIn job posting text here:",
            height=400,
            placeholder="Paste the complete job posting text here...",
            label_visibility="collapsed"
        )
        
        # Process button
        process_button = st.button("🚀 Process Data", type="primary", use_container_width=True)
    
    with col2:
        st.subheader("📊 Output: Structured Data")
        
        if process_button:
            # Validate input
            if not raw_text or not raw_text.strip():
                st.warning("⚠️ Please enter job posting text before processing.")
            else:
                with st.spinner("🤖 Processing with AI..."):
                    # Extract data using LLM
                    job_data, company_data = extract_job_data_with_llm(raw_text.strip())
                    
                    if job_data and company_data:
                        st.session_state.processed_data = job_data
                        st.session_state.processed_company_data = company_data
                        st.session_state.insertion_success = False
                        st.success("✅ Data extracted successfully!")
                    elif job_data:
                        st.session_state.processed_data = job_data
                        st.session_state.processed_company_data = None
                        st.session_state.insertion_success = False
                        st.warning("⚠️ Job data extracted, but company data is missing.")
                    else:
                        st.error("❌ Failed to extract data from the job posting.")
        
        # Display extracted data
        if st.session_state.processed_data:
            # Create tabs for job and company data
            tab1, tab2 = st.tabs(["📋 Job Data", "🏢 Company Data"])
            
            with tab1:
                # Format JSON for display
                job_json_display = json.dumps(st.session_state.processed_data, indent=2, ensure_ascii=False)
                
                # Show JSON in expandable code block
                with st.expander("📋 View Extracted Job JSON", expanded=True):
                    st.code(job_json_display, language="json")
            
            with tab2:
                if st.session_state.processed_company_data:
                    # Format JSON for display
                    company_json_display = json.dumps(st.session_state.processed_company_data, indent=2, ensure_ascii=False)
                    
                    # Show JSON in expandable code block
                    with st.expander("📋 View Extracted Company JSON", expanded=True):
                        st.code(company_json_display, language="json")
                else:
                    st.warning("⚠️ No company data extracted.")
            
            # Download buttons
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button(
                    label="💾 Download Job JSON",
                    data=job_json_display,
                    file_name=f"job_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            with col_dl2:
                if st.session_state.processed_company_data:
                    st.download_button(
                        label="💾 Download Company JSON",
                        data=company_json_display,
                        file_name=f"company_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
            
            # Store to MongoDB button
            st.markdown("---")
            if st.button("💾 Store to MongoDB", type="primary", use_container_width=True):
                try:
                    with st.spinner("💾 Storing data to MongoDB..."):
                        # Make copies to avoid modifying session state
                        job_data_to_insert = st.session_state.processed_data.copy()
                        company_data_to_insert = st.session_state.processed_company_data.copy() if st.session_state.processed_company_data else None
                        
                        # Store job data
                        job_document_id = insert_job_data(job_data_to_insert)
                        st.success(f"✅ Job data stored successfully!")
                        st.info(f"📄 Job Document ID: `{job_document_id}`")
                        st.info(f"🗄️ Database: `Kinnective_testing` | Collection: `linkedin_jobs`")
                        
                        # Store company data if available
                        if company_data_to_insert:
                            company_document_id = insert_company_data(company_data_to_insert)
                            st.success(f"✅ Company data stored successfully!")
                            st.info(f"📄 Company Document ID: `{company_document_id}`")
                            st.info(f"🗄️ Database: `Kinnective_testing` | Collection: `companies`")
                        
                        st.session_state.insertion_success = True
                except ValueError as e:
                    st.error(f"❌ Validation Error: {str(e)}")
                    with st.expander("🔍 Debug Info"):
                        st.json({
                            "job_data": st.session_state.processed_data,
                            "company_data": st.session_state.processed_company_data
                        })
                except Exception as e:
                    st.error(f"❌ Database Error: {str(e)}")
                    with st.expander("🔍 Error Details"):
                        st.exception(e)
                        st.text("Check your MongoDB connection string and network access.")
            
            # Show success message if data was stored
            if st.session_state.insertion_success:
                st.balloons()
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
        <p>LinkedIn Job Extractor | Powered by OpenAI & MongoDB</p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()

