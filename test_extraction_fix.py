"""
Quick test to verify the empty array → None conversion fix
"""
import os
from dotenv import load_dotenv
from workflows.chatbot_workflow import ChatbotWorkflow

# Load environment
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("❌ No API key found!")
    exit(1)

print("🧪 Testing extraction with incremental data...\n")

# Initialize workflow
workflow = ChatbotWorkflow(api_key)

# Test 1: Just username
print("=" * 60)
print("Test 1: User provides only name")
print("=" * 60)
result1 = workflow.process_input("my name is rahul", [])
print(f"Extracted data: {result1['extracted_data']}")
print(f"Is complete: {result1['is_complete']}")
print(f"Missing fields: {result1['validation_result'].get('missing_fields', [])}")
print(f"Follow-up: {result1['follow_up_message']}")

# Test 2: Add number of records
print("\n" + "=" * 60)
print("Test 2: User adds number of records")
print("=" * 60)
result2 = workflow.process_input(
    "100", 
    result1['conversation_history'],
    result1['extracted_data']
)
print(f"Extracted data: {result2['extracted_data']}")
print(f"Is complete: {result2['is_complete']}")
print(f"Missing fields: {result2['validation_result'].get('missing_fields', [])}")
print(f"Follow-up: {result2['follow_up_message']}")

# Test 3: Add env and usertype
print("\n" + "=" * 60)
print("Test 3: User adds environment and usertype")
print("=" * 60)
result3 = workflow.process_input(
    "v2 and fepoc", 
    result2['conversation_history'],
    result2['extracted_data']
)
print(f"Extracted data: {result3['extracted_data']}")
print(f"Is complete: {result3['is_complete']}")
print(f"Missing fields: {result3['validation_result'].get('missing_fields', [])}")
print(f"Follow-up: {result3['follow_up_message']}")

# Check if it's asking for remaining fields
print("\n" + "=" * 60)
print("✅ TEST RESULTS:")
print("=" * 60)

missing = result3['validation_result'].get('missing_fields', [])
expected_missing = ['states', 'genders', 'enrollments', 'ages']

if result3['is_complete']:
    print("❌ FAIL: Should not be complete yet!")
else:
    print("✅ PASS: Correctly marked as incomplete")

if all(field in missing for field in expected_missing):
    print(f"✅ PASS: Correctly identified missing fields: {missing}")
else:
    print(f"❌ FAIL: Expected missing fields {expected_missing}, got {missing}")

if "state" in result3['follow_up_message'].lower():
    print("✅ PASS: Follow-up message asks for missing fields")
else:
    print(f"❌ FAIL: Follow-up should ask for states, genders, etc.")

print("\n" + "=" * 60)
