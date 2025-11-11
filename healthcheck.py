#!/usr/bin/env python3
"""
Health check script for Book OCR system.
Validates all dependencies and configurations.
"""

import sys
import os
from pathlib import Path
import subprocess

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_status(check_name, passed, message=""):
    status = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
    print(f"{status} {check_name}", end="")
    if message:
        print(f" - {message}")
    else:
        print()
    return passed

def check_python_version():
    """Check Python version >= 3.11"""
    version = sys.version_info
    passed = version.major == 3 and version.minor >= 11
    msg = f"Python {version.major}.{version.minor}.{version.micro}"
    return print_status("Python Version", passed, msg)

def check_command_exists(cmd):
    """Check if a command exists"""
    try:
        subprocess.run([cmd, "--version"], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False

def check_tesseract():
    """Check Tesseract installation"""
    exists = check_command_exists("tesseract")
    return print_status("Tesseract OCR", exists, 
                       "Required for fallback OCR" if not exists else "Installed")

def check_docker():
    """Check Docker installation"""
    exists = check_command_exists("docker")
    return print_status("Docker", exists, 
                       "Optional (needed for containerized deployment)" if not exists else "Installed")

def check_env_file():
    """Check .env file exists and has API key"""
    env_path = Path(".env")
    if not env_path.exists():
        return print_status(".env file", False, "File not found. Copy from .env.example")
    
    with open(env_path) as f:
        content = f.read()
    
    if "your_api_key_here" in content:
        return print_status("API Key", False, "Update GEMINI_API_KEY in .env")
    
    if "GEMINI_API_KEY" not in content:
        return print_status("API Key", False, "GEMINI_API_KEY not found in .env")
    
    return print_status("API Key", True, "Configured")

def check_directories():
    """Check required directories exist"""
    dirs = ["input", "output", "cache", "src"]
    all_exist = True
    
    for dir_name in dirs:
        exists = Path(dir_name).exists()
        if not exists:
            all_exist = False
        print_status(f"Directory: {dir_name}", exists)
    
    return all_exist

def check_python_packages():
    """Check required Python packages"""
    required = [
        "google.generativeai",
        "pdf2image",
        "PIL",
        "pytesseract",
        "cv2",
        "yaml",
        "tenacity",
        "tqdm"
    ]
    
    all_installed = True
    for package in required:
        try:
            if package == "PIL":
                __import__("PIL")
            elif package == "cv2":
                __import__("cv2")
            elif package == "yaml":
                __import__("yaml")
            else:
                __import__(package)
            print_status(f"Package: {package}", True)
        except ImportError:
            print_status(f"Package: {package}", False, "Not installed")
            all_installed = False
    
    return all_installed

def check_gemini_connection():
    """Test Gemini API connection"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your_api_key_here":
            return print_status("Gemini API Connection", False, "Invalid API key")
        
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Simple test
        response = model.generate_content("Hello")
        success = bool(response.text)
        
        return print_status("Gemini API Connection", success, 
                          "Connected" if success else "Failed")
    except Exception as e:
        return print_status("Gemini API Connection", False, str(e))

def main():
    print("\n" + "="*50)
    print("Book OCR System Health Check")
    print("="*50 + "\n")
    
    results = []
    
    # System checks
    print("System Dependencies:")
    results.append(check_python_version())
    results.append(check_tesseract())
    results.append(check_docker())
    print()
    
    # Configuration checks
    print("Configuration:")
    results.append(check_env_file())
    results.append(check_directories())
    print()
    
    # Python packages
    print("Python Packages:")
    results.append(check_python_packages())
    print()
    
    # API connection
    print("API Connection:")
    results.append(check_gemini_connection())
    print()
    
    # Summary
    print("="*50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"{GREEN}✓ All checks passed! ({passed}/{total}){RESET}")
        print("\nYou're ready to process books!")
        print("Try: python main.py -i input/book.pdf -o output/book.md")
        return 0
    else:
        print(f"{RED}✗ Some checks failed ({passed}/{total}){RESET}")
        print("\nPlease fix the issues above before proceeding.")
        return 1

if __name__ == "__main__":
    sys.exit(main())