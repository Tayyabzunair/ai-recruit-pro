"""
Gemini AI service wrapper.
"""
import json
import google.generativeai as genai
from flask import current_app
from loguru import logger


class AIService:
    """Wrapper for Gemini AI interactions."""
    
    _model = None
    
    @classmethod
    def _get_model(cls):
        """Lazy initialization of Gemini model."""
        if cls._model is None:
            api_key = current_app.config['GENAI_API_KEY']
            if not api_key:
                raise ValueError('GENAI_API_KEY not configured in .env')
            
            genai.configure(api_key=api_key)
            cls._model = genai.GenerativeModel(
                current_app.config['GEMINI_MODEL'],
                generation_config={
                    'temperature': 0.3,
                    'top_p': 0.95,
                    'max_output_tokens': 2048,
                }
            )
            logger.info(f'Gemini model initialized: {current_app.config["GEMINI_MODEL"]}')
        return cls._model
    
    @classmethod
    def generate(cls, prompt, json_mode=False):
        """
        Generate response from Gemini.
        
        Args:
            prompt: Input prompt string
            json_mode: If True, extract JSON from response
        
        Returns:
            String response or dict if json_mode=True
        """
        try:
            model = cls._get_model()
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            if json_mode:
                return cls._extract_json(text)
            return text
        
        except Exception as e:
            logger.error(f'AI generation failed: {e}')
            if json_mode:
                return {}
            return 'Sorry, AI service is currently unavailable. Please try again.'
    
    @staticmethod
    def _extract_json(text):
        """Extract JSON from text, handling markdown code blocks."""
        try:
            # Remove markdown code fences
            text = text.replace('```json', '').replace('```', '').strip()
            
            # Try to find JSON object
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                text = text[start:end + 1]
            
            return json.loads(text)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f'JSON extraction failed: {e}, text: {text[:200]}')
            return {}
