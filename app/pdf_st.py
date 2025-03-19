import streamlit as st
import os
from pathlib import Path
import uuid
import base64
from datetime import datetime, timedelta
import sys
from pathlib import Path

parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))
from tools.pdf_processor import PDFProcessor
from tools.knowledge_base import KnowledgeBase
from tools.lancedb_manager import LanceDBManager
from utils.file_remover import FileRemover

class PDFConverterApp:
    def __init__(self, upload_folder='data/uploads', processor_class=None, lancedb_path='data/lancedb'):
        """Initialize the PDF Converter application"""
        
        if not os.path.isabs(upload_folder):
            abs_upload_folder = str(parent_dir / upload_folder)
            print(f"Converting relative path {upload_folder} to absolute: {abs_upload_folder}")
            self.upload_folder = abs_upload_folder
        else:
            self.upload_folder = upload_folder
            
        if not os.path.isabs(lancedb_path):
            self.lancedb_path = str(parent_dir / lancedb_path)
        else:
            self.lancedb_path = lancedb_path
            
        self.processor_class = processor_class
        
        os.makedirs(self.upload_folder, exist_ok=True)
        if self.processor_class:
            self.pdf_processor = self.processor_class(upload_dir=self.upload_folder)
        else:
            self.pdf_processor = None
        
        self.db_manager = LanceDBManager(db_path=self.lancedb_path)
        self._init_session_state()
        
    def _init_session_state(self):
        """Initialize session state variables"""
        if 'markdown_text' not in st.session_state:
            st.session_state.markdown_text = None
        if 'download_filename' not in st.session_state:
            st.session_state.download_filename = None
        if 'processing' not in st.session_state:
            st.session_state.processing = False
        if 'kb_added' not in st.session_state:
            st.session_state.kb_added = False
        if 'show_category_selector' not in st.session_state:
            st.session_state.show_category_selector = False
        if 'selected_category' not in st.session_state:
            st.session_state.selected_category = None
        if 'selected_topic' not in st.session_state:
            st.session_state.selected_topic = None
        if 'custom_title' not in st.session_state:
            st.session_state.custom_title = None
        if 'show_removal_confirmation' not in st.session_state:
            st.session_state.show_removal_confirmation = False
    
    def render(self):
        """Render the PDF converter interface"""
        st.markdown('<div class="upload-container">', unsafe_allow_html=True)
        st.write("Upload a PDF file to convert it to markdown format:")
        uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"], key="pdf_uploader")
        st.markdown('</div>', unsafe_allow_html=True)

        if uploaded_file is not None:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"Selected file: **{uploaded_file.name}**")
            
            with col2:
                process_button = st.button("Process PDF", key="process_button")
            
            if process_button:
                self._process_pdf(uploaded_file)

        if st.session_state.markdown_text is not None:
            self._display_results()
            
        self._render_sidebar()
    
    def _process_pdf(self, uploaded_file):
        """Process the uploaded PDF file"""
        st.session_state.processing = True
        
        with st.spinner("Processing PDF..."):
            try:
                filename = f"{uuid.uuid4()}_{uploaded_file.name}"
                filepath = os.path.join(self.upload_folder, filename)
                
                st.info(f"Saving uploaded file to: {filepath}")
                
                with open(filepath, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                markdown_text = self.pdf_processor.process_pdf(filepath)
                markdown_filename = f"{os.path.splitext(filename)[0]}.md"
                markdown_filepath = os.path.join(self.upload_folder, markdown_filename)
                
                with open(markdown_filepath, 'w', encoding='utf-8') as f:
                    f.write(markdown_text)
                
                st.session_state.markdown_text = markdown_text
                st.session_state.download_filename = markdown_filepath
                st.markdown('<div class="success-msg">PDF processed successfully!</div>', unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"Error processing PDF: {str(e)}")
                import traceback
                st.error(traceback.format_exc())
            
            st.session_state.processing = False
    
    def _display_results(self):
        """Display the conversion results"""
        st.subheader("Converted Markdown")
        st.markdown('<div class="markdown-output">' + st.session_state.markdown_text.replace('<', '&lt;').replace('>', '&gt;') + '</div>', 
                    unsafe_allow_html=True)
        st.markdown('<div class="actions-container">', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            file_name = os.path.basename(st.session_state.download_filename)
            st.markdown(self._get_download_link(st.session_state.download_filename, file_name), 
                        unsafe_allow_html=True)
        
        with col2:
            if st.button("Copy to Clipboard", key="copy_button"):
                st.write("Copied to clipboard!")
                escaped_text = st.session_state.markdown_text.replace("`", "\\`")
                st.markdown(f"""
                <script>
                    const text = `{escaped_text}`;
                    navigator.clipboard.writeText(text);
                </script>
                """, unsafe_allow_html=True)
                
        with col3:
            kb_button_disabled = st.session_state.kb_added
            if st.button("Add to Knowledge Base", key="kb_button", disabled=kb_button_disabled):
                st.session_state.show_category_selector = True
                
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.session_state.show_category_selector and not st.session_state.kb_added:
            self._display_category_topic_selector()
    
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
                lines = st.session_state.markdown_text.strip().split('\n')
                default_title = lines[0].strip().replace('#', '').strip() if lines else "Untitled Document"
                
                st.subheader("Document Details")
                custom_title = st.text_input("Document Title", value=default_title)
                submit_button = st.form_submit_button("Create and Add Document")
                
                if submit_button:
                    try:
                        category_id = self.db_manager.create_category(category_name, category_desc)
                        topic_id = self.db_manager.create_topic(category_id, topic_name, topic_desc)
                        
                        st.session_state.custom_title = custom_title
                        self._add_to_knowledge_base(topic_id)
                        
                        st.success(f"Created category '{category_name}', topic '{topic_name}' and added document successfully!")
                        st.session_state.kb_added = True
                        st.session_state.show_category_selector = False
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
                    
                    lines = st.session_state.markdown_text.strip().split('\n')
                    default_title = lines[0].strip().replace('#', '').strip() if lines else "Untitled Document"
                    
                    st.subheader("Document Details")
                    custom_title = st.text_input("Document Title", value=default_title)
                    
                    submit_button = st.form_submit_button("Create Topic and Add Document")
                    
                    if submit_button:
                        try:
                            topic_id = self.db_manager.create_topic(selected_category_id, topic_name, topic_desc)
                            
                            st.session_state.custom_title = custom_title
                            
                            self._add_to_knowledge_base(topic_id)
                            
                            st.success(f"Created topic '{topic_name}' and added document successfully!")
                            st.session_state.kb_added = True
                            st.session_state.show_category_selector = False
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
                lines = st.session_state.markdown_text.strip().split('\n')
                default_title = lines[0].strip().replace('#', '').strip() if lines else "Untitled Document"
                custom_title = st.text_input("Document Title", value=default_title, key="kb_doc_title")
                
                tags_input = st.text_input("Add tags (comma-separated, optional):")
                
                if st.button("Add to Knowledge Base", key="add_to_kb_confirmed"):
                    tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else []
                    
                    st.session_state.custom_title = custom_title
                    
                    self._add_to_knowledge_base(selected_topic_id, tags)
                    
                    st.success("Document added to knowledge base successfully!")
                    st.session_state.kb_added = True
                    st.session_state.show_category_selector = False
    
    def _add_to_knowledge_base(self, topic_id, tags=None):
        """Add the converted markdown to the knowledge base under the specified topic"""
        try:
            source = os.path.basename(st.session_state.download_filename)
            if st.session_state.custom_title:
                title = st.session_state.custom_title
            else:
                lines = st.session_state.markdown_text.strip().split('\n')
                title = lines[0].strip().replace('#', '').strip() if lines else "Untitled Document"
            
            entry_id = self.db_manager.create_entry(
                topic_id=topic_id,
                title=title,
                content=st.session_state.markdown_text,
                tags=tags,
                source=source,
                generate_embedding=True
            )
            
            return True
                
        except Exception as e:
            st.error(f"Error adding to knowledge base: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return False
    
    def _render_sidebar(self):
        """Render the sidebar with cleanup options"""
        with st.sidebar:
            st.header("Maintenance")
            
            st.write("⚠️ **Danger Zone**")
            st.write("Use this option to remove all uploaded files and converted markdown files from the system.")
            
            if not st.session_state.show_removal_confirmation:
                if st.button("Remove Cached Files"):
                    st.session_state.show_removal_confirmation = True
                    st.rerun()
            
            if st.session_state.show_removal_confirmation:
                st.warning("Are you sure you want to remove ALL files? This action cannot be undone.")
                col1, col2 = st.columns(2)
        
                if col1.button("Yes", key="confirm_remove"):
                    try:
                        uploads_dir = self.upload_folder
                        st.info(f"Removing files from: {uploads_dir}")
                        
                        files_before = self._list_files_in_directory(uploads_dir)
                        st.write(f"Found {len(files_before)} files before removal:")
                        for file in files_before:
                            st.write(f"- {file}")
                        
                        if not files_before:
                            st.info("No files found to remove.")
                            st.session_state.show_removal_confirmation = False
                            st.rerun()
                            return
                        
                        try:
                            file_remover = FileRemover(
                                directory_path=uploads_dir, 
                                st_callback=self._st_log_callback
                            )
                            st.write(f"FileRemover initialized with directory: {file_remover.directory_path}")
                            files_removed = file_remover.remove_all_files()
                            if files_removed == 0 and files_before:
                                st.warning("FileRemover didn't remove any files. Trying direct removal...")
                                files_removed = 0
                                for file_path in files_before:
                                    try:
                                        os.remove(file_path)
                                        files_removed += 1
                                        st.write(f"Directly removed: {file_path}")
                                    except Exception as e:
                                        st.error(f"Error directly removing {file_path}: {str(e)}")
                            
                        except Exception as e:
                            st.error(f"Error with FileRemover: {str(e)}")
                            st.warning("Falling back to direct file removal...")
                            
                            files_removed = 0
                            for file_path in files_before:
                                try:
                                    if file_path.endswith('.gitkeep'):
                                        st.write(f"Skipping .gitkeep file: {file_path}")
                                        continue
                                    os.remove(file_path)
                                    files_removed += 1
                                    st.write(f"Directly removed: {file_path}")
                                except Exception as e:
                                    st.error(f"Error directly removing {file_path}: {str(e)}")
                        
                        files_after = self._list_files_in_directory(uploads_dir)
                        st.write(f"Found {len(files_after)} files after removal:")
                        for file in files_after:
                            st.write(f"- {file}")
                        
                        st.session_state.show_removal_confirmation = False
                        if files_removed > 0:
                            st.success(f"Removed {files_removed} files successfully!")
                            st.session_state.markdown_text = None
                            st.session_state.download_filename = None
                        else:
                            st.warning("No files were removed. Please check the logs for errors.")
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error during file removal process: {str(e)}")
                        import traceback
                        st.error(traceback.format_exc())
                        st.session_state.show_removal_confirmation = False
                
                if col2.button("Cancel", key="cancel_remove"):
                    st.session_state.show_removal_confirmation = False
                    st.info("File removal cancelled.")
                    st.rerun()
    
    def _get_download_link(self, file_path, file_name):
        """Create a download link for the given file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = f.read()
        b64 = base64.b64encode(data.encode()).decode()
        return f'<a href="data:text/markdown;base64,{b64}" download="{file_name}" class="stButton"><button>Download Markdown File</button></a>'

    def _list_files_in_directory(self, directory):
        """List files in a directory and return them as a list of strings"""
        files = []
        try:
            path = Path(directory)
            if path.exists() and path.is_dir():
                for file_path in path.iterdir():
                    if file_path.is_file():
                        files.append(str(file_path))
        except Exception as e:
            st.error(f"Error listing files: {str(e)}")
        return files

    def _st_log_callback(self, message, level="info"):
        """Callback function for FileRemover to log messages to Streamlit"""
        if level == "error":
            st.error(message)
        elif level == "warning":
            st.warning(message)
        else:
            st.write(message)

if __name__ == '__main__':
    
    st.set_page_config(
        page_title="PDF to Markdown Converter",
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
        .upload-container {
            border: 2px dashed #ccc;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            margin-bottom: 20px;
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
        .success-msg {
            padding: 10px;
            border-radius: 5px;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            margin-bottom: 10px;
        }
        .copy-btn {
            font-size: 14px;
            padding: 5px 15px;
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
        h1, h2, h3 {
            color: #2196F3;
        }
        .category-topic-selector {
            margin-top: 20px;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
            background-color: #f9f9f9;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("PDF to Markdown Converter")
    
    app = PDFConverterApp(processor_class=PDFProcessor)
    app.render()
    
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666;">
            PDF to Markdown Converter | Streamlit App
        </div>
        """, 
        unsafe_allow_html=True
    )

