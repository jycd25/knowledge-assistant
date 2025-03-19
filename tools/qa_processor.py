#!/usr/bin/env python3

import os
import time
import traceback
from typing import List, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv
import logging
from .knowledge_base import KnowledgeBase
import sys
from pathlib import Path
import re
from openai import OpenAI

parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))
from .lancedb_manager import LanceDBManager

load_dotenv(Path(parent_dir, '.env')) 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_openai_client():    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        env_paths = [
            '.env',
            Path(Path(__file__).resolve().parent.parent, '.env'),
            Path(Path(__file__).resolve().parent.parent, 'data', '.env'),
            Path(os.path.expanduser('~'), '.env')
        ]
        for env_path in env_paths:
            logger.info(f"Trying to load .env from: {env_path}")
            load_dotenv(env_path)
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                logger.info(f"Found API key in {env_path}")
                break
    
    if not api_key:
        logger.error("No OpenAI API key found, QA processor will not work")
        return None
    
    logger.info("Initializing OpenAI client for QA processing")
    client = OpenAI(api_key=api_key)
    logger.info("OpenAI client initialized successfully")
    return client

class QAProcessor:
    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None, db_manager: Optional[LanceDBManager] = None):
        """Initialize the QA processor with a knowledge base and/or db_manager
        
        Args:
            knowledge_base: Optional KnowledgeBase instance for searching the documents table
            db_manager: Optional LanceDBManager instance for searching the entries table
        """
        self.kb = knowledge_base
        self.db_manager = db_manager
        self.client = None
        self.api_key = None
        
        if not self.kb and not self.db_manager:
            logger.warning("QAProcessor initialized without either a knowledge base or db_manager")
        
        logger.info("QA Processor initialization complete - client will be initialized on demand")

    def _ensure_client_initialized(self):
        """Ensure the client is initialized when needed"""
        if self.client is None:
            logger.info("Initializing OpenAI client on first use")
            self.client = get_openai_client()
            if self.client is None:
                logger.warning("Failed to initialize OpenAI client - QA processing will be limited")

    def generate_search_query(self, user_question: str) -> str:
        """Use LLM to generate an effective search query from the user's question"""
        start_time = time.time()
        logger.info(f"Generating search query for: '{user_question}'")
        
        self._ensure_client_initialized()
        if not self.client:
            logger.warning("OpenAI client not initialized - using original question as query")
            return user_question
            
        try:
            prompt = f"""Given this user question, generate a search query that would be effective for semantic search in a knowledge base.
                    The query should:
                    1. Focus on the key concepts and entities
                    2. Remove unnecessary words and context
                    3. Be concise but maintain important details
                    4. Be optimized for semantic similarity search

                    User question: "{user_question}"

                    Respond with ONLY the search query, no other text.
                """

            logger.info("Sending request to OpenAI API...")
            api_start_time = time.time()
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a search query optimization assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100,
                timeout=15
            )
            api_time = time.time() - api_start_time
            logger.info(f"OpenAI API response received in {api_time:.2f} seconds")
            
            query = response.choices[0].message.content.strip()
            logger.info(f"Generated search query: '{query}'")
            
            total_time = time.time() - start_time
            logger.info(f"Total query generation time: {total_time:.2f} seconds")
            return query
            
        except Exception as e:
            error_msg = f"Error generating search query: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            logger.info("Falling back to original question as query")
            return user_question

    def answer_question(self, user_question: str, max_results: int = 5, relevance_threshold: float = 0.5) -> Dict:
        """Process a user's question and return an answer based on knowledge base content
        
        Args:
            user_question: The user's question
            max_results: Maximum number of search results to retrieve
            relevance_threshold: Threshold for filtering results by relevance score (lower is more relevant)
            
        Returns:
            Dictionary with answer and sources
        """
        start_time = time.time()
        logger.info(f"Processing question: '{user_question}'")
        logger.info(f"Using relevance threshold: {relevance_threshold}")
        
        try:
            self._ensure_client_initialized()
            
            logger.info("Step 1: Generating optimized search query")
            query_start_time = time.time()
            search_query = self.generate_search_query(user_question)
            query_time = time.time() - query_start_time
            logger.info(f"Search query generation completed in {query_time:.2f} seconds")
            
            search_results = []
            
            if self.db_manager:
                logger.info("Step 2a: Searching entries table for information")
                entries_start_time = time.time()
                entry_results = self.db_manager.search_entries(search_query, limit=max_results)
                entries_time = time.time() - entries_start_time
                
                logger.info(f"Entries search completed in {entries_time:.2f} seconds, found {len(entry_results)} results")
                
                if entry_results:
                    for result in entry_results:
                        search_results.append({
                            'text': result.get('content', ''),
                            'title': result.get('title', 'Untitled'),
                            'source': result.get('source', 'Unknown'),
                            'score': result.get('score', 1.0)
                        })
            
            if not search_results and self.kb:
                logger.info(f"Step 2b: Searching knowledge base with query: '{search_query}'")
                search_start_time = time.time()
                kb_results = self.kb.search(search_query, limit=max_results)
                search_time = time.time() - search_start_time
                
                logger.info(f"Knowledge base search completed in {search_time:.2f} seconds, found {len(kb_results)} results")
                
                if kb_results:
                    search_results = kb_results
            
            if not search_results:
                logger.info("No search results found in any knowledge source")
                return {
                    'answer': "I couldn't find any relevant information in the knowledge base to answer your question.",
                    'sources': []
                }
            
            logger.info(f"Step 3: Filtering search results by relevance (threshold: {relevance_threshold})")
            filtered_results = [
                result for result in search_results 
                if result['score'] < relevance_threshold  # Lower score means higher relevance
            ]
            logger.info(f"Filtered to {len(filtered_results)} relevant results")
            

            if not filtered_results and search_results:
                logger.info("No results passed the relevance filter, using top search results instead")
                # Take the top 2 results regardless of score
                filtered_results = search_results[:2]
                logger.info(f"Using {len(filtered_results)} top results regardless of relevance score")
            
            if not filtered_results:
                logger.info("No relevant results found, returning default answer")
                return {
                    'answer': "I couldn't find any relevant information in the knowledge base to answer your question.",
                    'sources': []
                }
            s
            logger.info("Step 4: Formatting context from search results")
            context = []
            sources = []
            for i, result in enumerate(filtered_results):
                title = result.get('title') or "Untitled"
                source = result.get('source') or "Unknown"
                logger.info(f"Result {i+1}: {title} (Score: {result['score']:.4f})")
                context.append(f"Content: {result['text']}\nSource: {title} ({source})\n")
                sources.append({
                    'title': title,
                    'source': source,
                    'text': result['text'],
                    'relevance_score': result['score']
                })
            
            if self.client:
                logger.info("Step 5: Generating answer using OpenAI API")
                prompt = (
                    f"Based on the following information from a knowledge base, answer the user's question.\n"
                    f"If the information is not sufficient to answer the question completely, say so.\n"
                    f"Include specific references to sources when possible.\n\n"
                    f"User question: {user_question}\n\n"
                    f"Knowledge base information:\n"
                    f"{chr(10).join(context)}\n\n"
                    f"Provide a clear and concise answer that directly addresses the user's question."
                )

                logger.info("Sending request to OpenAI API for answer generation...")
                api_start_time = time.time()
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a knowledgeable assistant that provides accurate answers based on available information."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=500,
                        timeout=30
                    )
                    api_time = time.time() - api_start_time
                    logger.info(f"OpenAI API response received in {api_time:.2f} seconds")
                    
                    answer = response.choices[0].message.content.strip()
                    logger.info("Answer generated successfully")
                except Exception as api_error:
                    logger.error(f"Error calling OpenAI API: {str(api_error)}")
                    logger.info("Falling back to most relevant result as answer")
                    answer = f"API Error: {str(api_error)}\n\nHere is the most relevant information I found:\n\n{filtered_results[0]['text']}"
            else:
                logger.info("No OpenAI client available, using most relevant result as answer")
                answer = f"Here is the most relevant information I found:\n\n{filtered_results[0]['text']}"
            
            total_time = time.time() - start_time
            logger.info(f"Total question processing completed in {total_time:.2f} seconds")
            
            return {
                'answer': answer,
                'sources': sources
            }
            
        except Exception as e:
            error_msg = f"Error processing question: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return {
                'answer': f"An error occurred while processing your question: {str(e)}",
                'sources': []
            }

    def answer_question_with_docs(self, user_question: str, docs: List[Dict], relevance_threshold: float = 0.5) -> Dict:
        """Process a user's question using pre-filtered documents
        
        Args:
            user_question: The user's question
            docs: List of documents to use for answering
            relevance_threshold: Threshold for filtering results by relevance score
            
        Returns:
            Dictionary with answer and sources
        """
        start_time = time.time()
        logger.info(f"Processing question with provided docs: '{user_question}'")
        
        try:
            self._ensure_client_initialized()
            
            if not docs:
                logger.info("No documents provided")
                return {
                    'answer': "I couldn't find any relevant information to answer your question.",
                    'sources': []
                }
            
            logger.info(f"Processing question with {len(docs)} documents")
            
            for i, doc in enumerate(docs):
                title = doc.get('title', "Untitled")
                text = doc.get('text', "")
                logger.info(f"Document {i+1} title: {title}")
                text_lower = text.lower()
                for term in ["distillation", "distill", "distilling"]:
                    if term in text_lower:
                        positions = [m.start() for m in re.finditer(term, text_lower)]
                        for pos in positions:
                            start = max(0, pos - 50)
                            end = min(len(text), pos + len(term) + 50)
                            context = text[start:end]
                            logger.info(f"    Found '{term}' in content: ...{context}...")
            
            if all('score' in doc for doc in docs):
                logger.info(f"Filtering documents by relevance (threshold: {relevance_threshold})")
                filtered_docs = [
                    doc for doc in docs
                    if doc.get('score', 2.0) < relevance_threshold
                ]
                
                if not filtered_docs:
                    logger.info(f"No documents passed the relevance filter, using top documents instead")
                    sorted_docs = sorted(docs, key=lambda x: x.get('score', 2.0))
                    filtered_docs = sorted_docs[:5]
                    logger.info(f"Using top {len(filtered_docs)} documents regardless of relevance score")
                elif len(filtered_docs) < 3 and len(docs) > len(filtered_docs):
                    logger.info(f"Only {len(filtered_docs)} documents passed the filter, adding more relevant documents")
                    remaining_docs = [doc for doc in docs if doc not in filtered_docs]
                    sorted_remaining = sorted(remaining_docs, key=lambda x: x.get('score', 2.0))
                    additional_docs = sorted_remaining[:3-len(filtered_docs)]
                    filtered_docs.extend(additional_docs)
                    logger.info(f"Added {len(additional_docs)} more documents, now using {len(filtered_docs)} total")
                else:
                    logger.info(f"{len(filtered_docs)} documents passed the relevance filter")
            else:
                logger.info("No relevance scores in documents, using all provided documents")
                filtered_docs = docs[:8]
            
            context = []
            sources = []
            logger.info(f"Using {len(filtered_docs)} documents for context")
            for i, doc in enumerate(filtered_docs):
                title = doc.get('title', "Untitled")
                source = doc.get('source', "Unknown")
                text = doc.get('text', "")
                score = doc.get('score', 0.0)
                
                logger.info(f"Document {i+1}: {title} (Score: {score:.4f})")
                context.append(f"Content: {text}\nSource: {title} ({source})\n")
                sources.append({
                    'title': title,
                    'source': source,
                    'text': text,
                    'relevance_score': score
                })
            
            if self.client:
                logger.info(f"Generating answer using OpenAI API with {len(context)} documents as context")
              
                model = "gpt-4o-mini"  
                prompt = (
                    f"Based on the following information from a knowledge base, please answer the user's question.\n"
                    f"If the information is not sufficient to answer the question completely, say so.\n"
                    f"If the information is contradictory, explain the different perspectives.\n"
                    f"Include specific references to sources when possible.\n\n"
                    f"User question: {user_question}\n\n"
                    f"Knowledge base information:\n"
                    f"{chr(10).join(context)}\n\n"
                    f"Provide a clear and concise answer that directly addresses the user's question."
                )

                logger.info("Sending request to OpenAI API for answer generation...")
                api_start_time = time.time()
                try:
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are a knowledgeable assistant that provides accurate answers based on available information."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=500,
                        timeout=30
                    )
                    api_time = time.time() - api_start_time
                    logger.info(f"OpenAI API response received in {api_time:.2f} seconds")
                    
                    answer = response.choices[0].message.content.strip()
                    logger.info("Answer generated successfully")
                except Exception as api_error:
                    logger.error(f"Error calling OpenAI API: {str(api_error)}")
                    logger.info("Falling back to most relevant result as answer")
                    answer = f"API Error: {str(api_error)}\n\nHere is the most relevant information I found:\n\n{filtered_docs[0].get('text', '')}"
            else:
                logger.info("No OpenAI client available, using most relevant result as answer")
                answer = f"Here is the most relevant information I found:\n\n{filtered_docs[0].get('text', '')}"
            
            total_time = time.time() - start_time
            logger.info(f"Total question processing completed in {total_time:.2f} seconds")
            
            return {
                'answer': answer,
                'sources': sources
            }
            
        except Exception as e:
            error_msg = f"Error processing question: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return {
                'answer': f"An error occurred while processing your question: {str(e)}",
                'sources': []
            } 