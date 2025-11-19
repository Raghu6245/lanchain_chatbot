"""
JSON Generator Agent - Create final JSON files
============================================

Simple agent with one goal: Convert validated data to JSON matching exact template.
"""

import json
from datetime import datetime
from typing import Dict, Any
import os
from config import ENROLLMENT_MAP


class JsonGeneratorAgent:
    """Generate JSON files from validated data"""
    
    def __init__(self, output_dir: str = "generated_files"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate JSON file from validated data
        
        Args:
            validated_data: Data that passed validation
            
        Returns:
            Result with file path and status
        """
        
        # Double-check required fields before generating
        required_fields = ["username", "numberOfRecords", "env", "UserType", "states", "genders", "enrollments", "ages"]
        missing = []
        for field in required_fields:
            value = validated_data.get(field)
            if value is None or value == "" or value == [] or value == {}:
                missing.append(field)
        
        if missing:
            return {
                "success": False,
                "error": f"Cannot generate JSON - missing required fields: {', '.join(missing)}"
            }
        
        # Convert to JSON template format
        json_data = self._convert_to_template_format(validated_data)
        
        # Generate filename
        username = validated_data.get("username", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{username}_data_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        # Save file
        try:
            with open(filepath, 'w') as f:
                json.dump(json_data, f, indent=2)
            
            return {
                "success": True,
                "filepath": filepath,
                "filename": filename,
                "data": json_data
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _convert_to_template_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert validated data to exact JSON template format"""
        
        # Base structure matching template
        json_output = {
            "userId": str(data.get("username", "")),
            "env": data.get("env", ""),
            "UserType": data.get("UserType", ""),
            "numberOfRecords": str(data.get("numberOfRecords", "")),
            "statePercentage": self._format_state_percentage(data.get("states", [])),
            "subscriberGender": self._format_subscriber_gender(data.get("genders", [])),
            "enrollmentCode": self._format_enrollment_code(data.get("enrollments", [])),
            "memberAge": self._format_member_age(data.get("ages", [])),
            "dependentAge": self._format_dependent_age(data.get("children", []), data.get("enrollments", []), data.get("numberOfRecords", 0)),
            "spouseAge": self._format_spouse_age(data.get("spouses", []), data.get("enrollments", []), data.get("numberOfRecords", 0)),
            "optionalEntries": []
        }
        
        return json_output
    
    def _format_state_percentage(self, states: list) -> list:
        """Format state data to template structure"""
        if not states:
            return []
        
        return [
            {
                "state": state["state"],
                "count": str(state["count"])
            }
            for state in states
        ]
    
    def _format_subscriber_gender(self, genders: list) -> list:
        """Format gender data to template structure"""
        if not genders:
            return []
        
        return [
            {
                "gender": gender["gender"],
                "count": str(gender["count"])
            }
            for gender in genders
        ]
    
    def _format_enrollment_code(self, enrollments: list) -> list:
        """Format enrollment data to template structure with codes"""
        if not enrollments:
            return []
        
        result = []
        for enrollment in enrollments:
            enrollment_name = enrollment["name"]
            enrollment_code = ENROLLMENT_MAP.get(enrollment_name, "UNKNOWN")
            
            result.append({
                "enrollmentCode": enrollment_code,
                "count": str(enrollment["count"])
            })
        
        return result
    
    def _format_member_age(self, ages: list) -> list:
        """Format age data to template structure"""
        if not ages:
            return []
        
        return [
            {
                "age": age["age"],
                "type": "bracket" if age["age"] in ["over65", "under65"] else "age",
                "count": str(age["count"])
            }
            for age in ages
        ]
    
    def _format_dependent_age(self, children: list, enrollments: list, numberOfRecords: int) -> list:
        """Format dependent age based on enrollment type"""
        
        # Check if enrollment is Self Only
        is_self_only = self._is_self_only_enrollment(enrollments)
        
        if is_self_only:
            # For Self Only, all dependents should be EMPTY
            return [
                {
                    "childType": "EMPTY",
                    "count": str(numberOfRecords)
                }
            ]
        
        # For family enrollments, use provided children data or auto-fill to EMPTY
        if not children:
            return [
                {
                    "childType": "EMPTY", 
                    "count": str(numberOfRecords)
                }
            ]
        
        return [
            {
                "childType": child["type"],
                "count": str(child["count"])
            }
            for child in children
        ]
    
    def _format_spouse_age(self, spouses: list, enrollments: list, numberOfRecords: int) -> list:
        """Format spouse age based on enrollment type"""
        
        # Check if enrollment is Self Only
        is_self_only = self._is_self_only_enrollment(enrollments)
        
        if is_self_only:
            # For Self Only, all spouses should be EMPTY
            return [
                {
                    "spouseType": "EMPTY",
                    "count": str(numberOfRecords)
                }
            ]
        
        # For family enrollments, use provided spouse data or default to EMPTY
        if not spouses:
            return [
                {
                    "spouseType": "EMPTY",
                    "count": str(numberOfRecords)
                }
            ]
        
        return [
            {
                "spouseType": spouse["type"],
                "count": str(spouse["count"])
            }
            for spouse in spouses
        ]
    
    def _is_self_only_enrollment(self, enrollments: list) -> bool:
        """Check if all enrollments are Self Only type"""
        if not enrollments:
            return False
        
        for enrollment in enrollments:
            enrollment_name = enrollment.get("name", "")
            if "Self Only" not in enrollment_name:
                return False
        
        return True
    
    def _get_total_records_from_enrollments(self, enrollments: list) -> int:
        """Get total records from enrollment counts"""
        if not enrollments:
            return 0
        
        return sum(int(enrollment.get("count", 0)) for enrollment in enrollments)