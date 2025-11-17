"""
Test count validation - verify that partial counts are caught
"""
import os
from dotenv import load_dotenv
from workflows.chatbot_workflow import ChatbotWorkflow

# Load environment
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

print("🧪 Testing count validation...\n")

workflow = ChatbotWorkflow(api_key)

# Simulate the conversation
print("=" * 60)
print("Step 1: User provides name")
print("=" * 60)
result1 = workflow.process_input("my name is raghu", [])
print(f"Follow-up: {result1['follow_up_message']}\n")

print("=" * 60)
print("Step 2: User provides 100 records")
print("=" * 60)
result2 = workflow.process_input(
    "100 records",
    result1['conversation_history'],
    result1['extracted_data']
)
print(f"Follow-up: {result2['follow_up_message']}\n")

print("=" * 60)
print("Step 3: User provides v2 and fepoc")
print("=" * 60)
result3 = workflow.process_input(
    "v2 and fepoc",
    result2['conversation_history'],
    result2['extracted_data']
)
print(f"Follow-up: {result3['follow_up_message']}\n")

print("=" * 60)
print("Step 4: User provides PARTIAL counts (CA 50, Male 100)")
print("=" * 60)
result4 = workflow.process_input(
    "california 50 and male 100 and fepoc standard self+1 100 and over65 100",
    result3['conversation_history'],
    result3['extracted_data']
)

print(f"Extracted data: {result4['extracted_data']}")
print(f"\nValidation result:")
print(f"  - Is valid: {result4['validation_result']['is_valid']}")
print(f"  - Missing fields: {result4['validation_result'].get('missing_fields', [])}")
print(f"  - Count errors: {result4['validation_result'].get('count_errors', [])}")
print(f"\nFollow-up: {result4['follow_up_message']}\n")

print("=" * 60)
print("✅ TEST RESULTS:")
print("=" * 60)

count_errors = result4['validation_result'].get('count_errors', [])
if count_errors:
    print(f"✅ PASS: Count errors detected: {count_errors}")
else:
    print("❌ FAIL: Should have detected count errors (CA 50 != 100 total)")

if not result4['is_complete']:
    print("✅ PASS: Correctly marked as incomplete")
else:
    print("❌ FAIL: Should not be complete with count errors")

if "50" in result4['follow_up_message'] or "count" in result4['follow_up_message'].lower():
    print("✅ PASS: Follow-up mentions count issue")
else:
    print(f"❌ FAIL: Follow-up should mention count problem")
