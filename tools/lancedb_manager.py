import lancedb
import pandas as pd
import os
from typing import List, Dict, Any, Optional, Union
import uuid
import json
import pyarrow as pa
import datetime
import logging
import time
from pathlib import Path
import sys

parent_dir = str(Path(__file__).parent.parent.absolute())
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from tools.knowledge_base import OpenAIEmbeddings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCHEMAS = {
    "categories": {
        "id": "string",
        "name": "string",
        "description": "string"
    },
    "topics": {
        "id": "string",
        "category_id": "string",
        "name": "string",
        "description": "string"
    },
    "entries": {
        "id": "string",
        "topic_id": "string",
        "title": "string",
        "content": "string",
        "tags_json": "string",  
        "created_at": "string",
        "updated_at": "string",
        "vector": "list<float>",  
        "source": "string"      
    }
}

class LanceDBManager:
    TEXT_COLUMNS_FOR_INDEX = {
        "entries": ["title", "content"]
    }
    
    VECTOR_COLUMNS_FOR_INDEX = {
        "entries": ["vector"]
    }
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db = lancedb.connect(db_path)
        
        logger.info("Initializing OpenAI embeddings for LanceDBManager...")
        start_time = time.time()
        self.embeddings = OpenAIEmbeddings()
        logger.info(f"Initialized OpenAI embeddings in {time.time() - start_time:.2f} seconds")
        
        self._ensure_table_exists()
    
    def get_available_tables(self) -> List[str]:
        """Get a list of available tables in the database."""
        return self.db.table_names()
        
    def count_records(self, table_name: str) -> int:
        """Count the number of records in a table."""
        if table_name not in self.db.table_names():
            return 0
        
        table = self.db.open_table(table_name)
        return table.count_rows()
        
    def add_to_table(self, table_name: str, data: List[Dict[str, Any]]) -> None:
        """Add data to a table."""
        if table_name not in self.db.table_names():
            schema = self._get_pa_schema(table_name)
            table = self.db.create_table(table_name, schema=schema)
        else:
            table = self.db.open_table(table_name)
            
        if len(data) > 0:
            df = pd.DataFrame(data)
            pa_table = pa.Table.from_pandas(df)
            table.add(pa_table)
            self._create_or_update_inverted_indices(table_name)
            
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a list of texts."""
        embeddings = []
        for text in texts:
            embedding = self.embeddings.get_embedding(text)
            embeddings.append(embedding)
        return embeddings
        
    def create_inverted_index(self, table_name: str, column_name: str) -> bool:
        """Create a full-text search index for text search."""
        logger.info(f"Creating full-text search index for {table_name}.{column_name}")
        if table_name not in self.db.table_names():
            logger.error(f"Table {table_name} does not exist")
            return False
            
        try:
            table = self.db.open_table(table_name)
            table_schema = table.schema
            if column_name not in [field.name for field in table_schema]:
                logger.error(f"Column {column_name} does not exist in table {table_name}")
                return False
                
            start_time = time.time()
            table.create_fts_index(column_name)
            logger.info(f"Created full-text search index for {table_name}.{column_name} in {time.time() - start_time:.2f} seconds")
            return True
        except Exception as e:
            logger.error(f"Error creating full-text search index for {table_name}.{column_name}: {str(e)}")
            return False
            
    def create_vector_index(self, table_name: str, column_name: str) -> bool:
        """Create a vector index (IVF_PQ) for efficient vector search."""
        logger.info(f"Creating vector index for {table_name}.{column_name}")
        if table_name not in self.db.table_names():
            logger.error(f"Table {table_name} does not exist")
            return False
            
        try:
            table = self.db.open_table(table_name)
            table_schema = table.schema
            if column_name not in [field.name for field in table_schema]:
                logger.error(f"Column {column_name} does not exist in table {table_name}")
                return False
                
            table_size = table.count_rows()
            
            if table_size < 5:
                logger.warning(f"Table {table_name} has fewer than 5 rows, skipping vector index creation for now")
                return False
                
            # Calculate optimal parameters based on dimensions and table size
            if self.embeddings.dimensions > 1000:
                # For high-dimensional vectors like OpenAI's
                # More partitions for larger datasets, but at least 2 for testing
                num_partitions = max(int(table_size ** 0.5), 2) 
                # For high dimensions, we use more sub-vectors, but at least 4 for testing
                num_sub_vectors = min(max(int(self.embeddings.dimensions / 100), 4), 96)  # At least 4, max 96
            else:
                # For lower-dimensional vectors
                num_partitions = max(int(table_size ** 0.5), 2)  
                num_sub_vectors = max(int(self.embeddings.dimensions / 8), 4)  
            
            # Create the vector index, use cosine similarity for text embeddings
            start_time = time.time()
            logger.info(f"Creating IVF_PQ index with {num_partitions} partitions and {num_sub_vectors} sub-vectors")
            table.create_index(
                column_name,
                distance_type="cosine", 
                num_partitions=num_partitions,
                num_sub_vectors=num_sub_vectors
            )
            logger.info(f"Created vector index for {table_name}.{column_name} in {time.time() - start_time:.2f} seconds")
            return True
        except Exception as e:
            logger.error(f"Error creating vector index for {table_name}.{column_name}: {str(e)}")
            return False
    
    def _create_or_update_inverted_indices(self, table_name: str) -> None:
        """Create or update all indices for a table (both text and vector)."""
        if table_name in self.TEXT_COLUMNS_FOR_INDEX:
            for column_name in self.TEXT_COLUMNS_FOR_INDEX[table_name]:
                self.create_inverted_index(table_name, column_name)
        
        if table_name in self.VECTOR_COLUMNS_FOR_INDEX:
            for column_name in self.VECTOR_COLUMNS_FOR_INDEX[table_name]:
                self.create_vector_index(table_name, column_name)
    
    def _ensure_table_exists(self, tables: List[str] = None):
        """Ensure that all required tables exist in the database."""
        if tables is None:
            tables = list(SCHEMAS.keys())
            
        for table in tables:
            if table not in self.db.table_names():
                schema = self._get_pa_schema(table)
                self.db.create_table(table, schema=schema)
                self._create_or_update_inverted_indices(table)
            else:
                self._create_or_update_inverted_indices(table)

    def _get_pa_schema(self, table_name):
        if table_name not in SCHEMAS:
            raise ValueError(f"Unknown table: {table_name}")
        
        fields = []
        for name, type_str in SCHEMAS[table_name].items():
            if type_str == "list<float>" and name == "vector":
                vector_field = pa.field(name, pa.list_(pa.float32(), self.embeddings.dimensions))
                fields.append(vector_field)
            else:
                fields.append(pa.field(name, pa.string()))
                
        return pa.schema(fields)
    
    def create_category(self, name: str, description: str):
        """Create a new category to the categories table."""
        categories_table = self.db.open_table("categories")
        existing = categories_table.to_pandas()
        if len(existing) > 0 and name in existing["name"].values:
            raise ValueError(f"Category '{name}' already exists")

        category_id = str(uuid.uuid4()) 

        category_data = pa.Table.from_arrays(
            [
                pa.array([category_id], type=pa.string()),
                pa.array([name], type=pa.string()),
                pa.array([description], type=pa.string())
            ],
            schema=self._get_pa_schema("categories")
        )

        categories_table.add(category_data)
        return category_id
    
    def get_categories(self):
        """Get all categories from the categories table."""
        table = self.db.open_table("categories")
        return table.to_pandas()
    
    def get_category(self, category_id: str):
        """Get a single category from the categories table by category_id."""
        try:
            categories_table = self.db.open_table("categories")
            return categories_table.search().where(f"id = '{category_id}'").to_pandas()
        except Exception as e:
            print(f"Error getting category: {e}")
            return None
        
    def update_category(self, category_id: str, name: Optional[str] = None, description: Optional[str] = None):
        """Update a category in the categories table."""
        table = self.db.open_table("categories")
        existing = table.search().where(f"id = '{category_id}'").to_pandas()
        if len(existing) == 0:
            raise ValueError(f"Category with id {category_id} not found")
        
        current = existing.iloc[0]
        updated_name = name if name else current["name"]
        category_data = pa.Table.from_arrays(
            [
                pa.array([category_id], type=pa.string()),
                pa.array([updated_name], type=pa.string()),
                pa.array([description], type=pa.string())
            ],
            schema=self._get_pa_schema("categories")
        )
        
        table.delete(f"id = '{category_id}'")
        table.add(category_data)
        return True
    
    def delete_category(self, category_id: str):
        """Delete a category from the categories table.
        Also deletes all topics, and entries associated with the category.
        """
        try:
            topics_table = self.db.open_table("topics")
            category_topics = topics_table.search().where(f"category_id = '{category_id}'").to_pandas()
            topic_ids = category_topics["id"].tolist()

            entries_table = self.db.open_table("entries")
            topic_ids_str = "(" + ", ".join([f"'{id}'" for id in topic_ids]) + ")" if topic_ids else "()"
            if topic_ids:
                topic_entries = entries_table.search().where(f"topic_id IN {topic_ids_str}").to_pandas()
                entry_ids = topic_entries["id"].tolist()

                for entry_id in entry_ids:
                    entries_table.delete(f"id = '{entry_id}'")
            for topic_id in topic_ids:
                topics_table.delete(f"id = '{topic_id}'")
            
            categories_table = self.db.open_table("categories")
            categories_table.delete(f"id = '{category_id}'")
            return True
        
        except Exception as e:
            print(f"Error deleting category: {e}")
            return False
    
    def create_topic(self, category_id: str, name: Optional[str] = None, description: Optional[str] = None):
        """Create a new topic to the topics table under a given category."""
        category_table = self.db.open_table("categories")
        category = category_table.search().where(f"id = '{category_id}'").to_pandas()
        if len(category) == 0:
            raise ValueError(f"Category with id {category_id} not found")
        
        topic_table = self.db.open_table("topics")
        existing = topic_table.search().where(f"category_id = '{category_id}'").to_pandas()
        if len(existing) > 0 and name in existing["name"].values:
            raise ValueError(f"Topic '{name}' already exists")
        
        topic_id = str(uuid.uuid4())
        topic_data = pa.Table.from_arrays(
            [
                pa.array([topic_id], type=pa.string()),
                pa.array([category_id], type=pa.string()),
                pa.array([name], type=pa.string()),
                pa.array([description], type=pa.string())
            ],
            schema=self._get_pa_schema("topics")
        )

        topic_table.add(topic_data)
        return topic_id

    def get_topics(self, category_id: Optional[str] = None):
        """Get all topics, optionally filtered by category_id."""
        if category_id: 
            return self.db.open_table("topics").search().where(f"category_id = '{category_id}'").to_pandas()
        return self.db.open_table("topics").to_pandas()
    
    def get_topic(self, topic_id: str):
        """Get a single topic from the topics table given a topic_id."""
        try:
            return self.db.open_table("topics").search().where(f"id = '{topic_id}'").to_pandas()
        except Exception as e:
            print(f"Error getting topic: {e}")
            return None
    
    def update_topic(self, topic_id: str, name: Optional[str] = None, description: Optional[str] = None):
        """Update a topic in the topics table."""
        topic_table = self.db.open_table("topics")
        existing = topic_table.search().where(f"id = '{topic_id}'").to_pandas()
        if len(existing) == 0:
            raise ValueError(f"Topic with id {topic_id} not found")
        
        current = existing.iloc[0]
        updated_name = name if name else current["name"]
        updated_description = description if description else current["description"]

        topic_data = pa.Table.from_arrays(
            [
                pa.array([topic_id], type=pa.string()),
                pa.array([current["category_id"]], type=pa.string()),
                pa.array([updated_name], type=pa.string()),
                pa.array([updated_description], type=pa.string())
            ],
            schema=self._get_pa_schema("topics")
        )

        topic_table.delete(f"id = '{topic_id}'")
        topic_table.add(topic_data)
        return True
    
    def delete_topic(self, topic_id: str):
        """Delete delete a topic and all associated entries."""
        try:
            entries_table = self.db.open_table("entries")
            topic_entries = entries_table.search().where(f"topic_id = '{topic_id}'").to_pandas()
            entry_ids = topic_entries["id"].tolist()
            for entry_id in entry_ids:
                entries_table.delete(f"id = '{entry_id}'")
            
            topics_table = self.db.open_table("topics")
            topics_table.delete(f"id = '{topic_id}'")
            return True
        
        except Exception as e:
            print(f"Error deleting topic: {e}")
            return False
    
    def create_entry(self, topic_id: str, title: Optional[str] = None, content: Optional[str] = None, 
                    tags: Optional[List[str]] = None, source: str = "manual", generate_embedding: bool = True):
        """Create a new entry to the entries table under a given topic."""
        topic_table = self.db.open_table("topics")
        topic = topic_table.search().where(f"id = '{topic_id}'").to_pandas()
        if len(topic) == 0:
            raise ValueError(f"Topic with id {topic_id} not found")
        
        entries_table = self.db.open_table("entries")
        existing = entries_table.search().where(f"topic_id = '{topic_id}'").to_pandas()
        if len(existing) > 0 and title in existing["title"].values:
            raise ValueError(f"Entry with title '{title}' already exists")
        
        tags_json = json.dumps(tags) if tags else json.dumps([])
        
        vector = None
        if generate_embedding and content:
            try:
                logger.info(f"Generating embedding for entry: {title}")
                start_time = time.time()
                vector = self.embeddings.get_embedding(content)
                logger.info(f"Generated embedding in {time.time() - start_time:.2f} seconds")
            except Exception as e:
                logger.error(f"Error generating embedding: {str(e)}")
                vector = [0.0] * self.embeddings.dimensions
        else:
            vector = [0.0] * self.embeddings.dimensions
        
        entry_id = str(uuid.uuid4())
        
        arrays = [
            pa.array([entry_id], type=pa.string()),
            pa.array([topic_id], type=pa.string()),
            pa.array([title], type=pa.string()),
            pa.array([content], type=pa.string()),
            pa.array([tags_json], type=pa.string()),
            pa.array([datetime.datetime.now().isoformat()], type=pa.string()),
            pa.array([datetime.datetime.now().isoformat()], type=pa.string()),
            pa.array([vector], type=pa.list_(pa.float32())),
            pa.array([source], type=pa.string())
        ]
        
        schema_fields = [
            pa.field("id", pa.string()),
            pa.field("topic_id", pa.string()),
            pa.field("title", pa.string()),
            pa.field("content", pa.string()),
            pa.field("tags_json", pa.string()),
            pa.field("created_at", pa.string()),
            pa.field("updated_at", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), self.embeddings.dimensions)),
            pa.field("source", pa.string())
        ]
        
        entry_schema = pa.schema(schema_fields)
        entry_data = pa.Table.from_arrays(arrays, schema=entry_schema)

        entries_table.add(entry_data)
        
        self._create_or_update_inverted_indices("entries")
        
        return entry_id
    
    def get_entries(self, topic_id: Optional[str] = None):
        """Get all entries, optionally filtered by topic_id."""
        if topic_id:
            return self.db.open_table("entries").search().where(f"topic_id = '{topic_id}'").to_pandas()
        return self.db.open_table("entries").to_pandas()
    
    def get_entry(self, entry_id: str):
        """Get a single entry from the entries table given an entry_id."""
        try:
            return self.db.open_table("entries").search().where(f"id = '{entry_id}'").to_pandas()
        except Exception as e:
            print(f"Error getting entry: {e}")
            return None
    
    def update_entry(self, entry_id: str, title: Optional[str] = None, content: Optional[str] = None, 
                    tags: Optional[List[str]] = None, source: Optional[str] = None, generate_embedding: bool = True):
        """Update an entry in the entries table."""
        entries_table = self.db.open_table("entries")
        existing = entries_table.search().where(f"id = '{entry_id}'").to_pandas()
        if len(existing) == 0:
            raise ValueError(f"Entry with id {entry_id} not found")
        
        current = existing.iloc[0]
        updated_title = title if title else current["title"]
        updated_content = content if content is not None else current["content"]
        updated_source = source if source is not None else current.get("source", "manual")
        
        if tags is None:
            if isinstance(current["tags_json"], str):
                updated_tags_json = current["tags_json"]
            else:
                updated_tags_json = json.dumps(current["tags_json"] if current["tags_json"] else [])
        else:
            updated_tags_json = json.dumps(tags)
        
        if generate_embedding and content is not None:
            try:
                logger.info(f"Generating updated embedding for entry: {updated_title}")
                start_time = time.time()
                vector = self.embeddings.get_embedding(updated_content)
                logger.info(f"Generated embedding in {time.time() - start_time:.2f} seconds")
            except Exception as e:
                logger.error(f"Error generating embedding: {str(e)}")
                if "vector" in current and current["vector"] is not None:
                    vector = current["vector"]
                else:
                    vector = [0.0] * self.embeddings.dimensions
        else:
            if "vector" in current and current["vector"] is not None:
                vector = current["vector"]
            else:
                vector = [0.0] * self.embeddings.dimensions
        
        arrays = [
            pa.array([entry_id], type=pa.string()),
            pa.array([current["topic_id"]], type=pa.string()),
            pa.array([updated_title], type=pa.string()),
            pa.array([updated_content], type=pa.string()),
            pa.array([updated_tags_json], type=pa.string()),
            pa.array([current["created_at"]], type=pa.string()),
            pa.array([datetime.datetime.now().isoformat()], type=pa.string()),
            pa.array([vector], type=pa.list_(pa.float32())),
            pa.array([updated_source], type=pa.string())
        ]
        
        schema_fields = [
            pa.field("id", pa.string()),
            pa.field("topic_id", pa.string()),
            pa.field("title", pa.string()),
            pa.field("content", pa.string()),
            pa.field("tags_json", pa.string()),
            pa.field("created_at", pa.string()),
            pa.field("updated_at", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), self.embeddings.dimensions)),
            pa.field("source", pa.string())
        ]
        
        entry_schema = pa.schema(schema_fields)
        entry_data = pa.Table.from_arrays(arrays, schema=entry_schema)

        entries_table.delete(f"id = '{entry_id}'")
        entries_table.add(entry_data)
        
        self._create_or_update_inverted_indices("entries")
        
        return True
    
    def delete_entry(self, entry_id: str):
        """Delete an entry from the entries table."""
        entries_table = self.db.open_table("entries")
        entries_table.delete(f"id = '{entry_id}'")
        return True
    
    def search_table_fulltext(self, table_name: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search a table using full-text search.
        
        Args:
            table_name: The name of the table to search
            query: The search query
            limit: Maximum number of results to return
            
        Returns:
            List of entries sorted by relevance
        """
        if table_name not in self.db.table_names():
            logger.error(f"Table {table_name} does not exist")
            return []
        
        table = self.db.open_table(table_name)
        
        has_fts_index = False
        indexed_columns = []
        
        if table_name in self.TEXT_COLUMNS_FOR_INDEX:
            for column_name in self.TEXT_COLUMNS_FOR_INDEX[table_name]:
                try:
                    test_query = table.search(query)
                    test_query.limit(1).to_pandas()
                    has_fts_index = True
                    indexed_columns.append(column_name)
                    logger.info(f"Found FTS index for {table_name}.{column_name}")
                except Exception as e:
                    logger.info(f"No FTS index for {table_name}.{column_name} or error testing it: {str(e)}")
        
        if not has_fts_index:
            logger.warning(f"No FTS indices found for table {table_name}, using vector search as fallback")
            return []
        
        try:
            logger.info(f"Using full-text search for query: {query}")
            start_time = time.time()
            
            results = table.search(query).limit(limit).to_pandas()
            logger.info(f"Full-text search completed in {time.time() - start_time:.2f} seconds")
            
            formatted_results = []
            for _, row in results.iterrows():
                result = row.to_dict()
                
                if "_score" in result:
                    result["score"] = float(result["_score"])
                else:
                    result["score"] = 1.0  # Default score 
                
                if "vector" in result:
                    del result["vector"]
                
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in full-text search: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def search_entries(self, query: str, limit: int = 5, category_id: Optional[str] = None, topic_id: Optional[str] = None):
        """Search entries using vector similarity or full-text search.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            category_id: Optional category ID to filter results
            topic_id: Optional topic ID to filter results
            
        Returns:
            List of entries sorted by relevance
        """
        try:
            logger.info(f"Searching entries for: {query}")
            
            fulltext_results = self.search_table_fulltext("entries", query, limit=limit)
            has_fulltext_results = len(fulltext_results) > 0
            
            if has_fulltext_results and not (category_id or topic_id):
                logger.info(f"Using {len(fulltext_results)} results from full-text search")
        
                topics_table = self.db.open_table("topics")
                topics_df = topics_table.to_pandas()
                
                categories_table = self.db.open_table("categories")
                categories_df = categories_table.to_pandas()
                
                formatted_results = []
                for result in fulltext_results:
                    if "topic_id" in result:
                        topic_info = topics_df[topics_df["id"] == result["topic_id"]].iloc[0] if not topics_df.empty else None
                        
                        category_info = None
                        if topic_info is not None:
                            category_info = categories_df[categories_df["id"] == topic_info["category_id"]].iloc[0] if not categories_df.empty else None
                        
                        result["topic_name"] = topic_info["name"] if topic_info is not None else "Unknown"
                        result["category_id"] = topic_info["category_id"] if topic_info is not None else None
                        result["category_name"] = category_info["name"] if category_info is not None else "Unknown"
                        
                        if "tags_json" in result and not "tags" in result:
                            result["tags"] = json.loads(result["tags_json"]) if result["tags_json"] else []
                    
                    formatted_results.append(result)
                
                return formatted_results
            
            # If full-text search didn't work or filters are applied, 
            # use vector search
            
            start_time = time.time()
            query_embedding = self.embeddings.get_embedding(query)
            logger.info(f"Generated query embedding in {time.time() - start_time:.2f} seconds")
            
            # Search entries table
            entries_table = self.db.open_table("entries")
            search_query = entries_table.search(query_embedding, vector_column_name="vector")
            
            # Apply filters if provided
            if topic_id:
                search_query = search_query.where(f"topic_id = '{topic_id}'")
            elif category_id: 
                topics_table = self.db.open_table("topics")
                topics = topics_table.search().where(f"category_id = '{category_id}'").to_pandas()
                topic_ids = topics["id"].tolist()
                
                if topic_ids:
                    topic_ids_str = "(" + ", ".join([f"'{id}'" for id in topic_ids]) + ")"
                    search_query = search_query.where(f"topic_id IN {topic_ids_str}")
            
            start_time = time.time()
            results = search_query.limit(limit).to_pandas()
            logger.info(f"Vector search completed in {time.time() - start_time:.2f} seconds")
            
            topics_table = self.db.open_table("topics")
            topics_df = topics_table.to_pandas()
            
            categories_table = self.db.open_table("categories")
            categories_df = categories_table.to_pandas()
            
            formatted_results = []
            for _, row in results.iterrows():
                topic_info = topics_df[topics_df["id"] == row["topic_id"]].iloc[0] if not topics_df.empty else None
                category_info = None
                if topic_info is not None:
                    category_info = categories_df[categories_df["id"] == topic_info["category_id"]].iloc[0] if not categories_df.empty else None
                
                formatted_results.append({
                    "id": row["id"],
                    "title": row["title"],
                    "content": row["content"],
                    "score": float(row["_distance"]),
                    "source": row.get("source", "unknown"),
                    "topic_id": row["topic_id"],
                    "topic_name": topic_info["name"] if topic_info is not None else "Unknown",
                    "category_id": topic_info["category_id"] if topic_info is not None else None,
                    "category_name": category_info["name"] if category_info is not None else "Unknown",
                    "tags": json.loads(row["tags_json"]) if row["tags_json"] else []
                })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching entries: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def get_full_hierarchy(self):
        """Get the full hierarchy of categories, topics, and entries."""
        categories = self.get_categories()
        result = []
        
        for _, category in categories.iterrows():
            cat_dict = category.to_dict()
            topics = self.get_topics(category["id"])
            cat_dict["topics"] = []
            
            for _, topic in topics.iterrows():
                topic_dict = topic.to_dict()
                entries = self.get_entries(topic["id"])
                entry_list = []
                for _, entry in entries.iterrows():
                    entry_dict = entry.to_dict()
                    if "tags" not in entry_dict and "tags_json" in entry_dict:
                        entry_dict["tags"] = json.loads(entry_dict["tags_json"])
                    entry_list.append(entry_dict)

                topic_dict["entries"] = entry_list
                cat_dict["topics"].append(topic_dict)
            result.append(cat_dict)
            
        return {"categories": result}

    def check_indices(self, table_name: str) -> Dict[str, List[str]]:
        """Check which indices exist for a given table.
        
        Args:
            table_name: The name of the table to check
            
        Returns:
            Dictionary with keys 'vector_indices' and 'text_indices', each containing a list of column names
        """
        if table_name not in self.db.table_names():
            logger.error(f"Table {table_name} does not exist")
            return {"vector_indices": [], "text_indices": []}
        
        table = self.db.open_table(table_name)
        
        result = {
            "vector_indices": [],
            "text_indices": []
        }

        table_schema = table.schema
        column_names = [field.name for field in table_schema]
        
        if table_name in self.TEXT_COLUMNS_FOR_INDEX:
            for column_name in self.TEXT_COLUMNS_FOR_INDEX[table_name]:
                if column_name not in column_names:
                    continue
                
                try:
                    test_query = "test"  # test the index
                    results = table.search(test_query).limit(1).to_pandas()
                    
                    result["text_indices"].append(column_name)
                    logger.info(f"Found text index for {table_name}.{column_name}")
                except Exception as e:
                    logger.info(f"No text index for {table_name}.{column_name}: {str(e)}")
        
        if table_name in self.VECTOR_COLUMNS_FOR_INDEX:
            for column_name in self.VECTOR_COLUMNS_FOR_INDEX[table_name]:
                if column_name not in column_names:
                    continue
                
                try:
                    vector_dims = self.embeddings.dimensions
                    zero_vector = [0.0] * vector_dims
                    
                    table.search(zero_vector).limit(1).to_pandas()
                    
                    table_size = table.count_rows()
                    if table_size >= 5: 
                        result["vector_indices"].append(column_name)
                        logger.info(f"Found vector index for {table_name}.{column_name}")
                    else:
                        logger.info(f"Table {table_name} has {table_size} rows, not enough for a vector index")
                except Exception as e:
                    logger.info(f"Error checking vector index for {table_name}.{column_name}: {str(e)}")
        
        return result
    
    def optimize_table(self, table_name: str) -> bool:
        """Optimize a table to ensure indices are up-to-date.
        
        This is useful after adding a lot of data to a table, as it will merge
        any incremental indices and improve search performance.
        """
        if table_name not in self.db.table_names():
            logger.error(f"Table {table_name} does not exist")
            return False
        
        try:
            table = self.db.open_table(table_name)
            logger.info(f"Optimizing table {table_name}...")
            start_time = time.time()
            table.optimize()
            logger.info(f"Optimized table {table_name} in {time.time() - start_time:.2f} seconds")
            return True
        except Exception as e:
            logger.error(f"Error optimizing table {table_name}: {str(e)}")
            return False

    