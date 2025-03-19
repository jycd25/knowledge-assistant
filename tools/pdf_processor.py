#!/usr/bin/env python3

import os
from pathlib import Path
from typing import Dict, Optional
from docling.document_converter import DocumentConverter
import re
from datetime import datetime

class PDFProcessor:
    def __init__(self, upload_dir: str = 'data/uploads'):
        """Initialize the PDF processor.
        
        Args:
            upload_dir: Directory to store uploaded PDF files temporarily
        """
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.converter = DocumentConverter()
        
    def process_pdf(self, pdf_path: str) -> Dict[str, str]:
        """Process a PDF file and convert it to markdown format.
        
        """
        try:
            result = self.converter.convert(pdf_path)
            
            # # Extract metadata
            # metadata = {
            #     'title': result.document.metadata.get('title', 'Untitled'),
            #     'author': result.document.metadata.get('author', 'Unknown'),
            #     'subject': result.document.metadata.get('subject', ''),
            #     'keywords': result.document.metadata.get('keywords', ''),
            #     'created_date': result.document.metadata.get('created', ''),
            #     'modified_date': result.document.metadata.get('modified', ''),
            #     'page_count': len(result.document.pages) if hasattr(result.document, 'pages') else 0
            # }
            
            # Convert to markdown
            markdown_text = result.document.export_to_markdown()
            
            return markdown_text
            
        except Exception as e:
            return {
                'error': f'Error processing PDF: {str(e)}'
            }
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """Clean up old uploaded files.
        
        Args:
            max_age_hours: Maximum age of files to keep in hours
        """
        current_time = datetime.now().timestamp()
        
        for file_path in self.upload_dir.glob('*.pdf'):
            file_age = current_time - file_path.stat().st_mtime
            if file_age > max_age_hours * 3600:
                try:
                    file_path.unlink()
                except Exception as e:
                    print(f"Error deleting old file {file_path}: {e}") 