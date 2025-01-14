import json
import os
from datetime import datetime
from elasticsearch import Elasticsearch, helpers

def transform_data(file_path):
    """
    Transform raw JSON data into a format suitable for Elasticsearch.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Extract and transform required fields
    transformed_data = {
        "id": data.get("id"),
        "title": data.get("title"),
        "url": data.get("url"),
        "score": data.get("score"),
        "timestamp": datetime.utcfromtimestamp(data.get("time", 0)).isoformat()
    }
    return transformed_data

def bulk_insert_to_elasticsearch(es, index_name, docs):
    """
    Insert multiple documents into Elasticsearch using the bulk API.
    """
    actions = [
        {
            "_index": index_name,
            "_id": doc["id"],
            "_source": doc,
        }
        for doc in docs
    ]
    helpers.bulk(es, actions)
    print(f"Inserted {len(docs)} documents into Elasticsearch index '{index_name}'.")

def main():
    # Elasticsearch client
    es = Elasticsearch("http://localhost:9200")

    # Elasticsearch index name
    index_name = "hackernews"

    # Directory containing raw JSON files
    raw_data_dir = "./raw"

    # Transform and insert documents
    documents = []
    for file_name in os.listdir(raw_data_dir):
        if file_name.endswith(".json"):
            file_path = os.path.join(raw_data_dir, file_name)
            print(f"Processing {file_name}...")
            transformed_doc = transform_data(file_path)
            documents.append(transformed_doc)

    if documents:
        bulk_insert_to_elasticsearch(es, index_name, documents)

if __name__ == "__main__":
    main()
