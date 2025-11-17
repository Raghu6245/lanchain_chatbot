# Health Insurance Data Generator Chatbot

A simple 3-agent LLM system for generating synthetic health insurance data through natural language conversation.

## Features

- **Natural Language Processing**: Understand complex requirements in plain English
- **Count Validation**: Ensure all distributions sum correctly to total records
- **Configuration Compliance**: Validate against state codes, enrollment types, etc.
- **Conditional Logic**: Handle family enrollment requirements automatically
- **JSON Generation**: Output properly formatted JSON files with string counts

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up your OpenAI API key**:
   ```bash
   copy .env.example .env
   # Edit .env and add your OpenAI API key
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

## Usage Examples

### Complete Input
```
john123, 1000 records for V2, NON-FEPOC, California 600 Texas 400, male 700 female 300, FEPOC Standard Self+Family 1000, under65 800 over65 200, minor children 600 major children 400
```

### Incomplete Input
```
sarah, need 500 records for production with mostly California and some Texas
```
→ System will ask for specific counts and missing details

## Architecture

- **Extraction Agent**: Parse natural language → structured data
- **Validation Agent**: Check completeness + count accuracy
- **JSON Generator**: Create final JSON files
- **LangGraph Workflow**: Coordinate agents with smart routing
- **Streamlit UI**: Simple chat interface with file download

## Configuration

All valid states, enrollment codes, and business rules are defined in `config.py`.

## Output

Generated JSON files are saved to `generated_files/` with format:
`{username}_data_{timestamp}.json`