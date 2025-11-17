"""
Main Application Entry Point
==========================

Simple entry point to run the chatbot application.
"""

import os
import sys
from dotenv import load_dotenv

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main entry point"""
    
    # Load environment variables safely
    try:
        load_dotenv()
    except UnicodeDecodeError:
        print("⚠️ Warning: Could not read .env file (encoding issue)")
        print("Please ensure .env file is saved in UTF-8 format")
    except Exception as e:
        print(f"⚠️ Warning: Could not load .env file: {e}")
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        print("❌ Error: OPENAI_API_KEY not found or not set properly")
        print("Please edit the .env file and add your actual OpenAI API key:")
        print("OPENAI_API_KEY=sk-your-actual-key-here")
        return
    
    print("🏥 Health Insurance Data Generator")
    print("================================")
    print("Starting Streamlit application...")
    
    # Run Streamlit app
    os.system("streamlit run streamlit_app.py")


if __name__ == "__main__":
    main()