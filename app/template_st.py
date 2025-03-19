import streamlit as st
import os
from pathlib import Path
import base64
import sys
from pathlib import Path

parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))
from tools.template_generator import TemplateGenerator

class TemplateGeneratorApp:
    def __init__(self, templates_folder=None, generator_class=None):
        """
        Initialize the Template Generator application
        
        Args:
            templates_folder (str): Path to store saved templates
            generator_class: The template generator class to use
        """
        self.generator_class = generator_class or TemplateGenerator
        
        if templates_folder is None:
            self.templates_folder = Path(parent_dir) / "data" / "templates"
        else:
            self.templates_folder = Path(templates_folder)
        
        self.templates_folder.mkdir(parents=True, exist_ok=True)
        
        if generator_class:
            self.template_generator = self.generator_class()
        else:
            self.template_generator = None
            
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state variables for template generator"""
        if 'template_content' not in st.session_state:
            st.session_state.template_content = None
        if 'template_type' not in st.session_state:
            st.session_state.template_type = None
        if 'original_filename' not in st.session_state:
            st.session_state.original_filename = None
        if 'confirm_delete' not in st.session_state:
            st.session_state.confirm_delete = None
    
    def render(self):
        """Render the template generator interface"""
        saved_templates = self._get_saved_templates()
        
        self._render_template_selector()
        
        if saved_templates:
            self._render_saved_templates(saved_templates)
        
        if st.session_state.template_content:
            self._render_template_editor()
    
    def _render_template_selector(self):
        """Render the template type selector and generation button"""
        col1, col2 = st.columns([3, 1])
        
        with col1:
            template_type = st.selectbox(
                "Template Type:", 
                ["", "basic", "meeting", "project", "research", "study"],
                format_func=lambda x: {
                    "": "-- Select a template --",
                    "basic": "Basic Note",
                    "meeting": "Meeting Notes",
                    "project": "Project Documentation",
                    "research": "Research Notes",
                    "study": "Study Notes"
                }.get(x, x)
            )
        
        with col2:
            generate_btn = st.button("Generate Template", disabled=not template_type)
        
        if generate_btn and template_type:
            self._generate_template(template_type)
    
    def _generate_template(self, template_type):
        """Generate a template based on the selected type"""
        with st.spinner("Generating template..."):
            result = self.template_generator.generate_template('', template_type=template_type)
            
            if result['success']:
                st.session_state.template_content = result['template']
                st.session_state.template_type = template_type
                st.session_state.original_filename = ''
            else:
                st.error(f"Error generating template: {result['error']}")
    
    def _render_saved_templates(self, saved_templates):
        """Render the list of saved templates"""
        st.subheader("Saved Templates")
        
        with st.expander("View saved templates", expanded=False):
            for template in saved_templates:
                col1, col2, col3, col4 = st.columns([4, 1, 1, 1])
                
                with col1:
                    st.write(template)
                
                with col2:
                    if st.button("Load", key=f"load_{template}"):
                        self._load_template(template)
                
                with col3:
                    if st.button("Edit", key=f"edit_{template}"):
                        self._load_template(template)
                        st.markdown('<div id="template_editor"></div>', unsafe_allow_html=True)
                        st.markdown(
                            """
                            <script>
                                document.querySelector('#template_editor').scrollIntoView({
                                    behavior: 'smooth'
                                });
                            </script>
                            """,
                            unsafe_allow_html=True
                        )
                
                with col4:
                    if st.session_state.confirm_delete == template:
                        if st.button("✓", key=f"confirm_{template}", help="Confirm deletion"):
                            self._delete_template(template)
                            st.session_state.confirm_delete = None
                        if st.button("✗", key=f"cancel_{template}", help="Cancel deletion"):
                            st.session_state.confirm_delete = None
                            st.rerun()
                    else:
                        if st.button("Delete", key=f"delete_{template}"):
                            st.session_state.confirm_delete = template
                            st.rerun()
    
    def _render_template_editor(self):
        """Render the template editor and related actions"""
        st.subheader("Template Content")
        
        template_text = st.text_area(
            "Edit Template:",
            value=st.session_state.template_content,
            height=300,
            key="template_editor"
        )
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            template_name = st.text_input("Template Name:") 
        with col2:
            save_btn = st.button("Save Template", disabled=not template_name)
        with col3:
            if st.button("Copy to Clipboard"):
                st.markdown(
                    """
                    <script>
                        const text = document.querySelector('[data-testid="stTextArea"] textarea').value;
                        navigator.clipboard.writeText(text);
                    </script>
                    """,
                    unsafe_allow_html=True
                )
                st.success("Copied to clipboard!")
        
        if save_btn and template_name:
            self._save_template(template_text, template_name)
    
    def _get_saved_templates(self):
        """Get a list of saved templates."""
        templates = []
        
        try:
            for file_path in self.templates_folder.glob('*.md'):
                templates.append(file_path.name)
        except Exception as e:
            st.error(f"Error reading templates: {str(e)}")
        
        return templates
    
    def _load_template(self, template_name):
        """Load a saved template for editing."""
        template_path = self.templates_folder / template_name
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            st.session_state.template_content = template_content
            st.session_state.template_type = 'custom'
            st.session_state.original_filename = template_name
            
        except Exception as e:
            st.error(f"Error loading template: {str(e)}")
    
    def _save_template(self, template_text, template_name):
        """Save a template with the given name"""
        if not template_name.endswith('.md'):
            template_name += '.md'
        
        template_path = self.templates_folder / template_name
        result = self.template_generator.save_template(template_text, str(template_path))
        
        if result['success']:
            st.success(f"Template '{template_name}' saved successfully!")
            st.info(f"Saved to: {template_path}")
            
            self._get_saved_templates()
            
            st.session_state.template_name = ""
            st.session_state.template_text = ""
            
            st.rerun()
        else:
            st.error(f"Error saving template: {result['error']}")

    def _delete_template(self, template_name):
        """Delete a saved template."""
        template_path = self.templates_folder / template_name
        
        try:
            if template_path.exists():
                template_path.unlink()
                st.success(f"Template '{template_name}' deleted successfully!")
                st.rerun()
            else:
                st.error(f"Template '{template_name}' not found.")
        except Exception as e:
            st.error(f"Error deleting template: {str(e)}")


if __name__ == '__main__':
    
    st.set_page_config(
        page_title="Template Generator",
        page_icon="📄",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    st.markdown("""
    <style>
        .main {
            background-color: #f8f9fa;
        }
        .stApp {
            max-width: 900px;
            margin: 0 auto;
        }
        .stButton > button {
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 10px 24px;
            font-weight: 500;
        }
        .stButton > button:hover {
            background-color: #0b7dda;
        }
        .template-list {
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 10px;
        }
        .template-item {
            padding: 10px;
            border-bottom: 1px solid #e0e0e0;
        }
        h1, h2, h3 {
            color: #2196F3;
        }
        /* Template action buttons */
        div[data-testid="column"] > div.stButton > button {
            width: auto;
            padding: 3px 15px;
            font-size: 0.8rem;
        }
        /* Load button */
        button[data-testid^="stButton-"]:has(div:contains("Load")) {
            background-color: #4CAF50;
        }
        button[data-testid^="stButton-"]:has(div:contains("Load")):hover {
            background-color: #388E3C;
        }
        /* Edit button */
        button[data-testid^="stButton-"]:has(div:contains("Edit")) {
            background-color: #2196F3;
        }
        button[data-testid^="stButton-"]:has(div:contains("Edit")):hover {
            background-color: #1976D2;
        }
        /* Delete button */
        button[data-testid^="stButton-"]:has(div:contains("Delete")) {
            background-color: #F44336;
        }
        button[data-testid^="stButton-"]:has(div:contains("Delete")):hover {
            background-color: #D32F2F;
        }
        /* Confirmation buttons */
        button[data-testid^="stButton-"]:has(div:contains("✓")) {
            background-color: #4CAF50;
            padding: 3px 10px;
        }
        button[data-testid^="stButton-"]:has(div:contains("✗")) {
            background-color: #F44336;
            padding: 3px 10px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("Template Generator")
    
    app = TemplateGeneratorApp(generator_class=TemplateGenerator)
    app.render()
    
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666;">
            Template Generator | Streamlit App
        </div>
        """, 
        unsafe_allow_html=True
    )

