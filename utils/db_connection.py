"""
MongoDB Connection Helper
Handles database connection and operations for storing LinkedIn job data.
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from datetime import datetime
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# MongoDB connection string - must be set in environment variable
MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING")
if not MONGO_CONNECTION_STRING:
    raise ValueError("MONGO_CONNECTION_STRING environment variable is required. Please set it in your .env file.")

# Database and Collection names
DATABASE_NAME = "Kinnective_testing"
COLLECTION_NAME = "linkedin_jobs"
COMPANY_COLLECTION_NAME = "companies"


def get_mongo_client():
    """
    Create and return a MongoDB client connection.
    
    Returns:
        MongoClient: MongoDB client instance
        
    Raises:
        ConnectionFailure: If connection to MongoDB fails
    """
    try:
        # Create client with connection timeout
        client = MongoClient(
            MONGO_CONNECTION_STRING,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=10000,  # 10 second connection timeout
            socketTimeoutMS=10000   # 10 second socket timeout
        )
        # Test the connection by pinging the database
        client.admin.command('ping')
        return client
    except ConnectionFailure as e:
        raise ConnectionFailure(f"Failed to connect to MongoDB: {str(e)}")
    except Exception as e:
        raise ConnectionFailure(f"Failed to connect to MongoDB: {str(e)}")


def validate_json_structure(data):
    """
    Validate that the data contains all required fields.
    
    Args:
        data (dict): The JSON data to validate
        
    Returns:
        tuple: (is_valid: bool, missing_fields: list)
    """
    required_fields = [
        "application_link", "application_posted", "categories", "city",
        "company", "company_url", "country", "description", "description_full",
        "industry", "job_description_roles_resp", "job_id", "job_type",
        "location", "position_title", "remote_in_person", "required_skills",
        "salary", "start_date", "state", "created_date", "logo_url",
        "number_of_viewed", "number_of_applied", "number_of_saved"
    ]
    
    missing_fields = [field for field in required_fields if field not in data]
    return len(missing_fields) == 0, missing_fields


def validate_company_structure(data):
    """
    Validate that the company data contains all required fields.
    
    Args:
        data (dict): The company JSON data to validate
        
    Returns:
        tuple: (is_valid: bool, missing_fields: list)
    """
    required_fields = [
        "name", "city", "state", "industry", "description",
        "url", "company_domain", "logo_url", "company_id"
    ]
    
    missing_fields = [field for field in required_fields if field not in data]
    return len(missing_fields) == 0, missing_fields


def insert_job_data(job_data):
    """
    Insert job data into MongoDB collection.
    
    Args:
        job_data (dict): The structured job data to insert
        
    Returns:
        str: Inserted document ID
        
    Raises:
        ValueError: If JSON structure is invalid
        OperationFailure: If MongoDB operation fails
    """
    # Validate JSON structure
    is_valid, missing_fields = validate_json_structure(job_data)
    if not is_valid:
        raise ValueError(f"Invalid JSON structure. Missing fields: {', '.join(missing_fields)}")
    
    # Ensure created_date is set
    if not job_data.get("created_date"):
        job_data["created_date"] = datetime.now().strftime("%Y-%m-%d")
    
    # Add insertion timestamp
    job_data["inserted_at"] = datetime.now().isoformat()
    
    client = None
    try:
        # Get MongoDB client
        client = get_mongo_client()
        
        # Access database and collection
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        # Verify collection exists (create if it doesn't)
        # MongoDB will create the collection automatically on first insert, but let's be explicit
        if COLLECTION_NAME not in db.list_collection_names():
            # Collection doesn't exist yet, it will be created on insert
            pass
        
        # Insert the document
        result = collection.insert_one(job_data)
        
        # Verify insertion was successful
        if result.inserted_id:
            # Double-check by querying the inserted document
            inserted_doc = collection.find_one({"_id": result.inserted_id})
            if inserted_doc:
                return str(result.inserted_id)
            else:
                raise Exception("Document was inserted but could not be verified in database")
        else:
            raise Exception("Insert operation returned no document ID")
            
    except ConnectionFailure as e:
        raise ConnectionFailure(f"Failed to connect to MongoDB: {str(e)}")
    except OperationFailure as e:
        raise OperationFailure(f"Failed to insert data into MongoDB: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error during database operation: {str(e)}")
    finally:
        # Always close the connection
        if client:
            client.close()


def insert_company_data(company_data):
    """
    Insert company data into MongoDB companies collection.
    
    Args:
        company_data (dict): The structured company data to insert
        
    Returns:
        str: Inserted document ID
        
    Raises:
        ValueError: If JSON structure is invalid
        OperationFailure: If MongoDB operation fails
    """
    # Validate JSON structure
    is_valid, missing_fields = validate_company_structure(company_data)
    if not is_valid:
        raise ValueError(f"Invalid company JSON structure. Missing fields: {', '.join(missing_fields)}")
    
    # Add insertion timestamp
    company_data["inserted_at"] = datetime.now().isoformat()
    
    client = None
    try:
        # Get MongoDB client
        client = get_mongo_client()
        
        # Access database and collection
        db = client[DATABASE_NAME]
        collection = db[COMPANY_COLLECTION_NAME]
        
        # Insert the document
        result = collection.insert_one(company_data)
        
        # Verify insertion was successful
        if result.inserted_id:
            # Double-check by querying the inserted document
            inserted_doc = collection.find_one({"_id": result.inserted_id})
            if inserted_doc:
                return str(result.inserted_id)
            else:
                raise Exception("Company document was inserted but could not be verified in database")
        else:
            raise Exception("Insert operation returned no document ID")
            
    except ConnectionFailure as e:
        raise ConnectionFailure(f"Failed to connect to MongoDB: {str(e)}")
    except OperationFailure as e:
        raise OperationFailure(f"Failed to insert company data into MongoDB: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error during database operation: {str(e)}")
    finally:
        # Always close the connection
        if client:
            client.close()


def test_connection():
    """
    Test MongoDB connection and verify database/collection access.
    
    Returns:
        tuple: (is_connected: bool, message: str)
    """
    try:
        client = get_mongo_client()
        db = client[DATABASE_NAME]
        
        # Check if database exists (it will be created on first insert)
        db_names = client.list_database_names()
        
        # Check if collections exist
        collection_names = db.list_collection_names()
        job_collection_exists = COLLECTION_NAME in collection_names
        company_collection_exists = COMPANY_COLLECTION_NAME in collection_names
        
        # Get collection counts if they exist
        job_count = 0
        company_count = 0
        if job_collection_exists:
            job_collection = db[COLLECTION_NAME]
            job_count = job_collection.count_documents({})
        if company_collection_exists:
            company_collection = db[COMPANY_COLLECTION_NAME]
            company_count = company_collection.count_documents({})
        
        client.close()
        
        status_msg = f"✅ Connected | Database: {DATABASE_NAME}"
        if job_collection_exists:
            status_msg += f" | Jobs: {COLLECTION_NAME} ({job_count} docs)"
        else:
            status_msg += f" | Jobs: {COLLECTION_NAME} (will be created)"
        if company_collection_exists:
            status_msg += f" | Companies: {COMPANY_COLLECTION_NAME} ({company_count} docs)"
        else:
            status_msg += f" | Companies: {COMPANY_COLLECTION_NAME} (will be created)"
        
        return True, status_msg
    except Exception as e:
        return False, f"❌ Connection failed: {str(e)}"

