# 🏥 Health Insurance Data Generator - Quick Start

## ✅ Installation Complete!

Your chatbot is ready to use. Here's what was built:

### 📁 Project Structure
```
lanchain_chatbot/
├── agents/                    # 3 specialized AI agents
├── workflows/                 # LangGraph orchestration  
├── generated_files/           # Output JSON files
├── config.py                  # Validation rules & mappings
├── streamlit_app.py          # Chat interface
├── requirements.txt          # Dependencies (installed ✅)
├── venv/                     # Virtual environment (ready ✅)
└── run_chatbot.bat           # Easy launcher
```

### 🚀 How to Run

**Option 1: Easy Launcher (Windows)**
1. Double-click `run_chatbot.bat`
2. Your browser will open automatically

**Option 2: Manual Start**
1. Open command prompt in this folder
2. Run: `venv\Scripts\activate`
3. Run: `streamlit run streamlit_app.py`

### 🔑 Setup Required

**IMPORTANT**: Add your OpenAI API key to `.env` file:
```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 💬 Example Usage

Try these inputs in the chat:

**Complete Input:**
```
john123, 1000 records for V2, NON-FEPOC, California 600 Texas 400, 
male 700 female 300, FEPOC Standard Self+Family 1000, 
under65 800 over65 200, minor children 600 major children 400
```

**Incomplete Input:**
```
sarah, need 500 records for production with CA and TX
```

### ✨ Features Tested & Working

- ✅ Natural language parsing
- ✅ Count validation (must sum correctly)
- ✅ State & enrollment code validation
- ✅ Family logic (Self Only vs Self+Family)
- ✅ JSON generation with string counts
- ✅ File download in Streamlit
- ✅ Conversation history
- ✅ Error handling & follow-up questions

### 🛠️ Architecture

**3-Agent System:**
1. **Extraction Agent**: Parses natural language → structured data
2. **Validation Agent**: Checks completeness & count accuracy  
3. **JSON Generator**: Creates properly formatted JSON files

**LangGraph Workflow:**
```
User Input → Extract → Validate → [Complete?] → Generate JSON
                                    ↓ [Missing data]
                                Ask Follow-up Questions
```

### 📋 Validation Rules

- All counts must sum exactly to `numberOfRecords`
- Valid state codes (50 states + DC + OS)
- Valid enrollment types from configuration
- Conditional family details based on enrollment type
- All output counts stored as strings

### 🎯 Ready to Use!

Your chatbot follows KERNEL principles:
- **K**eep it simple: Clean, focused agents
- **E**asy to verify: Clear success criteria  
- **R**eproducible: No temporal dependencies
- **N**arrow scope: One goal per agent
- **E**xplicit constraints: Clear validation rules
- **L**ogical structure: Input → Process → Output

Enjoy building synthetic health insurance datasets! 🎉