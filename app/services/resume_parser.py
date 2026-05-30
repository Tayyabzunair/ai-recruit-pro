"""
Resume parsing service using PyMuPDF + Gemini AI.
"""
import fitz  # PyMuPDF
from loguru import logger
from app.services.ai_service import AIService


class ResumeParser:
    """Extract structured data from resume PDFs."""
    
    @staticmethod
    def extract_text(pdf_path):
        """
        Extract raw text from PDF using PyMuPDF (faster + more accurate than PyPDF2).
        """
        try:
            doc = fitz.open(pdf_path)
            text = ''
            for page in doc:
                text += page.get_text() + '\n'
            doc.close()
            
            # Clean up
            text = ' '.join(text.split())  # Normalize whitespace
            logger.info(f'Extracted {len(text)} chars from PDF')
            return text
        except Exception as e:
            logger.error(f'PDF extraction failed: {e}')
            return ''
    
    @staticmethod
    def parse_with_ai(text):
        """
        Use Gemini to extract structured fields from resume text.
        """
        if not text or len(text) < 50:
            return ResumeParser._empty_data()
        
        # Truncate for API limits
        text_sample = text[:5000]
        
        prompt = f"""You are a professional resume parser. Extract information from this resume and return ONLY a valid JSON object (no markdown, no explanation).

Required JSON structure:
{{
    "full_name": "candidate's full name",
    "email": "email address",
    "phone": "phone number with country code if available",
    "skills": "comma-separated technical skills only (e.g., Python, React, AWS, SQL)",
    "experience_years": 0.0,
    "education": "highest degree and institution",
    "summary": "2-3 sentence professional summary"
}}

Rules:
- If any field is not found, use "Not Found" for strings, 0.0 for experience_years
- For skills, extract ONLY technical/professional skills, separated by commas
- experience_years should be a number (e.g., 2.5 for 2 years 6 months)
- summary should be concise and professional

Resume Text:
{text_sample}

Return ONLY the JSON object:"""
        
        result = AIService.generate(prompt, json_mode=True)
        
        if not result:
            return ResumeParser._empty_data()
        
        # Ensure all required keys exist
        return {
            'full_name': result.get('full_name', 'Not Found'),
            'email': result.get('email', 'Not Found'),
            'phone': result.get('phone', 'Not Found'),
            'skills': result.get('skills', ''),
            'experience_years': float(result.get('experience_years', 0) or 0),
            'education': result.get('education', 'Not Found'),
            'summary': result.get('summary', ''),
        }
    
    @staticmethod
    def _empty_data():
        return {
            'full_name': 'Not Found',
            'email': 'Not Found',
            'phone': 'Not Found',
            'skills': '',
            'experience_years': 0.0,
            'education': 'Not Found',
            'summary': '',
        }
    
    @classmethod
    def parse(cls, pdf_path):
        """Full parsing pipeline: PDF → text → AI → structured data."""
        text = cls.extract_text(pdf_path)
        if not text:
            return cls._empty_data(), ''
        
        data = cls.parse_with_ai(text)
        return data, text
