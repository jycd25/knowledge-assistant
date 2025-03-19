#!/usr/bin/env python3

import re
from typing import Dict, Optional, Union
from pathlib import Path
import logging
import os
import json
import sys

sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TemplateGenerator:
    """A tool for generating templates from markdown content."""
    
    def __init__(self):
        """Initialize the template generator."""
        pass
    
    def generate_template(self, content: str, template_type: str = 'basic') -> Dict[str, Union[bool, str, str]]:
        """
        Generate a template from markdown content.
        
        Args:
            content (str): The markdown content to analyze
            template_type (str): Type of template to generate ('basic', 'meeting', 'project', 'research', 'study')
            
        Returns:
            dict: A dictionary containing:
                - success (bool): Whether the operation was successful
                - template (str): The generated template
                - error (str): Error message if any
        """
        try:
            if template_type == 'meeting':
                return self._generate_meeting_template()
            elif template_type == 'project':
                return self._generate_project_template()
            elif template_type == 'research':
                return self._generate_research_template()
            elif template_type == 'study':
                return self._generate_study_template()
            else:
                return self._generate_basic_template()
        except Exception as e:
            logger.error(f"Error generating template: {str(e)}")
            return {
                'success': False,
                'template': '',
                'error': str(e)
            }
    
    def _generate_basic_template(self) -> Dict[str, Union[bool, str, str]]:
        """Generate a basic template."""
        try:
            sections = [
                '# [Title]', 
                '',
                '## Table of Contents',
                '- [Topic 1](#topic-1)',
                '- [Key Points](#key-points)',
                '- [Action Items](#action-items)',
                '',
                '## Topic 1', 
                '[Content]', 
                '',
                '## Key Points', 
                '- [Item 1]', 
                '- [Item 2]', 
                '- [Item 3]',
                '',
                '## Action Items', 
                '- [ ] [Action item 1]', 
                '- [ ] [Action item 2]',
                ''
            ]
            
            template = '\n'.join(sections)
            
            return {
                'success': True,
                'template': template,
                'error': None
            }
        except Exception as e:
            logger.error(f"Error in basic template generation: {str(e)}")
            return {
                'success': False,
                'template': '',
                'error': str(e)
            }
    
    def _generate_meeting_template(self) -> Dict[str, Union[bool, str, str]]:
        """Generate a meeting notes template."""
        try:
            sections = [
                '# Meeting: [Title]',
                '',
                '**Date**: [YYYY-MM-DD]',
                '**Time**: [HH:MM] - [HH:MM]',
                '**Location**: [Location]',
                '',
                '## Attendees',
                '- [Name], [Role]',
                '- [Name], [Role]',
                '',
                '## Agenda',
                '1. [Topic 1]',
                '2. [Topic 2]',
                '',
                '## Discussion',
                '### [Topic 1]',
                '- [Point 1]',
                '- [Point 2]',
                '',
                '### [Topic 2]',
                '- [Point 1]',
                '- [Point 2]',
                '',
                '## Action Items',
                '- [ ] [Action 1] (@[owner], Due: [date])',
                '- [ ] [Action 2] (@[owner], Due: [date])',
                '',
                '## Next Meeting',
                '**Date**: [YYYY-MM-DD]',
                '**Time**: [HH:MM]',
                ''
            ]
            
            template = '\n'.join(sections)
            
            return {
                'success': True,
                'template': template,
                'error': None
            }
        except Exception as e:
            logger.error(f"Error in meeting template generation: {str(e)}")
            return {
                'success': False,
                'template': '',
                'error': str(e)
            }
    
    def _generate_project_template(self) -> Dict[str, Union[bool, str, str]]:
        """Generate a project documentation template."""
        try:
            sections = [
                '# Project: [Title]',
                '',
                '## Overview',
                '[Project description]',
                '',
                '## Objectives',
                '1. [Objective 1]',
                '2. [Objective 2]',
                '',
                '## Timeline',
                '- Start: [YYYY-MM-DD]',
                '- End: [YYYY-MM-DD]',
                '',
                '## Tasks',
                '### Phase 1',
                '- [ ] [Task 1]',
                '- [ ] [Task 2]',
                '',
                '### Phase 2',
                '- [ ] [Task 1]',
                '- [ ] [Task 2]',
                '',
                '## Resources',
                '- [Resource 1]',
                '- [Resource 2]',
                '',
                '## Notes',
                '[Additional notes]',
                ''
            ]
            
            template = '\n'.join(sections)
            
            return {
                'success': True,
                'template': template,
                'error': None
            }
        except Exception as e:
            logger.error(f"Error in project template generation: {str(e)}")
            return {
                'success': False,
                'template': '',
                'error': str(e)
            }
    
    def _generate_research_template(self) -> Dict[str, Union[bool, str, str]]:
        """Generate a research notes template."""
        try:
            sections = [
                '# Research: [Title]',
                '',
                '## Overview',
                '[Research description]',
                '',
                '## Questions',
                '1. [Question 1]',
                '2. [Question 2]',
                '',
                '## Sources',
                '### [Source 1]',
                '- Author: [Name]',
                '- Date: [YYYY-MM-DD]',
                '- Link: [URL]',
                '- Key Points:',
                '  - [Point 1]',
                '  - [Point 2]',
                '',
                '## Findings',
                '1. [Finding 1]',
                '2. [Finding 2]',
                '',
                '## Conclusions',
                '[Research conclusions]',
                '',
                '## Next Steps',
                '- [ ] [Step 1]',
                '- [ ] [Step 2]',
                ''
            ]
            
            template = '\n'.join(sections)
            
            return {
                'success': True,
                'template': template,
                'error': None
            }
        except Exception as e:
            logger.error(f"Error in research template generation: {str(e)}")
            return {
                'success': False,
                'template': '',
                'error': str(e)
            }

    def _generate_study_template(self) -> Dict[str, Union[bool, str, str]]:
        """Generate a study notes template with nested topics."""
        try:
            sections = [
                '# [Title]',
                '',
                '## Table of Contents',
                '- [Topic 1](#topic-1)',
                '  - [Subtopic 1.1](#subtopic-11)',
                '  - [Subtopic 1.2](#subtopic-12)',
                '- [Topic 2](#topic-2)',
                '  - [Subtopic 2.1](#subtopic-21)',
                '  - [Subtopic 2.2](#subtopic-22)',
                '',
                '## Topic 1',
                '',
                '### Subtopic 1.1',
                '[Content]',
                '',
                '### Subtopic 1.2',
                '[Content]',
                '',
                '## Topic 2',
                '',
                '### Subtopic 2.1',
                '[Content]',
                '',
                '### Subtopic 2.2',
                '[Content]',
                '',
                '## Summary',
                '- [Key point 1]',
                '- [Key point 2]',
                '',
                '## Questions for Review',
                '1. [Question 1]',
                '2. [Question 2]',
                '',
                '## References',
                '- [Reference 1]',
                '- [Reference 2]',
                ''
            ]
            
            template = '\n'.join(sections)
            
            return {
                'success': True,
                'template': template,
                'error': None
            }
        except Exception as e:
            logger.error(f"Error in study template generation: {str(e)}")
            return {
                'success': False,
                'template': '',
                'error': str(e)
            }

    def save_template(self, template: str, output_file: Optional[str] = None) -> Dict[str, Union[bool, str, str]]:
        """
        Save the generated template to a file.
        
        Args:
            template (str): The template to save
            output_file (str, optional): The file path to save to
            
        Returns:
            dict: Operation result
        """
        try:
            if output_file:
                Path(output_file).write_text(template, encoding='utf-8')
                logger.info(f"Template saved to {output_file}")
                return {
                    'success': True,
                    'path': output_file,
                    'error': None
                }
            return {
                'success': False,
                'path': None,
                'error': 'No output file specified'
            }
        except Exception as e:
            logger.error(f"Error saving template: {str(e)}")
            return {
                'success': False,
                'path': None,
                'error': str(e)
            }

def main():
    """CLI interface for template generation."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate a template from markdown content.')
    parser.add_argument('--type', '-t', choices=['basic', 'meeting', 'project', 'research', 'study'], 
                      default='basic', help='Type of template to generate')
    parser.add_argument('--output', '-o', help='Output file for the template')
    
    args = parser.parse_args()
    
    try:
        generator = TemplateGenerator()
        result = generator.generate_template('', template_type=args.type)
        
        if result['success']:
            if args.output:
                save_result = generator.save_template(result['template'], args.output)
                if save_result['success']:
                    print(f"Template saved to: {save_result['path']}")
                else:
                    print(f"Error saving template: {save_result['error']}")
            else:
                print("\nGenerated Template:")
                print("=" * 40)
                print(result['template'])
                print("=" * 40)
        else:
            print(f"Error generating template: {result['error']}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    main() 