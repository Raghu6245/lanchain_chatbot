"""
Streamlit Chat Interface
======================

Simple chat interface for the health insurance chatbot.
One goal: Enable easy conversation with file download.
"""

import streamlit as st
import os
from dotenv import load_dotenv
import json
import sys

# Add project root to Python path
sys.path.append('.')

from workflows.chatbot_workflow import ChatbotWorkflow

# Load environment variables safely
try:
    load_dotenv()
except UnicodeDecodeError:
    st.warning("⚠️ Could not read .env file (encoding issue). Please ensure it's saved in UTF-8 format.")
except Exception as e:
    st.warning(f"⚠️ Could not load .env file: {e}")

# Page configuration
st.set_page_config(
    page_title="Health Insurance Data Generator",
    page_icon="🏥",
    layout="wide"
)

def main():
    """Main Streamlit application"""
    
    st.title("🏥 Health Insurance Data Generator")
    st.markdown("Generate synthetic health insurance data through natural conversation")
    
    # Initialize session state
    if "workflow" not in st.session_state:
        st.session_state.workflow = None
    
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    
    if "accumulated_data" not in st.session_state:
        st.session_state.accumulated_data = {}
    
    if "last_json_result" not in st.session_state:
        st.session_state.last_json_result = None
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # OpenAI API Key input
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=os.getenv("OPENAI_API_KEY", ""),
            help="Enter your OpenAI API key"
        )
        
        if api_key and not st.session_state.workflow:
            try:
                st.session_state.workflow = ChatbotWorkflow(api_key)
                st.success("✅ Chatbot initialized!")
            except Exception as e:
                st.error(f"❌ Error initializing chatbot: {e}")
        
        # Show last generated file
        if st.session_state.last_json_result and st.session_state.last_json_result.get("success"):
            st.header("Last Generated File")
            
            # Download button
            json_data = st.session_state.last_json_result["data"]
            json_string = json.dumps(json_data, indent=2)
            
            st.download_button(
                label="📥 Download JSON",
                data=json_string,
                file_name=st.session_state.last_json_result["filename"],
                mime="application/json"
            )
            
            # Show preview
            with st.expander("Preview JSON"):
                st.json(json_data)
    
    # Main chat interface
    if not st.session_state.workflow:
        st.warning("⚠️ Please enter your OpenAI API key in the sidebar to start")
        
        # Show example inputs
        st.header("Example Inputs")
        
        examples = [
            "john123, 1000 records for V2, NON-FEPOC, California 600 Texas 400, male 700 female 300, FEPOC Standard Self+Family 1000, under65 800 over65 200, minor children 600 major children 400",
            "sarah, need 500 records for production with CA 300, TX 200, mostly female, USPS Basic Self Only",
            "mike123, 250 records, V2, FEPOC, Texas only, equal gender split, Standard Self+1"
        ]
        
        for i, example in enumerate(examples, 1):
            with st.expander(f"Example {i}"):
                st.code(example)
        
        return
    
    # Chat interface
    st.header("Chat")
    
    # Display conversation history
    for message in st.session_state.conversation_history:
        if message.startswith("User: "):
            with st.chat_message("user"):
                st.write(message[6:])  # Remove "User: " prefix
        elif message.startswith("Bot: "):
            with st.chat_message("assistant"):
                st.write(message[5:])  # Remove "Bot: " prefix
    
    # Chat input
    user_input = st.chat_input("Describe your health insurance data requirements...")
    
    if user_input:
        # Display user message
        with st.chat_message("user"):
            st.write(user_input)
        
        # Process with workflow
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                try:
                    result = st.session_state.workflow.process_input(
                        user_input, 
                        st.session_state.conversation_history,
                        st.session_state.accumulated_data
                    )
                    
                    # Update conversation history and accumulated data
                    st.session_state.conversation_history = result["conversation_history"]
                    st.session_state.accumulated_data = result["extracted_data"]
                    
                    # Display bot response
                    st.write(result["follow_up_message"])
                    
                    # If JSON was generated successfully, store it
                    if result.get("json_result") and result["json_result"].get("success"):
                        st.session_state.last_json_result = result["json_result"]
                        st.success("🎉 JSON file generated! Check the sidebar to download.")
                
                except Exception as e:
                    st.error(f"❌ Error processing input: {e}")
                    st.error("Please check your API key and try again.")
    
    # Clear conversation button
    if st.button("🗑️ Clear Conversation"):
        st.session_state.conversation_history = []
        st.session_state.accumulated_data = {}
        st.session_state.last_json_result = None
        st.rerun()


if __name__ == "__main__":
    main()