"""
Validation Agent - Check data completeness and business logic
===========================================================

Simple agent with one goal: Validate business rules for Pydantic-validated data.
Schema validation happens in ExtractionAgent. This focuses on business logic only.
"""

from typing import Dict, Any, List, Tuple, Union
from config import (
    ALL_STATES, ALL_ENROLLMENT_CODES, GENDER_TYPES, 
    MEMBER_AGE_TYPES, ALL_CHILD_TYPES, SPOUSE_AGE_OPTIONS,
    ENV_TYPES, USER_TYPES, ENROLLMENT_MAP
)
from models.health_insurance_models import HealthInsuranceRequest, ExtractionResult


class ValidationAgent:
    """Validate business rules for Pydantic-validated health insurance data"""
    
    def validate(self, extraction_result: ExtractionResult) -> Dict[str, Any]:
        """
        Validate business rules for extracted data
        
        Args:
            extraction_result: Result from ExtractionAgent with Pydantic validation
            
        Returns:
            Validation result with business rule errors and missing fields
        """
        
        validation_result = {
            "is_valid": False,
            "errors": [],
            "missing_fields": [],
            "count_errors": [],
            "suggestions": []
        }
        
        # Check if extraction was successful
        if not extraction_result.success or extraction_result.data is None:
            validation_result["errors"].append(f"Extraction failed: {extraction_result.error}")
            return validation_result
        
        data = extraction_result.data
        
        # Convert Pydantic model to dict for existing logic compatibility
        data_dict = self._pydantic_to_dict(data)
        
        # Check required fields
        missing_fields = self._check_required_fields(data_dict)
        validation_result["missing_fields"] = missing_fields
        
        # Validate field values (business logic)
        field_errors = self._validate_field_values(data_dict)
        validation_result["errors"].extend(field_errors)
        
        # Check count consistency
        count_errors = self._validate_counts(data_dict)
        validation_result["count_errors"] = count_errors
        
        # Check family logic
        family_errors = self._validate_family_logic(data_dict)
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
    
    def _pydantic_to_dict(self, data: HealthInsuranceRequest) -> Dict[str, Any]:
        """Convert Pydantic model to dict format for existing validation logic"""
        result = {}
        
        # Basic fields
        result["username"] = data.username
        result["numberOfRecords"] = data.numberOfRecords  
        result["env"] = data.env
        result["UserType"] = data.UserType
        result["confidence"] = data.confidence
        
        # Distribution fields - convert Pydantic models to dicts
        result["states"] = [{"state": s.state, "count": s.count} for s in data.states] if data.states else None
        result["genders"] = [{"gender": g.gender, "count": g.count} for g in data.genders] if data.genders else None
        result["enrollments"] = [{"name": e.name, "count": e.count} for e in data.enrollments] if data.enrollments else None
        result["ages"] = [{"age": a.age, "count": a.count} for a in data.ages] if data.ages else None
        result["children"] = [{"type": c.type, "count": c.count} for c in data.children] if data.children else None
        result["spouses"] = [{"type": s.type, "count": s.count} for s in data.spouses] if data.spouses else None
        
        return result
    
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
        
        # CRITICAL: Only check for family fields if ALL count validations pass
        # This prevents asking for spouse/children when there are incomplete counts
        count_errors = self._validate_counts(data)
        if len(count_errors) > 0:
            # If there are count errors, don't ask for family fields yet
            # The user needs to complete the basic distributions first
            return missing
        
        # Only check for family fields if counts are complete and valid
        if data.get("enrollments"):
            has_family_enrollment = False
            has_self_plus_one = False
            
            for enrollment in data["enrollments"]:
                enrollment_name = enrollment.get("name", "")
                if "Self+Family" in enrollment_name or "Self + Family" in enrollment_name:
                    has_family_enrollment = True
                if "Self+1" in enrollment_name or "Self + 1" in enrollment_name:
                    has_self_plus_one = True
            
            # If ANY family enrollment exists (Self+1 OR Self+Family)
            if has_family_enrollment or has_self_plus_one:
                # Children are MANDATORY for family enrollments
                child_value = data.get("children")
                child_missing = child_value is None or child_value == "" or child_value == [] or child_value == {}
                
                if child_missing:
                    missing.append("children")
                
                # Spouses: All-or-nothing logic
                spouse_value = data.get("spouses")
                spouse_missing = spouse_value is None or spouse_value == "" or spouse_value == [] or spouse_value == {}
                
                # If spouses are provided but incomplete, this will be caught by count validation
                # If spouses are not provided at all, that's OK - we'll auto-fill in JSON generation
                # We only add "spouses" to missing if we want to ask the user for it
                # Since spouses are optional, we don't add them to missing fields
        
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
        
        # Check children counts (only when family enrollments exist)
        if data.get("children"):
            # First check if we have any family enrollments
            has_family_enrollments = False
            if data.get("enrollments"):
                for enrollment in data["enrollments"]:
                    enrollment_name = enrollment.get("name", "")
                    if "Self+Family" in enrollment_name or "Self + Family" in enrollment_name or "Self+1" in enrollment_name or "Self + 1" in enrollment_name:
                        has_family_enrollments = True
                        break
            
            # Only validate children counts if family enrollments exist
            if has_family_enrollments:
                children_sum = sum(int(c.get("count", 0)) for c in data["children"])
                if children_sum != total_records:
                    deficit = total_records - children_sum
                    count_errors.append(f"Children counts sum to {children_sum}, need {total_records}. Deficit: {deficit}")
        
        # Check spouse counts (only when family enrollments exist)
        if data.get("spouses"):
            # First check if we have any family enrollments
            has_family_enrollments = False
            if data.get("enrollments"):
                for enrollment in data["enrollments"]:
                    enrollment_name = enrollment.get("name", "")
                    if "Self+Family" in enrollment_name or "Self + Family" in enrollment_name or "Self+1" in enrollment_name or "Self + 1" in enrollment_name:
                        has_family_enrollments = True
                        break
            
            # Only validate spouse counts if family enrollments exist
            if has_family_enrollments:
                spouse_sum = sum(int(s.get("count", 0)) for s in data["spouses"])
                if spouse_sum != total_records:
                    deficit = total_records - spouse_sum
                    count_errors.append(f"Spouse counts sum to {spouse_sum}, need {total_records}. Deficit: {deficit}")
        
        return count_errors
    
    def _validate_family_logic(self, data: Dict[str, Any]) -> List[str]:
        """Validate family enrollment business rules"""
        errors = []
        
        if not data.get("enrollments"):
            return errors
        
        # Check if any enrollment requires family details
        has_family_enrollment = False
        for enrollment in data["enrollments"]:
            enrollment_name = enrollment.get("name", "")
            if "Self + 1" in enrollment_name or "Self + Family" in enrollment_name or "Self+1" in enrollment_name or "Self+Family" in enrollment_name:
                has_family_enrollment = True
                break
        
        if has_family_enrollment:
            # For family enrollments: Children are MANDATORY
            if not data.get("children"):
                errors.append("Children information is required for Self+1 or Self+Family enrollments")
            
            # For family enrollments: Spouses follow all-or-nothing rule
            # If spouses are provided, they must sum to numberOfRecords (handled by count validation)
            # If not provided, that's fine - will be auto-filled to EMPTY
            # No additional validation needed here for spouses
        
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