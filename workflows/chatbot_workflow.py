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


class WorkflowState(TypedDict):
    """State shared across all agents"""
    user_input: str
    extracted_data: Dict[str, Any]
    validation_result: Dict[str, Any]
    json_result: Dict[str, Any]
    conversation_history: List[str]
    is_complete: bool
    follow_up_message: str


class ChatbotWorkflow:
    """Main workflow orchestrating the 3 agents"""
    
    def __init__(self, openai_api_key: str):
        self.api_key = openai_api_key
        self.extraction_agent = ExtractionAgent(openai_api_key)
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
    
    def process_input(self, user_input: str, conversation_history: List[str] = None, accumulated_data: Dict[str, Any] = None) -> Dict[str, Any]:
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
            "extracted_data": accumulated_data or {},
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
        """Extract structured data from user input"""
        
        # Build full conversation context for extraction
        conversation_context = "\n".join(state["conversation_history"]) if state["conversation_history"] else ""
        full_input = f"{conversation_context}\nUser: {state['user_input']}" if conversation_context else state["user_input"]
        
        # Get previously accumulated data
        previous_data = state.get("extracted_data", {})
        
        # Extract new data from conversation
        new_extracted_data = self.extraction_agent.extract(full_input)
        
        # Post-process: Convert empty arrays/dicts to None (LLM sometimes ignores prompt)
        for key, value in new_extracted_data.items():
            if value == [] or value == {}:
                new_extracted_data[key] = None
        
        # Merge: Keep non-null values from new extraction, preserve previous data for null fields
        merged_data = {}
        all_keys = set(list(previous_data.keys()) + list(new_extracted_data.keys()))
        
        for key in all_keys:
            new_value = new_extracted_data.get(key)
            previous_value = previous_data.get(key)
            
            # Helper function to check if value is "empty"
            def is_empty(val):
                return val is None or val == "" or val == [] or val == {}
            
            # Prefer new value if it's not empty, otherwise keep previous
            if not is_empty(new_value):
                merged_data[key] = new_value
            elif not is_empty(previous_value):
                merged_data[key] = previous_value
            else:
                merged_data[key] = None
        
        state["extracted_data"] = merged_data
        state["conversation_history"].append(f"User: {state['user_input']}")
        
        return state
    
    def _validate_node(self, state: WorkflowState) -> WorkflowState:
        """Validate extracted data"""
        
        validation_result = self.validation_agent.validate(state["extracted_data"])
        
        state["validation_result"] = validation_result
        state["is_complete"] = validation_result["is_valid"]
        
        return state
    
    def _generate_json_node(self, state: WorkflowState) -> WorkflowState:
        """Generate final JSON file"""
        
        json_result = self.json_generator_agent.generate(state["extracted_data"])
        
        state["json_result"] = json_result
        
        if json_result["success"]:
            state["follow_up_message"] = f"✅ JSON file generated successfully: {json_result['filename']}"
        else:
            state["follow_up_message"] = f"❌ Error generating JSON: {json_result['error']}"
        
        state["conversation_history"].append(f"Bot: {state['follow_up_message']}")
        
        return state
    
    def _generate_followup_node(self, state: WorkflowState) -> WorkflowState:
        """Generate follow-up questions for missing data using LLM for natural conversation"""
        
        validation_result = state["validation_result"]
        extracted_data = state["extracted_data"]
        
        # Get username for personalization
        username = extracted_data.get("username", "")
        
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
            "children": "child information (if Self+1 or Self+Family)",
            "spouses": "spouse information (if Self+1 or Self+Family)"
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
        
        # Use LLM to generate natural follow-up
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        
        llm = ChatOpenAI(temperature=0.7, model="gpt-4", api_key=self.api_key)
        
        system_prompt = f"""You are a friendly, conversational AI assistant helping users generate health insurance data.

Your task: Generate a natural, conversational follow-up message asking for missing information or correcting count errors.

Guidelines:
- Be warm and friendly
- Use the user's name ({username}) if available
- If there are count errors, explain what's wrong and ask for correction in a natural way
- Ask for missing information in a natural way (not a list format)
- Keep it concise (1-2 sentences max)
- Sound like a real person having a conversation
- Don't use bullet points or formal lists

Examples of good responses:
- "Hey Sarah! I still need a few more details - could you share the state distribution and gender breakdown?"
- "Thanks! I'm still missing some info about the enrollment types and age distribution. Can you provide those?"
- "Almost there! Just need the state and gender information to complete this."
- "Hey! The state counts you gave me only add up to 50, but you need 100 total. Could you provide the remaining 50?"
- "I noticed the gender counts don't add up to your total of 100 records. Can you double-check those numbers?"
"""

        user_prompt = f"""Username: {username if username else "not provided"}
Missing information: {', '.join(missing_items) if missing_items else 'none'}
Validation errors: {', '.join(error_messages) if error_messages else 'none'}
Count errors: {', '.join(count_error_messages) if count_error_messages else 'none'}

Generate a friendly, natural follow-up message asking for the missing information or explaining count errors."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm(messages)
        follow_up_message = response.content.strip()
        
        state["follow_up_message"] = follow_up_message
        state["conversation_history"].append(f"Bot: {follow_up_message}")
        
        return state
    
    def _should_generate_json(self, state: WorkflowState) -> str:
        """Decide whether to generate JSON or ask for more info"""
        return "complete" if state["is_complete"] else "incomplete"