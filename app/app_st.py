import streamlit as st

# Set page config at the very beginning of the script
# This must be the first Streamlit command
st.set_page_config(
    page_title="Knowledge Assistant",
    page_icon="📄",
    layout="centered",
    initial_sidebar_state="collapsed"
)

import os
import sys
from pathlib import Path
import datetime
import json
import logging

from pdf_st import PDFConverterApp
from template_st import TemplateGeneratorApp
from conversation_st import PreferencesApp
from note_st import NoteProcessorApp
from kb_search_st import KnowledgeBaseSearchApp, initialize_kb
from kb_manager_st import KBManagerApp  # Import the KB Manager

sys.path.append(str(Path(__file__).parent.parent))
from tools.pdf_processor import PDFProcessor
from tools.template_generator import TemplateGenerator
from tools.user_preferences import UserPreferences
from tools.note_processor import NoteProcessor

# lancedb path for knowledge base
KB_MANAGER_DB_PATH = "data/lancedb"  

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DocumentToolsApp:
    def __init__(self):
        """Initialize the Knowledge Assistant application"""

        self.apply_custom_css()
        
        self.kb_db_path = KB_MANAGER_DB_PATH
        
        # Initialize kb resources using the cached_resource decorator to prevent reinitialization
        kb_resources = initialize_kb() 
        
        # Initialize sub-applications
        self.pdf_converter = PDFConverterApp(processor_class=PDFProcessor)
        self.template_generator = TemplateGeneratorApp(generator_class=TemplateGenerator)
        self.preferences_app = PreferencesApp()
        self.note_processor_app = NoteProcessorApp(processor_class=NoteProcessor)
        self.kb_search_app = KnowledgeBaseSearchApp(
            standalone_mode=False, 
            kb_resources=kb_resources
        )
        # Initialize KB Manager App with the same database path
        self.kb_manager_app = KBManagerApp(lancedb_path=self.kb_db_path, show_page_config=False)
        
        # Store knowledge base resources in session state for debugging
        if 'kb_resources_initialized' not in st.session_state:
            st.session_state.kb_resources_initialized = kb_resources["initialized"]
            
            if kb_resources["initialized"]:
                if kb_resources["kb"] is not None:
                    st.session_state.kb_resources_stats = kb_resources["kb"].get_stats()
                    st.session_state.kb_documents_available = True
                else:
                    st.session_state.kb_documents_available = False
                    
                st.session_state.kb_entries_available = kb_resources.get("has_entries_table", False)
                st.session_state.kb_resources = kb_resources
            else:
                st.session_state.kb_resources_error = kb_resources["error"]
                st.session_state.kb_documents_available = False
                st.session_state.kb_entries_available = kb_resources.get("has_entries_table", False)
                
                if "Table documents does not exist and create_if_not_exists is False" in kb_resources["error"]:
                    if kb_resources.get("has_entries_table", False):
                        st.session_state.kb_resources_error_type = "documents_table_not_found_but_entries_exist"
                    else:
                        st.session_state.kb_resources_error_type = "no_tables_found"
                else:
                    st.session_state.kb_resources_error_type = "general_error"
    
    def apply_custom_css(self):
        """Apply custom CSS styling to the app"""
        st.markdown("""
        <style>
            .main {
                background-color: var(--background-color);
                color: var(--text-color);
            }
            .stApp {
                max-width: 900px;
                margin: 0 auto;
            }
            .main .block-container {
                padding-top: 2rem;
                padding-bottom: 2rem;
            }
            .stTabs [data-baseweb="tab-list"] {
                gap: 8px;
            }
            .stTabs [data-baseweb="tab"] {
                background-color: #f1f3f4;
                border: none;
                border-radius: 4px 4px 0 0;
                padding: 10px 16px;
                height: auto;
                color: #333;
            }
            .stTabs [aria-selected="true"] {
                background-color: #2196F3;
                color: white !important;
            }
            h1, h2, h3 {
                color: #2196F3;
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
            /* Action buttons styling for KB Manager - override full width */
            .entry-row .stButton button,
            div[data-testid="column"] .stButton button {
                width: auto !important;
                border-radius: 4px;
                border: 1px solid #ddd;
                padding: 3px 10px;
                font-size: 0.5rem;
                font-weight: 200;
                min-width: 60px;
                transition: all 0.2s;
                background-color: #f8f9fa;
                color: #0066cc;
            }
            /* Action buttons container - better spacing */
            .entry-row .stButton,
            div[data-testid="column"] .stButton {
                margin: 0 2px;
                display: inline-block;
            }
            /* View buttons */
            button[data-testid^="stButton-"]:has(div:contains("View")) {
                color: #0066cc;
                border-color: #0066cc33;
                background-color: #f8f9fa;
            }
            button[data-testid^="stButton-"]:has(div:contains("View")):hover {
                background-color: #e7f0ff;
                border-color: #0066cc;
            }
            /* Edit buttons */
            button[data-testid^="stButton-"]:has(div:contains("Edit")) {
                color: #28a745;
                border-color: #28a74533;
                background-color: #f8f9fa;
            }
            button[data-testid^="stButton-"]:has(div:contains("Edit")):hover {
                background-color: #e7f5e7;
                border-color: #28a745;
            }
            /* Delete buttons */
            button[data-testid^="stButton-"]:has(div:contains("Delete")) {
                color: #dc3545;
                border-color: #dc354533;
                background-color: #f8f9fa;
            }
            button[data-testid^="stButton-"]:has(div:contains("Delete")):hover {
                background-color: #ffebee;
                border-color: #dc3545;
            }
            .tab-subheader {
                font-size: 26px;
                font-weight: 600;
                margin-bottom: 20px;
                color: #2196F3;
                padding-bottom: 10px;
                border-bottom: 1px solid #e0e0e0;
            }
            .upload-container {
                border: 2px dashed #ccc;
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                margin-bottom: 20px;
            }
            .success-msg {
                padding: 10px;
                border-radius: 5px;
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                color: #155724;
                margin-bottom: 10px;
            }
            .markdown-output {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
                font-family: monospace;
                white-space: pre-wrap;
                background-color: white;
                color: #333;
                height: 400px;
                overflow-y: auto;
            }
            .actions-container {
                display: flex;
                justify-content: center;
                gap: 10px;
                margin-top: 10px;
            }
            .preference-dialog {
                background-color: #f0f2f6;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
                border-left: 5px solid #2196F3;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            .debug-info {
                font-family: monospace;
                white-space: pre-wrap;
                background-color: #f5f5f5;
                padding: 10px;
                border-radius: 5px;
                max-height: 300px;
                overflow-y: auto;
            }
            .success-dialog {
                background-color: #e8f5e9;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
                border-left: 5px solid #4CAF50;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            .stButton button {
                width: 100%;
            }
            .stTextArea textarea {
                border-radius: 5px;
                border: 1px solid #ddd;
            }
            .stAlert {
                border-radius: 5px;
            }
            .button-container {
                display: flex;
                justify-content: center;
                gap: 10px;
                margin-top: 10px;
            }
            .search-result {
                background-color: var(--background-color);
                border-radius: 5px;
                padding: 15px;
                margin-bottom: 15px;
                border-left: 4px solid #4CAF50;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .search-result h4 {
                margin-top: 0;
                color: var(--text-color);
            }
            .search-result p {
                margin-bottom: 10px;
                color: var(--text-color);
            }
            .metadata {
                font-size: 0.8em;
                color: var(--secondary-text-color);
                margin-top: 10px;
                padding-top: 5px;
                border-top: 1px solid var(--border-color);
            }
            .relevance-high {
                color: #27AE60;
                font-weight: bold;
            }
            .relevance-medium {
                color: #F39C12;
            }
            .relevance-low {
                color: #E74C3C;
            }
            .answer-box {
                background-color: #E8F5E9;
                border-radius: 5px;
                padding: 20px;
                margin: 20px 0;
                border-left: 5px solid #2E7D32;
                color: #1B5E20;
            }
            .debug-box {
                background-color: #E3F2FD;
                border-radius: 5px;
                padding: 15px;
                margin: 20px 0;
                border-left: 5px solid #1976D2;
                font-family: monospace;
                font-size: 0.85em;
                white-space: pre-wrap;
                overflow-x: auto;
                color: #0D47A1;
            }
            .stTextInput input {
                color: var(--text-color) !important;
                background-color: var(--background-color) !important;
            }
            .app-description {
                margin-bottom: 1.5rem;
                color: #666;
            }
            .success-message {
                padding: 1rem;
                background-color: #d4edda;
                color: #155724;
                border-radius: 0.25rem;
                margin-bottom: 1rem;
            }
            .warning-message {
                padding: 1rem;
                background-color: #fff3cd;
                color: #856404;
                border-radius: 0.25rem;
                margin-bottom: 1rem;
            }
            .error-message {
                padding: 1rem;
                background-color: #f8d7da;
                color: #721c24;
                border-radius: 0.25rem;
                margin-bottom: 1rem;
            }
            /* Tab styling with radio buttons */
            .stRadio > div {
                display: flex;
                flex-direction: row;
                gap: 0;
            }
            .stRadio label {
                cursor: pointer;
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-bottom: none;
                padding: 10px 16px;
                margin: 0;
                border-radius: 4px 4px 0 0;
                font-weight: 500;
                color: #666;
                transition: all 0.2s;
            }
            .stRadio input:checked + label {
                background-color: white;
                color: #262730;
                border-top: 2px solid #1f77b4;
                border-bottom: 1px solid white;
                margin-bottom: -1px;
                position: relative;
                z-index: 10;
            }
            @media (prefers-color-scheme: dark) {
                .stRadio label {
                    background-color: #262730;
                    border-color: #3a3a3a;
                    color: #999;
                }
                .stRadio input:checked + label {
                    background-color: #1e1e1e;
                    color: white;
                    border-bottom: 1px solid #1e1e1e;
                }
                .app-description {
                    color: #999;
                }
            }
        </style>
        """, unsafe_allow_html=True)
    
    def render(self):
        """Render the Knowledge Assistant interface"""
        st.title("Knowledge Assistant")
        
        st.markdown("""
        <div class="app-description">
            <p>A comprehensive tool for managing and utilizing your knowledge base. 
            Convert PDFs to markdown, generate templates, process notes, manage AI preferences, and search your knowledge base.</p>
        </div>
        """, unsafe_allow_html=True)
        
        if 'active_tab' not in st.session_state:
            st.session_state.active_tab = "PDF Converter"
        
        # Create tabs using radio buttons that maintain state
        tab_options = ["PDF Converter", "Template Manager", "Note Processor", 
                      "AI Preferences", "Knowledge Base Search", "Knowledge Base Manager"]
        
        st.session_state.active_tab = st.radio("", tab_options, 
                                             index=tab_options.index(st.session_state.active_tab),
                                             label_visibility="collapsed")
        
        if st.session_state.active_tab == "PDF Converter":
            self.pdf_converter.render()
        
        elif st.session_state.active_tab == "Template Manager":
            self.template_generator.render()
            
        elif st.session_state.active_tab == "Note Processor":
            self.note_processor_app.render()
            
        elif st.session_state.active_tab == "AI Preferences":
            self.preferences_app.render()
            
        elif st.session_state.active_tab == "Knowledge Base Search":
            self.kb_search_app.render()
            
        elif st.session_state.active_tab == "Knowledge Base Manager":
            self.kb_manager_app.render()
        
        # Debug info in sidebar
        with st.sidebar:
            if st.checkbox("Show Debug Info", value=False, key="show_main_debug"):
                st.subheader("Knowledge Base Status")
                if hasattr(st.session_state, 'kb_resources_initialized'):
                    has_documents = st.session_state.get('kb_documents_available', False)
                    has_entries = st.session_state.get('kb_entries_available', False)
                    
                    if st.session_state.kb_resources_initialized:
                        st.success("✅ Knowledge Base Available")
                        
                        if has_documents:
                            st.write("### Documents Table")
                            if hasattr(st.session_state, 'kb_resources_stats'):
                                stats = st.session_state.kb_resources_stats
                                st.write(f"Table: {stats.get('table_name', 'documents')}")
                                st.write(f"Documents: {stats.get('row_count', 0)}")
                                st.write(f"Vector dimensions: {stats.get('vector_dimensions', 0)}")
                                st.write(f"Model: {stats.get('model_name', 'Unknown')}")
                        else:
                            st.info("ℹ️ Documents table not found (not required)")
                        
                        if has_entries:
                            st.write("### Entries Table")
                            entries_count = "Available"
                            if 'kb_resources' in st.session_state:
                                kb_res = st.session_state.kb_resources
                                if kb_res and kb_res.get('db_manager'):
                                    try:
                                        db = kb_res['db_manager'].db
                                        if "entries" in db.table_names():
                                            entries_table = db.open_table("entries")
                                            entries_count = f"{entries_table.count_rows()} records"
                                    except:
                                        pass
                            st.write(f"Entries: {entries_count}")
                        else:
                            st.warning("⚠️ Entries table not found")
                        
                        st.write(f"Database Path: {KB_MANAGER_DB_PATH}")
                    else:
                        error_type = st.session_state.get('kb_resources_error_type', 'general_error')
                        
                        if error_type == "documents_table_not_found_but_entries_exist":
                            st.warning("⚠️ Documents Table Not Found")
                            st.success("✅ Entries Table Available")
                            st.info("""
                            The search functionality will use the entries table for queries.
                            This is normal if you deleted the documents table.
                            """)
                        elif error_type == "no_tables_found":
                            st.error("❌ No Knowledge Base Tables Found")
                            st.info("""
                            **To fix this:**
                            1. Add entries using the KB Manager
                            2. Or add documents using the PDF Converter or Note Processor
                            """)
                        else:
                            st.error("❌ Knowledge Base Initialization Failed")
                        
                        if hasattr(st.session_state, 'kb_resources_error'):
                            with st.expander("Error Details"):
                                st.code(st.session_state.kb_resources_error)
                else:
                    st.warning("⚠️ Knowledge Base Status Unknown")
                
                st.subheader("Knowledge Base Session State")
                kb_vars = {k: v for k, v in st.session_state.items() if k.startswith('kb_')}
                
                for k in list(kb_vars.keys()):
                    if isinstance(kb_vars[k], dict) and 'kb' in kb_vars[k]:
                        kb_vars[k] = {key: "Object instance" if key == "kb" else value for key, value in kb_vars[k].items()}
                    if isinstance(kb_vars[k], dict) and 'db_manager' in kb_vars[k]:
                        kb_vars[k] = {key: "Object instance" if key == "db_manager" else value for key, value in kb_vars[k].items()}
                    if isinstance(kb_vars[k], dict) and 'qa_processor' in kb_vars[k]:
                        kb_vars[k] = {key: "Object instance" if key == "qa_processor" else value for key, value in kb_vars[k].items()}
                
                st.json(kb_vars)
        
        # Footer
        st.markdown("---")
        st.markdown(
            """
            <div style="text-align: center; color: #666;">
                Knowledge Assistant v1.0.0
            </div>
            """, 
            unsafe_allow_html=True
        )


if __name__ == "__main__":
    app = DocumentToolsApp()
    app.render()