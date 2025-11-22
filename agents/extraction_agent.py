"""
Extraction Agent - Parse natural language input
=============================================

Simple agent to extract structured data from user input.
One clear goal: Convert natural language to structured fields using Pydantic.
"""

from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
import json
import re
from config import STATE_MAPPINGS, ENROLLMENT_MAP
from models.health_insurance_models import HealthInsuranceRequest, ExtractionResult
from llm_config import get_extraction_llm


class ExtractionAgent:
    """Extract structured data from natural language input using Pydantic models"""
    
    def __init__(self, aws_access_key_id: str = None, aws_secret_access_key: str = None):
        # Use centralized LLM configuration
        self.llm = get_extraction_llm(aws_access_key_id, aws_secret_access_key)
        self.parser = PydanticOutputParser(pydantic_object=HealthInsuranceRequest)
    
    def extract(self, user_input: str) -> ExtractionResult:
        """
        Extract structured data using Pydantic schema validation
        
        Args:
            user_input: Natural language input from user (may include conversation history)
            
        Returns:
            ExtractionResult with validated Pydantic model or error details
        """
        
        try:
            system_prompt = self._build_extraction_prompt()
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Extract and accumulate data from this conversation:\n{user_input}")
            ]
            
            # Use structured output with retry logic
            response = self.llm.invoke(messages)
            
            # Parse with Pydantic validation
            try:
                parsed_data = self.parser.parse(response.content)
                
                return ExtractionResult(
                    success=True,
                    data=parsed_data,
                    error=None,
                    raw_response=response.content
                )
            except Exception as parse_error:
                # Fallback: try manual JSON parsing for backward compatibility
                try:
                    json_data = json.loads(response.content)
                    validated_data = HealthInsuranceRequest(**json_data)
                    return ExtractionResult(
                        success=True,
                        data=validated_data,
                        error=None,
                        raw_response=response.content
                    )
                except Exception as fallback_error:
                    return ExtractionResult(
                        success=False,
                        data=None,
                        error=f"Schema validation failed: {str(parse_error)}. Fallback error: {str(fallback_error)}",
                        raw_response=response.content
                    )
                    
        except Exception as llm_error:
            return ExtractionResult(
                success=False,
                data=None,
                error=f"LLM call failed: {str(llm_error)}",
                raw_response=None
            )
    
    def _build_extraction_prompt(self) -> str:
        """Build focused extraction prompt optimized for Llama 3.3 70B"""
        
        valid_states = ", ".join(sorted(set(STATE_MAPPINGS.values())))
        # Show ALL enrollment types (CRITICAL: Don't truncate!)
        valid_enrollments = "\n".join([f"  - {k}" for k in ENROLLMENT_MAP.keys()])
        
        # Get Pydantic format instructions
        format_instructions = self.parser.get_format_instructions()
        
        return f"""You are a health insurance data extraction expert. Extract ALL information from user messages into structured format.

TASK: Convert conversation to HealthInsuranceRequest JSON.

🚨 MOST IMPORTANT RULE - READ THIS FIRST:
NEVER AUTO-CORRECT USER'S NUMBERS. Extract EXACTLY what the user types.
- User says "under65 30" → Extract 30 (NOT 20, NOT 10, exactly 30)
- User says "over65 80" → Extract 80 (exactly as stated)
- Even if numbers don't sum correctly, extract them AS-IS
- Validation will handle errors - your ONLY job is verbatim extraction

CRITICAL RULES:
1. Extract EVERYTHING mentioned across all messages
2. Use null for missing fields (NEVER use "UNKNOWN")
3. Match enrollments to EXACT names from the list below
4. Be thorough - capture all details
5. ONLY accept COUNTS (direct numbers), NEVER accept percentages
   - If user provides percentages, set that field to null (they must provide counts)
   - Only extract if user gives direct count numbers like "Male 60, Female 40"
6. 🚨 NEVER AUTO-CORRECT OR ADJUST COUNTS - Extract VERBATIM from user input
   - If user says "over65 80, under65 30", extract EXACTLY 80 and 30 (NOT 80 and 20)
   - DO NOT "fix" counts to match numberOfRecords - NEVER change user's numbers
   - Validation handles count mismatches - your job is ONLY to extract what user typed
   - Even if counts don't sum to numberOfRecords, extract EXACTLY what user said

VALID OPTIONS FOR EACH FIELD:
- States: {valid_states}  
- Enrollments (MUST match exactly):
{valid_enrollments}
- Genders: M, F ONLY
- Ages: over65, under65, Any ONLY
- Environment: V2, F2, G2 ONLY
- UserType: FEPOC, NON-FEPOC ONLY
- Children: CHILD_MINOR, CHILD_MAJOR, CHILD_NEW_BORN, CHILD_UNDER_13, CHILD_OVER_13, EMPTY ONLY
- Spouses: SPOUSE_UNDER65, SPOUSE_OVER65, EMPTY ONLY

🚨 CRITICAL VALIDATION RULE - APPLIES TO ALL FIELDS:
If user provides ANY value that is NOT in the valid options list above, set that field to NULL.

MISSPELLING HANDLING:
- Minor misspellings are OK if intent is CLEAR (e.g., "femele" → "F", "stanard" → "Standard")
- BUT if the input is UNCLEAR or AMBIGUOUS, set field to NULL so bot asks for clarification
- Examples:
  * "femele 100" → CLEAR misspelling of female → Extract as {{"gender": "F", "count": 100}} ✓
  * "stanard self family" → CLEAR misspelling of standard → Extract with correct spelling ✓
  * "over66" → NOT a misspelling, wrong value → ages: null (ask for clarification) ✗
  * "V3" → NOT a misspelling, invalid env → env: null (ask for clarification) ✗

Examples of INVALID inputs (set to NULL):
- Ages: "over66", "over69", "over70", "under60" → ages: null
- Genders: "mal", "fem" (too unclear) → genders: null (only M, F valid)
- Environment: "V3", "prod", "dev" → env: null (only V2, F2, G2 valid)
- States: "XX", "ZZ" → reject those states
- Children: "infant", "teen" → children: null (only listed types valid)

RULE: Accept CLEAR misspellings, reject UNCLEAR/INVALID values. When in doubt, set to NULL to trigger clarification.

ENROLLMENT MATCHING RULES:
- "usps standard self family" → "USPS Standard Self + Family"
- "fepoc standard self only" → "FEPOC Standard-Self Only"
- Match case-insensitive, handle spacing variations
- If unclear, leave as null (DON'T use "UNKNOWN")

{format_instructions}

EXTRACTION EXAMPLES (COUNTS ONLY):
Input: "My name is John, 100 records, California 100, Male 100"
Output: {{"username": "John", "numberOfRecords": 100, "states": [{{"state": "CA", "count": 100}}], "genders": [{{"gender": "M", "count": 100}}], ...}}

Input: "100 records, 60% male, 40% female"
Output: {{"numberOfRecords": 100, "genders": null}}  // Percentages NOT accepted, must be counts

Input: "200 records, California 100, Texas 60, Florida 40"
Output: {{"numberOfRecords": 200, "states": [{{"state": "CA", "count": 100}}, {{"state": "TX", "count": 60}}, {{"state": "FL", "count": 40}}]}}

Input: "over65 80, under65 20" (VALID options)
Output: {{"ages": [{{"age": "over65", "count": 80}}, {{"age": "under65", "count": 20}}]}}

WRONG Example (DO NOT DO THIS):
Input: "over65 80, under65 30" with numberOfRecords=100
Output: {{"ages": [{{"age": "over65", "count": 80}}, {{"age": "under65", "count": 20}}]}}
// ❌ WRONG: Changed 30 to 20 to match numberOfRecords. NEVER do this! Extract exact numbers.

Input: "over69 80" (INVALID - not in valid list)
Output: {{"ages": null}}  // Reject invalid, system will ask for valid options

Input: "male 60, female 40" (INVALID - should be M, F)
Output: {{"genders": null}}  // Reject invalid format

Input: "V3 environment" (INVALID - only V2, F2, G2)
Output: {{"env": null}}  // Reject invalid

Input: "split between ca, tx, va" with 100 records
Output: {{"states": [{{"state": "CA", "count": 33}}, {{"state": "TX", "count": 33}}, {{"state": "VA", "count": 34}}]}}  // Auto-split evenly

Input: "split between texas and florida" with 100 records
Output: {{"states": [{{"state": "TX", "count": 50}}, {{"state": "FL", "count": 50}}]}}  // Handle "split between" phrase

Input: "split between texas and florida and raghu" with 100 records
Output: {{"states": [{{"state": "TX", "count": 50}}, {{"state": "FL", "count": 50}}]}}  // Ignore "raghu" (not a state)

Be precise and extract ALL data mentioned.
- UserType: FEPOC, NON-FEPOC only
- Children: CHILD_MINOR, CHILD_MAJOR, CHILD_NEW_BORN, CHILD_UNDER_13, CHILD_OVER_13, EMPTY
- Spouses: SPOUSE_UNDER65, SPOUSE_OVER65, EMPTY

SMART EXTRACTION RULES:

1. "SPLIT BETWEEN" HANDLING:
   - "split between TX and FL" → Auto-distribute evenly (50, 50 for 100 records)
   - "split between CA, TX, VA" → Auto-distribute evenly (33, 33, 34 for 100 records)
   - Calculate even split: divide numberOfRecords by number of states, remainder goes to last state

2. FILTER NON-VALID VALUES:
   - "split between texas and florida and raghu" → Extract ONLY TX and FL, IGNORE "raghu" (not a state)
   - "male 60, raghu, female 40" → Extract ONLY M and F, IGNORE "raghu" (not a gender)
   - For any field, extract ONLY values that match valid options, skip everything else

3. ACCUMULATION LOGIC:
   - Extract username from any greeting message
   - Keep username constant across conversation
   - Use LATEST values for conflicts
   - Combine all distribution data
   - IGNORE percentages - only extract direct count numbers

EXAMPLES:
"hi my name is raghu" → username: "raghu", others: null

"100 records, v2, california 50" → numberOfRecords: 100, env: "V2", states: [{{state: "CA", count: 50}}]

"Male 80, Female 20" → genders: [{{"gender": "M", "count": 80}}, {{"gender": "F", "count": 20}}]

"split between texas and florida and raghu" with 100 records → states: [{{state: "TX", count: 50}}, {{state: "FL", count: 50}}], username: "raghu"
// Smart extraction: TX and FL are states (split evenly), "raghu" is username (not a state)

"split contracts between ca, tx, va" with 90 records → states: [{{state: "CA", count: 30}}, {{state: "TX", count: 30}}, {{state: "VA", count: 30}}]
// Understands "split contracts between" = even distribution

{format_instructions}

OUTPUT REQUIREMENTS:
- Valid JSON matching HealthInsuranceRequest schema
- No empty arrays - use null instead
- All counts must be positive integers
- State codes must be 2 letters uppercase
"""