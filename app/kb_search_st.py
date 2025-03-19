import streamlit as st
import os
import sys
from pathlib import Path
import time
from datetime import datetime
import pandas as pd
import json
import traceback
import threading

parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))
from tools.knowledge_base import KnowledgeBase
from tools.qa_processor import QAProcessor
from tools.lancedb_manager import LanceDBManager
from tools.user_preferences import UserPreferences

KB_MANAGER_DB_PATH = "data/lancedb"

# Initialize knowledge base outside the app class to prevent reinitialization
# on each Streamlit rerun
@st.cache_resource
def initialize_kb():
    """Initialize the knowledge base and QA processor as a cached resource"""
    try:
        # Use the same database path as KBManagerApp
        # Set create_if_not_exists to False to prevent accidental creation of
        # a new table when the database already exists
        try:
            kb = KnowledgeBase(
                db_uri=KB_MANAGER_DB_PATH,
                create_if_not_exists=False 
            )
        except Exception as e:
            print(f"Note: LanceDB table not found - {str(e)}")
            kb = None
        
        db_manager = LanceDBManager(db_path=KB_MANAGER_DB_PATH)
        
        # initialize QA processor if KB is available
        # or if there are entries in the entries table
        has_entries = False
        try:
            db = db_manager.db
            if "entries" in db.table_names():
                entries_table = db.open_table("entries")
                has_entries = entries_table.count_rows() > 0
                print(f"Found entries table with {entries_table.count_rows()} records")
        except Exception as e:
            print(f"Error checking entries table: {str(e)}")
            
        qa_processor = None
        if kb is not None or has_entries:
            qa_processor = QAProcessor(knowledge_base=kb, db_manager=db_manager)
            if kb is None and has_entries:
                print("Initializing QA processor with entries table (no documents table)")
            
            return {
                "kb": kb,
                "db_manager": db_manager,
                "qa_processor": qa_processor,
                "initialized": True,
                "has_documents_table": kb is not None,
                "has_entries_table": has_entries,
                "error": None
            }
        else:
            return {
                "kb": None,
                "db_manager": db_manager,
                "qa_processor": None,
                "initialized": False,
                "has_documents_table": False,  
                "has_entries_table": False,
                "error": "No knowledge base data found. Either documents table or entries table must exist and contain data."
            }
    except Exception as e:
        error_msg = f"Error initializing knowledge base: {str(e)}\n{traceback.format_exc()}"
        return {
            "kb": None,
            "db_manager": None,
            "qa_processor": None,
            "initialized": False,
            "has_documents_table": False,
            "has_entries_table": False,
            "error": error_msg
        }

class KnowledgeBaseSearchApp:
    def __init__(self, standalone_mode=False, kb_resources=None):
        """Initialize the Knowledge Base Search application
        
        Args:
            standalone_mode (bool): Whether the app is running in standalone mode.
                                   If True, set_page_config will be called.
            kb_resources (dict): Resources for the knowledge base, including kb and qa_processor.
                                If None, initialize_kb() will be called.
        """
        if standalone_mode:
            st.set_page_config(
                page_title="Knowledge Base Search",
                page_icon="📚",
                layout="wide",
                initial_sidebar_state="collapsed"
            )
        
        # Add prefix for session state variables to avoid conflicts when integrated with app_st.py
        self.prefix = "kb_" if not standalone_mode else ""
        
        self._apply_custom_css()
        self.user_preferences = UserPreferences()
        self._init_session_state()
        
        if kb_resources and kb_resources.get("initialized", False):
            self.kb = kb_resources.get("kb")
            self.db_manager = kb_resources.get("db_manager")
            self.qa_processor = kb_resources.get("qa_processor")
            
            if self.kb:
                kb_stats = self.kb.get_stats()
                st.session_state[f"{self.prefix}kb_stats"] = kb_stats
                print(f"Using provided knowledge base resources. Stats: {kb_stats}")
        else:
            resources = initialize_kb()
            self.kb = resources.get("kb")
            self.db_manager = resources.get("db_manager")
            self.qa_processor = resources.get("qa_processor")
            
            if resources.get("initialized", False):
                if self.kb:
                    kb_stats = self.kb.get_stats()
                    st.session_state[f"{self.prefix}kb_stats"] = kb_stats
                    print(f"Initialized knowledge base. Stats: {kb_stats}")
            else:
                st.session_state[f"{self.prefix}error"] = resources.get("error", "Unknown error initializing knowledge base")
                print(f"Error initializing knowledge base: {resources.get('error')}")
    
    def _apply_custom_css(self):
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
            .footer {
                margin-top: 50px;
                text-align: center;
                color: var(--secondary-text-color);
                font-size: 0.8em;
            }
            .success-dialog {
                margin-bottom: 20px;
            }
            .error-box {
                background-color: var(--error-bg-color);
                color: var(--error-text-color);
                padding: 16px;
                border-radius: 8px;
                margin-bottom: 16px;
            }
            .warning-box {
                background-color: var(--warning-bg-color);
                color: var(--warning-text-color);
                padding: 16px;
                border-radius: 8px;
                margin-bottom: 16px;
            }
            .success-box {
                background-color: var(--success-bg-color);
                color: var(--success-text-color);
                padding: 16px;
                border-radius: 8px;
                margin-bottom: 16px;
            }
            .debug-box {
                background-color: var(--secondary-bg-color);
                color: var(--secondary-text-color);
                padding: 16px;
                border-radius: 8px;
                margin-bottom: 16px;
                font-family: monospace;
                white-space: pre-wrap;
            }
            .search-container {
                margin-bottom: 20px;
            }
            .search-button-container {
                display: flex;
                justify-content: flex-end;
                margin-top: 10px;
            }
            /* Fix for Streamlit text input */
            .stTextInput input {
                color: var(--text-color) !important;
                background-color: var(--background-color) !important;
            }
          
            /* Source link buttons styling */
            .stButton button[data-baseweb="button"] {
                width: 100%;
                margin: 5px 0;
                padding: 8px 10px;
                font-size: 0.9em;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                border-radius: 4px;
            }
            
            /* Source grid layout */
            .source-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 10px;
                margin-bottom: 20px;
            }
            
            /* Content preview styling */
            .content-preview {
                background-color: var(--secondary-bg-color);
                padding: 10px;
                border-radius: 4px;
                margin: 10px 0;
                border-left: 3px solid #2196F3;
            }
            
            /* View/Hide content buttons */
            .view-button button {
                background-color: #2196F3 !important;
                color: white !important;
            }
            
            .hide-button button {
                background-color: #f44336 !important;
                color: white !important;
                margin-top: 10px;
            }
                
            .stCheckbox [data-baseweb="checkbox"] div[data-testid="stMarkdownContainer"] p {
                color: #2196F3 !important;
                font-weight: 500;
            }
            .stCheckbox [data-baseweb="checkbox"] [data-testid="stMarkdownContainer"] {
                color: #2196F3 !important;
            }
            
            .settings-expander {
                padding: 10px 0;
            }
            
            .slider-container {
                margin: 20px 0;
            }
            /* Make the expander header more prominent */
            button[data-baseweb="accordion"] div[data-testid="stMarkdownContainer"] p {
                color: #2196F3 !important;
                font-weight: bold !important;
                font-size: 1.1em !important;
            }
            /* Upload container styles */
            .upload-container {
                padding: 10px 0;
            }
            .stExpander {
                margin-bottom: 20px !important;
            }
            button[data-baseweb="accordion"] {
                background-color: var(--background-color) !important;
                border-radius: 8px !important;
                padding: 10px !important;
            }
            .stExpander button p {
                font-weight: 600 !important;
                color: var(--text-color) !important;
            }
            /* Compact sliders */
            .slider-container .stSlider {
                padding-top: 0 !important;
                padding-bottom: 0 !important;
            }
            /* Checkbox label style */
            .stCheckbox [data-baseweb="checkbox"] div[data-testid="stMarkdownContainer"] p {
                color: #2196F3 !important;
                font-weight: 500;
            }
            .stCheckbox [data-baseweb="checkbox"] [data-testid="stMarkdownContainer"] {
                color: #2196F3 !important;
            }
            /* File upload section styling */
            .upload-section {
                border: 2px dashed #aaa;
                border-radius: 8px;
                padding: 20px;
                margin: 15px 0;
                background-color: var(--background-color);
                text-align: center;
            }
            .upload-icon {
                font-size: 24px;
                margin-bottom: 10px;
            }
            /* Progress indicator styling */
            .stProgress .st-bo {
                background-color: #2196F3;
            }
            .stProgress .st-bp {
                height: 10px;
                border-radius: 5px;
            }
        </style>
        """, unsafe_allow_html=True)
    
    def _process_with_qa(self, query, search_results):
        """
        Process the search results with QA processor to generate an answer.
        Returns the answer and the search results, or just the search results if QA fails.
        """
        if not st.session_state.get(f"{self.prefix}use_qa", True) or not hasattr(self, 'qa_processor') or self.qa_processor is None:
            return search_results
        
        print("Starting AI processing with QA processor")
        try:
            # Use threading with timeout to prevent hanging
            result_container = {"answer": None, "error": None, "preferences_applied": False}
            
            def process_question():
                try:
                    relevance_threshold = self._get_relevance_threshold()

                    user_preferences_str = ""
                    preferences_applied = False
                    
                    # Add user preferences with contents and custom prompt if available
                    if hasattr(self, 'user_preferences') and self.user_preferences:
                        user_preferences_str = self.user_preferences.get_prompt_customization()
                        if user_preferences_str:
                            preferences_applied = True
                            print(f"Applying user preferences to AI response: {user_preferences_str}")
                    
                    if search_results:
                        docs_for_qa = []
                        for result in search_results:
                            docs_for_qa.append({
                                'text': result.get('content', ''),
                                'title': result.get('title', 'Untitled'),
                                'source': result.get('source', 'Unknown'),
                                'score': result.get('score', 1.0)
                            })
                        
                        answer_result = self.qa_processor.answer_question_with_docs(
                            query + (f"\n\nPlease apply these preferences: {user_preferences_str}" if user_preferences_str else ""),
                            docs=docs_for_qa,
                            relevance_threshold=relevance_threshold
                        )
                        
                        result_container["answer"] = answer_result
                        result_container["preferences_applied"] = preferences_applied
                    else:
                        answer_result = self.qa_processor.answer_question(
                            query + (f"\n\nPlease apply these preferences: {user_preferences_str}" if user_preferences_str else ""),
                            max_results=5,
                            relevance_threshold=relevance_threshold
                        )
                        
                        result_container["answer"] = answer_result
                        result_container["preferences_applied"] = preferences_applied
                except Exception as e:
                    result_container["error"] = str(e)
            
            qa_thread = threading.Thread(target=process_question)
            qa_thread.daemon = True
            qa_thread.start()
            timeout = st.session_state.get(f"{self.prefix}qa_timeout", 30)  
            qa_thread.join(timeout)
            
            if qa_thread.is_alive():
                print(f"QA processing timed out after {timeout} seconds")
                if hasattr(st, 'session_state'):
                    st.session_state[f"{self.prefix}error"] = f"AI processing timed out after {timeout} seconds"
                return search_results
            
            if result_container["error"]:
                print(f"QA processing error: {result_container['error']}")
                if hasattr(st, 'session_state'):
                    st.session_state[f"{self.prefix}error"] = f"AI processing error: {result_container['error']}"
                return search_results
            
            if result_container["answer"]:
                st.session_state[f"{self.prefix}preferences_applied"] = result_container["preferences_applied"]
                
                return {
                    "answer": result_container["answer"]["answer"],
                    "sources": result_container["answer"]["sources"],
                    "search_results": search_results,
                    "preferences_applied": result_container["preferences_applied"]
                }
            
            return search_results
        except Exception as e:
            print(f"Exception during QA processing: {str(e)}")
            if hasattr(st, 'session_state'):
                st.session_state[f"{self.prefix}error"] = f"Exception during AI processing: {str(e)}"
            return search_results
            
    def _init_session_state(self):
        """Initialize session state variables."""
        prefix = self.prefix
        
        if f"{prefix}query" not in st.session_state:
            st.session_state[f"{prefix}query"] = ""
        
        if f"{prefix}search_triggered" not in st.session_state:
            st.session_state[f"{prefix}search_triggered"] = False
        
        if f"{prefix}results" not in st.session_state:
            st.session_state[f"{prefix}results"] = None
            
        if f"{prefix}error" not in st.session_state:
            st.session_state[f"{prefix}error"] = None
            
        if f"{prefix}preferences_applied" not in st.session_state:
            st.session_state[f"{prefix}preferences_applied"] = False
            
        if f"{prefix}last_updated" not in st.session_state:
            st.session_state[f"{prefix}last_updated"] = None
            
        if f"{prefix}api_key_status" not in st.session_state:
            st.session_state[f"{prefix}api_key_status"] = "unknown"
            
        if f"{prefix}use_qa" not in st.session_state:
            st.session_state[f"{prefix}use_qa"] = True
            
        if f"{prefix}relevance_threshold" not in st.session_state:
            st.session_state[f"{prefix}relevance_threshold"] = 0.4
            
        if f"{prefix}qa_timeout" not in st.session_state:
            st.session_state[f"{prefix}qa_timeout"] = 30
            
        if f"{prefix}result_limit" not in st.session_state:
            st.session_state[f"{prefix}result_limit"] = 10
            
        if f"{prefix}show_debug" not in st.session_state:
            st.session_state[f"{prefix}show_debug"] = False
            
        if f"{prefix}viewing_content" not in st.session_state:
            st.session_state[f"{prefix}viewing_content"] = None
            
        if f"{prefix}viewing_source" not in st.session_state:
            st.session_state[f"{prefix}viewing_source"] = None
            
        if f"{prefix}selected_category" not in st.session_state:
            st.session_state[f"{prefix}selected_category"] = None
            
        if f"{prefix}selected_topic" not in st.session_state:
            st.session_state[f"{self.prefix}selected_topic"] = None
            
        if f"{prefix}show_filters" not in st.session_state:
            st.session_state[f"{prefix}show_filters"] = False

    def _display_category_topic_filters(self):
        """Display category and topic filters for the search."""
        # Only show filters if we have a db_manager
        if not hasattr(self, 'db_manager') or self.db_manager is None:
            return None, None
        
        show_filters = st.checkbox(
            "Show Category/Topic Filters", 
            value=st.session_state.get(f"{self.prefix}show_filters", False),
            key=f"{self.prefix}show_filters"
        )
        
        category_id = None
        topic_id = None
        
        if show_filters:
            with st.container():
                st.markdown("### Filter by Category and Topic")
                
                try:
                    categories = []
                    try:
                        if self.db_manager and hasattr(self.db_manager, 'get_categories'):
                            categories = self.db_manager.get_categories()
                    except Exception as e:
                        st.warning(f"Error loading categories: {str(e)}")
                    
                    if not categories.empty:
                        category_options = [("", "All Categories")] + [(cat["id"], cat["name"]) for _, cat in categories.iterrows()]
                        selected_category = st.session_state.get(f"{self.prefix}selected_category", "")
                        
                        category_name_map = {id: name for id, name in category_options}
                        
                        selected_category_name = category_name_map.get(selected_category, "All Categories")
                        selected_index = next((i for i, (id, _) in enumerate(category_options) if id == selected_category), 0)
                        
                        new_category = st.selectbox(
                            "Category",
                            options=[name for _, name in category_options],
                            index=selected_index,
                            key=f"{self.prefix}category_selector"
                        )
                        
                        new_category_id = next((id for id, name in category_options if name == new_category), "")
                        if new_category_id != selected_category:
                            st.session_state[f"{self.prefix}selected_category"] = new_category_id
                            st.session_state[f"{self.prefix}selected_topic"] = None
                            st.rerun()
                        
                        category_id = st.session_state.get(f"{self.prefix}selected_category")
                        
                        if category_id:
                            topics = []
                            try:
                                if self.db_manager and hasattr(self.db_manager, 'get_topics'):
                                    topics = self.db_manager.get_topics(category_id)
                            except Exception as e:
                                st.warning(f"Error loading topics: {str(e)}")
                            
                            if not topics.empty:
                                topic_options = [("", "All Topics")] + [(topic["id"], topic["name"]) for _, topic in topics.iterrows()]
                                selected_topic = st.session_state.get(f"{self.prefix}selected_topic", "")
                                
                                topic_name_map = {id: name for id, name in topic_options}
                                
                                selected_topic_name = topic_name_map.get(selected_topic, "All Topics")
                                selected_index = next((i for i, (id, _) in enumerate(topic_options) if id == selected_topic), 0)
                                new_topic = st.selectbox(
                                    "Topic",
                                    options=[name for _, name in topic_options],
                                    index=selected_index,
                                    key=f"{self.prefix}topic_selector"
                                )
                                
                                new_topic_id = next((id for id, name in topic_options if name == new_topic), "")
                                
                                if new_topic_id != selected_topic:
                                    st.session_state[f"{self.prefix}selected_topic"] = new_topic_id
                                
                                topic_id = st.session_state.get(f"{self.prefix}selected_topic")
                    else:
                        st.info("No categories available. Add categories and topics in the Knowledge Base Manager.")
                except Exception as e:
                    st.error(f"Error displaying category/topic filters: {str(e)}")
            
            st.markdown("---")
        
        return category_id, topic_id

    def _get_relevance_threshold(self):
        """Get the relevance threshold from session state."""
        return st.session_state.get(f"{self.prefix}relevance_threshold", 0.4)
    
    def _display_settings_in_expander(self):
        """Display search settings in an expander in the main content area."""
        with st.expander("🔧 Search Settings", expanded=False):
            st.markdown("### Search Settings")
            
            with st.container():
                st.markdown(
                    '<div style="background-color: rgba(33, 150, 243, 0.1); padding: 10px; '
                    'border-radius: 5px; margin-bottom: 15px;">'
                    '🤖 <span style="color: #2196F3; font-weight: 500;">AI-powered search is enabled</span>'
                    '</div>',
                    unsafe_allow_html=True
                )
                
                st.markdown("#### Relevance Threshold")
                st.markdown(
                    "Lower values make the search more selective (requiring higher relevance). "
                    "Higher values include more results that may be less relevant."
                )
                relevance_threshold = st.slider(
                    "Relevance Threshold", 
                    min_value=0.1, 
                    max_value=0.9, 
                    value=st.session_state.get(f"{self.prefix}relevance_threshold", 0.4),
                    step=0.05,
                    key=f"{self.prefix}relevance_threshold_slider",
                    help="Lower values are more strict, requiring closer matches. Higher values include more diverse results."
                )
                
                st.markdown("#### Maximum Search Results")
                result_limit = st.slider(
                    "Max Search Results", 
                    min_value=1, 
                    max_value=25, 
                    value=st.session_state.get(f"{self.prefix}result_limit", 10),
                    step=1,
                    key=f"{self.prefix}result_limit_slider",
                    help="Maximum number of search results to retrieve."
                )
                show_debug = st.checkbox(
                    "Show Debug Information", 
                    value=st.session_state.get(f"{self.prefix}show_debug", False),
                    key=f"{self.prefix}show_debug_checkbox"
                )
    
    def _handle_enter_key(self):
        """Handle Enter key press in the search input."""
        current_query = st.session_state.get(f"{self.prefix}query_input", "")
        if current_query and current_query != st.session_state.get(f"{self.prefix}query", ""):
            st.session_state[f"{self.prefix}query"] = current_query
            st.session_state[f"{self.prefix}search_triggered"] = True
    
    def _display_debug_info(self, query, search_results, answer=None, error=None):
        """Display debug information about the search and QA process."""
        with st.expander("Debug Information", expanded=False):
            st.markdown("### Debug Information")
            
            debug_info = {
                "query": query,
                "timestamp": str(datetime.now()),
                "relevance_threshold": self._get_relevance_threshold(),
                "max_results": st.session_state.get(f"{self.prefix}result_limit", 10),
                "use_qa": st.session_state.get(f"{self.prefix}use_qa", True),
                "qa_timeout": st.session_state.get(f"{self.prefix}qa_timeout", 30),
                "error": error
            }
            
            if search_results:
                if isinstance(search_results, dict) and "search_results" in search_results:
                    result_info = []
                    for i, result in enumerate(search_results.get("search_results", [])):
                        result_info.append({
                            "index": i,
                            "title": result.get("title", "Untitled"),
                            "score": result.get("score", 0),
                            "source": result.get("source", "Unknown"),
                            "content_length": len(result.get("content", "")) if "content" in result else 0
                        })
                    debug_info["search_results"] = result_info
                    debug_info["answer_length"] = len(search_results.get("answer", "")) if "answer" in search_results else 0
                    debug_info["sources_count"] = len(search_results.get("sources", [])) if "sources" in search_results else 0
                else:
                    result_info = []
                    for i, result in enumerate(search_results):
                        result_info.append({
                            "index": i,
                            "title": result.get("title", "Untitled"),
                            "score": result.get("score", 0),
                            "source": result.get("source", "Unknown"),
                            "content_length": len(result.get("content", "")) if "content" in result else 0
                        })
                    debug_info["search_results"] = result_info
            
            debug_json = json.dumps(debug_info, indent=2)
            st.code(debug_json, language="json")
            
            st.download_button(
                label="Download Debug Info",
                data=debug_json,
                file_name=f"kb_search_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
            )
    
    def render(self):
        """Render the Knowledge Base Search application."""
        st.title("Knowledge Base Search")
        st.markdown("Search across your knowledge base for relevant information. Get AI-powered answers to your questions.")
        
        self._display_settings_in_expander()
        
        category_id, topic_id = self._display_category_topic_filters()
        search_col1, search_col2 = st.columns([5, 1])
        with search_col1:
            query = st.text_input(
                "Search Query", 
                value=st.session_state.get(f"{self.prefix}query", ""),
                key=f"{self.prefix}query_input",
                placeholder="Enter your search query or question...",
                on_change=self._handle_enter_key
            )
        
        with search_col2:
            search_button = st.button("Search", use_container_width=True)
            
        if search_button or st.session_state.get(f"{self.prefix}search_triggered", False):
            st.session_state[f"{self.prefix}search_triggered"] = False
            
            if query:
                st.session_state[f"{self.prefix}query"] = query
                st.session_state[f"{self.prefix}error"] = None
                st.session_state[f"{self.prefix}results"] = None
                with st.spinner("Searching knowledge base..."):
                    results = self._search_knowledge_base(
                        query,
                        category_id=category_id,
                        topic_id=topic_id,
                        limit=st.session_state.get(f"{self.prefix}result_limit", 10)
                    )
                    st.session_state[f"{self.prefix}results"] = results
                    st.session_state[f"{self.prefix}last_updated"] = datetime.now()
                st.rerun()
        
        results = st.session_state.get(f"{self.prefix}results")
        if results:
            if isinstance(results, dict) and "answer" in results:
                st.markdown("### AI-Generated Answer")
                st.markdown(f"<div class='answer-box'>{results['answer']}</div>", unsafe_allow_html=True)
                
                if results.get("preferences_applied", False):
                    st.info("User preferences have been applied to this answer.")
                
                if results.get("sources"):
                    st.markdown("### Sources")
                    for i, source in enumerate(results.get("sources", [])):
                        title = source.get('title', 'Untitled')
                        source_name = source.get('source', 'Unknown')
                        score = source.get('relevance_score', 0.0)
                        relevance_class = "relevance-high" if score < 0.3 else "relevance-medium" if score < 0.5 else "relevance-low"
                        
                        st.markdown(f"**Source {i+1}**: {title} ({source_name}) - Relevance: "
                                    f"<span class='{relevance_class}'>{score:.4f}</span>", unsafe_allow_html=True)
            
            st.markdown("### Search Results")
            if isinstance(results, dict) and "search_results" in results:
                result_list = results.get("search_results", [])
            else:
                result_list = results
                
            if not result_list:
                st.info("No search results found. Try a different query or adjust the relevance threshold.")
            else:
                for i, result in enumerate(result_list):
                    self._display_result_item(result)
        
        if st.session_state.get(f"{self.prefix}show_debug", False):
            self._display_debug_info(
                query=st.session_state.get(f"{self.prefix}query", ""),
                search_results=results,
                answer=results.get('answer', None) if isinstance(results, dict) else None,
                error=st.session_state.get(f"{self.prefix}error", None)
            )
            
        st.markdown("---")
        st.markdown(
            "<div class='footer'>Knowledge Base Search | Powered by LanceDB and OpenAI | "
            f"Last updated: {st.session_state.get(f'{self.prefix}last_updated', 'Never')}</div>",
            unsafe_allow_html=True
        )
        
    def _search_knowledge_base(self, query, category_id=None, topic_id=None, limit=None):
        """
        Search the knowledge base using the db_manager and fall back to the knowledge base if needed.
        """
        if not query:
            return []
        
        if limit is None:
            limit = st.session_state.get(f"{self.prefix}result_limit", 10)
        
        print(f"Starting search for query: {query} with limit: {limit}")
        
        debug_info = {
            "query": query,
            "category_id": category_id,
            "topic_id": topic_id,
            "limit": limit,
            "timestamp": str(datetime.now()),
            "steps": []
        }
        
        print(f"Calling db_manager.search_entries with query: {query}")
        search_results = []
        
        db_search_start = time.time()
        if hasattr(self, 'db_manager') and self.db_manager is not None:
            try:
                kwargs = {}
                if category_id:
                    kwargs["category_id"] = category_id
                if topic_id:
                    kwargs["topic_id"] = topic_id
                
                raw_results = self.db_manager.search_entries(query, limit=limit, **kwargs)
                db_search_time = time.time() - db_search_start
                
                debug_info["steps"].append({
                    "step": "db_manager.search_entries",
                    "time_taken": f"{db_search_time:.2f}s",
                    "results_count": len(raw_results) if raw_results else 0,
                    "filters": {"category_id": category_id, "topic_id": topic_id}
                })
                
                if raw_results:
                    search_results = raw_results
                    print(f"Found {len(search_results)} results from db_manager")
                else:
                    print("No results from db_manager")
            except Exception as e:
                db_search_time = time.time() - db_search_start
                error_msg = f"Error searching entries: {str(e)}"
                print(error_msg)
                
                debug_info["steps"].append({
                    "step": "db_manager.search_entries",
                    "time_taken": f"{db_search_time:.2f}s",
                    "error": error_msg
                })
        
        if not search_results and hasattr(self, 'kb') and self.kb is not None:
            # allow fall back due to integration of kb and lancedb_manager
            should_fallback = True
            
            keywords_to_prevent_fallback = [
                "ai", "artificial intelligence", "machine learning",
                "javascript", "react", "python", "programming"
            ]
            
            query_lower = query.lower().strip()
            for keyword in keywords_to_prevent_fallback:
                if keyword in query_lower:
                    print(f"Query contains keyword '{keyword}'. Being selective with fallback.")
                    should_fallback = False
                    break
            
            if category_id or topic_id:
                print("Category or topic filters active. Skipping fallback to documents table.")
                should_fallback = False
            
            if should_fallback:
                kb_search_start = time.time()
                try:
                    print("No results from db_manager, falling back to knowledge base search")
                    
                    if not hasattr(self.kb, 'search'):
                        print("KB does not have search method, skipping fallback")
                        debug_info["steps"].append({
                            "step": "kb.search",
                            "error": "KB does not have search method"
                        })
                    else:
                        direct_results = self.kb.search(query, limit=limit)
                        kb_search_time = time.time() - kb_search_start
                        
                        debug_info["steps"].append({
                            "step": "kb.search",
                            "time_taken": f"{kb_search_time:.2f}s",
                            "results_count": len(direct_results) if direct_results else 0
                        })
                        
                        if direct_results and "streamlit" not in query_lower:
                            filtered_direct_results = []
                            for result in direct_results:
                                title = result.get("title", "").lower()
                                if "streamlit" in title and "streamlit" not in query_lower:
                                    print(f"Filtering out less relevant document: {title}")
                                    continue
                                filtered_direct_results.append(result)
                            
                            direct_results = filtered_direct_results
                        
                        if direct_results:
                            direct_search_results = []
                            for result in direct_results:
                                search_result = {
                                    "title": result.get("title", "Untitled"),
                                    "content": result.get("text", "")[:1000],  
                                    "score": result.get("score", 0.0),
                                    "source": result.get("source", ""),
                                    "is_from_documents_table": True 
                                }
                                direct_search_results.append(search_result)
                            
                            search_results = direct_search_results
                except Exception as e:
                    debug_info["steps"].append({
                        "step": "kb.search",
                        "error": str(e)
                    })
                    print(f"Error in knowledge base search: {e}")
        
        if not search_results:
            print("No results found in either entries table or documents table")
            debug_info["steps"].append({
                "step": "search_summary",
                "message": "No results found in either entries table or documents table"
            })
            return []
        
        if st.session_state.get(f"{self.prefix}use_qa", True) and hasattr(self, 'qa_processor') and self.qa_processor is not None:
            processed_results = self._process_with_qa(query, search_results)
            return processed_results
        
        return search_results
    
    def _display_result_item(self, result):
        """Display a single search result item."""
        score = result.get("score", 0)
        
        # For OpenAI embeddings, lower score is better (it's a distance measure)
        normalized_score = 1.0 - min(score, 1.0)
        
        relevance_class = "relevance-high" if normalized_score > 0.7 else "relevance-medium" if normalized_score > 0.4 else "relevance-low"
        formatted_score = self._format_relevance_score(normalized_score)
        
        st.markdown(
            f"""
            <div class='search-result'>
                <h4>{result.get('title', 'Untitled')}</h4>
                <p>{result.get('content', '')[:250]}...</p>
                <div class='metadata'>
                    Source: {result.get('source', 'Unknown')} | 
                    Relevance: {formatted_score}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        button_key = f"view_{result.get('id', hash(str(result.get('content', ''))[:50]))}"
        if st.button(f"View Full Content", key=button_key):
            st.session_state[f"{self.prefix}viewing_content"] = result
        
        viewing_content = st.session_state.get(f"{self.prefix}viewing_content")
        if viewing_content and viewing_content.get('id', hash(str(viewing_content.get('content', '')))) == result.get('id', hash(str(result.get('content', '')))):
            with st.expander("Full Content", expanded=True):
                st.markdown(viewing_content.get('content', 'No content available.'))
                if st.button("Hide Content", key=f"hide_{button_key}"):
                    st.session_state[f"{self.prefix}viewing_content"] = None
                    
    def _format_relevance_score(self, normalized_score):
        """Format relevance score with appropriate styling."""
        relevance_class = "relevance-high" if normalized_score > 0.7 else "relevance-medium" if normalized_score > 0.4 else "relevance-low"
        return f"<span class='{relevance_class}'>{normalized_score:.2f}</span>"


if __name__ == '__main__':
    app = KnowledgeBaseSearchApp(standalone_mode=True)
    app.render()    