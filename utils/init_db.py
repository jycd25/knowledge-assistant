#!/usr/bin/env python3
"""
Database Initialization Script for Knowledge Assistant

This script initializes the LanceDB database with necessary tables and
creates some initial categories and topics for the Knowledge Assistant.

Usage:
    python utils/init_db.py

"""

import os
import sys
from pathlib import Path
import logging
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Add parent directory to path to access tools
parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

# Import necessary modules
from tools.lancedb_manager import LanceDBManager
from tools.knowledge_base import KnowledgeBase

# Default database path
DB_PATH = "data/lancedb"

def initialize_database(db_path, sample_data=True):
    """
    Initialize the LanceDB database with necessary tables.
    
    Args:
        db_path (str): Path to the LanceDB database
        sample_data (bool): Whether to create sample categories and topics
    """
    logger.info(f"Initializing database at {db_path}")
    
    # Create database directory if it doesn't exist
    os.makedirs(db_path, exist_ok=True)
    
    try:
        # Initialize the LanceDB manager
        db_manager = LanceDBManager(db_path=db_path)
        logger.info("LanceDB manager initialized successfully")
        
        # Check for categories
        categories = db_manager.get_categories()
        has_categories = not categories.empty if hasattr(categories, 'empty') else len(categories) > 0
        logger.info(f"Categories exist: {has_categories}")
        
        # Create sample data if requested
        if sample_data and not has_categories:
            logger.info("No categories found, creating sample data")
            create_sample_data(db_manager)
        
        logger.info("Database initialization complete")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def create_sample_data(db_manager):
    """
    Create sample categories and topics in the database.
    
    Args:
        db_manager (LanceDBManager): The LanceDB manager
    """
    logger.info("Creating sample categories and topics")
    
    try:
        categories = [
            {
                "name": "Work",
                "description": "Professional documents and resources"
            },
            {
                "name": "Personal",
                "description": "Personal notes and documents"
            },
        
        ]
        
        category_ids = {}
        for category in categories:
            category_id = db_manager.create_category(
                name=category["name"],
                description=category["description"]
            )
            category_ids[category["name"]] = category_id
            logger.info(f"Created category: {category['name']} (ID: {category_id})")
        
        topics = {
            }
        
        for category_name, topic_list in topics.items():
            category_id = category_ids.get(category_name)
            if category_id:
                for topic in topic_list:
                    topic_id = db_manager.create_topic(
                        category_id=category_id,
                        name=topic["name"],
                        description=topic["description"]
                    )
                    logger.info(f"Created topic: {topic['name']} under {category_name} (ID: {topic_id})")
        
        logger.info("Sample data creation complete")
        return True
        
    except Exception as e:
        logger.error(f"Error creating sample data: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def create_knowledge_base_docs_table(db_path):
    """
    Initialize the Knowledge Base with the documents table.
    
    Args:
        db_path (str): Path to the LanceDB database
    """
    logger.info(f"Initializing Knowledge Base with documents table at {db_path}")
    
    try:
        kb = KnowledgeBase(db_uri=db_path, table_name="documents", create_if_not_exists=True)
        try:
            kb.get_stats()
            logger.info("Documents table already exists")
        except Exception as e:
            if "Table documents does not exist" in str(e):
                logger.info("Creating documents table")
                try:
                    kb.add_document(
                        text="This is a sample document for initializing the Knowledge Base.",
                        source="init_db.py",
                        title="Sample Document"
                    )
                    logger.info("Documents table created successfully")
                except Exception as doc_error:
                    logger.error(f"Error creating documents table: {doc_error}")
                    return False
            else:
                logger.error(f"Error checking documents table: {e}")
                return False
        
        logger.info("Knowledge Base initialization complete")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing Knowledge Base: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    parser = argparse.ArgumentParser(description="Initialize the Knowledge Assistant database")
    parser.add_argument("--db-path", type=str, default=DB_PATH,
                        help=f"Path to the LanceDB database (default: {DB_PATH})")
    parser.add_argument("--no-sample-data", action="store_true",
                        help="Don't create sample categories and topics")
    
    args = parser.parse_args()
    db_path = args.db_path
    if not os.path.isabs(db_path):
        db_path = str(parent_dir / db_path)
    success = initialize_database(db_path, not args.no_sample_data)
    if success:
        success = create_knowledge_base_docs_table(db_path)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 