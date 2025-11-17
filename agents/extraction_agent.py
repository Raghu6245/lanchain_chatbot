"""
Extraction Agent - Parse natural language input
=============================================

Simple agent to extract structured data from user input.
One clear goal: Convert natural language to structured fields.
"""

from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json
import re
from config import STATE_MAPPINGS, ENROLLMENT_MAP


class ExtractionAgent:
    """Extract structured data from natural language input"""
    
    def __init__(self, api_key: str):
        self.llm = ChatOpenAI(
            temperature=0,
            model="gpt-4",
            api_key=api_key
        )
    
    def extract(self, user_input: str) -> Dict[str, Any]:
        """
        Extract all possible fields from user input
        
        Args:
            user_input: Natural language input from user (may include conversation history)
            
        Returns:
            Dictionary with extracted fields and confidence
        """
        
        system_prompt = self._build_extraction_prompt()
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Extract and accumulate data from this conversation:\n{user_input}")
        ]
        
        response = self.llm(messages)
        
        try:
            extracted_data = json.loads(response.content)
            return extracted_data
        except json.JSONDecodeError:
            return {"error": "Failed to parse extraction result", "raw_response": response.content}
    
    def _build_extraction_prompt(self) -> str:
        """Build focused extraction prompt following KERNEL principles"""
        
        valid_states = ", ".join(sorted(set(STATE_MAPPINGS.values())))
        valid_enrollments = list(ENROLLMENT_MAP.keys())[:5]  # Show first 5 as examples
        
        return f"""EXTRACT and ACCUMULATE health insurance data from conversation. Be conversational and friendly.

CRITICAL: You will receive the full conversation history. Extract ALL data mentioned across ALL messages and combine them into ONE complete response.

OUTPUT REQUIREMENTS:
Return valid JSON with these exact fields. IMPORTANT: Use null (not empty array []) for missing fields:

{{
    "username": "string or null - alphanumeric only (extract from greetings like 'my name is X')",
    "numberOfRecords": "integer or null - 1 to 10000",
    "env": "string or null - ONLY V2, F2, or G2 (reject v3, v1, etc.)",
    "UserType": "string or null - FEPOC/NON-FEPOC only",
    "states": "null or [{{"state": "XX", "count": "number"}}] - null if not mentioned",
    "genders": "null or [{{"gender": "M/F/EMPTY", "count": "number"}}] - null if not mentioned",
    "enrollments": "null or [{{"name": "enrollment_name", "count": "number"}}] - null if not mentioned",
    "ages": "null or [{{"age": "over65/under65/Any", "count": "number"}}] - null if not mentioned",
    "children": "null or [{{"type": "child_type", "count": "number"}}] - null if not mentioned",
    "spouses": "null or [{{"type": "spouse_type", "count": "number"}}] - null if not mentioned",
    "confidence": "high/medium/low"
}}

CRITICAL: If a field is not mentioned in the conversation, set it to null, NOT to an empty array [].

MAPPING RULES:
- States: Convert to 2-letter codes: {valid_states}
- Enrollments: Match to: {valid_enrollments}...
- Genders: M, F, EMPTY only
- Ages: over65, under65, Any only
- Environment: ONLY V2, F2, G2 - if user says v3, v1, etc. set to null
- Children: CHILD_MINOR, CHILD_MAJOR, CHILD_NEW_BORN, CHILD_UNDER_13, CHILD_OVER_13, EMPTY
- Spouses: SPOUSE_UNDER65, SPOUSE_OVER65, EMPTY

ACCUMULATION LOGIC (MOST IMPORTANT):
1. Read through ALL messages in the conversation
2. Extract username from ANY message where user introduces themselves
3. Keep username constant - if "raghu" was mentioned before, always use "raghu"
4. Accumulate data: if first message has username, second has states, combine both
5. For counts/distributions, use the LATEST values if there's conflict
6. Always preserve previously extracted fields unless explicitly overridden

EXAMPLES:
Message 1: "hi my name is rahul"
→ {{"username": "rahul", all other fields: null}}

Full conversation:
"User: hi my name is raghu"
"User: environment is v2 and 100 records"
→ {{"username": "raghu", "numberOfRecords": 100, "env": "V2", other fields: null}}

Full conversation:
"User: my name is raghu"
"User: v3 environment, 100 contracts, california 50 texas 50"
→ {{"username": "raghu", "numberOfRecords": 100, "env": null, "states": [{{"state": "CA", "count": 50}}, {{"state": "TX", "count": 50}}], ...}}"""

    def _normalize_state(self, state_text: str) -> Optional[str]:
        """Convert state name/abbreviation to standard 2-letter code"""
        state_clean = state_text.lower().strip()
        return STATE_MAPPINGS.get(state_clean)
    
    def _normalize_enrollment(self, enrollment_text: str) -> Optional[str]:
        """Find matching enrollment type"""
        enrollment_clean = enrollment_text.lower().strip()
        
        for enrollment_name in ENROLLMENT_MAP:
            if enrollment_clean in enrollment_name.lower():
                return enrollment_name
        return None