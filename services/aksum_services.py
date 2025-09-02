import json
import re
from typing import Dict, Any, Optional
from langchain_zunno import create_zunno_llm
from pypdf import PdfReader
import logging
import datetime
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize LLM
llm = create_zunno_llm(model_name='mistral:latest')

def extract_text_from_file(file_path: str) -> str:
    """
    Extract text content from a file (PDF, DOC, or TXT).
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        str: Extracted text content
    """
    try:
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            return extract_text_from_pdf(file_path)
        elif file_extension == '.doc' or file_extension == '.docx':
            return extract_text_from_doc(file_path)
        elif file_extension == '.txt':
            return extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
            
    except Exception as e:
        logger.error(f"Error extracting text from file {file_path}: {str(e)}")
        raise

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        
        for page in reader.pages:
            text += page.extract_text() + "\n"
            
        logger.info(f"Successfully extracted text from PDF: {pdf_path}")
        return text.strip()
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF {pdf_path}: {str(e)}")
        raise

def extract_text_from_doc(doc_path: str) -> str:
    """Extract text content from a DOC/DOCX file."""
    try:
        # For DOC files, we'll use a simple approach
        # In production, you might want to use python-docx for DOCX files
        if doc_path.endswith('.docx'):
            try:
                from docx import Document
                doc = Document(doc_path)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text.strip()
            except ImportError:
                logger.warning("python-docx not available, trying alternative method")
        
        # Fallback for .doc files or when python-docx is not available
        # This is a basic text extraction - for production use, consider using antiword or similar tools
        with open(doc_path, 'rb') as f:
            content = f.read()
            # Simple text extraction - this is basic and may not work for all DOC files
            text = content.decode('utf-8', errors='ignore')
            # Remove binary content and keep only printable text
            text = re.sub(r'[^\x20-\x7E\n\r\t]', '', text)
            return text.strip()
            
    except Exception as e:
        logger.error(f"Error extracting text from DOC {doc_path}: {str(e)}")
        raise

def extract_text_from_txt(txt_path: str) -> str:
    """Extract text content from a TXT file."""
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            text = f.read()
        logger.info(f"Successfully extracted text from TXT: {txt_path}")
        return text.strip()
        
    except Exception as e:
        logger.error(f"Error extracting text from TXT {txt_path}: {str(e)}")
        raise

def clean_text(text: str) -> str:
    """
    Clean and preprocess extracted text for better LLM processing.
    
    Args:
        text (str): Raw extracted text
        
    Returns:
        str: Cleaned text
    """
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters that might interfere with LLM processing
    text = re.sub(r'[^\w\s\-.,;:()%$#@!&*+=<>?/\\[\]{}|~`]', '', text)
    
    # Remove page numbers and headers/footers
    text = re.sub(r'Page \d+', '', text)
    text = re.sub(r'\d+ of \d+', '', text)
    
    return text.strip()

def create_extraction_prompt(text: str) -> str:
    """
    Create a structured prompt for the LLM to extract RFQ data.
    
    Args:
        text (str): Cleaned text content
        
    Returns:
        str: Formatted prompt for the LLM
    """
    prompt = f"""
    You are a data extraction specialist. Extract RFQ (Request for Quotation) information from the following text.
    
    TEXT TO ANALYZE:
    {text}  # Limit text length for LLM processing
    
    INSTRUCTIONS:
    1. Analyze the text carefully to identify RFQ information
    2. Extract the following fields if available:
       - rfq_number: Request for Quotation number
       - rfq_date: Date of the RFQ
       - company_name: Company name
       - contact_person: Contact person name
       - email: Contact email
       - phone: Contact phone
       - project_title: Project title
       - project_description: Project description
       - required_services: Array of required services
       - budget_range: Budget range
       - deadline: Submission deadline
       - technical_requirements: Array of technical requirements
       - evaluation_criteria: Array of evaluation criteria
       - submission_instructions: Submission instructions
    
    3. If a field is not found, use null
    4. Return ONLY valid JSON that matches the schema exactly
    5. Do not include any explanations or additional text
    
    RESPONSE FORMAT:
    Return only the JSON object, no other text.
    """
    
    return prompt

def extract_data_with_llm(text: str) -> Dict[str, Any]:
    """
    Use LLM to extract RFQ data from text.
    
    Args:
        text (str): Cleaned text content
        
    Returns:
        Dict: Extracted RFQ data
    """
    try:
        # Create the extraction prompt
        prompt = create_extraction_prompt(text)
        
        # Get response from LLM
        response = llm.invoke(prompt)
        
        # Extract JSON from response
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            extracted_data = json.loads(json_str)
            logger.info("Successfully extracted RFQ data using LLM")
            return extracted_data
        else:
            logger.warning("No JSON found in LLM response, attempting to parse entire response")
            return json.loads(response_text)
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from LLM response: {str(e)}")
        logger.error(f"Raw response: {response_text}")
        raise
    except Exception as e:
        logger.error(f"Error during LLM extraction: {str(e)}")
        raise

def extract_aksum_data_from_RFQ(file_path: str) -> Dict[str, Any]:
    """
    Extract AKSUM RFQ data from a file (PDF, DOC, or TXT).
    
    Args:
        file_path (str): Path to the RFQ file
        
    Returns:
        Dict: Extracted RFQ data in JSON format
    """
    try:
        # Extract text from file
        raw_text = extract_text_from_file(file_path)
        
        # Clean the text
        cleaned_text = clean_text(raw_text)
        
        # Extract RFQ data using LLM
        extracted_data = extract_data_with_llm(cleaned_text)
        
        # Add metadata
        result = {
            "source_file": file_path,
            "extraction_timestamp": str(datetime.datetime.now()),
            "extracted_data": extracted_data,
            "processing_status": "success"
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error in extract_aksum_data_from_RFQ: {str(e)}")
        return {
            "source_file": file_path,
            "extraction_timestamp": str(datetime.datetime.now()),
            "processing_status": "error",
            "error_message": str(e)
        }

# Keep the old function name for backward compatibility
def extract_aksum_data_from_RFQ_pdf(file_path: str) -> Dict[str, Any]:
    """
    Extract AKSUM RFQ data from a file (PDF, DOC, or TXT).
    This function is kept for backward compatibility.
    
    Args:
        file_path (str): Path to the RFQ file
        
    Returns:
        Dict: Extracted RFQ data in JSON format
    """
    return extract_aksum_data_from_RFQ(file_path)
