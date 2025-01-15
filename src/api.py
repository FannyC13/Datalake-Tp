from fastapi import FastAPI, Query, HTTPException
from datetime import datetime
import boto3
import pymysql
from typing import Optional, List
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from botocore.exceptions import BotoCoreError, NoCredentialsError
from pydantic import BaseModel

app = FastAPI()


S3_ENDPOINT_URL = "http://localhost:4566"
s3_client = boto3.client("s3", endpoint_url=S3_ENDPOINT_URL)

MYSQL_HOST = "localhost"
MYSQL_PORT = 3307
MYSQL_USER = "root"
MYSQL_PASSWORD = "root"
MYSQL_DATABASE = "staging"

MONGODB_HOST = "localhost"
MONGODB_PORT = 27017
MONGODB_DATABASE = "curated"
MONGODB_COLLECTION = "wikitext"

client = MongoClient(MONGODB_HOST, MONGODB_PORT)
db = client[MONGODB_DATABASE]
collection = db[MONGODB_COLLECTION]

@app.get("/health")
async def health_check():
    health_status = {
        "API Status": "Online",
        "Timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "Connections Status": {}
    }
    try:
        s3_client = boto3.client("s3", endpoint_url=S3_ENDPOINT_URL)
        s3_client.list_buckets()
        health_status["Connections Status"]["S3"] = "Connected"
    except Exception as e:
        health_status["Connections Status"]["S3"] = f"Error: {str(e)}"

    try:
        connection = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        connection.close()
        health_status["Connections Status"]["MySQL"] = "Connected"
    except Exception as e:
        health_status["Connections Status"]["MySQL"] = f"Error: {str(e)}"

    try:
        client = MongoClient(MONGODB_HOST, MONGODB_PORT)
        client.admin.command('ping')
        health_status["Connections Status"]["MongoDB"] = "Connected"
    except Exception as e:
        health_status["Connections Status"]["MongoDB"] = f"Error: {str(e)}"

    return health_status


@app.get("/raw/")
async def get_raw_data(
    prefix: str = Query(default="", description="Préfixe pour filtrer les objets dans le bucket"),
    limit: int = Query(default=10, ge=1, description="Nombre maximum d'objets à retourner")
):
    """
    Endpoint pour récupérer les données brutes dans le bucket S3.
    - `prefix` : Filtrer les objets avec un préfixe donné.
    - `limit` : Limiter le nombre d'éléments retournés.
    """
    try:
        S3_BUCKET_NAME = "raw"
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix)
        
        if "Contents" not in response:
            return {"message": "Aucun objet trouvé dans le bucket", "data": []}
        
        objects = response["Contents"][:limit]
        result = []
        for obj in objects:
            key = obj["Key"]
            object_data = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=key)
            content = object_data["Body"].read().decode("utf-8")
            result.append({"key": key, "content": content})

        return {"message": "Données récupérées avec succès", "data": result}

    except NoCredentialsError:
        return {"error": "Les informations d'identification pour S3 ne sont pas configurées."}
    except BotoCoreError as e:
        return {"error": f"Erreur avec le client S3: {str(e)}"}
    except Exception as e:
        return {"error": f"Erreur inattendue: {str(e)}"}
    


class SQLQuery(BaseModel):
    query: str

def connect_to_mysql():
    """
    Connecte à la base de données MySQL.
    """
    try:
        connection = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        return connection
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de connexion MySQL: {str(e)}")

@app.get("/staging/")
async def get_staging_data():
    connection = connect_to_mysql()
    try:
        with connection.cursor() as cursor:
            query = f"SELECT * FROM texts LIMIT 10"
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            data = [dict(zip(columns, row)) for row in rows]
        return {"message": "Données récupérées avec succès", "data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lors de l'exécution de la requête: {str(e)}")
    finally:
        connection.close()

@app.post("/staging/query/")
async def execute_sql_query(query: SQLQuery):
    """
    Endpoint pour exécuter une requête SQL personnalisée sur la base de données staging.
    - Requête SQL à fournir dans le corps de la requête sous forme JSON.
    """
    connection = connect_to_mysql()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query.query)
            if cursor.description:
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                data = [dict(zip(columns, row)) for row in rows]
                return {"message": "Requête exécutée avec succès", "data": data}
            else:
                connection.commit()
                return {"message": "Requête exécutée avec succès", "affected_rows": cursor.rowcount}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lors de l'exécution de la requête: {str(e)}")
    finally:
        connection.close()


@app.get("/curated/")
async def get_curated_data(
    limit: int = Query(default=10, ge=1, description="Nombre maximum de documents à retourner"),
    filter_key: Optional[str] = Query(default=None, description="Clé pour filtrer les documents"),
    filter_value: Optional[str] = Query(default=None, description="Valeur pour filtrer les documents")
):
    """
    Endpoint pour récupérer les documents de la collection MongoDB.
    - `limit` : Nombre maximum de documents à retourner.
    - `filter_key` : Clé à utiliser pour le filtre (facultatif).
    - `filter_value` : Valeur à utiliser pour le filtre (facultatif).
    """
    try:
        # Construction du filtre
        query_filter = {}
        if filter_key and filter_value:
            query_filter[filter_key] = filter_value

        # Récupération des documents
        documents = list(collection.find(query_filter).limit(limit))
        for doc in documents:
            doc["_id"] = str(doc["_id"]) 

        return {"message": "Données récupérées avec succès", "data": documents}

    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Erreur MongoDB : {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur inattendue : {str(e)}")
