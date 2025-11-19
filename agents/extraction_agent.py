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

CRITICAL RULES:
1. Extract EVERYTHING mentioned across all messages
2. Use null for missing fields (NEVER use "UNKNOWN")
3. Match enrollments to EXACT names from the list below
4. Be thorough - capture all details

FIELD MAPPINGS:
- States: {valid_states}  
- Enrollments (MUST match exactly):
{valid_enrollments}
- Genders: M, F only
- Ages: over65, under65, Any only  
- Environment: V2, F2, G2 ONLY

ENROLLMENT MATCHING RULES:
- "usps standard self family" → "USPS Standard Self + Family"
- "fepoc standard self only" → "FEPOC Standard-Self Only"
- Match case-insensitive, handle spacing variations
- If unclear, leave as null (DON'T use "UNKNOWN")

{format_instructions}

EXAMPLES:
Input: "My name is John, 100 records, California 100, Male 100"
Output: {{"username": "John", "numberOfRecords": 100, "states": [{{"state": "CA", "count": 100}}], "genders": [{{"gender": "M", "count": 100}}], ...}}

Be precise and extract ALL data mentioned.
- UserType: FEPOC, NON-FEPOC only
- Children: CHILD_MINOR, CHILD_MAJOR, CHILD_NEW_BORN, CHILD_UNDER_13, CHILD_OVER_13, EMPTY
- Spouses: SPOUSE_UNDER65, SPOUSE_OVER65, EMPTY

ACCUMULATION LOGIC:
1. Extract username from any greeting message
2. Keep username constant across conversation
3. Use LATEST values for conflicts
4. Combine all distribution data

EXAMPLES:
"hi my name is raghu" → username: "raghu", others: null
"100 records, v2, california 50" → numberOfRecords: 100, env: "V2", states: [{{state: "CA", count: 50}}]

{format_instructions}

OUTPUT REQUIREMENTS:
- Valid JSON matching HealthInsuranceRequest schema
- No empty arrays - use null instead
- All counts must be positive integers
- State codes must be 2 letters uppercase
"""