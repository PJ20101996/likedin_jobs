"""
MongoDB Connection Helper
Handles database connection and operations for storing LinkedIn job data.
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from datetime import datetime
import json


# MongoDB connection string
MONGO_CONNECTION_STRING = "mongodb+srv://jagadishpagolu1996:Ammananna%40143@cluster0.cwibfnc.mongodb.net/"

# Database and Collection names
DATABASE_NAME = "Kinnective_testing"
COLLECTION_NAME = "linkedin_jobs"


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
        
        # Check if collection exists
        collection_names = db.list_collection_names()
        collection_exists = COLLECTION_NAME in collection_names
        
        # Get collection count if it exists
        count = 0
        if collection_exists:
            collection = db[COLLECTION_NAME]
            count = collection.count_documents({})
        
        client.close()
        
        status_msg = f"✅ Connected | Database: {DATABASE_NAME}"
        if collection_exists:
            status_msg += f" | Collection: {COLLECTION_NAME} ({count} documents)"
        else:
            status_msg += f" | Collection: {COLLECTION_NAME} (will be created)"
        
        return True, status_msg
    except Exception as e:
        return False, f"❌ Connection failed: {str(e)}"

