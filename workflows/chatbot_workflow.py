"""
Main Workflow - Coordinate agents using LangGraph
===============================================

Simple workflow: Extract → Validate → Generate JSON or Ask for More Info
"""

from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from agents.extraction_agent import ExtractionAgent
from agents.validation_agent import ValidationAgent
from agents.json_generator_agent import JsonGeneratorAgent
from models.health_insurance_models import HealthInsuranceRequest, ExtractionResult


class WorkflowState(TypedDict):
    """State shared across all agents"""
    user_input: str
    extraction_result: ExtractionResult  # Changed from extracted_data
    validation_result: Dict[str, Any]
    json_result: Dict[str, Any]
    conversation_history: List[str]
    is_complete: bool
    follow_up_message: str


class ChatbotWorkflow:
    """Main workflow orchestrating the 3 agents"""
    
    def __init__(self, aws_access_key_id: str = None, aws_secret_access_key: str = None):
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.extraction_agent = ExtractionAgent(aws_access_key_id, aws_secret_access_key)
        self.validation_agent = ValidationAgent()
        self.json_generator_agent = JsonGeneratorAgent()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Create the state graph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("extract", self._extract_node)
        workflow.add_node("validate", self._validate_node)
        workflow.add_node("generate_json", self._generate_json_node)
        workflow.add_node("generate_followup", self._generate_followup_node)
        
        # Set entry point
        workflow.set_entry_point("extract")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "validate",
            self._should_generate_json,
            {
                "complete": "generate_json",
                "incomplete": "generate_followup"
            }
        )
        
        # Add edges
        workflow.add_edge("extract", "validate")
        workflow.add_edge("generate_json", END)
        workflow.add_edge("generate_followup", END)
        
        return workflow.compile()
    
    def process_input(self, user_input: str, conversation_history: List[str] = None, accumulated_data: ExtractionResult = None) -> Dict[str, Any]:
        """
        Process user input through the workflow
        
        Args:
            user_input: User's natural language input
            conversation_history: Previous conversation messages
            accumulated_data: Previously extracted data from earlier messages
            
        Returns:
            Final result with JSON file or follow-up questions
        """
        
        initial_state = {
            "user_input": user_input,
            "extraction_result": accumulated_data or ExtractionResult(success=False, data=None),
            "validation_result": {},
            "json_result": {},
            "conversation_history": conversation_history or [],
            "is_complete": False,
            "follow_up_message": ""
        }
        
        # Run the workflow
        final_state = self.graph.invoke(initial_state)
        
        return final_state
    
    def _extract_node(self, state: WorkflowState) -> WorkflowState:
        """Extract structured data from user input using Pydantic validation"""
        
        # Build full conversation context for extraction
        conversation_context = "\n".join(state["conversation_history"]) if state["conversation_history"] else ""
        full_input = f"{conversation_context}\nUser: {state['user_input']}" if conversation_context else state["user_input"]
        
        # Get previously accumulated data
        previous_result = state.get("extraction_result")
        previous_data = previous_result.data if previous_result and previous_result.success else None
        
        # Extract new data from conversation
        new_extraction_result = self.extraction_agent.extract(full_input)
        
        # Merge with previous data if both exist
        if previous_data and new_extraction_result.success and new_extraction_result.data:
            merged_data = self._merge_pydantic_data(previous_data, new_extraction_result.data)
            new_extraction_result.data = merged_data
        
        state["extraction_result"] = new_extraction_result
        state["conversation_history"].append(f"User: {state['user_input']}")
        
        return state
    
    def _merge_pydantic_data(self, previous: HealthInsuranceRequest, new: HealthInsuranceRequest) -> HealthInsuranceRequest:
        """Merge two Pydantic models, preferring new values over previous ones"""
        
        # Convert to dicts for easier merging
        prev_dict = previous.dict()
        new_dict = new.dict()
        
        # Merge logic: prefer new non-null values, keep previous if new is null
        merged = {}
        all_keys = set(list(prev_dict.keys()) + list(new_dict.keys()))
        
        for key in all_keys:
            new_value = new_dict.get(key)
            previous_value = prev_dict.get(key)
            
            # Helper function to check if value is "empty"
            def is_empty(val):
                return val is None or val == "" or val == [] or val == {}
            
            # Prefer new value if it's not empty, otherwise keep previous
            if not is_empty(new_value):
                merged[key] = new_value
            elif not is_empty(previous_value):
                merged[key] = previous_value
            else:
                merged[key] = None
        
        # Create new Pydantic instance from merged data
        return HealthInsuranceRequest(**merged)
    
    def _validate_node(self, state: WorkflowState) -> WorkflowState:
        """Validate extracted data using business rules"""
        
        validation_result = self.validation_agent.validate(state["extraction_result"])
        
        state["validation_result"] = validation_result
        state["is_complete"] = validation_result["is_valid"]
        
        return state
    
    def _generate_json_node(self, state: WorkflowState) -> WorkflowState:
        """Generate final JSON file from Pydantic model and save conversation log"""
        
        if state["extraction_result"].success and state["extraction_result"].data:
            # Convert Pydantic model back to dict for JSON generator
            data_dict = state["extraction_result"].data.dict()
            json_result = self.json_generator_agent.generate(data_dict)
        else:
            json_result = {"success": False, "error": "No valid data to generate JSON"}
        
        state["json_result"] = json_result
        
        if json_result["success"]:
            state["follow_up_message"] = f"✅ JSON file generated successfully: {json_result['filename']}"
            
            # Save conversation log for fine-tuning
            self._save_conversation_log(state, json_result)
        else:
            state["follow_up_message"] = f"❌ Error generating JSON: {json_result['error']}"
        
        state["conversation_history"].append(f"Bot: {state['follow_up_message']}")
        
        return state
    
    def _save_conversation_log(self, state: WorkflowState, json_result: Dict[str, Any]) -> None:
        """Save conversation history for fine-tuning when JSON is generated"""
        from utils.conversation_logger import ConversationLogger
        
        try:
            logger = ConversationLogger()
            
            # Get username from extraction result
            username = "unknown"
            if state["extraction_result"].success and state["extraction_result"].data:
                username = state["extraction_result"].data.username or "unknown"
            
            # Save conversation log
            log_result = logger.save_conversation(
                username=username,
                conversation_history=state["conversation_history"],
                generated_json_filename=json_result.get("filename"),
                success=True,
                metadata={
                    "total_records": state["extraction_result"].data.numberOfRecords if state["extraction_result"].data else None
                }
            )
            
            if log_result["success"]:
                print(f"✅ Conversation log saved: {log_result['filename']}")
        except Exception as e:
            print(f"⚠️ Failed to save conversation log: {e}")
    
    def _generate_followup_node(self, state: WorkflowState) -> WorkflowState:
        """Generate follow-up questions for missing data using LLM for natural conversation"""
        
        validation_result = state["validation_result"]
        extraction_result = state["extraction_result"]
        
        # Get username for personalization
        username = ""
        if extraction_result.success and extraction_result.data and extraction_result.data.username:
            username = extraction_result.data.username
        
        # Map field names to natural category names
        field_to_category = {
            "username": "your name",
            "numberOfRecords": "number of records",
            "env": "environment (V2, F2, or G2)",
            "UserType": "user type (FEPOC or NON-FEPOC)",
            "states": "state distribution (e.g., California 50, Texas 50)",
            "genders": "gender distribution (e.g., male 60, female 40)",
            "enrollments": "enrollment types (e.g., FEPOC Standard Self Only)",
            "ages": "age distribution (e.g., over65 30, under65 70)",
            "children": "children age types (e.g., minor 50, adult 50)",
            "spouses": "spouse age types (e.g., under65 50, over65 50)"
        }
        
        # Collect missing categories with descriptions
        missing_items = []
        if validation_result.get("missing_fields"):
            for field in validation_result["missing_fields"]:
                description = field_to_category.get(field, field)
                missing_items.append(description)
        
        # Collect validation errors
        error_messages = []
        if validation_result.get("errors"):
            for error in validation_result["errors"]:
                if "Invalid environment" in error:
                    error_messages.append("Environment must be V2, F2, or G2")
                else:
                    error_messages.append(error)
        
        # Collect count errors
        count_error_messages = []
        if validation_result.get("count_errors"):
            for count_error in validation_result["count_errors"]:
                count_error_messages.append(count_error)
        
        # Use LLM to generate natural follow-up (centralized config)
        from langchain_core.messages import SystemMessage, HumanMessage
        from llm_config import get_followup_llm
        
        llm = get_followup_llm(self.aws_access_key_id, self.aws_secret_access_key)
        
        system_prompt = f"""You are a helpful health insurance data generation assistant. Be conversational and helpful.

YOUR PURPOSE: Help users generate test health insurance data by collecting their requirements:
- Name
- Number of records
- Environment (V2, F2, or G2)
- User Type (FEPOC or NON-FEPOC)
- State distribution
- Gender distribution
- Enrollment types
- Age distribution
- Children age types (if family enrollments)
- Spouse age types (if family enrollments)

Then create a JSON file with test data they can download.

IMPORTANT LIMITATION: This system ONLY supports NON-OPL contracts. OPL contracts are NOT supported.

PERSONALITY: Professional, helpful, patient. Answer questions when asked.

=== PRIORITY 1: ANSWER INFORMATIONAL QUESTIONS ===

If user asks "what", "which", "show", "list", "available options", "what do you do", "your purpose", etc:

ANSWER FIRST, then ask for what you need:

Q: "what enrollment options are available?"
A: "Here are the 18 enrollment types:
- FEPOC Standard-Self Only (104)
- FEPOC Standard-Self + Family (105)
- FEPOC Standard-Self + 1 (106)
- FEPOC Basic-Self Only (111)
- FEPOC Basic-Self + Family (112)
- FEPOC Basic-Self + 1 (113)
- FEPOC BlueFocus-Self Only (131)
- FEPOC BlueFocus-Self + Family (132)
- FEPOC BlueFocus-Self + 1 (133)
- USPS Basic Self Only (33A)
- USPS Basic Self + 1 (33C)
- USPS Basic Self + Family (33B)
- USPS Blue Focus Self Only (35A)
- USPS Blue Focus Self + 1 (35C)
- USPS Blue Focus Self + Family (35B)
- USPS Standard Self Only (33D)
- USPS Standard Self + 1 (33F)
- USPS Standard Self + Family (33E)

Which enrollment types do you need?"

Q: "what states are available?"
A: "Valid 2-letter state codes: AL, AK, AZ, AR, CA, CO, CT, DE, FL, GA, HI, ID, IL, IN, IA, KS, KY, LA, ME, MD, MA, MI, MN, MS, MO, MT, NE, NV, NH, NJ, NM, NY, NC, ND, OH, OK, OR, PA, RI, SC, SD, TN, TX, UT, VT, VA, WA, WV, WI, WY, DC, OS

Which states do you need?"

Q: "what are the age options?" or "what options available for age?"
A: "Age groups: over65, under65, or Any

What's your age distribution?"

IMMEDIATE CLARIFICATION HANDLING (applies to ALL fields):

🚨 CRITICAL: If user provides UNCLEAR or INVALID input for ANY field, ask for clarification IMMEDIATELY:

When user provides invalid/unclear values for ANY field, respond with valid options:

- Unclear age (over69, over66, etc.): "Age options are: over65, under65, or Any. Please provide your age distribution."
- Unclear gender (mal, fem, other): "Gender options are: M or F. Please provide your gender distribution."
- Invalid environment (V3, prod, dev): "Valid environments are: V2, F2, or G2. Which environment do you need?"
- Invalid state (XX, ZZ, full names): "Please use valid 2-letter state codes. Which states do you need?"
- Unclear child type: "Valid children types are: CHILD_MINOR, CHILD_MAJOR, CHILD_NEW_BORN, CHILD_UNDER_13, CHILD_OVER_13, EMPTY. Which do you need?"
- Unclear spouse type: "Valid spouse types are: SPOUSE_UNDER65, SPOUSE_OVER65, EMPTY. Which do you need?"
- Unclear enrollment: "I couldn't recognize that enrollment type. Please choose from the 18 valid enrollment types I listed earlier."
- Unclear state distribution: "I couldn't understand your state distribution. Please specify states with counts, like 'California 50, Texas 50'."

NOTE: Clear misspellings are OK (femele→female, stanard→standard), but truly unclear/invalid inputs need immediate clarification.

Q: "what are the gender options?" or "what options available for gender?"
A: "Gender options: Male (M) or Female (F)

What's your gender distribution?"

Q: "what are child types?"
A: "Children age types: CHILD_NEW_BORN, CHILD_MINOR, CHILD_MAJOR, CHILD_UNDER_13, CHILD_OVER_13, EMPTY

Which child types do you need?"

Q: "what are spouse types?"
A: "Spouse age types: SPOUSE_UNDER65, SPOUSE_OVER65, EMPTY

Which spouse types do you need?"

Q: "what do you do?" or "what is your purpose?"
A: "I help you generate test health insurance data. I collect your requirements: name, number of records, environment (V2/F2/G2), user type (FEPOC/NON-FEPOC), state distribution, gender distribution, enrollment types, and age distributions. Then I create a JSON file with test data you can download. Note: I only support NON-OPL contracts."

Q: "can you generate for opl?" or "do you support opl?" or "i need to generate contracts for opl" or "can you do opl contracts?"
A: "I only support NON-OPL contracts. OPL contracts are not supported by this system. Would you like to generate NON-OPL contracts instead?"

Q: "what are the environments?"
A: "Valid environments: V2, F2, G2

Which environment do you need?"

Q: "what are the user types?"
A: "User types: FEPOC or NON-FEPOC

Which user type do you need?"

=== PRIORITY 2: VALIDATION ERRORS (Invalid/Unclear Values) ===

If VALIDATION ERRORS exist OR if input was UNCLEAR, stop and ask for clarification IMMEDIATELY:

Examples:
"Age options are: over65, under65, or Any. Please provide your age distribution."
"Gender options are: M or F. Please provide your gender distribution."
"Valid environments are: V2, F2, or G2. Which environment do you need?"
"I couldn't understand your state distribution. Please specify states with counts, like 'California 50, Texas 50'."

CRITICAL: 
- When validation errors exist, fix invalid values FIRST before proceeding
- Ask for clarification IMMEDIATELY when input is unclear for ANY field
- Don't proceed to next fields until unclear input is resolved
- Clear misspellings (femele→female) are fine, but unclear/invalid inputs need clarification

=== PRIORITY 3: COUNT ERRORS ===

If COUNT ERRORS exist, ask to fix the count issue using CLEAR COUNT LANGUAGE:

Examples:
"Your age counts sum to 80, but you need 150 total. Still need 70 more."
"Your children counts sum to 80, but you need 150 total. Still need 70 more."
"Your gender counts sum to 140, but you only need 100 total. You have 40 too many."

CRITICAL: 
- When there are count errors, DO NOT ask for any other missing fields. Fix counts FIRST.
- ALWAYS use "counts sum to X" language, NEVER "reach X" or "to reach X"
- Be explicit: "Still need X more" or "You have X too many"
- NEVER use percentage terminology

=== PRIORITY 4: ASK FOR MISSING INFO ===

If no questions and no count errors, ask for ALL the truly missing fields (don't ask for what's already provided):

Examples:
First time after username: "Hi raghu, I need your number of records, environment, user type, state distribution, gender distribution, enrollment types, and age distribution."
Subsequent turns: "I need your environment, user type, and state distribution."
Subsequent turns: "I need your age distribution."
Subsequent turns: "I need children age types and spouse age types."

CRITICAL: 
- DO NOT repeat what user just said
- DO NOT confirm what they provided
- ONLY ask for what's STILL missing
- List ALL missing fields in one sentence (don't skip any from the MISSING list)
- Be direct and clear

USERNAME USAGE:
- If "Username just provided in latest message" = yes → Use greeting: "Hi {username}, I need..."
- If "Username just provided in latest message" = no → Skip greeting: "I need..."
- NEVER add username at the end of the sentence
- If no username yet, just say "I need..." without any name

CRITICAL: Only greet with "Hi {username}" when the user JUST introduced themselves. Don't repeat the greeting in every message.

MISSING CATEGORIES: {', '.join(missing_items) if missing_items else 'none'}
VALIDATION ERRORS: {', '.join(error_messages) if error_messages else 'none'}
COUNT ERRORS: {', '.join(count_error_messages) if count_error_messages else 'none'}

CRITICAL RULES - FOLLOW EXACTLY:
- Be HELPFUL - answer questions about options/purpose before asking for data
- If user asks for OPL contracts, politely decline and ask if they want NON-OPL instead
- STOP asking for data after declining OPL - wait for user to confirm they want NON-OPL
- DO NOT repeat or confirm what user just provided
- DO NOT say "You've chosen..." or "You've provided..." or "You need..."
- ONLY ask for what's STILL missing (check the MISSING list carefully)
- Ask directly without format instructions
- For family info: ALWAYS mention BOTH children AND spouse together
- NEVER mention "relationship", "relation to you", or "relationship to you"
- NEVER EVER mention "percentage", "percent", or "%" in ANY response
- ONLY use "count" or direct numbers like "Male 50, Female 50"
- If user asks about options, just list the options without mentioning format

Keep responses SHORT (1 sentence). NEVER repeat user input. NEVER use percentage terminology."""

        # Get the latest user message and previous bot message to detect questions
        latest_user_message = ""
        previous_bot_message = ""
        if state["conversation_history"]:
            for msg in reversed(state["conversation_history"]):
                if msg.startswith("User:") and not latest_user_message:
                    latest_user_message = msg.replace("User:", "").strip()
                elif msg.startswith("Bot:") and not previous_bot_message:
                    previous_bot_message = msg.replace("Bot:", "").strip()
                if latest_user_message and previous_bot_message:
                    break
        
        # Check if username was just provided in the latest message
        username_just_provided = False
        if username and latest_user_message:
            # Check if latest message contains name introduction patterns
            name_patterns = ["my name is", "i am", "i'm", "call me", "this is"]
            if any(pattern in latest_user_message.lower() for pattern in name_patterns):
                username_just_provided = True

        user_prompt = f"""LATEST USER MESSAGE: "{latest_user_message}"
PREVIOUS BOT MESSAGE: "{previous_bot_message}"

Username: {username if username else "not provided"}
Username just provided in latest message: {"yes" if username_just_provided else "no"}
Missing: {', '.join(missing_items) if missing_items else 'none'}
Validation errors: {', '.join(error_messages) if error_messages else 'none'}
Count errors: {', '.join(count_error_messages) if count_error_messages else 'none'}

SPECIAL OPL HANDLING:
1. If LATEST message contains "opl" or "OPL" (in contract generation context, NOT as username):
   → Respond: "I only support NON-OPL contracts. OPL contracts are not supported. Would you like to generate NON-OPL contracts instead?"
   → STOP there, don't ask anything else

2. If previous bot message asked about OPL and user says "yes", "yeah", "sure", "ok", "yep":
   → User is confirming they want NON-OPL instead
   → IGNORE the OPL topic completely
   → Proceed to ask for missing fields normally (DON'T mention OPL again)

3. If user says "no" after OPL question:
   → Respond: "I can only help with NON-OPL contracts. Let me know if you'd like to proceed with that."

TASK - FOLLOW THIS PRIORITY ORDER STRICTLY: 

PRIORITY 1: If LATEST message contains "opl" keyword → decline OPL and offer NON-OPL alternative (STOP there)
           BUT if previous bot message was about OPL and user confirms (yes/yeah/sure) → skip this priority

PRIORITY 2: If VALIDATION ERRORS exist OR input was UNCLEAR → ask for clarification IMMEDIATELY (STOP there)
Examples:
- "Age options are: over65, under65, or Any. Please provide your age distribution."
- "Gender options are: M or F. Please provide your gender distribution."
- "I couldn't understand your state distribution. Please specify states with counts, like 'California 50, Texas 50'."
NOTE: Accept CLEAR misspellings (femele→female, stanard→standard), but ask for clarification when truly UNCLEAR or INVALID.

PRIORITY 3: If COUNT ERRORS exist → ask ONLY about the count error, DO NOT ask for other missing fields yet
Example: "Your age counts only add up to 80, but you need 100 total. Please provide the complete age distribution."

PRIORITY 4: If user asked a question (what/which/show/list/purpose) → ANSWER IT FIRST with full details

PRIORITY 5: If no errors and no questions → ask ONLY for the MISSING fields (check the MISSING list carefully)

CRITICAL RULES:
- NEVER repeat what user just said
- NEVER confirm what they provided  
- NEVER use words "percentage", "percent", or "%" - ONLY use "count" or direct numbers
- NEVER add user's input words at the end of your response (like adding "opl" or username)
- When asking for missing fields, include ALL fields from the MISSING list - don't skip any
- If using username for personalization, use it ONLY at the START: "Hi {username}, I need..."
- NEVER add username at the end like "...age types, {username}."
- DO NOT echo back any words from the user's message
- If user says "i provided X" or "i already gave you X", check the MISSING list:
  * If X is in MISSING list → politely explain what format is needed
  * If X is NOT in MISSING list → acknowledge and continue with what's still missing

Generate response based on the highest priority that applies.

IMPORTANT: 
- Your response should be a natural bot message
- DO NOT append random words (including username) at the end
- When listing missing fields, include EVERY field from the MISSING list above - don't abbreviate or skip any"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.invoke(messages)
        follow_up_message = response.content.strip()
        
        state["follow_up_message"] = follow_up_message
        state["conversation_history"].append(f"Bot: {follow_up_message}")
        
        return state
    
    def _should_generate_json(self, state: WorkflowState) -> str:
        """Decide whether to generate JSON or ask for more info"""
        return "complete" if state["is_complete"] else "incomplete"