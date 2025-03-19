import os
from typing import List, Optional, Dict, Any
import lancedb
from lancedb.pydantic import LanceModel, Vector
import logging
import time
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import numpy as np
import traceback
from .tokenizer import Tokenizer

# database path for KBManagerApp
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "lancedb"
api_path = Path(__file__).resolve().parent.parent / '.env'

load_dotenv(api_path)  
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Maximum tokens for OpenAI embeddings
MAX_TOKENS = 8191

class OpenAIEmbeddings:    
    def __init__(self, model_name: str = "text-embedding-3-large"):
        """
        Initialize the OpenAI embeddings class
        
        Args:
            model_name: The OpenAI embedding model to use
        """
        self.model_name = model_name
        self.max_tokens = MAX_TOKENS
        
        self.api_key = os.getenv('OPENAI_API_KEY')
        # if not self.api_key:
        #     logger.warning("OpenAI API key not found in environment variables")
        #     logger.info("Checking for API key in common locations...")
        #     env_paths = [
        #         '.env',
        #         Path(Path(__file__).resolve().parent.parent, '.env'),
        #         Path(Path(__file__).resolve().parent.parent, 'data', '.env'),
        #         Path(os.path.expanduser('~'), '.env')
        #     ]
        #     for env_path in env_paths:
        #         logger.info(f"Trying to load .env from: {env_path}")
        #         load_dotenv(env_path)
        #         self.api_key = os.getenv('OPENAI_API_KEY')
        #         if self.api_key:
        #             logger.info(f"Found API key in {env_path}")
        #             break
        
        if self.api_key:
            logger.info(f"Initializing OpenAI client with API key for model {model_name}")
            self.client = OpenAI(api_key=self.api_key)
            logger.info("OpenAI client initialized successfully")
        else:
            logger.error("No OpenAI API key found, embeddings will not work")
            self.client = None
            
        self.tokenizer = Tokenizer(
            remove_stopwords=False,  # Keep stopwords for embeddings
            remove_punctuation=False,  # Keep punctuation for embeddings
            lowercase=True  # Convert to lowercase
        )
        
        if model_name == "text-embedding-3-small":
            self.dimensions = 1536
        elif model_name == "text-embedding-3-large":
            self.dimensions = 3072
        elif model_name == "text-embedding-ada-002":
            self.dimensions = 1536
        else:
            self.dimensions = 3072
            
        logger.info(f"OpenAI embeddings initialized with {self.dimensions} dimensions and max tokens {self.max_tokens}")
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Get embeddings for a text using OpenAI API
        
        Args:
            text: The text to embed
            
        Returns:
            List of embedding values
        """
        if not self.client:
            raise ValueError("OpenAI client not initialized - API key missing")
        
        processed_text = self.tokenizer.preprocess_for_embedding(text)
        
        try:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=processed_text,
                encoding_format="float",
                dimensions=self.dimensions
            )
            
            embedding = response.data[0].embedding
            return embedding
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}")
            return [0.0] * self.dimensions
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts in a batch
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not self.client:
            raise ValueError("OpenAI client not initialized - API key missing")
        
        processed_texts = [self.tokenizer.preprocess_for_embedding(text) for text in texts]
        
        try:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=processed_texts,
                encoding_format="float",
                dimensions=self.dimensions
            )
            
            embeddings = [data.embedding for data in response.data]
            return embeddings
        except Exception as e:
            logger.error(f"Error getting batch embeddings: {str(e)}")
            return [[0.0] * self.dimensions for _ in range(len(texts))]

def verify_openai_embeddings():
    """Verify that the OpenAI embeddings connection works"""
    try:
        logger.info("Verifying OpenAI embeddings connection...")
        start_time = time.time()
        embeddings = OpenAIEmbeddings()
        if not embeddings.client:
            logger.error("OpenAI client not initialized")
            return False
            
        temp_db_path = Path("temp_verify_db")
        temp_db_path.mkdir(exist_ok=True)
        
        try:
            db = lancedb.connect(temp_db_path)
            class TestDoc(LanceModel):
                text: str
                vector: Vector(embeddings.dimensions)
                
            try:
                table = db.create_table("test", schema=TestDoc)
                test_text = "This is a test document to verify OpenAI embeddings"
                embedding = embeddings.get_embedding(test_text)
                
                table.add([{"text": test_text, "vector": embedding}])
                
                logger.info(f"OpenAI embeddings verified in {time.time() - start_time:.2f} seconds")
                return True
            except Exception as e:
                logger.error(f"Error testing embeddings: {str(e)}")
                logger.error(traceback.format_exc())
                return False
        finally:
            import shutil
            if temp_db_path.exists():
                shutil.rmtree(temp_db_path)
    except Exception as e:
        logger.error(f"Error verifying OpenAI embeddings: {str(e)}")
        logger.error(traceback.format_exc())
        return False

class KnowledgeBase:
    def __init__(self, db_uri: str = None, table_name: str = "documents", create_if_not_exists: bool = True):
        """
        Initialize the Knowledge Base
        
        Args:
            db_uri: URI to the LanceDB database
            table_name: Name of the table to use for documents
            create_if_not_exists: Whether to create a new table if it doesn't exist.
                                 If False and the table doesn't exist, an error will be raised.
        """
        logger.info("Initializing Knowledge Base with OpenAI embeddings...")
        if not verify_openai_embeddings():
            raise RuntimeError("Failed to verify OpenAI embeddings connection")
            
        if db_uri is None:
            db_uri = str(DEFAULT_DB_PATH)
        
        logger.info(f"Connecting to database at: {db_uri}")
        start_time = time.time()
        self.db = lancedb.connect(db_uri)
        logger.info(f"Connected to database in {time.time() - start_time:.2f} seconds")
        
        logger.info("Initializing OpenAI embeddings...")
        start_time = time.time()
        self.embeddings = OpenAIEmbeddings()
        logger.info(f"Initialized OpenAI embeddings in {time.time() - start_time:.2f} seconds")
        
        self.tokenizer = Tokenizer(
            remove_stopwords=False,  # Keep stopwords for embeddings
            remove_punctuation=False,  # Keep punctuation for embeddings
            lowercase=True  # Convert to lowercase
        )
        
        class Document(LanceModel):
            text: str
            vector: Vector(self.embeddings.dimensions)
            source: str
            title: Optional[str] = None

        self.Document = Document
        self.table_name = table_name
        
        start_time = time.time()
        table_names = self.db.table_names()
        logger.info(f"Retrieved table names in {time.time() - start_time:.2f} seconds: {table_names}")
        
        if self.table_name in table_names:
            try:
                logger.info(f"Opening existing {self.table_name} table...")
                start_time = time.time()
                self.table = self.db.open_table(self.table_name)
                logger.info(f"Opened {self.table_name} table in {time.time() - start_time:.2f} seconds")
                
                table_schema = self.table.schema
                logger.info(f"Table schema: {table_schema}")
                
                vector_field = None
                for field in table_schema:
                    if field.name == "vector":
                        vector_field = field
                        break
                
                # Check if the dimensions match
                if vector_field:
                    vector_dimensions = vector_field.type.list_size
                    logger.info(f"Table vector dimensions: {vector_dimensions}, current dimensions: {self.embeddings.dimensions}")
                    
                    if vector_dimensions != self.embeddings.dimensions:
                        logger.warning(f"Vector dimensions mismatch: table has {vector_dimensions}, but model has {self.embeddings.dimensions}")
                        # Instead of creating a new table, raise an exception to prevent accidental data loss
                        raise RuntimeError(f"Vector dimensions mismatch: table has {vector_dimensions}, but model has {self.embeddings.dimensions}. Use a model with matching dimensions.")
                else:
                    logger.warning("Could not determine vector dimensions from schema")
                    # Instead of creating a new table, raise an exception
                    raise RuntimeError("Could not determine vector dimensions from schema. Please check the database structure.")
                
                try:
                    count = self.table.count_rows()
                    logger.info(f"{self.table_name} table has {count} rows")
                except Exception as e:
                    logger.error(f"Error getting row count: {str(e)}")
            except Exception as e:
                logger.error(f"Error opening existing table: {str(e)}")
                logger.error(traceback.format_exc())
                raise RuntimeError(f"Error opening existing table: {str(e)}. Please ensure database compatibility.")
        else:
            if create_if_not_exists:
                logger.info(f"Creating new {self.table_name} table...")
                start_time = time.time()
                self.table = self.db.create_table(self.table_name, schema=self.Document)
                logger.info(f"Created {self.table_name} table in {time.time() - start_time:.2f} seconds")
            else:
                logger.error(f"Table {self.table_name} does not exist and create_if_not_exists is False")
                raise RuntimeError(f"Table {self.table_name} does not exist and create_if_not_exists is False. Please create the table first.")

    def add_document(self, text: str, source: str, title: Optional[str] = None) -> bool:
        """Add a document to the knowledge base"""
        try:
            logger.info(f"Adding document to {self.table_name}: {title or 'Untitled'}")
            
            processed_text = self.tokenizer.preprocess_for_embedding(text)
            
            start_time = time.time()
            embedding = self.embeddings.get_embedding(processed_text)
            logger.info(f"Generated embedding in {time.time() - start_time:.2f} seconds")
            
            start_time = time.time()
            self.table.add([{
                "text": text,
                "vector": embedding,
                "source": source,
                "title": title
            }])
            logger.info(f"Document added to {self.table_name} in {time.time() - start_time:.2f} seconds")
            return True
        except Exception as e:
            logger.error(f"Error adding document: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def search(self, query: str, limit: int = 5) -> List[dict]:
        """Search the knowledge base"""
        try:
            logger.info(f"Searching in {self.table_name} for: {query}")
            
            processed_query = self.tokenizer.preprocess_for_embedding(query)
            
            # Get query embedding and then search database
            start_time = time.time()
            query_embedding = self.embeddings.get_embedding(processed_query)
            logger.info(f"Generated query embedding in {time.time() - start_time:.2f} seconds")
            start_time = time.time()
            results = self.table.search(query_embedding).limit(limit).to_pandas()
            logger.info(f"Search completed in {time.time() - start_time:.2f} seconds")
            logger.info(f"Found {len(results)} results in {self.table_name}")
            
            formatted_results = []
            for _, row in results.iterrows():
                formatted_results.append({
                    "text": row["text"],
                    "score": float(row["_distance"]),
                    "source": row["source"],
                    "title": row["title"] if "title" in row and row["title"] else None
                })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching {self.table_name}: {str(e)}")
            logger.error(traceback.format_exc())
            return []

    def get_all_documents(self) -> List[dict]:
        """Get all documents in the knowledge base"""
        try:
            logger.info("Retrieving all documents")
            return self.table.to_pandas().to_dict('records')
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base"""
        try:
            stats = {
                "table_name": self.table_name,
                "row_count": self.table.count_rows(),
                "vector_dimensions": self.embeddings.dimensions,
                "model_name": self.embeddings.model_name,
                "max_tokens": self.embeddings.max_tokens
            }
            return stats
        except Exception as e:
            logger.error(f"Error getting stats for {self.table_name}: {str(e)}")
            return {
                "table_name": self.table_name,
                "error": str(e)
            }

# Test usage
if __name__ == "__main__":
    try:
        kb = KnowledgeBase()
        logger.info("Knowledge base initialized successfully!")
        
        test_doc = "This is a test document about knowledge bases."
        success = kb.add_document(test_doc, source="test", title="Test Document")
        logger.info(f"Test document added: {success}")
        
        results = kb.search("knowledge base")
        logger.info("\nSearch results:")
        for result in results:
            logger.info(f"- {result['text'][:100]}...")
            
        logger.info("\nAll tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        logger.error(traceback.format_exc())