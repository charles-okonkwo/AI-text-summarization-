# FastAPI Backend for AI Text Summarizer Chatbot
# This module sets up a REST API endpoint for text summarization
# using Hugging Face Transformers library
 
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import logging
from fastapi import File, UploadFile
import PyPDF2
import io
 
# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
# ============================================================================
# Initialize FastAPI Application
# ============================================================================
app = FastAPI(
    title="AI Text Summarizer API",
    description="API for summarizing text using Hugging Face Transformers",
    version="1.0.0"
)
 
# ============================================================================
# Configure CORS (Cross-Origin Resource Sharing)
# This allows the frontend to communicate with the backend
# ============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for development)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
# ============================================================================
# Global variables to store the summarization model and tokenizer
# These are loaded on-demand (lazy loading) to save memory
# ============================================================================
model = None
tokenizer = None
 
 
# ============================================================================
# Data Model for Request/Response
# ============================================================================
class SummarizeRequest(BaseModel):
    """Data model for incoming request."""
    text: str
 
    class Config:
        schema_extra = {
            "example": {
                "text": "Your long text here..."
            }
        }
 
 
class SummarizeResponse(BaseModel):
    """Data model for outgoing response."""
    summary: str
 
 
# ============================================================================
# Function to Load Summarization Model
# ============================================================================
def load_summarization_model():
    """
    Load the Hugging Face summarization pipeline.
    Uses the 'facebook/bart-large-cnn' model which is optimized for summarization.
    
    Returns:
        tuple: (model, tokenizer) objects for text summarization
    """
    logger.info("Loading summarization model...")
    try:
        # Load tokenizer and model directly
        model_name = "facebook/bart-large-cnn"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        logger.info("Model loaded successfully!")
        return model, tokenizer
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        raise
 
 
# ============================================================================
# Function to Ensure Model is Loaded
# Load the model on-demand (lazy loading) to save memory
# ============================================================================
def ensure_model_loaded():
    """
    Ensure the model is loaded. Load on-demand if not already loaded.
    This saves memory by only loading when needed.
    """
    global model, tokenizer
    if model is None or tokenizer is None:
        logger.info("Model not loaded yet, loading now...")
        model, tokenizer = load_summarization_model()
    return model, tokenizer
 
 
# ============================================================================
# Function to Extract Text from PDF
# ============================================================================
def extract_text_from_pdf(file_content: bytes) -> str:
    """
    Extract text from a PDF file.
    
    Args:
        file_content (bytes): The PDF file content as bytes
        
    Returns:
        str: The extracted text from the PDF
        
    Raises:
        Exception: If PDF reading fails
    """
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        extracted_text = ""
        
        for page_num, page in enumerate(pdf_reader.pages):
            logger.info(f"Extracting text from page {page_num + 1}")
            extracted_text += page.extract_text()
        
        if not extracted_text.strip():
            raise Exception("No text could be extracted from the PDF")
        
        return extracted_text
    except Exception as e:
        logger.error(f"Error extracting PDF text: {str(e)}")
        raise
 
 
# ============================================================================
# Health Check Endpoint
# ============================================================================
@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the API is running.
    
    Returns:
        dict: Status message
    """
    return {"status": "API is running"}
 
 
# ============================================================================
# Main Summarization Endpoint
# ============================================================================
@app.post("/summarize", response_model=SummarizeResponse)
async def summarize_text(request: SummarizeRequest):
    """
    Summarize the provided text.
    
    Args:
        request (SummarizeRequest): JSON object containing 'text' field
        
    Returns:
        SummarizeResponse: JSON object with 'summary' field
        
    Raises:
        HTTPException: If text is empty or summarization fails
    """
    try:
        # Validate input
        if not request.text or len(request.text.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Text cannot be empty"
            )
        
        # Load model on-demand
        model, tokenizer = ensure_model_loaded()
        
        logger.info(f"Received text of length: {len(request.text)}")
        
        # Tokenize the input text
        inputs = tokenizer.encode(request.text, return_tensors="pt", max_length=1024, truncation=True)
        
        # Calculate dynamic summary length based on input length
        text_word_count = len(request.text.split())
        # Ensure reasonable limits
        max_summary_length = min(150, max(30, text_word_count // 3))
        min_summary_length = min(max_summary_length - 10, max(10, text_word_count // 5))
        
        # Ensure min is not greater than max
        if min_summary_length > max_summary_length:
            min_summary_length = max(10, max_summary_length - 10)
        
        logger.info(f"Summary length: min={min_summary_length}, max={max_summary_length}")
        
        # Generate summary with simpler parameters
        summary_ids = model.generate(
            inputs,
            max_length=max_summary_length,
            min_length=min_summary_length,
            do_sample=False
        )
        
        # Decode the summary
        summary_text = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        
        logger.info(f"Summarization successful!")
        
        return SummarizeResponse(summary=summary_text)
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Error during summarization: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error summarizing text: {str(e)}"
        )
 
 
# ============================================================================
# PDF Summarization Endpoint
# ============================================================================
@app.post("/summarize-pdf", response_model=SummarizeResponse)
async def summarize_pdf(file: UploadFile = File(...)):
    """
    Summarize text extracted from an uploaded PDF file.
    
    Args:
        file (UploadFile): The PDF file to summarize
        
    Returns:
        SummarizeResponse: JSON object with 'summary' field
        
    Raises:
        HTTPException: If file is not a PDF or summarization fails
    """
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="File must be a PDF"
            )
        
        # Check file size (max 50MB)
        file_size = 0
        file_content = b""
        while True:
            chunk = await file.read(1024 * 1024)  # Read 1MB at a time
            if not chunk:
                break
            file_size += len(chunk)
            file_content += chunk
            
            if file_size > 50 * 1024 * 1024:  # 50MB limit
                raise HTTPException(
                    status_code=413,
                    detail="File is too large (maximum 50MB)"
                )
        
        logger.info(f"Received PDF file: {file.filename} ({file_size} bytes)")
        
        # Extract text from PDF
        extracted_text = extract_text_from_pdf(file_content)
        logger.info(f"Extracted {len(extracted_text)} characters from PDF")
        
        # Load model on-demand
        model, tokenizer = ensure_model_loaded()
        
        # Tokenize the extracted text
        inputs = tokenizer.encode(extracted_text, return_tensors="pt", max_length=1024, truncation=True)
        
        # Calculate dynamic summary length
        text_word_count = len(extracted_text.split())
        max_summary_length = min(150, max(30, text_word_count // 3))
        min_summary_length = min(max_summary_length - 10, max(10, text_word_count // 5))
        
        if min_summary_length > max_summary_length:
            min_summary_length = max(10, max_summary_length - 10)
        
        logger.info(f"PDF Summary length: min={min_summary_length}, max={max_summary_length}")
        
        # Generate summary
        summary_ids = model.generate(
            inputs,
            max_length=max_summary_length,
            min_length=min_summary_length,
            do_sample=False
        )
        
        # Decode the summary
        summary_text = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        
        logger.info(f"PDF Summarization successful!")
        
        return SummarizeResponse(summary=summary_text)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during PDF summarization: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error summarizing PDF: {str(e)}"
        )
 
 
# ============================================================================
# Run the Server
# Use: python main.py
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    
    # Run the FastAPI server
    # reload=False disables auto-reload to prevent hot reload issues with model initialization
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8001,
        reload=False
    )
 