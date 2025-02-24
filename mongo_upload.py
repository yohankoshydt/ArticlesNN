from pymongo import MongoClient
from pymongo import MongoClient, TEXT
import numpy as np
from inf import encode_text
from dotenv import load_dotenv
import os

load_dotenv(override=True)

# MongoDB Configuration
MONGO_URI = rf'{os.getenv('MONGO_URI')}'
print(MONGO_URI)
DB_NAME = "vectors"
COLLECTION_NAME = "pubmed"


client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]




def upload_to_mongo(article_data):
    """
    Uploads a single article document to MongoDB.
    If the document exists, it updates it.
    If 'molecule' has a different value, it appends the new value to a list.
    """
    try:
        # Connect to MongoDB
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]

        # Identify the document by PubMed ID
        filter_query = {"pubmed ID": article_data["pubmed ID"]}
        existing_doc = collection.find_one(filter_query)

        if existing_doc:
            # If 'molecule' exists in the old document, check for changes
            if "molecule" in existing_doc:
                old_molecule = existing_doc["molecule"]
                new_molecule = article_data.get("molecule", None)

                if new_molecule and new_molecule != old_molecule:
                    # Append to 'molecule_history' if different
                    molecule_history = existing_doc.get("molecule_history", [])
                    
                    # Ensure old molecule is stored
                    if old_molecule not in molecule_history:
                        molecule_history.append(old_molecule)

                    # Ensure new molecule is stored
                    if new_molecule not in molecule_history:
                        molecule_history.append(new_molecule)

                    article_data["molecule_history"] = molecule_history
                    print(f"[INFO] Appended new molecule value: {new_molecule}")

            # Perform the update with upsert
            update_query = {"$set": article_data}
            result = collection.update_one(filter_query, update_query, upsert=True)
            
            print(f"[INFO] Updated existing article: {article_data['pubmed ID']}")

        else:
            # Insert new document
            result = collection.insert_one(article_data)
            print(f"[INFO] Inserted new article: {article_data['pubmed ID']}")

    except Exception as e:
        print(f"[ERROR] Failed to upload to MongoDB: {e}")




def vector_search(query_vector, k=5):
    """
    Perform a vector similarity search in MongoDB.
    
    :param query_vector: The embedding vector for search (list or numpy array)
    :param k: Number of top results to retrieve
    :return: List of matching documents sorted by vector similarity
    """
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",  # Your MongoDB vector index name
                "path": "article encoding",  # Field storing vector embeddings
                "queryVector": query_vector.tolist() if isinstance(query_vector, np.ndarray) else query_vector,
                "numCandidates": 100,  # More candidates improve recall
                "limit": k,
                "metric": "cosine"  # Can be "euclidean", "dotProduct", or "cosine"
            }
        },
        {
            "$project": {
                "vector_similarity": {"$meta": "vectorSearchScore"},  # Include similarity score
                "title": 1,
                "abstract": 1,
                "doi": 1,
                "pubmed ID": 1
            }
        },
        {
            "$sort": {
                "vector_similarity": -1  # Higher similarity first
            }
        }
    ]

    results = collection.aggregate(pipeline)

    results_list = list(results)

    print("[DEBUG] Number of results found:", len(results_list)) 
    return results_list # Execute the query








def search_mongo(query):
    """Search MongoDB for documents where query appears in 'title' or 'abstract'."""
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    print("[DEBUG] Running regex-based search query:", query)

    results = collection.find(
        {"$text": {"$search": query}},
        {"score": {"$meta": "textScore"}}  # Get the relevance score
    ).sort("score", {"$meta": "textScore"})  # Sort by relevance
    # Sort by relevance  # Limit results to avoid too much data

    results_list = list(results)

    print("[DEBUG] Number of results found:", len(results_list))  # Print count
    return results_list

#query = 'What is the mode of action of amylin in controlling body weight?'


# collection.create_index(
#     [("title", "text"), ("abstract", "text")],
#     weights={"title": 10, "abstract": 5}  # Title has higher priority than abstract
# )

# results = vector_search(encode_text(query, 'query'))




