#!/usr/bin/env python3
"""
Knowledge Assistant Runner

Usage:
    python run.py [options]

Examples:
    python run.py                           # Run the application normally
    python run.py --init-db                 # Initialize the database before running
    python run.py --port 8080               # Run on a specific port
    python run.py --check                   # Check dependencies only
    python run.py --reset-db                # Reset the database (warning: deletes data)
    python run.py --enable-watch            # Enable file watching (for development only)
    python run.py --streamlit-args "server.maxUploadSize=200,server.enableXsrfProtection=false"  # Pass additional Streamlit options
"""

import os
import sys
import argparse
import subprocess
import importlib
import shutil
from pathlib import Path

class Colors:
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    BOLD = '\033[1m'
    NC = '\033[0m' 

def print_colored(text, color=Colors.NC, end='\n'):
    """Print colored text to the console"""
    print(f"{color}{text}{Colors.NC}", end=end)

def check_dependencies():
    """Check if all required dependencies are installed"""
    print_colored("Checking dependencies...", Colors.BLUE)
    
    required_packages = [
        "streamlit", "docling", "lancedb", "tiktoken", "openai", 
        "pandas", "numpy", "pydantic", "nltk"
    ]
    
    package_map = {
        "python-dotenv": "dotenv"
    }
    
    optional_packages = [
        "tantivy"
    ]
    
    missing_packages = []
    optional_missing = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print_colored(f"✓ {package} installed", Colors.GREEN)
        except ImportError:
            missing_packages.append(package)
            print_colored(f"✗ {package} not installed", Colors.RED)
    
    for package, import_name in package_map.items():
        try:
            importlib.import_module(import_name)
            print_colored(f"✓ {package} installed", Colors.GREEN)
        except ImportError:
            missing_packages.append(package)
            print_colored(f"✗ {package} not installed", Colors.RED)
    
    for package in optional_packages:
        try:
            importlib.import_module(package)
            print_colored(f"✓ {package} installed (optional)", Colors.GREEN)
        except ImportError:
            optional_missing.append(package)
            print_colored(f"? {package} not installed (optional)", Colors.YELLOW)
    
    try:
        import nltk
        nltk_data_dir = Path("data/nltk_data")
        nltk_resources = ["punkt", "stopwords", "wordnet", "averaged_perceptron_tagger"]
        missing_nltk = []
        for resource in nltk_resources:
            try:
                if nltk.data.find(resource, paths=[str(nltk_data_dir)]):
                    continue
            except (LookupError, IOError):
                pass
            missing_nltk.append(resource)
        
        if missing_nltk:
            print_colored(f"? Some NLTK resources missing: {', '.join(missing_nltk)}", Colors.YELLOW)
            print_colored("  These will be downloaded automatically when needed", Colors.YELLOW)
        else:
            print_colored("✓ NLTK data is available", Colors.GREEN)
    except Exception as e:
        print_colored(f"? NLTK check failed: {e}", Colors.YELLOW)
        print_colored("  NLTK data will be downloaded automatically when needed", Colors.YELLOW)
    
    # Check OpenAI API key
    if os.getenv("OPENAI_API_KEY"):
        print_colored("✓ OpenAI API key found in environment", Colors.GREEN)
    else:
        dotenv_file = Path(".env")
        if dotenv_file.exists() and "OPENAI_API_KEY" in dotenv_file.read_text():
            print_colored("✓ OpenAI API key found in .env file", Colors.GREEN)
        else:
            print_colored("✗ OpenAI API key not found", Colors.RED)
            missing_packages.append("OPENAI_API_KEY")
    
    return missing_packages, optional_missing

def initialize_database(reset=False):
    """Initialize or reset the database"""
    if reset:
        print_colored("WARNING: You are about to reset the database. All data will be lost!", Colors.RED)
        print_colored("Are you sure you want to continue? (y/N): ", Colors.YELLOW, end="")
        response = input().strip().lower()
        
        if response != "y":
            print_colored("Database reset cancelled.", Colors.GREEN)
            return False
        
        # Remove the database directory
        db_path = Path("data/lancedb")
        if db_path.exists():
            try:
                shutil.rmtree(db_path)
                print_colored("Database directory removed.", Colors.GREEN)
            except Exception as e:
                print_colored(f"Error removing database directory: {e}", Colors.RED)
                return False
    
    print_colored("Initializing database...", Colors.BLUE)
    
    try:
        result = subprocess.run(
            [sys.executable, "utils/init_db.py"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print_colored("Database initialization successful!", Colors.GREEN)
            return True
        else:
            print_colored("Database initialization failed.", Colors.RED)
            print_colored("Error output:", Colors.RED)
            print(result.stderr)
            return False
    except Exception as e:
        print_colored(f"Error initializing database: {e}", Colors.RED)
        return False

def run_application(port=None, enable_watch=False, streamlit_args=None):
    """Run the Streamlit application
    
    Args:
        port (int, optional): Port to run the application on
        enable_watch (bool, optional): Whether to enable file watching
        streamlit_args (str, optional): Additional arguments to pass to Streamlit
    """
    print_colored("Starting Knowledge Assistant...", Colors.BLUE)
    
    command = [
        "streamlit", "run", "app/app_st.py",
    ]
    
    if port:
        command.extend(["--server.port", str(port)])
    
    command.extend([
        "--server.address", "0.0.0.0",
        "--browser.gatherUsageStats", "false",
    ])
    
    if not enable_watch:
        command.append("--server.fileWatcherType=none")
        os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
        os.environ["WATCHDOG_DISABLE"] = "1"
        print_colored("File watching disabled for better performance", Colors.YELLOW)
    else:
        print_colored("File watching enabled - use only during development", Colors.YELLOW)
    
    if streamlit_args:
        for arg_pair in streamlit_args.split(','):
            if '=' in arg_pair:
                key, value = arg_pair.split('=', 1)
                command.append(f"--{key.strip()}={value.strip()}")
    
    command_str = ' '.join(command)
    print_colored(f"Running command: {command_str}", Colors.BLUE)
    
    try:
        os.execvp(command[0], command)
    except Exception as e:
        print_colored(f"Error starting application: {e}", Colors.RED)
        return False

def main():
    """Main function to parse arguments and run the appropriate action"""
    parser = argparse.ArgumentParser(description="Knowledge Assistant Runner")
    
    parser.add_argument("--init-db", action="store_true", help="Initialize the database before running")
    parser.add_argument("--reset-db", action="store_true", help="Reset the database (warning: deletes data)")
    parser.add_argument("--port", type=int, help="Port to run the application on")
    parser.add_argument("--check", action="store_true", help="Check dependencies and exit")
    parser.add_argument("--enable-watch", action="store_true", 
                      help="Enable file watching (for development only)")
    parser.add_argument("--streamlit-args", type=str, help="Additional arguments to pass to Streamlit (format: 'arg1=val1,arg2=val2')")
    
    args = parser.parse_args()
    
    print_colored("\n" + "="*60, Colors.BOLD)
    print_colored("             KNOWLEDGE ASSISTANT RUNNER", Colors.BOLD)
    print_colored("="*60 + "\n", Colors.BOLD)
    
    missing_packages, optional_missing = check_dependencies()
    
    if missing_packages:
        print_colored("\nSome required dependencies are missing:", Colors.RED)
        print_colored("Please install them with pip:", Colors.YELLOW)
        print(f"pip install {' '.join(p for p in missing_packages if p != 'OPENAI_API_KEY')}")
        
        if "OPENAI_API_KEY" in missing_packages:
            print_colored("\nOpenAI API key is missing:", Colors.RED)
            print_colored("1. Create a .env file in the project root directory", Colors.YELLOW)
            print_colored("2. Add your OpenAI API key: OPENAI_API_KEY=your_key_here", Colors.YELLOW)
        
        if args.check or missing_packages:
            if args.check:
                print_colored("\nDependency check complete. Fix issues to run the application.", Colors.BLUE)
            sys.exit(1)
    
    if optional_missing and not args.check:
        print_colored("\nSome optional dependencies are missing:", Colors.YELLOW)
        print_colored("These provide additional functionality but aren't required:", Colors.YELLOW)
        print(f"pip install {' '.join(optional_missing)}")
    
    if args.check:
        print_colored("\nAll required dependencies are installed!", Colors.GREEN)
        sys.exit(0)
    
    for directory in ["data/uploads", "data/lancedb", "data/nltk_data"]:
        os.makedirs(directory, exist_ok=True)
    
    if args.reset_db or args.init_db:
        success = initialize_database(reset=args.reset_db)
        if not success:
            sys.exit(1)
    
    run_application(port=args.port, enable_watch=args.enable_watch, streamlit_args=args.streamlit_args)

if __name__ == "__main__":
    main() 