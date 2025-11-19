"""
Health Insurance Data Models
==========================

Pydantic models for schema validation and structured output parsing.
Goal: Validate LLM output structure before business logic validation.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum


class StateDistribution(BaseModel):
    """State distribution with 2-letter state code"""
    state: str = Field(..., pattern=r"^[A-Z]{2}$", description="2-letter state code")
    count: int = Field(..., gt=0, description="Number of records for this state")


class GenderDistribution(BaseModel):
    """Gender distribution"""
    gender: Literal["M", "F", "EMPTY"] = Field(..., description="Gender type")
    count: int = Field(..., gt=0, description="Number of records for this gender")


class EnrollmentDistribution(BaseModel):
    """Enrollment type distribution"""
    name: str = Field(..., min_length=1, description="Enrollment type name")
    count: int = Field(..., gt=0, description="Number of records for this enrollment")


class AgeDistribution(BaseModel):
    """Age group distribution"""
    age: Literal["over65", "under65", "Any"] = Field(..., description="Age group")
    count: int = Field(..., gt=0, description="Number of records for this age group")


class ChildDistribution(BaseModel):
    """Child/dependent distribution"""
    type: Literal["CHILD_MINOR", "CHILD_MAJOR", "CHILD_NEW_BORN", "CHILD_UNDER_13", "CHILD_OVER_13", "EMPTY"] = Field(
        ..., description="Child type"
    )
    count: int = Field(..., gt=0, description="Number of children")


class SpouseDistribution(BaseModel):
    """Spouse distribution"""
    type: Literal["SPOUSE_UNDER65", "SPOUSE_OVER65", "EMPTY"] = Field(
        ..., description="Spouse type"
    )
    count: int = Field(..., gt=0, description="Number of spouses")


class HealthInsuranceRequest(BaseModel):
    """Complete health insurance data request model"""
    
    # Required fields
    username: Optional[str] = Field(
        None, 
        pattern=r"^[a-zA-Z0-9]+$", 
        description="Alphanumeric username only"
    )
    numberOfRecords: Optional[int] = Field(
        None, 
        ge=1, 
        le=10000, 
        description="Total number of records to generate"
    )
    env: Optional[Literal["V2", "F2", "G2"]] = Field(
        None, 
        description="Environment type - only V2, F2, or G2"
    )
    UserType: Optional[Literal["FEPOC", "NON-FEPOC"]] = Field(
        None, 
        description="User type - FEPOC or NON-FEPOC only"
    )
    
    # Distribution fields
    states: Optional[List[StateDistribution]] = Field(
        None, 
        description="State distribution with counts"
    )
    genders: Optional[List[GenderDistribution]] = Field(
        None, 
        description="Gender distribution with counts"
    )
    enrollments: Optional[List[EnrollmentDistribution]] = Field(
        None, 
        description="Enrollment type distribution with counts"
    )
    ages: Optional[List[AgeDistribution]] = Field(
        None, 
        description="Age distribution with counts"
    )
    
    # Optional family fields
    children: Optional[List[ChildDistribution]] = Field(
        None, 
        description="Child/dependent distribution"
    )
    spouses: Optional[List[SpouseDistribution]] = Field(
        None, 
        description="Spouse distribution"
    )
    
    # Metadata
    confidence: Optional[Literal["high", "medium", "low"]] = Field(
        None, 
        description="Extraction confidence level"
    )

    class Config:
        """Pydantic configuration"""
        # Allow extra fields for backward compatibility
        extra = "allow"
        # Use enum values
        use_enum_values = True
        # Validate assignment
        validate_assignment = True


class ExtractionResult(BaseModel):
    """Wrapper for extraction results with error handling"""
    
    success: bool = Field(..., description="Whether extraction succeeded")
    data: Optional[HealthInsuranceRequest] = Field(None, description="Extracted data if successful")
    error: Optional[str] = Field(None, description="Error message if failed")
    raw_response: Optional[str] = Field(None, description="Raw LLM response for debugging")
    
    class Config:
        extra = "allow"