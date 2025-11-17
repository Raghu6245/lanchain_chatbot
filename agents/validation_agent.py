"""
Validation Agent - Check data completeness and count accuracy
===========================================================

Simple agent with one goal: Validate extracted data is complete and counts sum correctly.
"""

from typing import Dict, Any, List, Tuple
from config import (
    ALL_STATES, ALL_ENROLLMENT_CODES, GENDER_TYPES, 
    MEMBER_AGE_TYPES, ALL_CHILD_TYPES, SPOUSE_AGE_OPTIONS,
    ENV_TYPES, USER_TYPES, ENROLLMENT_MAP
)


class ValidationAgent:
    """Validate extracted data for completeness and accuracy"""
    
    def validate(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted data
        
        Args:
            extracted_data: Data from extraction agent
            
        Returns:
            Validation result with errors and missing fields
        """
        
        validation_result = {
            "is_valid": False,
            "errors": [],
            "missing_fields": [],
            "count_errors": [],
            "suggestions": []
        }
        
        # Check required fields
        missing_fields = self._check_required_fields(extracted_data)
        validation_result["missing_fields"] = missing_fields
        
        # Validate field values
        field_errors = self._validate_field_values(extracted_data)
        validation_result["errors"].extend(field_errors)
        
        # Check count consistency
        count_errors = self._validate_counts(extracted_data)
        validation_result["count_errors"] = count_errors
        
        # Check family logic
        family_errors = self._validate_family_logic(extracted_data)
        validation_result["errors"].extend(family_errors)
        
        # Generate suggestions for missing data
        suggestions = self._generate_suggestions(missing_fields, count_errors)
        validation_result["suggestions"] = suggestions
        
        # Overall validation status
        validation_result["is_valid"] = (
            len(missing_fields) == 0 and 
            len(validation_result["errors"]) == 0 and 
            len(count_errors) == 0
        )
        
        return validation_result
    
    def _check_required_fields(self, data: Dict[str, Any]) -> List[str]:
        """Check which required fields are missing"""
        # Basic required fields
        required_fields = [
            "username", "numberOfRecords", "env", "UserType",
            "states", "genders", "enrollments", "ages"
        ]
        
        missing = []
        for field in required_fields:
            value = data.get(field)
            # Check if field is missing, None, empty string, or empty list/dict
            if value is None or value == "" or value == [] or value == {}:
                missing.append(field)
        
        # Conditionally check for children and spouses based on enrollment type
        if data.get("enrollments"):
            has_family_enrollment = False
            has_self_plus_one = False
            
            for enrollment in data["enrollments"]:
                enrollment_name = enrollment.get("name", "")
                if "Self+Family" in enrollment_name or "Self + Family" in enrollment_name:
                    has_family_enrollment = True
                if "Self+1" in enrollment_name or "Self + 1" in enrollment_name:
                    has_self_plus_one = True
            
            # For Self+1: need spouse OR children (at least one)
            if has_self_plus_one:
                spouse_value = data.get("spouses")
                child_value = data.get("children")
                spouse_missing = spouse_value is None or spouse_value == "" or spouse_value == [] or spouse_value == {}
                child_missing = child_value is None or child_value == "" or child_value == [] or child_value == {}
                
                # If both are missing, ask for spouse (since it's more common for Self+1)
                if spouse_missing and child_missing:
                    missing.append("spouses")
            
            # For Self+Family: need both spouse AND children
            if has_family_enrollment:
                spouse_value = data.get("spouses")
                child_value = data.get("children")
                
                if spouse_value is None or spouse_value == "" or spouse_value == [] or spouse_value == {}:
                    if "spouses" not in missing:
                        missing.append("spouses")
                
                if child_value is None or child_value == "" or child_value == [] or child_value == {}:
                    if "children" not in missing:
                        missing.append("children")
        
        return missing
    
    def _validate_field_values(self, data: Dict[str, Any]) -> List[str]:
        """Validate field values against configuration"""
        errors = []
        
        # Validate environment
        if data.get("env") and data["env"] not in ENV_TYPES:
            errors.append(f"Invalid environment: {data['env']}. Must be: {ENV_TYPES}")
        
        # Validate user type
        if data.get("UserType") and data["UserType"] not in USER_TYPES:
            errors.append(f"Invalid UserType: {data['UserType']}. Must be: {USER_TYPES}")
        
        # Validate states
        if data.get("states"):
            for state_entry in data["states"]:
                if state_entry["state"] not in ALL_STATES:
                    errors.append(f"Invalid state: {state_entry['state']}")
        
        # Validate genders
        if data.get("genders"):
            for gender_entry in data["genders"]:
                if gender_entry["gender"] not in GENDER_TYPES:
                    errors.append(f"Invalid gender: {gender_entry['gender']}")
        
        return errors
    
    def _validate_counts(self, data: Dict[str, Any]) -> List[str]:
        """Validate that all counts sum to numberOfRecords"""
        if not data.get("numberOfRecords"):
            return ["numberOfRecords is required for count validation"]
        
        try:
            total_records = int(data["numberOfRecords"])
        except (ValueError, TypeError):
            return ["numberOfRecords must be a valid integer"]
        
        count_errors = []
        
        # Check state counts
        if data.get("states"):
            state_sum = sum(int(s.get("count", 0)) for s in data["states"])
            if state_sum != total_records:
                deficit = total_records - state_sum
                count_errors.append(f"State counts sum to {state_sum}, need {total_records}. Deficit: {deficit}")
        
        # Check gender counts
        if data.get("genders"):
            gender_sum = sum(int(g.get("count", 0)) for g in data["genders"])
            if gender_sum != total_records:
                deficit = total_records - gender_sum
                count_errors.append(f"Gender counts sum to {gender_sum}, need {total_records}. Deficit: {deficit}")
        
        # Check enrollment counts
        if data.get("enrollments"):
            enrollment_sum = sum(int(e.get("count", 0)) for e in data["enrollments"])
            if enrollment_sum != total_records:
                deficit = total_records - enrollment_sum
                count_errors.append(f"Enrollment counts sum to {enrollment_sum}, need {total_records}. Deficit: {deficit}")
        
        # Check age counts
        if data.get("ages"):
            age_sum = sum(int(a.get("count", 0)) for a in data["ages"])
            if age_sum != total_records:
                deficit = total_records - age_sum
                count_errors.append(f"Age counts sum to {age_sum}, need {total_records}. Deficit: {deficit}")
        
        return count_errors
    
    def _validate_family_logic(self, data: Dict[str, Any]) -> List[str]:
        """Validate family details based on enrollment type"""
        errors = []
        
        if not data.get("enrollments"):
            return errors
        
        # Check if any enrollment requires family details
        has_family_enrollment = False
        for enrollment in data["enrollments"]:
            enrollment_name = enrollment.get("name", "")
            if "Self + 1" in enrollment_name or "Self + Family" in enrollment_name:
                has_family_enrollment = True
                break
        
        if has_family_enrollment:
            # Family enrollments require dependent age info
            if not data.get("children"):
                errors.append("Family enrollment types require child/dependent information")
        else:
            # Self Only enrollments should have EMPTY dependents
            # This will be handled in JSON generation
            pass
        
        return errors
    
    def _generate_suggestions(self, missing_fields: List[str], count_errors: List[str]) -> List[str]:
        """Generate helpful suggestions for fixing issues"""
        suggestions = []
        
        for field in missing_fields:
            if field == "username":
                suggestions.append("Please provide a username (alphanumeric only)")
            elif field == "numberOfRecords":
                suggestions.append("Please specify total number of records (1-10000)")
            elif field == "env":
                suggestions.append(f"Please specify environment: {ENV_TYPES}")
            elif field == "UserType":
                suggestions.append(f"Please specify user type: {USER_TYPES}")
            elif field == "states":
                suggestions.append("Please specify state distribution with counts")
            elif field == "genders":
                suggestions.append("Please specify gender distribution with counts")
            elif field == "enrollments":
                suggestions.append("Please specify enrollment types with counts")
            elif field == "ages":
                suggestions.append("Please specify age distribution with counts")
        
        for count_error in count_errors:
            suggestions.append(f"Count issue: {count_error}")
        
        return suggestions