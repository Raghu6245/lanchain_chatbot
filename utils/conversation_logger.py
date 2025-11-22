"""
Conversation Logger - Save chat history for fine-tuning
====================================================

Saves complete conversation history in JSON format for each session.
Used for future model fine-tuning and analysis.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any


class ConversationLogger:
    """Log conversations in format suitable for LLM fine-tuning"""
    
    def __init__(self, output_dir: str = "conversation_logs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def save_conversation(
        self,
        username: str,
        conversation_history: List[str],
        generated_json_filename: str = None,
        success: bool = True,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Save complete conversation history to JSON file
        
        Args:
            username: User's name from the session
            conversation_history: List of "User: ..." and "Bot: ..." messages
            generated_json_filename: Name of the generated JSON data file
            success: Whether the session completed successfully
            metadata: Additional metadata about the session
            
        Returns:
            Dict with save status and filename
        """
        
        try:
            # Generate timestamp and filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{username}_conversation_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            # Parse conversation into structured format
            conversation = self._parse_conversation(conversation_history)
            
            # Calculate metrics
            total_turns = len([msg for msg in conversation if msg["role"] == "user"])
            
            # Build conversation log
            log_data = {
                "session_id": f"{username}_{timestamp}",
                "username": username,
                "timestamp": datetime.now().isoformat(),
                "generated_json_file": generated_json_filename,
                "success": success,
                "conversation": conversation,
                "metadata": {
                    "total_turns": total_turns,
                    "total_messages": len(conversation),
                    "model": "llama3.3-70b",
                    "extraction_success": success,
                    **(metadata or {})
                }
            }
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            
            return {
                "success": True,
                "filename": filename,
                "filepath": filepath,
                "message": f"Conversation log saved: {filename}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to save conversation log: {e}"
            }
    
    def _parse_conversation(self, conversation_history: List[str]) -> List[Dict[str, str]]:
        """
        Parse conversation history into fine-tuning format
        
        Args:
            conversation_history: List of "User: ..." and "Bot: ..." strings
            
        Returns:
            List of dicts with role and content
        """
        
        parsed = []
        
        for message in conversation_history:
            if message.startswith("User: "):
                parsed.append({
                    "role": "user",
                    "content": message[6:].strip(),  # Remove "User: " prefix
                    "timestamp": datetime.now().isoformat()
                })
            elif message.startswith("Bot: "):
                parsed.append({
                    "role": "assistant",
                    "content": message[5:].strip(),  # Remove "Bot: " prefix
                    "timestamp": datetime.now().isoformat()
                })
        
        return parsed
    
   