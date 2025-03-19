#!/usr/bin/env python3

import re
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from collections import Counter
import string
import os
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv
import json
from .prompt_builder import PromptBuilder
import sys

@dataclass
class ProcessedNote:
    title: str
    sections: Dict[str, str]
    tags: List[str]
    summary: str
    raw_text: str

class NoteProcessor:
    def __init__(self, preferences=None):
        """Initialize the NoteProcessor
        
        Args:
            preferences: Optional preferences object or dictionary
        """
        parent_dir = Path(__file__).resolve().parent.parent
        sys.path.append(str(parent_dir))
    
        load_dotenv(Path(parent_dir, '.env'))  # Try parent directory
        
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            print("WARNING: OpenAI API key not found in environment variables")
        
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.preferences = preferences
        self.prompt_builder = PromptBuilder()
        
        self.stop_words = set([
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'were', 'will', 'with'
        ])

    def split_sentences(self, text: str) -> List[str]:
        """Split text into sentences using regex"""
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        return [s.strip() for s in sentences if s.strip()]

    def tokenize_words(self, text: str) -> List[str]:
        """Split text into words"""
        words = text.lower().split()
        return [w.strip(string.punctuation) for w in words if w.strip(string.punctuation)]

    def extract_title(self, text: str) -> str:
        """Extract or generate a title from the text"""
        sentences = self.split_sentences(text)
        if not sentences:
            return "Untitled Note"
        
        first_sentence = sentences[0]
        
        intro_phrases = ["today i learned", "i learned", "note about", "today's note"]
        cleaned = first_sentence.lower()
        for phrase in intro_phrases:
            cleaned = cleaned.replace(phrase, "").strip()
        
        words = self.tokenize_words(cleaned)
        words = [w for w in words if w not in self.stop_words]
        
        title_words = words[:6]
        title = " ".join(title_words).strip().title()
        
        return title if title else "Untitled Note"

    def identify_sections(self, text: str) -> Dict[str, str]:
        """Identify and organize content into logical sections"""
        sentences = self.split_sentences(text)
        sections = {}
        
        current_section = []
        current_topic = "Main Points"
        
        for sentence in sentences:
            lower_sent = sentence.lower()
            if any(phrase in lower_sent for phrase in ["additionally", "moreover", "furthermore", "however", "on the other hand", "in contrast"]):
                if current_section:
                    sections[current_topic] = " ".join(current_section)
                    current_section = []
                    current_topic = self._generate_section_title(sentence)
            current_section.append(sentence)
        
        if current_section:
            sections[current_topic] = " ".join(current_section)
        
        return sections

    def extract_tags(self, text: str) -> List[str]:
        """Extract relevant tags from the text"""
        words = self.tokenize_words(text)
        words = [w for w in words if w not in self.stop_words and len(w) > 3]
        
        word_freq = Counter(words)
        
        tags = [f"#{word.title()}" for word, _ in word_freq.most_common(5)]
        return tags

    def generate_summary(self, text: str, sections: Dict[str, str]) -> str:
        """Generate a brief summary of the note"""
        if len(text.split()) < 50:
            return text
        
        summary_points = []
        for section, content in sections.items():
            sentences = self.split_sentences(content)
            if sentences:
                summary_points.append(sentences[0])
        
        return " ".join(summary_points)

    def _generate_section_title(self, first_sentence: str) -> str:
        """Generate a section title from the first sentence of the section"""
        words = self.tokenize_words(first_sentence)
        words = [w for w in words if w not in self.stop_words][:3]
        return " ".join(words).title()

    def format_processed_note(self, processed: ProcessedNote) -> str:
        """Format the processed note into markdown"""
        lines = [
            f"# {processed.title}\n",
        ]
        
        for section_title, content in processed.sections.items():
            lines.extend([
                f"\n## {section_title}",
                content
            ])
        
        if processed.summary and processed.summary != processed.raw_text:
            lines.extend([
                "\n## Summary",
                processed.summary
            ])
        
        if processed.tags:
            lines.extend([
                "\n## Tags",
                " ".join(processed.tags)
            ])
        
        return "\n".join(lines)

    def get_preferences_dict(self) -> Dict[str, Any]:
        """Get preferences as a dictionary, regardless of the original format"""
        if not self.preferences:
            return {}
            
        if isinstance(self.preferences, dict):
            return self.preferences
            
        if hasattr(self.preferences, 'preferences'):
            return self.preferences.preferences
            
        return {}

    def process_with_llm(self, text: str, user_request: str = None) -> Dict:
        """Process the note using LLM with structured input
        
        Args:
            text: The note text to process
            user_request: Optional user instructions for processing (may include template information)
            
        Returns:
            Dictionary containing processed text and metadata
        """
        try:
            if not self.client:
                print("OpenAI client not initialized - falling back to basic processing")
                return {
                    'text': self.process_without_llm(text),
                    'applied_preferences': None
                }

            current_prefs = self.get_preferences_dict()
            
            template_name = None
            if user_request and "template" in user_request.lower():
                template_match = re.search(r"based on the '([^']+)' template", user_request)
                if template_match:
                    template_name = template_match.group(1)
                    print(f"Detected template in request: {template_name}")
            
            prompt = self.prompt_builder.build_prompt(
                text=text,
                user_request=user_request,
                preferences=current_prefs
            )
            
            self.prompt_builder.debug_prompt(prompt, "debug_last_prompt.txt")
            
            applied_preferences = []
            if current_prefs and "preferences" in current_prefs:
                for name, pref in current_prefs["preferences"].items():
                    applied_preferences.append({
                        "name": name,
                        "value": pref["value"],
                        "explanation": pref.get("explanation", "")
                    })
            
            print(f"Sending request to OpenAI API (text length: {len(text)})")
            if template_name:
                print(f"Using template: {template_name}")
            print(f"Applied preferences: {json.dumps(applied_preferences, indent=2)}")
            
            system_message = "You are a helpful note processing assistant that follows formatting instructions precisely."
            
            if template_name or applied_preferences:
                system_message += "\n\nImportant context:"
                if template_name:
                    system_message += f"\n- Using template: {template_name}"
                if applied_preferences:
                    system_message += f"\n- Applied preferences: {len(applied_preferences)}"
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            processed_text = response.choices[0].message.content
            print(f"Received response from OpenAI API (length: {len(processed_text)})")
            
            if template_name:
                if f"template" not in processed_text.lower() and f"{template_name}" not in processed_text:
                    template_footer = f"\n\n---\n*Based on the {template_name} template*"
                    processed_text += template_footer
            
            return {
                'text': processed_text,
                'applied_preferences': applied_preferences
            }

        except Exception as e:
            print(f"Error in process_with_llm: {str(e)}")
            return {
                'text': self.process_without_llm(text),
                'applied_preferences': None
            }

    def process_note(self, text: str, user_request: str = None, use_llm: bool = True) -> Dict:
        """Process a note with optional user request and LLM usage
        
        Args:
            text: The note text to process
            user_request: Optional user instructions for processing (may include template information)
            use_llm: Whether to use LLM for processing
            
        Returns:
            Dictionary containing processed text and metadata
        """
        if use_llm:
            return self.process_with_llm(text, user_request)
            
        return {
            'text': self.process_without_llm(text),
            'applied_preferences': None
        }

    def process_without_llm(self, text: str) -> str:
        """Process a note without using LLM"""
        title = self.extract_title(text)
        sections = self.identify_sections(text)
        tags = self.extract_tags(text)
        summary = self.generate_summary(text, sections)
        
        processed = ProcessedNote(
            title=title,
            sections=sections,
            tags=tags,
            summary=summary,
            raw_text=text
        )
        
        return self.format_processed_note(processed) 