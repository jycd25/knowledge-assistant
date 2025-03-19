import streamlit as st
import os
import sys
from pathlib import Path
import json
import time
from datetime import datetime
import uuid

parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))
from tools.note_processor import NoteProcessor
from tools.prompt_builder import PromptBuilder
from tools.user_preferences import UserPreferences
from tools.knowledge_base import KnowledgeBase
from tools.lancedb_manager import LanceDBManager

class NoteProcessorApp:
    def __init__(self, notes_folder=None, processor_class=None, lancedb_path='data/lancedb'):
        """Initialize the Note Processor application"""
        
        # Set the notes folder path
        if notes_folder is None:
            self.notes_folder = str(Path(parent_dir) / "data" / "notes")
        else:
            self.notes_folder = notes_folder

        self.processor_class = processor_class
        self.lancedb_path = lancedb_path
        
        os.makedirs(self.notes_folder, exist_ok=True)
        
        self.user_preferences = UserPreferences()
        
        if self.processor_class:
            self.note_processor = self.processor_class(preferences=self.user_preferences)
        else:
            self.note_processor = NoteProcessor(preferences=self.user_preferences)
            
        self.prompt_builder = PromptBuilder()
        self.db_manager = LanceDBManager(db_path=self.lancedb_path)
            
        self._init_session_state()
        
    def _init_session_state(self):
        """Initialize session state variables"""
        if 'processed_text' not in st.session_state:
            st.session_state.processed_text = None
        if 'raw_text' not in st.session_state:
            st.session_state.raw_text = None
        if 'user_request' not in st.session_state:
            st.session_state.user_request = None
        if 'processing' not in st.session_state:
            st.session_state.processing = False
        if 'llm_processing' not in st.session_state:
            st.session_state.llm_processing = False
        if 'processing_status' not in st.session_state:
            st.session_state.processing_status = ""
        if 'processing_progress' not in st.session_state:
            st.session_state.processing_progress = 0
        if 'processing_start_time' not in st.session_state:
            st.session_state.processing_start_time = None
        if 'trigger_process_with_ai' not in st.session_state:
            st.session_state.trigger_process_with_ai = False
        if 'trigger_process_without_ai' not in st.session_state:
            st.session_state.trigger_process_without_ai = False
        if 'applied_preferences' not in st.session_state:
            st.session_state.applied_preferences = []
        if 'show_debug' not in st.session_state:
            st.session_state.show_debug = False
        if 'debug_info' not in st.session_state:
            st.session_state.debug_info = []
        if 'show_success' not in st.session_state:
            st.session_state.show_success = False
        if 'success_message' not in st.session_state:
            st.session_state.success_message = ""
        if 'templates' not in st.session_state:
            st.session_state.templates = self._load_templates()
        if 'selected_template' not in st.session_state:
            st.session_state.selected_template = None
        if 'template_content' not in st.session_state:
            st.session_state.template_content = None
        if 'template_used' not in st.session_state:
            st.session_state.template_used = None
        if 'previous_template_selection' not in st.session_state:
            st.session_state.previous_template_selection = None
        if 'kb_added' not in st.session_state:
            st.session_state.kb_added = False
        if 'show_category_selector' not in st.session_state:
            st.session_state.show_category_selector = False
        if 'selected_category' not in st.session_state:
            st.session_state.selected_category = None
        if 'selected_topic' not in st.session_state:
            st.session_state.selected_topic = None
    
    def _load_templates(self):
        """Load available templates"""
        templates_dir = Path(parent_dir) / "data" / "templates"
        templates = []
        
        if templates_dir.exists():
            for file in templates_dir.glob("*.md"):
                if file.name != "README.md":
                    templates.append({
                        "name": file.stem,
                        "path": str(file)
                    })
        
        return templates
    
    def _add_debug(self, message):
        """Add a debug message with timestamp"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        st.session_state.debug_info.append(f"[{timestamp}] {message}")
    
    def _clear_debug(self):
        """Clear debug information"""
        st.session_state.debug_info = []
    
    def _update_processing_status(self, status, progress=None):
        """Update the processing status and progress"""
        st.session_state.processing_status = status
        if progress is not None:
            st.session_state.processing_progress = progress
        self._add_debug(f"Processing status: {status} ({progress if progress is not None else 'N/A'}%)")
        st.rerun()
    
    def _process_note(self, use_llm=True):
        """Process the note with or without LLM"""
        if not st.session_state.raw_text:
            st.warning("Please enter some text to process")
            return
        
        # Set processing flags
        st.session_state.processing = True
        st.session_state.processing_start_time = time.time()
        
        if use_llm:
            st.session_state.llm_processing = True
            st.session_state.processing_status = "Processing with AI..."

        try:
            self._add_debug(f"Processing note (length: {len(st.session_state.raw_text)}, use_llm: {use_llm})")
            if st.session_state.user_request:
                self._add_debug(f"User request: {st.session_state.user_request}")
            if st.session_state.selected_template:
                self._add_debug(f"Using template: {st.session_state.selected_template}")
            
            current_prefs = self.user_preferences.preferences
            if current_prefs and "preferences" in current_prefs:
                self._add_debug(f"Current preferences: {len(current_prefs['preferences'])} preferences loaded")
            
            combined_request = st.session_state.user_request or ""
            if st.session_state.selected_template:
                template_info = f"This note is based on the '{st.session_state.selected_template}' template. Please maintain the template structure while enhancing the content."
                combined_request = f"{template_info}\n\n{combined_request}" if combined_request else template_info
                self._add_debug(f"Added template information to request: {st.session_state.selected_template}")
            
            start_time = time.time()
            
            result = self.note_processor.process_note(
                text=st.session_state.raw_text,
                user_request=combined_request,
                use_llm=use_llm
            )
            
            if isinstance(result, str):
                result = {
                    'text': result,
                    'applied_preferences': []
                }
            
            st.session_state.processed_text = result['text']
            st.session_state.applied_preferences = result.get('applied_preferences', [])
            st.session_state.template_used = st.session_state.selected_template
            
            elapsed = time.time() - start_time
            self._add_debug(f"Processing completed in {elapsed:.2f} seconds")
            
            if use_llm and st.session_state.user_request:
                self._add_debug("Analyzing user request for preferences...")
                analysis = self.user_preferences.update_from_request(
                    st.session_state.user_request,
                    len(st.session_state.raw_text)
                )
                
                if analysis and analysis.get("success") and "identified_preferences" in analysis:
                    prefs = analysis["identified_preferences"]
                    if prefs:
                        self._add_debug(f"Identified {len(prefs)} potential preferences in request")
            
        except Exception as e:
            st.error(f"Error processing note: {str(e)}")
            self._add_debug(f"ERROR: {str(e)}")
        finally:
            st.session_state.processing = False
            st.session_state.llm_processing = False
    
    def _save_note(self):
        """Save the processed note as a markdown file"""
        if not st.session_state.processed_text:
            st.warning("No processed text to save")
            return
        
        try:
            lines = st.session_state.processed_text.strip().split('\n')
            title = lines[0].strip().replace('#', '').strip() if lines else "Untitled Note"
            
            safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
            safe_title = safe_title.replace(' ', '_')
            
            if st.session_state.template_used:
                safe_title = f"{safe_title}_{st.session_state.template_used}"
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{safe_title}_{timestamp}.md"
            
            file_path = Path(self.notes_folder) / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(st.session_state.processed_text)
            
            self._add_debug(f"Note saved to {file_path}")
            
            st.session_state.show_success = True
            st.session_state.success_message = f"Note saved successfully as {filename}"
            
        except Exception as e:
            st.error(f"Error saving note: {str(e)}")
            self._add_debug(f"ERROR saving note: {str(e)}")
    
    def _load_template(self, template_path):
        """Load a template file"""
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            st.error(f"Error loading template: {str(e)}")
            self._add_debug(f"ERROR loading template: {str(e)}")
            return None
    
    def _update_template_preview(self, template_name):
        """Update the template preview without changing the text input"""
        if not template_name or template_name == "None":
            st.session_state.selected_template = None
            st.session_state.template_content = None
            self._add_debug("Template selection cleared")
            return
        
        if template_name == st.session_state.selected_template:
            return
            
        template_path = None
        for template in st.session_state.templates:
            if template["name"] == template_name:
                template_path = template["path"]
                break
        
        if not template_path:
            return
        
        template_content = self._load_template(template_path)
        if template_content:
            st.session_state.selected_template = template_name
            st.session_state.template_content = template_content
            self._add_debug(f"Template selected: {template_name}")
    
    def _add_to_knowledge_base(self):
        """Show UI for selecting category and topic, then add to knowledge base"""
        if not st.session_state.processed_text:
            st.warning("No processed text to add to knowledge base")
            return
        
        st.session_state.show_category_selector = True
        st.rerun()
    
    def _display_category_topic_selector(self):
        """Display category and topic selector for adding to knowledge base"""
        st.markdown("### Add to Knowledge Base")
        st.markdown("Select a category and topic to add this document to:")
        
        categories_df = self.db_manager.get_categories()
        
        if categories_df.empty:
            st.warning("No categories found. Please create a category in the KB Manager first.")
            
            with st.form("create_category_form"):
                st.subheader("Create New Category")
                category_name = st.text_input("Category Name")
                category_desc = st.text_area("Category Description")
                
                st.subheader("Create New Topic")
                topic_name = st.text_input("Topic Name")
                topic_desc = st.text_area("Topic Description")
                
                submit_button = st.form_submit_button("Create and Add Document")
                
                if submit_button:
                    try:
                        category_id = self.db_manager.create_category(category_name, category_desc)
                        topic_id = self.db_manager.create_topic(category_id, topic_name, topic_desc)
                        self._add_document_to_kb(topic_id)
                        
                        st.success(f"Created category '{category_name}', topic '{topic_name}' and added document successfully!")
                        st.session_state.kb_added = True
                        st.session_state.show_category_selector = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating category/topic: {str(e)}")
            
        else:
            category_options = categories_df['name'].tolist()
            category_ids = categories_df['id'].tolist()
            
            selected_category_name = st.selectbox(
                "Select a category:", 
                category_options,
                key="kb_category_selector"
            )
            
            selected_category_id = categories_df[categories_df['name'] == selected_category_name]['id'].iloc[0]
            
            topics_df = self.db_manager.get_topics(selected_category_id)
            
            if topics_df.empty:
                st.warning(f"No topics found in category '{selected_category_name}'. Please create a topic first.")
                
                with st.form("create_topic_form"):
                    st.subheader("Create New Topic")
                    topic_name = st.text_input("Topic Name")
                    topic_desc = st.text_area("Topic Description")
                    
                    submit_button = st.form_submit_button("Create Topic and Add Document")
                    
                    if submit_button:
                        try:
                            topic_id = self.db_manager.create_topic(selected_category_id, topic_name, topic_desc)
                            self._add_document_to_kb(topic_id)
                            
                            st.success(f"Created topic '{topic_name}' and added document successfully!")
                            st.session_state.kb_added = True
                            st.session_state.show_category_selector = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error creating topic: {str(e)}")
            else:
                topic_options = topics_df['name'].tolist()
                selected_topic_name = st.selectbox(
                    "Select a topic:", 
                    topic_options,
                    key="kb_topic_selector"
                )
                
                selected_topic_id = topics_df[topics_df['name'] == selected_topic_name]['id'].iloc[0]
                tags_input = st.text_input("Add tags (comma-separated, optional):")
                
                if st.button("Add to Knowledge Base", key="add_to_kb_confirmed"):
                    tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else []
                    self._add_document_to_kb(selected_topic_id, tags)
                    
                    st.success("Document added to knowledge base successfully!")
                    st.session_state.kb_added = True
                    st.session_state.show_category_selector = False
                    st.rerun()
    
    def _add_document_to_kb(self, topic_id, tags=None):
        """Add the processed note to the knowledge base under the specified topic"""
        try:
            lines = st.session_state.processed_text.strip().split('\n')
            title = lines[0].strip().replace('#', '').strip() if lines else "Untitled Note"
            
            self._add_debug(f"Adding note to topic {topic_id} with title: {title}")
            entry_id = self.db_manager.create_entry(
                topic_id=topic_id,
                title=title,
                content=st.session_state.processed_text,
                tags=tags,
                source="note_processor",
                generate_embedding=True
            )
            
            self._add_debug(f"Note added to knowledge base with entry ID: {entry_id}")
            return True
                
        except Exception as e:
            error_msg = f"Error adding to knowledge base: {str(e)}"
            self._add_debug(error_msg)
            st.error(error_msg)
            import traceback
            st.error(traceback.format_exc())
            return False
    
    def render(self):
        """Render the Note Processor interface"""
        st.markdown("Enter your notes below to process them with AI.")
        st.text_area(
            "Enter your note here:",
            height=200,
            key="raw_text"
        )
        
        if st.session_state.templates:
            st.markdown('<div class="template-section">', unsafe_allow_html=True)
            st.markdown("### Templates")
            
            template_options = ["No template"] + [t["name"] for t in st.session_state.templates]
            selected_index = 0
            
            if st.session_state.selected_template:
                if st.session_state.selected_template in template_options:
                    selected_index = template_options.index(st.session_state.selected_template)
            
            selected_template = st.selectbox(
                "Use a template (optional):",
                options=template_options,
                index=selected_index,
                key="template_selector"
            )
            
            if selected_template != "No template":
                if st.session_state.selected_template != selected_template:
                    st.session_state.selected_template = selected_template
                    
                    for template in st.session_state.templates:
                        if template["name"] == selected_template:
                            with open(template["path"], 'r', encoding='utf-8') as f:
                                st.session_state.template_content = f.read()
                            break
                    
                    st.markdown("#### Template Preview")
                    with st.expander("Preview", expanded=False):
                        st.markdown(st.session_state.template_content)
                    
                    if st.button("Use Template Content"):
                        st.session_state.raw_text = st.session_state.template_content
                        st.rerun()
                
            else:
                st.session_state.selected_template = None
                st.session_state.template_content = None
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.text_input(
            "Processing instructions (optional):",
            key="user_request",
            help="Specify how you want the note to be processed, e.g., 'Make it concise and add bullet points'"
        )
        
        processing_placeholder = st.empty()
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("Process with AI", use_container_width=True, type="primary", disabled=st.session_state.processing):
                text_to_process = st.session_state.raw_text
                request_to_process = st.session_state.user_request
                template_to_use = st.session_state.selected_template
                
                st.session_state.trigger_process_with_ai = True
                st.rerun()
        
        with col2:
            if st.button("Process without AI", use_container_width=True, disabled=st.session_state.processing):
                text_to_process = st.session_state.raw_text
                request_to_process = st.session_state.user_request
                template_to_use = st.session_state.selected_template
                
                st.session_state.trigger_process_without_ai = True
                st.rerun()
        
        with col3:
            if st.button("Save Note", use_container_width=True, disabled=not st.session_state.processed_text or st.session_state.processing):
                self._save_note()
        
        if hasattr(st.session_state, 'trigger_process_with_ai') and st.session_state.trigger_process_with_ai:
            st.session_state.trigger_process_with_ai = False
            self._process_note(use_llm=True)
            
        if hasattr(st.session_state, 'trigger_process_without_ai') and st.session_state.trigger_process_without_ai:
            st.session_state.trigger_process_without_ai = False
            self._process_note(use_llm=False)
        
        if st.session_state.processing:
            elapsed_time = 0
            if st.session_state.processing_start_time:
                elapsed_time = time.time() - st.session_state.processing_start_time
                
            if st.session_state.llm_processing:
                st.markdown(f"""
                <div class="processing-dialog">
                    <div class="processing-spinner"></div>
                    <h3>Processing with AI...</h3>
                    <p>This may take a few moments. Please wait...</p>
                    <p class="processing-time">Time elapsed: {elapsed_time:.1f}s</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                with st.spinner("Processing note..."):
                    pass
        
        if st.session_state.processed_text:
            st.divider()
            st.subheader("Processed Note")
            
            info_cols = st.columns([1, 1])
            
            with info_cols[0]:
                if st.session_state.template_used:
                    st.markdown(f"**Template used:** {st.session_state.template_used}")
            
            with info_cols[1]:
                if st.session_state.applied_preferences:
                    num_prefs = len(st.session_state.applied_preferences)
                    st.markdown(f"**Applied preferences:** {num_prefs}")
            
            if st.session_state.applied_preferences:
                with st.expander("View Applied Preferences"):
                    for pref in st.session_state.applied_preferences:
                        st.markdown(f"**{pref['name']}**: {pref['value']}")
                        if pref.get('explanation'):
                            st.markdown(f"*{pref['explanation']}*")
            
            st.markdown("### Preview")
            st.markdown(st.session_state.processed_text)
            
            download_filename = f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            st.download_button(
                label="Download as Markdown",
                data=st.session_state.processed_text,
                file_name=download_filename,
                mime="text/markdown",
                use_container_width=True
            )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Save Note", key="save_button"):
                    self._save_note()
            
            with col2:
                if st.button("Copy to Clipboard", key="copy_button"):
                    escaped_text = st.session_state.processed_text.replace("`", "\\`")
                    st.markdown(f"""
                    <script>
                        const text = `{escaped_text}`;
                        navigator.clipboard.writeText(text);
                    </script>
                    """, unsafe_allow_html=True)
                    st.success("Copied to clipboard!")
            
            with col3:
                kb_button_disabled = st.session_state.kb_added
                if st.button("Add to Knowledge Base", key="kb_button", disabled=kb_button_disabled):
                    self._add_to_knowledge_base()
            
            if st.session_state.show_category_selector and not st.session_state.kb_added:
                self._display_category_topic_selector()
        
        with st.expander("Debug Information", expanded=st.session_state.show_debug):
            st.checkbox("Show Debug Info", value=st.session_state.show_debug, key="show_debug")
            
            if st.session_state.show_debug:
                st.markdown("### Debug Log")
                st.markdown('<div class="debug-info">', unsafe_allow_html=True)
                for log in st.session_state.debug_info:
                    st.text(log)
                st.markdown('</div>', unsafe_allow_html=True)
                
                if st.button("Clear Debug Log"):
                    self._clear_debug()
                
                debug_prompt_file = Path("debug_last_prompt.txt")
                if debug_prompt_file.exists():
                    with st.expander("Last Generated Prompt"):
                        st.code(debug_prompt_file.read_text(encoding='utf-8'), language="text")

if __name__ == "__main__":
    st.set_page_config(
        page_title="Note Processor",
        page_icon="📝",
        layout="wide"
    )
    
    st.markdown("""
    <style>
        .main {
            background-color: #f8f9fa;
        }
        .stApp {
            max-width: 1200px;
            margin: 0 auto;
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
        .stButton > button:disabled {
            background-color: #cccccc;
            color: #666666;
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
        /* Success pop-up styling */
        .success-dialog {
            background-color: #e8f5e9;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            border-left: 5px solid #4CAF50;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        /* Processing dialog styling */
        .processing-dialog {
            background-color: #e3f2fd;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            border-left: 5px solid #2196F3;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            text-align: center;
            animation: pulse 2s infinite ease-in-out;
        }
        .processing-dialog h3 {
            color: #0d47a1;
            margin-top: 10px;
        }
        .processing-dialog p {
            color: #1976d2;
            margin: 10px 0;
        }
        .processing-time {
            color: #666;
            font-size: 14px;
        }
        /* Spinner animation */
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .processing-spinner {
            border: 5px solid #f3f3f3;
            border-top: 5px solid #2196F3;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        /* Pulsing animation */
        @keyframes pulse {
            0% { opacity: 0.8; }
            50% { opacity: 1; }
            100% { opacity: 0.8; }
        }
        /* Template section styling */
        .template-section {
            background-color: #e3f2fd;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            border-left: 5px solid #2196F3;
        }
        /* Info box styling */
        .info-box {
            background-color: #f1f8e9;
            border-radius: 5px;
            padding: 10px;
            margin-bottom: 15px;
            border-left: 3px solid #8bc34a;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("Note Processor")
    
    app = NoteProcessorApp()
    app.render()
    
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666;">
            Note Processor
        </div>
        """, 
        unsafe_allow_html=True
    ) 