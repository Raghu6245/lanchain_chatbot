"""
Configuration and Constants for BERT Chatbot
===========================================

Centralized configuration file containing all mappings, constants,
and default values used across the chatbot application.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# AWS Bedrock Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.meta.llama3-3-70b-instruct-v1:0")

# State mappings for natural language processing
STATE_MAPPINGS = {
    # Full state names to abbreviations
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "washington dc": "DC", "district of columbia": "DC",
    # Common abbreviations
    "ca": "CA", "ny": "NY", "tx": "TX", "fl": "FL", "va": "VA", "ga": "GA",
    "pa": "PA", "oh": "OH", "il": "IL", "mi": "MI", "nc": "NC", "nj": "NJ",
    # Overseas
    "overseas": "OS"
}

# Enrollment mappings
ENROLLMENT_MAP = {
    "FEPOC Standard-Self Only": "104",
    "FEPOC Standard-Self + Family": "105",
    "FEPOC Standard-Self + 1": "106",
    "FEPOC Basic-Self Only": "111",
    "FEPOC Basic-Self + Family": "112",
    "FEPOC Basic-Self + 1": "113",
    "FEPOC BlueFocus-Self Only": "131",
    "FEPOC BlueFocus-Self + Family": "132",
    "FEPOC BlueFocus-Self + 1": "133",
    "USPS Basic Self Only": "33A",
    "USPS Basic Self + 1": "33C",
    "USPS Basic Self + Family": "33B",
    "USPS Blue Focus Self Only": "35A",
    "USPS Blue Focus Self + 1": "35C",
    "USPS Blue Focus Self + Family": "35B",
    "USPS Standard Self Only": "33D",
    "USPS Standard Self + 1": "33F",
    "USPS Standard Self + Family": "33E",
}


# Gender types
GENDER_TYPES = ["M", "F", "EMPTY"]

# Member age types
MEMBER_AGE_TYPES = ["over65", "under65", "Any"]

# Child type constants
ALL_CHILD_TYPES = [
    "CHILD_NEW_BORN", 
    "CHILD_MINOR", 
    "CHILD_MAJOR", 
    "CHILD_UNDER_13", 
    "CHILD_OVER_13",
    "EMPTY"
]

# Spouse age options
SPOUSE_AGE_OPTIONS = ["SPOUSE_UNDER65", "SPOUSE_OVER65", "EMPTY"]

# Environment types
ENV_TYPES = ["V2", "F2", "G2"]

# User types
USER_TYPES = ["FEPOC", "NON-FEPOC"]

# Get all valid state codes
ALL_STATES = list(set(STATE_MAPPINGS.values()))

# Get all enrollment codes
ALL_ENROLLMENT_CODES = list(ENROLLMENT_MAP.values())

# Default form data structure
DEFAULT_FORM_DATA = {
  "userId": "",
  "env": "",
  "numberOfRecords": "",
  "statePercentage": [],
  "subscriberGender": [],
  "enrollmentCode": [],
  "memberAge": [],
  "dependentAge": [],
  "spouseAge": [],
  "optionalEntries": []
}
