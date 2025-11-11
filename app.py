"""
LinkedIn Job Extractor - Streamlit Application
Main application for extracting structured data from LinkedIn job postings.
"""

import streamlit as st
import json
import os
from datetime import datetime
from openai import OpenAI
from prompts import get_extraction_prompt
from utils.db_connection import insert_job_data, test_connection

# Page configuration
st.set_page_config(
    page_title="LinkedIn Job Extractor",
    page_icon="💼",
    layout="wide"
)

# Initialize session state
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'insertion_success' not in st.session_state:
    st.session_state.insertion_success = False


def extract_job_data_with_llm(raw_text):
    """
    Send raw job text to LLM and get structured JSON response.
    
    Args:
        raw_text (str): Raw LinkedIn job posting text
        
    Returns:
        dict: Structured job data as dictionary
    """
    # Get API key from environment or Streamlit secrets
    api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", None)
    
    if not api_key:
        st.error("⚠️ OpenAI API key not found! Please set OPENAI_API_KEY environment variable or add it to Streamlit secrets.")
        return None
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Get the formatted prompt with the job text
        formatted_prompt = get_extraction_prompt(raw_text)
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using gpt-4o-mini for cost efficiency, can be changed to gpt-4
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
            temperature=0.1,  # Low temperature for consistent extraction
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
            job_data = json.loads(json_text)
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
                    job_data = json.loads(json_text)
                    st.warning("⚠️ Attempted to fix JSON by extracting the JSON object. Please verify the data.")
                else:
                    return None
            except:
                return None
        
        # Ensure all required fields are present with defaults
        default_structure = {
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
        
        # Merge with defaults to ensure all fields exist
        for key, default_value in default_structure.items():
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
        
        return job_data
        
    except json.JSONDecodeError as e:
        # This should not be reached due to inner try-catch, but keeping as backup
        st.error(f"❌ Invalid JSON response from LLM: {str(e)}")
        try:
            st.code(json_text[:1000] if 'json_text' in locals() else "No response received", language="json")
        except:
            pass
        return None
    except Exception as e:
        error_details = f"❌ Error calling LLM: {str(e)}"
        st.error(error_details)
        # Show more details in expander for debugging
        with st.expander("🔍 Error Details (Click to expand)"):
            st.exception(e)
            if 'json_text' in locals():
                st.text("Raw LLM Response:")
                st.code(json_text[:2000], language="text")
        return None


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
                    extracted_data = extract_job_data_with_llm(raw_text.strip())
                    
                    if extracted_data:
                        st.session_state.processed_data = extracted_data
                        st.session_state.insertion_success = False
                        st.success("✅ Data extracted successfully!")
        
        # Display extracted data
        if st.session_state.processed_data:
            # Format JSON for display
            json_display = json.dumps(st.session_state.processed_data, indent=2, ensure_ascii=False)
            
            # Show JSON in expandable code block
            with st.expander("📋 View Extracted JSON", expanded=True):
                st.code(json_display, language="json")
            
            # Download button
            st.download_button(
                label="💾 Download JSON",
                data=json_display,
                file_name=f"job_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
            
            # Store to MongoDB button
            st.markdown("---")
            if st.button("💾 Store to MongoDB", type="primary", use_container_width=True):
                try:
                    with st.spinner("💾 Storing data to MongoDB..."):
                        # Make a copy to avoid modifying session state
                        data_to_insert = st.session_state.processed_data.copy()
                        document_id = insert_job_data(data_to_insert)
                        st.session_state.insertion_success = True
                        st.success(f"✅ Successfully stored to MongoDB!")
                        st.info(f"📄 Document ID: `{document_id}`")
                        st.info(f"🗄️ Database: `Kinnective_testing` | Collection: `linkedin_jobs`")
                except ValueError as e:
                    st.error(f"❌ Validation Error: {str(e)}")
                    with st.expander("🔍 Debug Info"):
                        st.json(st.session_state.processed_data)
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

