import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path to import tools
sys.path.append(str(Path(__file__).parent.parent))
from tools.user_preferences import UserPreferences

class PreferencesApp:
    def __init__(self):
        """Initialize the AI Preferences Management application"""
        # Initialize preferences with a configurable confidence threshold
        default_threshold = 80
        self.preferences = UserPreferences(confidence_threshold=default_threshold)
        
    def render(self):
        """Render the AI Preferences Management interface"""
        # Session state variables
        if 'show_preference_confirmation' not in st.session_state:
            st.session_state.show_preference_confirmation = False
        if 'detected_preferences' not in st.session_state:
            st.session_state.detected_preferences = None
        if 'suggested_prompt' not in st.session_state:
            st.session_state.suggested_prompt = ""
        if 'debug_info' not in st.session_state:
            st.session_state.debug_info = []
        if 'show_debug' not in st.session_state:
            st.session_state.show_debug = False

        if 'show_success_popup' not in st.session_state:
            st.session_state.show_success_popup = False
        if 'success_message' not in st.session_state:
            st.session_state.success_message = ""

        if 'show_current_prefs_result' not in st.session_state:
            st.session_state.show_current_prefs_result = False
        if 'current_preferences' not in st.session_state:
            st.session_state.current_preferences = []
            
        confidence_threshold = self.preferences.confidence_threshold
            
        # Success pop-up
        if st.session_state.show_success_popup:
            st.markdown("""
            <style>
            .success-dialog {
                background-color: #e8f5e9;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
                border-left: 5px solid #4CAF50;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            </style>
            """, unsafe_allow_html=True)
            
            with st.container():
                st.markdown('<div class="success-dialog">', unsafe_allow_html=True)
                st.markdown("### ✅ Success!")
                st.markdown(f"**{st.session_state.success_message}**")
                
                if st.button("Dismiss", key="dismiss_success", use_container_width=True):
                    st.session_state.show_success_popup = False
                    st.session_state.success_message = ""
                    st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
            
        # High-confidence preferences and confirmation dialog
        if st.session_state.show_preference_confirmation and st.session_state.detected_preferences:
            st.markdown("""
            <style>
            .preference-dialog {
                background-color: #f0f2f6;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
                border-left: 5px solid #2196F3;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            </style>
            """, unsafe_allow_html=True)
            
            with st.container():
                st.markdown('<div class="preference-dialog">', unsafe_allow_html=True)
                st.markdown("### 🔔 New Preferences Detected!")
                st.markdown(f"**{st.session_state.suggested_prompt}**")
                st.markdown("---")
                
                # Only show llm fetchedpreferences with confidence >= threshold
                high_confidence_prefs = {name: details for name, details in st.session_state.detected_preferences.items() 
                                        if details['confidence'] >= confidence_threshold}
                
                if high_confidence_prefs:
                    st.markdown(f"### High Confidence Preferences (≥{confidence_threshold}%):")
                    for name, details in high_confidence_prefs.items():
                        st.info(f"**{name}**: {details['value']} (Confidence: {details['confidence']}%)\n\n{details['explanation']}")
                else:
                    st.info(f"No preferences with confidence ≥{confidence_threshold}% detected. Please try being more specific.")
                    
                # Only show low confidence preferences if there are high confidence ones too
                if high_confidence_prefs:
                    low_confidence_prefs = {name: details for name, details in st.session_state.detected_preferences.items() 
                                          if details['confidence'] < confidence_threshold}
                    if low_confidence_prefs:
                        st.markdown("### Lower Confidence Preferences:")
                        for name, details in low_confidence_prefs.items():
                            st.warning(f"**{name}**: {details['value']} (Confidence: {details['confidence']}%)\n\n{details['explanation']}")
                
                # Only show confirmation if there are high confidence preferences
                if high_confidence_prefs:
                    # Explicit confirmation checkbox
                    confirmation = st.checkbox("I confirm I want to save these preferences", key="explicit_confirmation")
                    
                    # Use columns for the buttons
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("✅ Save Preferences", use_container_width=True, disabled=not confirmation):
                            if confirmation:
                                saved = self.preferences.save_identified_preferences({"identified_preferences": high_confidence_prefs})
                                st.session_state.success_message = f"Saved {len(saved)} preferences successfully!"
                                st.session_state.show_success_popup = True
                                st.session_state.show_preference_confirmation = False
                                st.session_state.detected_preferences = None
                                st.session_state.suggested_prompt = ""
                                st.rerun()
                    
                    with col2:
                        if st.button("❌ Cancel", use_container_width=True):
                            # Reset the state
                            st.session_state.show_preference_confirmation = False
                            st.session_state.detected_preferences = None
                            st.session_state.suggested_prompt = ""
                            st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
        
        # AI pref management section
        st.markdown("### AI Preference Management")
        
        # use slider for confidence threshold setting
        new_threshold = st.slider(
            "Confidence Threshold (%)", 
            min_value=60, 
            max_value=95, 
            value=confidence_threshold,
            step=5,
            help="Set the minimum confidence level required for preferences to be automatically applied."
        )
        
        if new_threshold != confidence_threshold:
            self.preferences.confidence_threshold = new_threshold
            st.success(f"Confidence threshold updated to {new_threshold}%")
        
        if st.button("Show Current Preferences", key="show_current_prefs", use_container_width=True):
            with st.spinner("Loading current preferences..."):
                try:
                    all_preferences = self.preferences.preferences
                    if all_preferences and "preferences" in all_preferences:
                        current_prefs = all_preferences["preferences"]
                        if current_prefs and len(current_prefs) > 0:
                            # Format the preferences for display
                            formatted_prefs = []
                            for name, details in current_prefs.items():
                                formatted_prefs.append({
                                    "name": name,
                                    "value": details["value"],
                                    "description": details.get("explanation", "")
                                })
                            
                            st.session_state.current_preferences = formatted_prefs
                            st.session_state.show_current_prefs_result = True
                            st.session_state.success_message = "Successfully retrieved your current preferences."
                            st.session_state.show_success_popup = True
                            st.rerun()
                        else:
                            st.info("You don't have any saved preferences yet.")
                    else:
                        st.info("No preferences found.")
                except Exception as e:
                    st.error(f"Error retrieving preferences: {str(e)}")
        
        if st.session_state.get('show_current_prefs_result', False):
            with st.container():
                st.markdown("### Your Current Preferences:")
                current_prefs = st.session_state.get('current_preferences', [])
                if not current_prefs:
                    st.info("No preferences found.")
                else:
                    for pref in current_prefs:
                        st.info(f"**{pref['name']}**: {pref['value']}" + 
                               (f"\n\n{pref.get('description', '')}" if pref.get('description') else ""))
                if st.button("Hide Preferences", key="hide_prefs", use_container_width=True):
                    st.session_state.show_current_prefs_result = False
                    st.rerun()
                st.markdown("---")
        
        pref_request = st.text_area(
            "Tell me what you'd like to do with your preferences:",
            placeholder="E.g., 'Add a preference to always use bullet points' or 'Remove the preference for bolding names'...",
            key="preference_request",
            height=150
        )
        
        if st.button("Send Request", key="send_pref_request", type="primary", use_container_width=True):
            if not pref_request:
                st.error("Please enter your request first")
                return
                
            with st.spinner("Processing preference request..."):
                try:
                    result = self.preferences.process_request(pref_request)
                    
                    if (result and "identified_preferences" in result and 
                        result["identified_preferences"] and 
                        any(details.get('confidence', 0) >= (confidence_threshold - 10) for name, details in result["identified_preferences"].items())):
                        
                        st.session_state.detected_preferences = result["identified_preferences"]
                        st.session_state.suggested_prompt = result.get("suggested_prompt", "Would you like to save these preferences?")
                        st.session_state.show_preference_confirmation = True
                        st.rerun()
                        return
                    
                    if result.get('success'):
                        action = result.get('action', '')
                        
                        if action == 'update':
                            message = result.get('message', 'Preferences updated successfully!')
                            if result.get('updates_applied'):
                                updates = ', '.join(result.get('updates_applied', []))
                                detail = f"Updated preferences: {updates}"
                            else:
                                detail = "No updates were necessary."
                        elif action == 'remove':
                            message = result.get('message', 'Preferences removed successfully!')
                            if result.get('removals_applied'):
                                removals = ', '.join(result.get('removals_applied', []))
                                detail = f"Removed preferences: {removals}"
                            else:
                                detail = "No removals were necessary."
                        elif action == 'list':
                            st.session_state.show_current_prefs_result = True
                            message = "Here are your current preferences."
                            detail = ""
                            
                            if "current_preferences" in result:
                                formatted_prefs = []
                                for name, details in result["current_preferences"].items():
                                    formatted_prefs.append({
                                        "name": name,
                                        "value": details["value"],
                                        "description": details.get("explanation", "")
                                    })
                                st.session_state.current_preferences = formatted_prefs
                        elif action == 'help':
                            message = result.get('message', 'Here is help with managing your preferences.')
                            detail = result.get('help_text', '')
                        else:
                            message = result.get('message', 'Preferences processed successfully!')
                            detail = result.get('action_taken', '')
                        
                        # show success pop-up and rerun
                        st.session_state.success_message = message
                        if detail:
                            st.session_state.success_message += f"\n\n{detail}"
                        st.session_state.show_success_popup = True
                        st.rerun()
                    else:
                        st.error(result.get('error', 'Failed to process preference request'))
                except Exception as e:
                    st.error(f"Error managing preferences: {str(e)}")

# for standalone testing
if __name__ == "__main__":
    st.set_page_config(
        page_title="AI Preferences Management",
        page_icon="⚙️",
        layout="centered"
    )
    
    st.markdown("""
    <style>
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
        .stMarkdown h3 {
            color: #2196F3;
            margin-top: 20px;
        }
        .button-container {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 10px;
        }
        h1, h2, h3 {
            color: #2196F3;
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
        /* Preference dialog styling */
        .preference-dialog {
            background-color: #f0f2f6;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            border-left: 5px solid #2196F3;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("AI Preferences Management")
    
    app = PreferencesApp()
    app.render()
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666;">
            AI Preferences Management | Streamlit App
        </div>
        """, 
        unsafe_allow_html=True
    )