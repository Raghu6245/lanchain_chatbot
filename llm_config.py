"""
LLM Configuration - Centralized Bedrock Setup
===========================================

Single source of truth for AWS Bedrock Llama 3.3 70B configuration.
Avoids code duplication across agents and workflows.
"""

from langchain_aws import ChatBedrock
from config import BEDROCK_MODEL_ID, AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY


def get_bedrock_llm(
    aws_access_key_id: str = None,
    aws_secret_access_key: str = None,
    max_tokens: int = 1000,
    temperature: float = 0.1,
    top_p: float = 0.9
) -> ChatBedrock:
    """
    Get configured Bedrock LLM instance with Llama 3.3 70B
    
    Args:
        aws_access_key_id: AWS access key (uses env var if not provided)
        aws_secret_access_key: AWS secret key (uses env var if not provided)
        max_tokens: Maximum tokens to generate
        temperature: Temperature for response generation (0.0-1.0)
        top_p: Top-p sampling parameter
    
    Returns:
        Configured ChatBedrock instance
    """
    return ChatBedrock(
        model_id=BEDROCK_MODEL_ID,  # "us.meta.llama3-3-70b-instruct-v1:0"
        region_name=AWS_REGION,
        credentials_profile_name=None,
        aws_access_key_id=aws_access_key_id or AWS_ACCESS_KEY_ID,
        aws_secret_access_key=aws_secret_access_key or AWS_SECRET_ACCESS_KEY,
        model_kwargs={
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
    )


def get_extraction_llm(aws_access_key_id: str = None, aws_secret_access_key: str = None) -> ChatBedrock:
    """
    Get LLM optimized for data extraction
    - Low temperature for consistent extraction
    - Higher token limit for structured output
    """
    return get_bedrock_llm(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        max_tokens=1000,
        temperature=0.1,
        top_p=0.9
    )


def get_followup_llm(aws_access_key_id: str = None, aws_secret_access_key: str = None) -> ChatBedrock:
    """
    Get LLM optimized for follow-up generation
    - Medium temperature for natural conversation
    - Lower token limit for concise responses
    """
    return get_bedrock_llm(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        max_tokens=150,
        temperature=0.3,
        top_p=0.8
    )
