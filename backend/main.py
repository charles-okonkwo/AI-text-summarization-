# FastAPI Backend for AI Text Summarizer Chatbot
# This module sets up a lightweight summarization API
# using extractive summarization (no heavy ML models needed)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from fastapi import File, UploadFile
import PyPDF2
import io
import re
from collections import Counter

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
# ============================================================================
# Initialize FastAPI Application
# ============================================================================
app = FastAPI(
    title="AI Text Summarizer API",
    description="API for summarizing text using lightweight extractive summarization (no heavy ML models)",
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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)
 
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
# Function to Perform Extractive Summarization
# ============================================================================
def extractive_summarize(text: str, num_sentences: int = None) -> str:
    """
    Extract the most important sentences from text based on word frequency.
    This is lightweight and doesn't require loading large ML models.
    
    Args:
        text (str): The text to summarize
        num_sentences (int): Number of sentences to extract (auto-calculated if None)
        
    Returns:
        str: The summary
    """
    try:
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) == 0:
            return text
        
        # Auto-calculate number of sentences (roughly 30% of original)
        if num_sentences is None:
            num_sentences = max(1, len(sentences) // 3)
        
        if len(sentences) <= num_sentences:
            return text
        
        # Calculate word frequencies (excluding common words)
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'if', 'then', 'is', 'are', 'was', 'were',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can', 'to', 'of', 'in', 'for', 'from',
            'with', 'by', 'on', 'at', 'it', 'this', 'that', 'these', 'those', 'i', 'you', 'he',
            'she', 'we', 'they', 'what', 'which', 'who', 'when', 'where', 'why', 'how'
        }
        
        word_freq = Counter()
        for sentence in sentences:
            words = re.findall(r'\b\w+\b', sentence.lower())
            for word in words:
                if word not in stopwords and len(word) > 2:
                    word_freq[word] += 1
        
        # Score sentences based on word frequency
        sentence_scores = {}
        for i, sentence in enumerate(sentences):
            words = re.findall(r'\b\w+\b', sentence.lower())
            score = sum(word_freq[word] for word in words if word in word_freq)
            sentence_scores[i] = score
        
        # Get top sentences in original order
        top_sentence_indices = sorted(
            sorted(sentence_scores, key=lambda x: sentence_scores[x], reverse=True)[:num_sentences]
        )
        
        summary = ' '.join(sentences[i] for i in top_sentence_indices)
        logger.info(f"Extractive summarization: {len(sentences)} sentences → {len(top_sentence_indices)} sentences")
        return summary
        
    except Exception as e:
        logger.error(f"Error during summarization: {str(e)}")
        raise
 
 
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
    Summarize the provided text using extractive summarization.
    
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
        
        logger.info(f"Received text of length: {len(request.text)}")
        
        # Perform extractive summarization (no model loading needed!)
        summary_text = extractive_summarize(request.text)
        
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
        
        # Perform extractive summarization (no model loading needed!)
        summary_text = extractive_summarize(extracted_text)
        
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
        host="0.0.0.0",
        port=8000,
        reload=False
    )
 