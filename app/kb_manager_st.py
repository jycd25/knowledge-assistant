import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path
import sys

# add parent dir for eary imports
parent_dir = str(Path(__file__).parent.parent.absolute())
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from tools.lancedb_manager import LanceDBManager

# Define CSS
def local_css():
    st.markdown("""
    <style>
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .stButton button {
            width: 100%;
        }
        .success-message {
            padding: 10px;
            background-color: #d4edda;
            color: #155724;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .error-message {
            padding: 10px;
            background-color: #f8d7da;
            color: #721c24;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .warning-message {
            padding: 10px;
            background-color: #fff3cd;
            color: #856404;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .info-card {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .hierarchy-view {
            font-family: monospace;
            white-space: pre-wrap;
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
        }
        /* Tree view styling */
        .tree-item {
            margin-left: 20px;
        }
        .tree-category {
            font-weight: bold;
            color: #5a5a5a;
        }
        .tree-topic {
            color: #007bff;
        }
        .tree-subtopic {
            color: #28a745;
        }
        .tree-entry {
            color: #dc3545;
        }
        .subtitle {
            font-size: 1.5rem;
            margin-bottom: 1rem;
            border-bottom: 1px solid #0066cc33;
            padding-bottom: 0.5rem;
            color: #0066cc;
        }
        /* Table styling */
        .dataframe {
            width: 100%;
            border-collapse: collapse;
            border: 1px solid #0066cc33; /* Subtle blue border */
            border-radius: 5px;
            overflow: hidden; /* Makes sure the border-radius works */
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0, 102, 204, 0.1); /* Subtle blue shadow */
        }
        .dataframe th {
            background-color: #0066cc;
            color: white;
            text-align: left;
            padding: 10px 8px; /* Slightly more top/bottom padding */
        }
        .dataframe td {
            border: 1px solid #ddd;
            padding: 8px;
        }
        .dataframe tr:nth-child(even) {
            background-color: #f0f5ff; /* Subtle blue tint */
        }
        .dataframe tr:hover {
            background-color: #d4e6ff; /* Light blue on hover */
        }
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: #f0f0f0;
            border-radius: 4px 4px 0px 0px;
            gap: 1px;
            padding-top: 10px;
            padding-bottom: 10px;
            color: #555; /* Darker text color for better contrast */
            font-weight: 500;
            border: 1px solid #ddd;
        }
        .stTabs [aria-selected="true"] {
            background-color: #0066cc !important; /* Blue background for selected tab */
            color: white !important;
            font-weight: 600;
            border: 1px solid #0066cc;
        }
        /* Hover effect for tabs */
        .stTabs [data-baseweb="tab"]:hover {
            background-color: #e0e0e0;
            cursor: pointer;
        }
        /* Expander styling */
        .streamlit-expanderHeader {
            background-color: #f0f5ff;
            border-radius: 5px;
            border-left: 4px solid #0066cc;
            padding: 10px;
            font-weight: 500;
        }
        .streamlit-expanderHeader:hover {
            background-color: #d4e6ff;
        }
        .streamlit-expanderContent {
            border-left: 1px solid #0066cc33;
            padding-left: 20px;
            margin-left: 10px;
        }
        /* Heading styling */
        h1, h2, h3 {
            color: #0066cc;
        }
        h2 {
            border-bottom: 1px solid #0066cc33;
            padding-bottom: 0.5rem;
        }
        /* Entry table styling */
        .entry-row {
            padding: 10px 0;
            border-bottom: 1px solid #eee;
            transition: background-color 0.2s;
        }
        .entry-row:hover {
            background-color: #f0f5ff;
        }
        /* Action buttons styling - override the width: 100% for action buttons */
        .entry-row .stButton button,
        div[data-testid="column"] .stButton button {
            width: auto !important;
            border-radius: 4px;
            border: 1px solid #ddd;
            padding: 3px 10px;
            font-size: 0.85rem;
            font-weight: 500;
            min-width: 60px;
            transition: all 0.2s;
        }
        /* Standard button */
        button[data-testid^="stButton-"] {
            background-color: #f8f9fa;
            color: #0066cc;
            border-color: #0066cc33;
        }
        button[data-testid^="stButton-"]:hover {
            background-color: #e7f0ff;
            border-color: #0066cc;
        }
        /* Action buttons container - better spacing */
        .entry-row .stButton,
        div[data-testid="column"] .stButton {
            margin: 0 2px;
            display: inline-block;
        }
        /* Delete buttons */
        button[data-testid^="stButton-"]:has(div:contains("Delete")) {
            color: #dc3545;
            border-color: #dc354533;
        }
        button[data-testid^="stButton-"]:has(div:contains("Delete")):hover {
            background-color: #ffebee;
            border-color: #dc3545;
        }
        /* Edit buttons */
        button[data-testid^="stButton-"]:has(div:contains("Edit")) {
            color: #28a745;
            border-color: #28a74533;
        }
        button[data-testid^="stButton-"]:has(div:contains("Edit")):hover {
            background-color: #e7f5e7;
            border-color: #28a745;
        }
        /* View buttons */
        button[data-testid^="stButton-"]:has(div:contains("View")) {
            color: #0066cc;
            border-color: #0066cc33;
        }
        button[data-testid^="stButton-"]:has(div:contains("View")):hover {
            background-color: #e7f0ff;
            border-color: #0066cc;
        }
        /* Entry table row separator */
        hr {
            margin: 8px 0;
            border: 0;
            border-top: 1px solid #eee;
        }
        /* Entry title styling */
        .entry-title {
            font-weight: 500;
            color: #0066cc;
            cursor: pointer;
            text-decoration: none;
        }
        .entry-title:hover {
            text-decoration: underline;
            font-weight: 600;
        }
        /* Add CSS for hierarchical styling */
        .hierarchy-container {
            font-family: monospace;
            white-space: pre-wrap;
            background-color: rgba(var(--theme-background-color-secondary-rgb), 0.3);
            color: var(--theme-text-color-primary);
            padding: 20px;
            border-radius: 5px;
            border-left: 3px solid var(--theme-primary-color);
            margin: 10px 0;
        }
        .category-item {
            font-weight: bold;
            color: var(--theme-primary-color);
        }
        .topic-item {
            font-weight: bold;
            color: var(--theme-primary-color);
            margin-left: 20px;
        }
        .entry-item {
            margin-left: 40px;
        }
        .note-text {
            color: var(--theme-text-color-secondary);
            font-style: italic;
        }
        .tag-text {
            color: var(--theme-text-color-secondary);
            font-style: italic;
        }
    </style>
    """, unsafe_allow_html=True)


class KBManagerApp:
    """A Streamlit app for managing a knowledge base."""
    
    def __init__(self, lancedb_path="data/lancedb", show_page_config=True):
        """Initialize the app with a LanceDBManager instance.
        
        Args:
            lancedb_path (str): Path to the LanceDB database
            show_page_config (bool): Whether to show the page config. Set to False when integrated in app_st.py
        """
        self.manager = LanceDBManager(lancedb_path)
    
    def set_success(self, message):
        """Set success message in session state."""
        st.session_state.success_message = message
    
    def set_error(self, message):
        """Set error message in session state."""
        st.session_state.error_message = message
    
    def display_messages(self):
        """Display success or error messages from the session state."""
        if 'success_message' in st.session_state and st.session_state.success_message:
            st.success(st.session_state.success_message)
            st.session_state.success_message = None
        
        if 'error_message' in st.session_state and st.session_state.error_message:
            st.error(st.session_state.error_message)
            st.session_state.error_message = None
    
    def render_category_manager(self):
        """Render the category management section."""
        st.markdown("<h2>Category Management</h2>", unsafe_allow_html=True)
        
        categories_df = self.manager.get_categories()
        
        if not categories_df.empty:
            st.markdown("<div class='subtitle'>Existing Categories</div>", unsafe_allow_html=True)
            
            # Use session state to track which category is being edited or viewed
            if 'edit_category_id' not in st.session_state:
                st.session_state.edit_category_id = None
            if 'view_category_id' not in st.session_state:
                st.session_state.view_category_id = None
            if 'delete_category_id' not in st.session_state:
                st.session_state.delete_category_id = None
            
            # Initialize the view state for each category
            for _, row in categories_df.iterrows():
                category_id = row['id']
                if f"view_state_category_{category_id}" not in st.session_state:
                    st.session_state[f"view_state_category_{category_id}"] = False
            
            cols = st.columns([4, 5, 3])
            cols[0].markdown("<b>Name</b>", unsafe_allow_html=True)
            cols[1].markdown("<b>Description</b>", unsafe_allow_html=True)
            cols[2].markdown("<b>Actions</b>", unsafe_allow_html=True)
            
            st.markdown("<hr>", unsafe_allow_html=True)
            
            for _, row in categories_df.iterrows():
                category_id = row['id']
                name = row['name']
                description = row['description']
                
                # Add category row with hover effect
                st.markdown(f"<div class='entry-row'>", unsafe_allow_html=True)
                
                cols = st.columns([4, 5, 3])
                cols[0].markdown(f"<div class='entry-title' onclick=\"this.style.fontWeight='bold'; document.getElementById('btn_view_category_{category_id}').click()\">{name}</div>", unsafe_allow_html=True)
                
                # Show truncated description
                max_desc_length = 80
                display_desc = description if len(description) <= max_desc_length else description[:max_desc_length] + "..."
                cols[1].markdown(f"{display_desc}")
                
                # buttons for the action column
                action_col1, action_col2, action_col3 = cols[2].columns(3)
                if action_col1.button("View", key=f"btn_view_category_{category_id}", help="View category details"):
                    st.session_state[f"view_state_category_{category_id}"] = not st.session_state[f"view_state_category_{category_id}"]
                    st.session_state.view_category_id = category_id
                
                if action_col2.button("Edit", key=f"btn_edit_category_{category_id}", help="Edit this category"):
                    st.session_state.edit_category_id = category_id
                    st.session_state.edit_mode = True
                
                if action_col3.button("Delete", key=f"btn_delete_category_{category_id}", help="Delete this category"):
                    st.session_state.delete_category_id = category_id
                
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("<hr>", unsafe_allow_html=True)
            
            # process edit and delete actions
            if 'edit_category_id' in st.session_state and st.session_state.edit_category_id:
                category_id = st.session_state.edit_category_id
                self.display_category_form(edit=True, category_id=category_id)
                if st.button("Cancel Editing", key="btn_cancel_edit_category"):
                    st.session_state.edit_category_id = None
                    st.session_state.edit_mode = False
                    st.rerun()
            
            if 'delete_category_id' in st.session_state and st.session_state.delete_category_id:
                category_id = st.session_state.delete_category_id
                category_name = categories_df[categories_df['id'] == category_id]['name'].iloc[0]
                
                st.warning(f"Are you sure you want to delete the category: **{category_name}**? This will also delete all topics and entries in this category.")
                col1, col2 = st.columns(2)
                
                if col1.button("Yes, Delete", key="btn_confirm_delete_category"):
                    try:
                        if self.manager.delete_category(category_id):
                            self.set_success(f"Category '{category_name}' deleted successfully!")
                            st.session_state.delete_category_id = None
                            st.rerun()
                    except Exception as e:
                        self.set_error(f"Error deleting category: {str(e)}")
                
                if col2.button("Cancel", key="btn_cancel_delete_category"):
                    st.session_state.delete_category_id = None
                    st.rerun()
            
            # Display category details for the viewed category
            for _, row in categories_df.iterrows():
                category_id = row['id']
                if 'view_state_category_' + category_id in st.session_state and st.session_state['view_state_category_' + category_id]:
                    with st.expander(f"Details for: {row['name']}", expanded=True):
                        st.markdown(f"**Name:** {row['name']}")
                        st.markdown(f"**Description:** {row['description']}")
                        
                        topics_df = self.manager.get_topics(category_id)
                        if not topics_df.empty:
                            st.markdown("**Topics in this category:**")
                            topics_list = ", ".join([f"`{topic}`" for topic in topics_df['name']])
                            st.markdown(topics_list)
                        else:
                            st.info("No topics in this category yet.")
                        
                        if st.button("Close", key=f"btn_close_category_{category_id}"):
                            st.session_state[f"view_state_category_{category_id}"] = False
                            st.rerun()
        
        st.markdown("<div class='subtitle'>Create New Category</div>", unsafe_allow_html=True)
        self.display_category_form()
    
    def display_category_form(self, edit=False, category_id=None):
        """Display form for creating or editing a category."""
        category_data = None
        
        if edit and category_id:
            category_data = self.manager.get_category(category_id).iloc[0]
        
        with st.form("category_form"):
            name = st.text_input("Category Name", value=category_data['name'] if category_data is not None else "")
            description = st.text_area("Description", value=category_data['description'] if category_data is not None else "")
            
            if edit:
                submit_button = st.form_submit_button("Update Category")
                if submit_button:
                    try:
                        self.manager.update_category(category_id, name, description)
                        self.set_success(f"Category '{name}' updated successfully!")
                        st.session_state.edit_mode = False
                        st.rerun()
                    except Exception as e:
                        self.set_error(f"Error updating category: {str(e)}")
            else:
                submit_button = st.form_submit_button("Create Category")
                if submit_button:
                    try:
                        category_id = self.manager.create_category(name, description)
                        self.set_success(f"Category '{name}' created successfully!")
                        st.rerun()
                    except Exception as e:
                        self.set_error(f"Error creating category: {str(e)}")
    
    def render_topic_manager(self):
        """Render the topic management section."""
        st.markdown("<h2>Topic Management</h2>", unsafe_allow_html=True)
    
        categories_df = self.manager.get_categories()
        if categories_df.empty:
            st.info("Please create a category first.")
            return
        
        category_options = categories_df['name'].tolist()
        category_options.insert(0, "Select a category")
        
        selected_category_name = st.selectbox("Select a category:", category_options, key="topic_category_select")
        
        if selected_category_name != "Select a category":
            category_id = categories_df[categories_df['name'] == selected_category_name]['id'].iloc[0]
            st.session_state.selected_category = category_id
            
            topics_df = self.manager.get_topics(category_id)
            if not topics_df.empty:
                st.markdown("<div class='subtitle'>Existing Topics</div>", unsafe_allow_html=True)
                
                if 'edit_topic_id' not in st.session_state:
                    st.session_state.edit_topic_id = None
                if 'view_topic_id' not in st.session_state:
                    st.session_state.view_topic_id = None
                if 'delete_topic_id' not in st.session_state:
                    st.session_state.delete_topic_id = None
                
                for _, row in topics_df.iterrows():
                    topic_id = row['id']
                    if f"view_state_topic_{topic_id}" not in st.session_state:
                        st.session_state[f"view_state_topic_{topic_id}"] = False
                
                cols = st.columns([4, 5, 3])
                cols[0].markdown("<b>Name</b>", unsafe_allow_html=True)
                cols[1].markdown("<b>Description</b>", unsafe_allow_html=True)
                cols[2].markdown("<b>Actions</b>", unsafe_allow_html=True)
                
                st.markdown("<hr>", unsafe_allow_html=True)
                
                for _, row in topics_df.iterrows():
                    topic_id = row['id']
                    name = row['name']
                    description = row['description']
                    
                    st.markdown(f"<div class='entry-row'>", unsafe_allow_html=True)
                    
                    cols = st.columns([4, 5, 3])
                    cols[0].markdown(f"<div class='entry-title' onclick=\"this.style.fontWeight='bold'; document.getElementById('btn_view_topic_{topic_id}').click()\">{name}</div>", unsafe_allow_html=True)
                    
                    # Show truncated description
                    max_desc_length = 80
                    display_desc = description if len(description) <= max_desc_length else description[:max_desc_length] + "..."
                    cols[1].markdown(f"{display_desc}")

                    action_col1, action_col2, action_col3 = cols[2].columns(3)
                    if action_col1.button("View", key=f"btn_view_topic_{topic_id}", help="View topic details"):
                        st.session_state[f"view_state_topic_{topic_id}"] = not st.session_state[f"view_state_topic_{topic_id}"]
                        st.session_state.view_topic_id = topic_id
                    
                    if action_col2.button("Edit", key=f"btn_edit_topic_{topic_id}", help="Edit this topic"):
                        st.session_state.edit_topic_id = topic_id
                        st.session_state.edit_mode = True
                    
                    if action_col3.button("Delete", key=f"btn_delete_topic_{topic_id}", help="Delete this topic"):
                        st.session_state.delete_topic_id = topic_id
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown("<hr>", unsafe_allow_html=True)
                
                if 'edit_topic_id' in st.session_state and st.session_state.edit_topic_id:
                    topic_id = st.session_state.edit_topic_id
                    self.display_topic_form(category_id, edit=True, topic_id=topic_id)
                    if st.button("Cancel Editing", key="btn_cancel_edit_topic"):
                        st.session_state.edit_topic_id = None
                        st.session_state.edit_mode = False
                        st.rerun()
                
                if 'delete_topic_id' in st.session_state and st.session_state.delete_topic_id:
                    topic_id = st.session_state.delete_topic_id
                    topic_name = topics_df[topics_df['id'] == topic_id]['name'].iloc[0]
                    
                    st.warning(f"Are you sure you want to delete the topic: **{topic_name}**? This will also delete all entries in this topic.")
                    col1, col2 = st.columns(2)
                    
                    if col1.button("Yes, Delete", key="btn_confirm_delete_topic"):
                        try:
                            if self.manager.delete_topic(topic_id):
                                self.set_success(f"Topic '{topic_name}' deleted successfully!")
                                st.session_state.delete_topic_id = None
                                st.rerun()
                        except Exception as e:
                            self.set_error(f"Error deleting topic: {str(e)}")
                
                for _, row in topics_df.iterrows():
                    topic_id = row['id']
                    if 'view_state_topic_' + topic_id in st.session_state and st.session_state['view_state_topic_' + topic_id]:
                        with st.expander(f"Details for: {row['name']}", expanded=True):
                            st.markdown(f"**Name:** {row['name']}")
                            st.markdown(f"**Description:** {row['description']}")
                            
                            # Get entries for this topic
                            entries_df = self.manager.get_entries(topic_id)
                            if not entries_df.empty:
                                st.markdown("**Entries in this topic:**")
                                entries_list = ", ".join([f"`{entry}`" for entry in entries_df['title']])
                                st.markdown(entries_list)
                            else:
                                st.info("No entries in this topic yet.")
                            
                            if st.button("Close", key=f"btn_close_topic_{topic_id}"):
                                st.session_state[f"view_state_topic_{topic_id}"] = False
                                st.rerun()
            
            # Create new topic form
            st.markdown("<div class='subtitle'>Create New Topic</div>", unsafe_allow_html=True)
            self.display_topic_form(category_id)
    
    def display_topic_form(self, category_id, edit=False, topic_id=None):
        """Display form for creating or editing a topic."""
        topic_data = None
        
        if edit and topic_id:
            topic_data = self.manager.get_topic(topic_id).iloc[0]
        
        with st.form("topic_form"):
            name = st.text_input("Topic Name", value=topic_data['name'] if topic_data is not None else "")
            description = st.text_area("Description", value=topic_data['description'] if topic_data is not None else "")
            
            if edit:
                submit_button = st.form_submit_button("Update Topic")
                if submit_button:
                    try:
                        self.manager.update_topic(topic_id, name, description)
                        self.set_success(f"Topic '{name}' updated successfully!")
                        st.session_state.edit_mode = False
                        st.rerun()
                    except Exception as e:
                        self.set_error(f"Error updating topic: {str(e)}")
            else:
                submit_button = st.form_submit_button("Create Topic")
                if submit_button:
                    try:
                        topic_id = self.manager.create_topic(category_id, name, description)
                        self.set_success(f"Topic '{name}' created successfully!")
                        st.rerun()
                    except Exception as e:
                        self.set_error(f"Error creating topic: {str(e)}")
    
    def render_entry_manager(self):
        """Render the entry management section."""
        st.markdown("<h2>Entry Management</h2>", unsafe_allow_html=True)
        if 'show_new_entry_form' not in st.session_state:
            st.session_state.show_new_entry_form = False
        
        should_display_form = False
        
        categories_df = self.manager.get_categories()
        if categories_df.empty:
            st.info("Please create a category first.")
            col1, col2, col3 = st.columns([3, 2, 3])
            with col2:
                if st.button("➕ Create New Entry", key="create_new_entry_button_empty", use_container_width=True):
                    st.session_state.show_new_entry_form = True
                    should_display_form = True
            
        else:
            category_options = categories_df['name'].tolist()
            category_options.insert(0, "Select a category")
            
            selected_category_name = st.selectbox("Select a category:", category_options, key="entry_category_select")
            
            if selected_category_name != "Select a category":
                category_id = categories_df[categories_df['name'] == selected_category_name]['id'].iloc[0]
                st.session_state.selected_category = category_id
                
                topics_df = self.manager.get_topics(category_id)
                if topics_df.empty:
                    st.info("Please create a topic for this category first.")
                else:
                    topic_options = topics_df['name'].tolist()
                    topic_options.insert(0, "Select a topic")
                    
                    selected_topic_name = st.selectbox("Select a topic:", topic_options, key="entry_topic_select")
                    
                    if selected_topic_name != "Select a topic":
                        topic_id = topics_df[topics_df['name'] == selected_topic_name]['id'].iloc[0]
                        st.session_state.selected_topic = topic_id
                        
                        entries_df = self.manager.get_entries(topic_id)
                        
                        if not entries_df.empty:
                            st.markdown("<div class='subtitle'>Existing Entries</div>", unsafe_allow_html=True)
                            cols = st.columns([4, 2, 3])
                            cols[0].markdown("<b>Title</b>", unsafe_allow_html=True)
                            cols[1].markdown("<b>Created</b>", unsafe_allow_html=True)
                            cols[2].markdown("<b>Actions</b>", unsafe_allow_html=True)
                            
                            st.markdown("<hr>", unsafe_allow_html=True)
                            
                            for idx, row in entries_df.iterrows():
                                entry_id = row['id']
                                title = row['title']
                                created = row['created_at'].split('T')[0] if 'T' in row['created_at'] else row['created_at']
                                
                                # Add entry row
                                st.markdown(f"<div class='entry-row'>", unsafe_allow_html=True)
                                
                                cols = st.columns([4, 2, 3])
                                cols[0].markdown(f"<div class='entry-title'>{title}</div>", unsafe_allow_html=True)
                                cols[1].markdown(f"{created}")
                                

                                action_col1, action_col2, action_col3 = cols[2].columns(3)
                                if action_col1.button(key=f"btn_view_{entry_id}", label="View"):
                                    st.session_state[f"view_entry_{entry_id}"] = True
                                
                                if action_col2.button(key=f"btn_edit_{entry_id}", label="Edit"):
                                    st.session_state.edit_entry_id = entry_id
                                
                                if action_col3.button(key=f"btn_delete_{entry_id}", label="Delete"):
                                    st.session_state.delete_entry_id = entry_id
                                
                                st.markdown("</div>", unsafe_allow_html=True)
                                st.markdown("<hr>", unsafe_allow_html=True)
                                
                                # expand entry details if view button was clicked
                                if st.session_state.get(f"view_entry_{entry_id}", False):
                                    with st.expander(f"Details for: {title}", expanded=True):
                                        st.markdown(f"**Title:** {title}")
                                        st.markdown("**Content:**")
                                        st.markdown(row['content'])
                                        
                                        # Show tags if any
                                        if row['tags_json']:
                                            tags = json.loads(row['tags_json'])
                                            tags_str = ", ".join([f"`{tag}`" for tag in tags]) if tags else ""
                                            st.markdown(f"**Tags:** {tags_str}")
                                        
                                        if st.button(key=f"btn_close_{entry_id}", label="Close"):
                                            st.session_state[f"view_entry_{entry_id}"] = False
                                            st.rerun()
                        
                            if 'edit_entry_id' in st.session_state and st.session_state.edit_entry_id:
                                entry_id = st.session_state.edit_entry_id
                                st.markdown("<div class='subtitle'>Edit Entry</div>", unsafe_allow_html=True)
                                self.display_entry_form(topic_id=st.session_state.selected_topic, edit=True, entry_id=entry_id)
                                if st.button("Cancel Editing", key="btn_cancel_edit_entry"):
                                    st.session_state.edit_entry_id = None
                                    st.rerun()

                            if 'delete_entry_id' in st.session_state and st.session_state.delete_entry_id:
                                entry_id = st.session_state.delete_entry_id
                                entry_data = self.manager.get_entry(entry_id)
                                if not entry_data.empty:
                                    entry_title = entry_data.iloc[0]['title']
                                    
                                    st.warning(f"Are you sure you want to delete the entry: **{entry_title}**?")
                                    col1, col2 = st.columns(2)
                                    
                                    if col1.button("Yes, Delete", key="btn_confirm_delete_entry"):
                                        try:
                                            if self.manager.delete_entry(entry_id):
                                                self.set_success(f"Entry '{entry_title}' deleted successfully!")
                                                st.session_state.delete_entry_id = None
                                                st.rerun()
                                        except Exception as e:
                                            self.set_error(f"Error deleting entry: {str(e)}")
                                    
                                    if col2.button("Cancel", key="btn_cancel_delete_entry"):
                                        st.session_state.delete_entry_id = None
                                        st.rerun()
                        else:
                            st.info("No entries found in this topic. Use the button below to create one.")
            else:
                st.info("Please select a category and topic to view or create entries.")
            
            # Add the "Create New Entry" button or form at the bottom middle
            st.markdown("<br>", unsafe_allow_html=True)  
            create_entry_container = st.container()
            
            if st.session_state.show_new_entry_form:
                with create_entry_container:
                    st.markdown("<div class='subtitle'>Create New Entry</div>", unsafe_allow_html=True)
                    self.display_entry_form()
                    if st.button("Cancel", key="cancel_new_entry"):
                        st.session_state.show_new_entry_form = False
                        st.rerun()
            else:
                with create_entry_container:
                    col1, col2, col3 = st.columns([3, 2, 3])
                    with col2:
                        if st.button("➕ Create New Entry", key="create_new_entry_button_bottom", use_container_width=True):
                            st.session_state.show_new_entry_form = True
                            st.rerun()  # Rerun to show the form
    
    def display_entry_form(self, topic_id=None, edit=False, entry_id=None):
        """Display form for creating or editing an entry."""
        entry_data = None
        tags = []
        
        if edit and entry_id:
            entry_data = self.manager.get_entry(entry_id).iloc[0]
            if entry_data['tags_json']:
                tags = json.loads(entry_data['tags_json'])
        
        with st.form("entry_form"):
            if edit:
                title = st.text_input("Entry Title", value=entry_data['title'] if entry_data is not None else "")
                content = st.text_area("Content", value=entry_data['content'] if entry_data is not None else "", height=200)
                tags_input = st.text_input("Tags (comma-separated)", value=", ".join(tags) if tags else "")
                
                if tags_input:
                    tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
                
                submit_button = st.form_submit_button("Update Entry")
                if submit_button:
                    try:
                        self.manager.update_entry(entry_id, title, content, tags)
                        self.set_success(f"Entry '{title}' updated successfully!")
                        st.session_state.edit_mode = False
                        st.rerun()
                    except Exception as e:
                        self.set_error(f"Error updating entry: {str(e)}")
            else:
                title = st.text_input("Entry Title")
                content = st.text_area("Content", height=200)
                tags_input = st.text_input("Tags (comma-separated)")
                
                if tags_input:
                    tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
                
                categories_df = self.manager.get_categories()
                selected_category_id = None
                target_topic_id = topic_id  # Default is the current topic
                
                if not categories_df.empty:
                    st.markdown("### Entry Location")
                    category_options = categories_df['name'].tolist()
                    category_ids = categories_df['id'].tolist()
                    
                    # If we have a current topic, auto-select its category
                    if topic_id:
                        try:
                            topic_data = self.manager.get_topic(topic_id).iloc[0]
                            category_id = topic_data['category_id']
                            if category_id in category_ids:
                                default_idx = category_ids.index(category_id)
                            else:
                                default_idx = 0
                        except:
                            default_idx = 0
                    else:
                        default_idx = 0
                    
                    selected_category = st.selectbox(
                        "Category", 
                        options=category_options,
                        index=default_idx,
                        key="new_entry_category"
                    )
                    
                    selected_category_id = categories_df[categories_df['name'] == selected_category]['id'].iloc[0]
                    topics_df = self.manager.get_topics(selected_category_id)
                    if not topics_df.empty:
                        topic_options = topics_df['name'].tolist()
                        topic_ids = topics_df['id'].tolist()
                        
                        # auto-select the topic if there's any
                        if topic_id and topic_id in topic_ids:
                            default_idx = topic_ids.index(topic_id)
                        else:
                            default_idx = 0
                        
                        selected_topic = st.selectbox(
                            "Topic", 
                            options=topic_options,
                            index=default_idx,
                            key="new_entry_topic"
                        )
                        
                        target_topic_id = topics_df[topics_df['name'] == selected_topic]['id'].iloc[0]
                    else:
                        st.warning("Please create a topic in the selected category first.")
                
                submit_button = st.form_submit_button("Create Entry")
                if submit_button:
                    try:
                        if title and target_topic_id:
                            self.manager.create_entry(target_topic_id, title, content, tags)
                            self.set_success(f"Entry '{title}' created successfully!")
                            st.rerun()
                        elif not title:
                            self.set_error("Entry title cannot be empty!")
                        else:
                            self.set_error("Please select a valid topic!")
                    except Exception as e:
                        self.set_error(f"Error creating entry: {str(e)}")
    
    def render_hierarchy_view(self):
        """Render a hierarchical view of the entire knowledge base as a text-based TOC."""
        st.markdown("<h2>Knowledge Base Hierarchy</h2>", unsafe_allow_html=True)
        
        try:
            # Get the full view of lancedb hierarchy
            hierarchy = self.manager.get_full_hierarchy()
            
            if not hierarchy["categories"]:
                st.info("No data available in the knowledge base yet.")
                return
            
            html_content = '<div class="hierarchy-container">'
            
            for i, category in enumerate(hierarchy["categories"]):
                html_content += f'<div class="category-item">Category {i+1}: {category["name"]}</div>\n\n'
                
                if not category["topics"]:
                    html_content += '<div class="note-text" style="margin-left: 20px;">No topics in this category</div>\n\n'
                    continue
                
                for j, topic in enumerate(category["topics"]):
                    html_content += f'<div class="topic-item">Topic {i+1}.{j+1}: {topic["name"]}</div>\n\n'
                    if not topic["entries"]:
                        html_content += '<div class="note-text" style="margin-left: 40px;">No entries in this topic</div>\n\n'
                        continue
                    
                    total_entries = len(topic["entries"])
                    displayed_entries = topic["entries"][:5]
                    
                    for k, entry in enumerate(displayed_entries):
                        created_date = entry['created_at'].split('T')[0] if 'T' in entry['created_at'] else entry['created_at']
                        html_content += f'<div class="entry-item">Entry {i+1}.{j+1}.{k+1}: {entry["title"]} ({created_date})'
                        if entry['tags']:
                            tags_text = ", ".join(entry['tags'])
                            html_content += f' <span class="tag-text">[{tags_text}]</span>'
                        
                        html_content += '</div>\n'
                
                    if total_entries > 5:
                        html_content += f'<div class="note-text" style="margin-left: 40px;">... and {total_entries - 5} more entries</div>\n'
                    
                    html_content += '\n'
            
            html_content += '</div>'
            
            st.markdown(html_content, unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"Error loading hierarchy: {str(e)}")
            st.exception(e)  
    
    def render(self):
        """Main rendering function."""
        local_css()
        
        st.title("Knowledge Base Manager")
        st.markdown("Manage your knowledge base structure and content")
        
        self.display_messages()
        
        if 'kb_manager_active_tab' not in st.session_state:
            st.session_state.kb_manager_active_tab = 0
        
        tab_names = ["Categories", "Topics", "Entries", "Hierarchy View"]
        active_tab = st.radio("Navigation Tabs", tab_names, index=st.session_state.kb_manager_active_tab, horizontal=True, label_visibility="collapsed")
        
        st.session_state.kb_manager_active_tab = tab_names.index(active_tab)
    
        st.markdown("""
        <style>
            div[data-testid*="stHorizontalBlock"] div[data-testid="stRadio"] {
                width: 100%;
                margin-bottom: 1rem;
            }
            div[data-testid*="stHorizontalBlock"] div[data-testid="stRadio"] > div {
                display: flex;
                justify-content: space-between;
                flex-direction: row;
                width: 100%;
            }
            div[data-testid*="stHorizontalBlock"] div[data-testid="stRadio"] label {
                background-color: #f0f0f0;
                padding: 10px 15px;
                border-radius: 4px 4px 0 0;
                border: 1px solid #ddd;
                border-bottom: none;
                font-weight: 500;
                text-align: center;
                color: #555;
                min-width: 120px;
                transition: all 0.3s;
            }
            div[data-testid*="stHorizontalBlock"] div[data-testid="stRadio"] label:hover {
                background-color: #e0e0e0;
                cursor: pointer;
            }
            div[data-testid*="stHorizontalBlock"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
                background-color: #0066cc !important;
                color: white !important;
                font-weight: 600;
                border: 1px solid #0066cc;
                border-bottom: none;
            }
            /* Hide the radio button circle */
            div[data-testid*="stHorizontalBlock"] div[data-testid="stRadio"] label div:first-child {
                display: none;
            }
            /* Add a line under the tabs */
            div[data-testid*="stHorizontalBlock"] div[data-testid="stRadio"] {
                border-bottom: 1px solid #ddd;
            }
        </style>
        """, unsafe_allow_html=True)
        
        if active_tab == "Categories":
            self.render_category_manager()
        elif active_tab == "Topics":
            self.render_topic_manager()
        elif active_tab == "Entries":
            self.render_entry_manager()
        elif active_tab == "Hierarchy View":
            self.render_hierarchy_view()
        
        st.markdown("---")
        st.markdown("Knowledge Base Manager v1.0")
    
    


def main():
    app = KBManagerApp()
    app.render()



if __name__ == "__main__":
    st.set_page_config(
        page_title="Knowledge Base Manager",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )