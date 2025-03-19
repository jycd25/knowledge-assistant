#!/usr/bin/env python3

import re
import nltk
from typing import List, Dict, Optional, Union
import logging
from pathlib import Path
import os
import time
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
import string
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_TOKENS = 8191

try:
    from .setup_nltk import setup_nltk
    setup_nltk()
except (ImportError, ModuleNotFoundError):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.append(current_dir)
        from setup_nltk import setup_nltk
        setup_nltk()
    except (ImportError, ModuleNotFoundError):
        logger.warning("Could not import setup_nltk, falling back to direct NLTK downloads")
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            logger.info("Downloading NLTK resources...")
            nltk.download('punkt')
            nltk.download('stopwords')
        
        try:
            nltk.data.find('corpora/wordnet')
        except LookupError:
            logger.info("Downloading WordNet...")
            nltk.download('wordnet')
            
        try:
            nltk.data.find('taggers/averaged_perceptron_tagger')
        except LookupError:
            logger.info("Downloading POS tagger...")
            nltk.download('averaged_perceptron_tagger')

class Tokenizer:
    """
    A text tokenizer for preprocessing documents before embedding.
    This helps improve the quality of embeddings by cleaning and normalizing text.
    """
    
    def __init__(self, 
                 remove_stopwords: bool = True,
                 remove_punctuation: bool = True,
                 lowercase: bool = True,
                 max_length: Optional[int] = MAX_TOKENS):
        """
        Initialize the tokenizer with configuration options.
        
        Args:
            remove_stopwords: Whether to remove common stopwords
            remove_punctuation: Whether to remove punctuation
            lowercase: Whether to convert text to lowercase
            max_length: Maximum number of tokens to keep (None for no limit)
        """
        self.remove_stopwords = remove_stopwords
        self.remove_punctuation = remove_punctuation
        self.lowercase = lowercase
        self.max_length = max_length
        self.stop_words = set(stopwords.words('english')) if remove_stopwords else set()
        self.punctuation = set(string.punctuation)
        
        logger.info(f"Tokenizer initialized with config: remove_stopwords={remove_stopwords}, "
                   f"remove_punctuation={remove_punctuation}, lowercase={lowercase}, "
                   f"max_length={max_length}")
    
    def clean_text(self, text: str) -> str:
        """
        Clean text by applying various preprocessing steps.
        
        Args:
            text: The input text to clean
            
        Returns:
            Cleaned text
        """
        if self.lowercase:
            text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove URLs
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove punctuation if configured
        if self.remove_punctuation:
            text = ''.join([c for c in text if c not in self.punctuation])
        
        return text
    
    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.
        
        Args:
            text: The input text to tokenize
            
        Returns:
            List of tokens
        """
        # Clean the text first
        cleaned_text = self.clean_text(text)
        
        # Simple tokenization by splitting on whitespace
        tokens = cleaned_text.split()
        
        # Remove stopwords if configured
        if self.remove_stopwords:
            tokens = [token for token in tokens if token.lower() not in self.stop_words]
        
        # Limit to max_length if specified
        if self.max_length is not None and len(tokens) > self.max_length:
            tokens = tokens[:self.max_length]
        
        return tokens
    
    def split_into_chunks(self, text: str, chunk_size: int = 4000, overlap: int = 200) -> List[str]:
        """
        Split a long text into overlapping chunks for better processing.
        Optimized for the larger context window of text-embedding-3-large.
        
        Args:
            text: The input text to split
            chunk_size: Maximum size of each chunk in characters
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        if self.max_length and self.max_length > 4000:
            chunk_size = min(chunk_size * 2, 8000)
            overlap = min(overlap * 2, 400)
        
        chunks = []
        start = 0
        max_iterations = (len(text) // (chunk_size - overlap)) + 2
        iteration = 0
        
        while start < len(text) and iteration < max_iterations:
            iteration += 1
            end = min(start + chunk_size, len(text))
            
            if end < len(text):
                last_period = max(text.rfind('. ', start, end), 
                                 text.rfind('? ', start, end),
                                 text.rfind('! ', start, end),
                                 text.rfind('\n', start, end))
                
                if last_period != -1 and last_period > start + chunk_size // 2:
                    end = last_period + 1
            
            chunks.append(text[start:end])
            
            new_start = end - overlap
            
            if new_start <= start:
                new_start = start + max(1, chunk_size // 10)
                logger.warning(f"Forced progress in chunking to avoid infinite loop: {start} -> {new_start}")
            
            start = new_start
            
            if len(chunks) > max_iterations:
                logger.warning(f"Breaking out of chunking loop after {len(chunks)} chunks to avoid freezing")
                break
        
        logger.info(f"Split text into {len(chunks)} chunks (chunk_size={chunk_size}, overlap={overlap})")
        return chunks
    
    def estimate_token_count(self, text: str) -> int:
        """
        Estimate the number of tokens in a text.
        This is a rough approximation based on whitespace splitting.
        
        Args:
            text: The input text
            
        Returns:
            Estimated token count
        """
        return len(text) // 4
    
    def truncate_to_max_tokens(self, text: str) -> str:
        """
        Truncate text to fit within the maximum token limit.
        
        Args:
            text: The input text
            
        Returns:
            Truncated text
        """
        if not self.max_length:
            return text
            
        if self.estimate_token_count(text) <= self.max_length:
            return text
            
        char_limit = self.max_length * 4
        
        if len(text) > char_limit:
            last_period = max(text.rfind('. ', 0, char_limit), 
                             text.rfind('? ', 0, char_limit),
                             text.rfind('! ', 0, char_limit))
            
            if last_period != -1:
                return text[:last_period + 1]
            else:
                return text[:char_limit]
        
        return text
    
    def preprocess_for_embedding(self, text: str) -> str:
        """
        Prepare text for embedding by applying minimal cleaning.
        For embeddings, we want to preserve most of the original text structure.
        
        Args:
            text: The input text to preprocess
            
        Returns:
            Preprocessed text ready for embedding
        """
        text = re.sub(r'\s+', ' ', text).strip()
        
        if self.lowercase:
            text = text.lower()
        
        text = self.truncate_to_max_tokens(text)
        
        return text
    
    def preprocess_document(self, document: str, for_embedding: bool = True) -> Union[str, List[str]]:
        """
        Preprocess a document, either for embedding or for tokenization.
        
        Args:
            document: The document text to preprocess
            for_embedding: Whether to prepare for embedding (True) or tokenization (False)
            
        Returns:
            Preprocessed text if for_embedding=True, otherwise a list of tokens
        """
        if for_embedding:
            return self.preprocess_for_embedding(document)
        else:
            return self.tokenize(document)

# Example usage
if __name__ == "__main__":
    tokenizer = Tokenizer()
    
    text = """
    This is an example document for testing the tokenizer. 
    It contains multiple sentences, some punctuation, and stopwords.
    We want to see how the tokenizer handles this text.
    https://example.com is a URL that should be removed.
    test@example.com is an email that should be removed.
    """
    
    tokens = tokenizer.tokenize(text)
    print(f"Tokenized text: {tokens}")
    
    processed = tokenizer.preprocess_for_embedding(text)
    print(f"Preprocessed for embedding: {processed}")
    
    chunks = tokenizer.split_into_chunks(text, chunk_size=100, overlap=20)
    print(f"Split into {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}: {chunk[:50]}...") 