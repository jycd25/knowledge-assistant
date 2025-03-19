#!/usr/bin/env python3

from typing import Dict, Optional, Any
import json
from pathlib import Path

class PromptBuilder:
    """
    A tool to structure input for LLM processing, combining:
    - User request/prompt
    - Saved preferences
    - Input text
    - Formatting instructions
    """
    
    def __init__(self):
        self.base_instructions = {
            "format": """
Format Requirements:
1. Use markdown formatting
2. Create clear section headers (H1, H2)
3. Use bullet points for lists
4. Include a summary section
5. Add relevant tags at the end
""",
            "structure": """
Required Sections:
- Title (H1)
- Summary
- Main Points
- Action Items (if applicable)
- Tags
"""
        }
    
    def format_preferences(self, preferences: Dict[str, Any]) -> str:
        """Format user preferences into clear instructions"""
        if not preferences or "preferences" not in preferences:
            return ""
            
        formatted = []
        for name, pref in preferences["preferences"].items():
            if name == "special emphasis":
                formatted.append(
                    "IMPORTANT: Format all names of important figures, people, or key terms "
                    "by surrounding them with double asterisks for bold text. "
                    "Example: **Albert Einstein**, **Theory of Relativity**"
                )
            else:
                formatted.append(f"{name}: {pref['value']}")
        
        return "\n".join(formatted)
    
    def build_prompt(self, 
                    text: str, 
                    user_request: Optional[str] = None,
                    preferences: Optional[Dict[str, Any]] = None) -> str:
        """
        Build a structured prompt combining all elements
        """
        sections = []
        
        sections.append("=== FORMATTING INSTRUCTIONS ===")
        sections.append(self.base_instructions["format"].strip())
        sections.append(self.base_instructions["structure"].strip())
        
        if preferences:
            formatted_prefs = self.format_preferences(preferences)
            if formatted_prefs:
                sections.append("\n=== USER PREFERENCES ===")
                sections.append(formatted_prefs)
        if user_request:
            sections.append("\n=== USER REQUEST ===")
            sections.append(user_request)
        
        sections.append("\n=== INPUT TEXT ===")
        sections.append(text)
        
        return "\n\n".join(sections)
    
    def debug_prompt(self, prompt: str, output_file: Optional[str] = None):
        """
        Save the built prompt to a file for debugging/verification
        """
        if output_file:
            Path(output_file).write_text(prompt, encoding='utf-8')
            print(f"Prompt saved to {output_file}")
        else:
            print("\n=== GENERATED PROMPT ===")
            print(prompt)

def main():
    """Test the prompt builder"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build and test LLM prompts')
    parser.add_argument('--text', '-t', required=True, help='Input text to process')
    parser.add_argument('--request', '-r', help='User request/instructions')
    parser.add_argument('--prefs-file', '-p', help='Path to preferences.json file')
    parser.add_argument('--output', '-o', help='Output file for the generated prompt')
    
    args = parser.parse_args()
    preferences = None
    if args.prefs_file:
        try:
            with open(args.prefs_file, 'r', encoding='utf-8') as f:
                preferences = json.load(f)
        except Exception as e:
            print(f"Error loading preferences: {e}")
            
    builder = PromptBuilder()
    prompt = builder.build_prompt(
        text=args.text,
        user_request=args.request,
        preferences=preferences
    )
    
    builder.debug_prompt(prompt, args.output)

if __name__ == '__main__':
    main() 