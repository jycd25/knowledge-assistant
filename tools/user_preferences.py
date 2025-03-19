#!/usr/bin/env python3

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from openai import OpenAI
from dotenv import load_dotenv

class UserPreferences:
    """
    A class to manage user preferences for note processing.
    Uses LLM with prompt chaining to intelligently analyze user requests and manage preferences.
    """
    default_dir = Path(__file__).resolve().parent.parent / "user_data"
    
    def __init__(self, storage_dir: str = default_dir, confidence_threshold: int = 80):
        """
        Initialize the UserPreferences manager
        
        Args:
            storage_dir: Directory to store preference files
            confidence_threshold: Threshold value (0-100) for confidence scores
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        self.confidence_threshold = confidence_threshold
        print(f"Preference confidence threshold set to: {self.confidence_threshold}%")
        
        self.preferences_file = self.storage_dir / "preferences.json"
        self.request_history_file = self.storage_dir / "request_history.json"
        
        import sys
        parent_dir = Path(__file__).resolve().parent.parent
        sys.path.append(str(parent_dir))
        load_dotenv(Path(parent_dir, '.env'))
        
        self.api_key = os.getenv('OPENAI_API_KEY')
        
        try:
            self.client = OpenAI(api_key=self.api_key)
            print("OpenAI client initialized successfully")
        except Exception as e:
            print(f"Error initializing OpenAI client: {str(e)}")
            self.client = None
        
        self.preferences = self._load_preferences()
        self.request_history = self._load_request_history()
    
    def _load_preferences(self) -> Dict[str, Any]:
        """Load preferences from file or create default if not exists"""
        default_prefs = {
            "preferences": {},
            "last_updated": datetime.now().isoformat()
        }
        
        if self.preferences_file.exists():
            try:
                with open(self.preferences_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if not isinstance(data, dict) or "preferences" not in data:
                        print("Invalid preferences file structure, creating new file")
                        return default_prefs
                    return data
            except (json.JSONDecodeError, FileNotFoundError):
                print(f"Error loading preferences, creating new file")
                return default_prefs
        else:
            with open(self.preferences_file, 'w', encoding='utf-8') as f:
                json.dump(default_prefs, f, indent=2)
            return default_prefs
    
    def _load_request_history(self) -> List[Dict[str, Any]]:
        """Load request history from file or create empty list if not exists"""
        if self.request_history_file.exists():
            try:
                with open(self.request_history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                print(f"Error loading request history, starting fresh")
                return []
        else:
            with open(self.request_history_file, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2)
            return []
    
    def save_preferences(self):
        """Save current preferences to file"""
        self.preferences["last_updated"] = datetime.now().isoformat()
        with open(self.preferences_file, 'w', encoding='utf-8') as f:
            json.dump(self.preferences, f, indent=2)
    
    def save_request_history(self):
        """Save request history to file"""
        with open(self.request_history_file, 'w', encoding='utf-8') as f:
            json.dump(self.request_history, f, indent=2)
    
    def process_request(self, user_request: str) -> Dict[str, Any]:
        """
        Main entry point for processing a request. Uses prompt chaining to:
        1. Classify the request type
        2. Process accordingly based on classification
        
        Returns a dictionary with the processing results and recommended action.
        """
        if not self.client:
            return {
                "success": False,
                "error": "OpenAI client not initialized - cannot process request"
            }
        
        try:
            # Classify the request to determine the right action
            classification = self._classify_request(user_request)
            request_type = classification.get("request_type", "unknown")
            confidence = classification.get("confidence", 0)
            
            print(f"Request classified as '{request_type}' with confidence {confidence}")
            
            # Process based on classification with confidence threshold
            if confidence >= self.confidence_threshold:
                if request_type == "add_preference":
                    return self._identify_preferences(user_request)
                elif request_type == "update_preference":
                    return self._update_preferences(user_request)
                elif request_type == "remove_preference":
                    return self._remove_preferences(user_request)
                elif request_type == "list_preferences":
                    return {
                        "action": "list",
                        "success": True,
                        "message": "Here are your current preferences.",
                        "current_preferences": self.preferences["preferences"]
                    }
                elif request_type == "help":
                    return {
                        "action": "help",
                        "success": True,
                        "message": "Here's how you can manage your preferences:",
                        "help_text": (
                            "1. Add preferences: 'Add a preference to use bullet points'\n"
                            "2. Update preferences: 'Change my formal style to casual'\n"
                            "3. Remove preferences: 'Remove my bullet points preference'\n"
                            "4. List preferences: 'Show me my preferences'"
                        )
                    }
            
            print(f"Low confidence ({confidence}) or unknown request type ({request_type}). Using general analysis.")
            general_analysis = self._identify_preferences(user_request)
            
            if (general_analysis.get("identified_preferences") and 
                len(general_analysis.get("identified_preferences", {})) > 0):
                return general_analysis
            
            return self._legacy_manage_preferences(user_request)
            
        except Exception as e:
            print(f"Error processing request: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _classify_request(self, user_request: str) -> Dict[str, Any]:
        """
        Classify the user request to determine what action to take.
        This is the first step in the prompt chain.
        """
        if not self.client:
            return {"request_type": "unknown", "confidence": 0}
            
        try:
            prompt = f"""
            Classify this user request about preference management into one of these categories:
                1. add_preference: User wants to add a new preference
                2. update_preference: User wants to change an existing preference
                3. remove_preference: User wants to remove a preference
                4. list_preferences: User wants to see current preferences
                5. help: User is asking for help with preferences
                6. unknown: Can't determine the request type

                User request: "{user_request}"

                Respond in JSON format:
                {{
                    "request_type": "add_preference|update_preference|remove_preference|list_preferences|help|unknown",
                    "confidence": 0-100,
                    "reasoning": "brief explanation of why you classified it this way"
                }}

                Consider the intent carefully. For example:
                - "I want bullet points in my summaries" -> add_preference (adding a new formatting preference)
                - "Change my summary style to bullet points" -> update_preference (changing an existing style preference)
                - "I don't want bullet points anymore" -> remove_preference (removing an existing preference)
                """

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a request classification assistant that categorizes user preference requests."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            print(f"Request classification: {json.dumps(result, indent=2)}")
            return result
            
        except Exception as e:
            print(f"Error in request classification: {str(e)}")
            return {"request_type": "unknown", "confidence": 0}
    
    def _identify_preferences(self, user_request: str) -> Dict[str, Any]:
        """
        Identify potential new preferences in the user request.
        This is used for add_preference requests.
        """
        if not self.client:
            return {"identified_preferences": {}}
            
        try:
            current_prefs = json.dumps(self.preferences["preferences"], indent=2)
            
            min_confidence = max(70, self.confidence_threshold - 10)
            
            prompt = f"""Analyze this user request for new note processing preferences. Identify any preferences about:
            1. Writing style (e.g., formal, casual, technical)
            2. Format preferences (e.g., bullet points, paragraphs, headers)
            3. Content organization (e.g., chronological, topic-based)
            4. Special emphasis (e.g., focus on action items, highlight key points)
            5. Any other notable preferences

            User's current preferences:
            {current_prefs}

            User request: "{user_request}"

            Respond in JSON format:
            {{
                "identified_preferences": {{
                    "preference_name": {{
                        "value": "the preferred value",
                        "confidence": 0-100,
                        "explanation": "why this preference was identified"
                    }}
                }},
                "suggested_prompt": "a prompt to ask the user if they want to save these preferences",
                "action": "add"
            }}
            Only include preferences that:
            1. Are clearly indicated or strongly implied in the request
            2. Are not already present in the user's current preferences
            3. Have a confidence score of at least {min_confidence}
            """

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a preference analysis assistant that helps identify new user preferences from their requests."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            print(f"Identified preferences: {json.dumps(result, indent=2)}")
            result["success"] = True
            
            return result
            
        except Exception as e:
            print(f"Error in preference identification: {str(e)}")
            return {
                "identified_preferences": {},
                "success": False,
                "error": str(e)
            }
    
    def _update_preferences(self, user_request: str) -> Dict[str, Any]:
        """
        Process a request to update existing preferences.
        This is used for update_preference requests.
        """
        if not self.client:
            return {"success": False, "error": "OpenAI client not initialized"}
            
        try:
            current_prefs = json.dumps(self.preferences["preferences"], indent=2)
            min_confidence = max(70, self.confidence_threshold - 10)
            
            prompt = f"""The user wants to update one or more of their existing preferences. 
            Identify which preferences should be updated and the new values.

            User's current preferences:
            {current_prefs}

            User request: "{user_request}"

            Respond in JSON format:
            {{
                "updates": [
                    {{
                        "preference_name": "name of the preference to update",
                        "current_value": "current value of the preference",
                        "new_value": "new value to set",
                        "confidence": 0-100,
                        "explanation": "why this update was identified"
                    }}
                ],
                "message": "message explaining the updates to show to the user",
                "action": "update"
            }}

            Only include updates that:
            1. Reference existing preferences
            2. Have a clear new value
            3. Have a confidence score of at least {min_confidence}
            """

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a preference management assistant that helps update user preferences."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            print(f"Update preferences result: {json.dumps(result, indent=2)}")
            
            updates_applied = []
            updates = result.get("updates", [])
            
            for update in updates:
                name = update.get("preference_name")
                new_value = update.get("new_value")
                explanation = update.get("explanation")
                confidence = update.get("confidence", 0)
                
                if name and new_value is not None and confidence >= self.confidence_threshold and name in self.preferences["preferences"]:
                    self.preferences["preferences"][name]["value"] = new_value
                    self.preferences["preferences"][name]["explanation"] = explanation
                    self.preferences["preferences"][name]["updated_at"] = datetime.now().isoformat()
                    updates_applied.append(name)
            
            if updates_applied:
                self.save_preferences()
                
                result["success"] = True
                result["updates_applied"] = updates_applied
                result["action_taken"] = f"Updated {len(updates_applied)} preference(s): {', '.join(updates_applied)}"
            else:
                result["success"] = False
                result["error"] = f"No updates were applied. Either no preferences matched or confidence was below {self.confidence_threshold}%."
                result["action_taken"] = "No changes were made to your preferences."
            
            return result
            
        except Exception as e:
            print(f"Error in update preferences: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "action": "update"
            }
    
    def _remove_preferences(self, user_request: str) -> Dict[str, Any]:
        """
        Process a request to remove existing preferences.
        This is used for remove_preference requests.
        """
        if not self.client:
            return {"success": False, "error": "OpenAI client not initialized"}
            
        try:
            current_prefs = json.dumps(self.preferences["preferences"], indent=2)
            min_confidence = max(70, self.confidence_threshold - 10)
            
            prompt = f"""The user wants to remove one or more of their existing preferences.
                Identify which preferences should be removed.

                User's current preferences:
                {current_prefs}

                User request: "{user_request}"

                Respond in JSON format:
                {{
                    "removals": [
                        {{
                            "preference_name": "name of the preference to remove",
                            "confidence": 0-100,
                            "explanation": "why this removal was identified"
                        }}
                    ],
                    "message": "message explaining the removals to show to the user",
                    "action": "remove"
                }}

                Only include removals that:
                1. Reference existing preferences
                2. Have a confidence score of at least {min_confidence}
                """

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a preference management assistant that helps remove user preferences."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            print(f"Remove preferences result: {json.dumps(result, indent=2)}")
            
            removals_applied = []
            removals = result.get("removals", [])
            for removal in removals:
                name = removal.get("preference_name")
                confidence = removal.get("confidence", 0)
                
                if name and confidence >= self.confidence_threshold and name in self.preferences["preferences"]:
                    del self.preferences["preferences"][name]
                    removals_applied.append(name)
            
            if removals_applied:
                self.save_preferences()
                
                # Add success info to result
                result["success"] = True
                result["removals_applied"] = removals_applied
                result["action_taken"] = f"Removed {len(removals_applied)} preference(s): {', '.join(removals_applied)}"
            else:
                result["success"] = False
                result["error"] = f"No removals were applied. Either no preferences matched or confidence was below {self.confidence_threshold}%."
                result["action_taken"] = "No changes were made to your preferences."
            
            return result
            
        except Exception as e:
            print(f"Error in remove preferences: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "action": "remove"
            }
    
    def _legacy_manage_preferences(self, user_request: str) -> Dict[str, Any]:
        """
        Legacy method for backward compatibility.
        This is used as a fallback when the new prompt chain can't determine the action.
        """
        if not self.client:
            return {
                "success": False,
                "error": "OpenAI client not initialized - cannot manage preferences"
            }
            
        try:
            # Prepare current preferences for the prompt
            current_prefs_json = json.dumps(self.preferences, indent=2)
            
            prompt = f"""Analyze this user request about managing note processing preferences. The user can:
            1. Add new preferences
            2. Update existing preferences
            3. Remove preferences
            4. List current preferences
            5. Get help with preferences

            Current preferences: {current_prefs_json}

            User request: "{user_request}"

            Determine what action to take and respond in JSON format:
            {{
                "action": "add|update|remove|list|help",
                "preference_name": "name of the preference (if applicable)",
                "preference_value": "value to set (if applicable)",
                "explanation": "explanation of the preference (if applicable)",
                "message": "message to show to the user",
                "action_taken": "brief notification of what was done"
            }}

            Only include fields that are relevant to the action."""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a preference management assistant that helps users manage their note processing preferences."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            print(f"Legacy preference management response: {json.dumps(result, indent=2)}")
            
            # Take action based on LLM response
            action = result.get('action')
            if action == 'add' or action == 'update':
                name = result.get('preference_name')
                value = result.get('preference_value')
                explanation = result.get('explanation')
                if name and value is not None:
                    self.add_preference(name, value, explanation)
                    result['success'] = True
                else:
                    result['success'] = False
                    result['error'] = "Missing preference name or value"
            elif action == 'remove':
                name = result.get('preference_name')
                if name:
                    self.remove_preference(name)
                    result['success'] = True
                else:
                    result['success'] = False
                    result['error'] = "Missing preference name"
            elif action == 'list' or action == 'help':
                result['success'] = True
            else:
                result['success'] = False
                result['error'] = "Unknown action"
                
            return result
            
        except Exception as e:
            print(f"Error in legacy_manage_preferences: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def add_preference(self, name: str, value: Any, explanation: str = None):
        """Add or update a preference"""
        print(f"Adding preference: name={name}, value={value}, explanation={explanation}")
        if "preferences" not in self.preferences:
            self.preferences = {
                "preferences": {},
                "last_updated": datetime.now().isoformat()
            }
        
        self.preferences["preferences"][name] = {
            "value": value,
            "explanation": explanation,
            "updated_at": datetime.now().isoformat()
        }
        print(f"Current preferences before save: {self.preferences}")
        self.save_preferences()
        print(f"Preferences saved to {self.preferences_file}")
    
    def get_preference(self, name: str) -> Optional[Any]:
        """Get a specific preference value"""
        pref = self.preferences["preferences"].get(name)
        return pref["value"] if pref else None
    
    def remove_preference(self, name: str):
        """Remove a preference"""
        if name in self.preferences["preferences"]:
            del self.preferences["preferences"][name]
            self.save_preferences()
    
    def get_prompt_customization(self) -> str:
        """
        Generate a customization string to add to LLM prompts based on user preferences.
        """
        if not self.preferences["preferences"]:
            return ""
            
        customizations = ["USER PREFERENCES:"]
        
        for name, pref in self.preferences["preferences"].items():
            value = pref["value"]
            explanation = pref.get("explanation", "")
            customizations.append(f"- {name}: {value}" + (f" ({explanation})" if explanation else ""))
        
        return "\n".join(customizations) if len(customizations) > 1 else ""
    
    def save_identified_preferences(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Save preferences identified by the LLM analysis.
        Returns a list of saved preferences.
        """
        saved_preferences = []
        
        if not analysis_result or "identified_preferences" not in analysis_result:
            return saved_preferences
            
        identified_prefs = analysis_result["identified_preferences"]
        
        for name, details in identified_prefs.items():
            if not isinstance(details, dict):
                continue
                
            value = details.get("value")
            explanation = details.get("explanation")
            confidence = details.get("confidence", 0)
            
            if value and confidence >= self.confidence_threshold:
                self.add_preference(name, value, explanation)
                saved_preferences.append({
                    "name": name,
                    "value": value,
                    "explanation": explanation,
                    "confidence": confidence
                })
                
        return saved_preferences
    
    def add_request(self, request_text: str, note_length: int):
        """Add a user request to the history"""
        request_entry = {
            "timestamp": datetime.now().isoformat(),
            "request": request_text,
            "note_length": note_length
        }
        self.request_history.append(request_entry)
        
        if len(self.request_history) > 50:
            self.request_history = self.request_history[-50:]
            
        self.save_request_history()
    
    def update_from_request(self, user_request: str, note_length: int) -> Dict[str, Any]:
        """
        Update preferences based on the current user request and return the updated preferences.
        Also adds the request to history and uses LLM to identify new preferences.
        """
        if not user_request:
            return self.preferences
        self.add_request(user_request, note_length)
        analysis = self.process_request(user_request)
        
        return analysis
    
    def analyze_request_with_llm(self, user_request: str) -> Dict[str, Any]:
        """Legacy method for backward compatibility"""
        return self._identify_preferences(user_request)
    
    def manage_preferences(self, user_request: str) -> Dict[str, Any]:
        """Legacy method for backward compatibility"""
        return self.process_request(user_request)