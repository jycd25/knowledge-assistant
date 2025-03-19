#!/usr/bin/env python3

import nltk
import os
import sys

def setup_nltk():
    """Download required NLTK data packages if they don't exist"""
    print("Setting up NLTK data...")
    
    nltk_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "nltk_data")
    os.makedirs(nltk_data_dir, exist_ok=True)
    
    nltk.data.path.append(nltk_data_dir)
    
    required_packages = [
        'punkt',           # Sentence tokenizer
        'stopwords',       # Stopwords corpus
        'wordnet',         # WordNet dictionary
        'averaged_perceptron_tagger'  # Part-of-speech tagger
    ]
    
    # Download required packages
    for package in required_packages:
        try:
            print(f"Checking for {package}...")
            nltk.data.find(f'tokenizers/{package}' if package == 'punkt' else f'corpora/{package}')
            print(f"  {package} already downloaded")
        except LookupError:
            print(f"  Downloading {package}...")
            nltk.download(package, download_dir=nltk_data_dir)
            print(f"  {package} downloaded successfully")
    
    print("NLTK setup complete!")
    return True

if __name__ == "__main__":
    setup_nltk() 