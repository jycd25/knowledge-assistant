import os
from pathlib import Path
import argparse
import logging

class FileRemover:
    
    def __init__(self, directory_path=None, st_callback=None):
        self.directory_path = directory_path
        self.st_callback = st_callback
        
    def log(self, message, level="info"):
        print(message)
        
        if self.st_callback and callable(self.st_callback):
            try:
                self.st_callback(message, level)
            except Exception as e:
                print(f"Error with Streamlit callback: {e}")
    
    def remove(self, file_path):
        path = Path(file_path)
        if not path.exists():
            self.log(f"Error: File '{file_path}' does not exist.", "error")
            return False
        
        if not path.is_file():
            self.log(f"Error: '{file_path}' is not a file.", "error")
            return False
            
        try:
            os.remove(path)
            self.log(f"Removed: {file_path}")
            return True
        except Exception as e:
            self.log(f"Error removing {file_path}: {e}", "error")
            return False
    
    def remove_all_files(self, directory_path=None):
        """Remove all files in the specified directory."""
        target_dir = directory_path or self.directory_path
        self.log(f"remove_all_files called with target_dir: {target_dir}")
        
        if not target_dir:
            self.log("Error: No directory path specified.", "error")
            return 0
        
        path = Path(target_dir)
        self.log(f"Absolute path: {path.absolute()}")
        self.log(f"Path exists: {path.exists()}, is_dir: {path.is_dir()}")
        
        if not path.exists() or not path.is_dir():
            self.log(f"Error: Directory '{target_dir}' does not exist or is not a directory.", "error")
            return 0
        
        success_count = 0
        failure_count = 0
        
        self.log(f"Files in directory before removal:")
        file_list = []
        for file_path in path.iterdir():
            if file_path.is_file():
                file_list.append(file_path)
                self.log(f"  {file_path}")
        
        if not file_list:
            self.log("No files found to remove.")
            return 0
        
        for file_path in file_list:
            if file_path.is_file():
                self.log(f"Attempting to remove: {file_path}")
                if self.remove(file_path):
                    success_count += 1
                else:
                    failure_count += 1
        
        self.log(f"Files in directory after removal:")
        remaining_files = 0
        for file_path in path.iterdir():
            if file_path.is_file():
                self.log(f"  {file_path}")
                remaining_files += 1
        
        self.log(f"Files removed: {success_count}, Files failed: {failure_count}")
        return success_count