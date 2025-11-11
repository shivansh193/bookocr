import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential
from PIL import Image
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GeminiClient:
    """Handles all Gemini API interactions with retry logic and rate limiting."""
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash",
        max_retries: int = 3
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.max_retries = max_retries
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        logger.info(f"Initialized Gemini client with model: {model_name}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def extract_page_markdown(
        self,
        image: Image.Image,
        context_from_previous: Optional[str] = None,
        page_number: int = 1
    ) -> dict:
        """
        Extract text from a page image and convert to markdown.
        
        Args:
            image: PIL Image of the page
            context_from_previous: Text fragment from previous page (if any)
            page_number: Current page number for logging
            
        Returns:
            dict with keys: 'markdown', 'ends_incomplete', 'incomplete_text'
        """
        prompt = self._build_extraction_prompt(context_from_previous)
        
        try:
            logger.info(f"Processing page {page_number} with Gemini...")
            response = self.model.generate_content([prompt, image])
            
            # Parse the response
            result = self._parse_response(response.text)
            logger.info(f"Page {page_number} processed successfully")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing page {page_number}: {str(e)}")
            raise
    
    def _build_extraction_prompt(self, context: Optional[str]) -> str:
        """Build the prompt for Gemini with context handling."""
        
        base_prompt = """Extract ALL text from this book page and convert it to clean markdown format.

FORMATTING RULES:
- Use ## for chapter titles, ### for sections, #### for subsections
- Preserve **bold** and *italic* formatting
- Convert lists to proper markdown (- or 1. 2. 3.)
- Tables should use markdown table syntax
- Preserve paragraph breaks (double newline)
- Remove headers/footers/page numbers

CRITICAL - HANDLING INCOMPLETE TEXT:
- If text at the BOTTOM of the page ends mid-word or mid-sentence, mark it with {EOL} tag
- Extract the incomplete fragment and add it after {INCOMPLETE: fragment text here}
- Example: "The quick brown fox jum{EOL}{INCOMPLETE: jum}"

OUTPUT FORMAT:
```markdown
[Your markdown content here]
```

If incomplete text detected:
{EOL}
{INCOMPLETE: incomplete text fragment}
"""
        
        if context:
            context_section = f"""
CONTEXT FROM PREVIOUS PAGE:
The previous page ended with incomplete text: "{context}"
Start your extraction by completing this text naturally, then continue with the rest of the page.
"""
            return context_section + base_prompt
        
        return base_prompt
    
    def _parse_response(self, response_text: str) -> dict:
        """Parse Gemini response to extract markdown and context markers."""
        
        # Initialize result
        result = {
            'markdown': '',
            'ends_incomplete': False,
            'incomplete_text': None
        }
        
        # Extract markdown content (between ```markdown and ```)
        if '```markdown' in response_text:
            start = response_text.find('```markdown') + len('```markdown')
            end = response_text.find('```', start)
            if end != -1:
                result['markdown'] = response_text[start:end].strip()
        else:
            # Fallback: use entire response
            result['markdown'] = response_text.strip()
        
        # Check for incomplete text markers
        if '{EOL}' in response_text:
            result['ends_incomplete'] = True
            
            # Extract incomplete text
            if '{INCOMPLETE:' in response_text:
                incomplete_start = response_text.find('{INCOMPLETE:') + len('{INCOMPLETE:')
                incomplete_end = response_text.find('}', incomplete_start)
                if incomplete_end != -1:
                    result['incomplete_text'] = response_text[incomplete_start:incomplete_end].strip()
        
        # Clean up the markdown (remove EOL markers)
        result['markdown'] = result['markdown'].replace('{EOL}', '').strip()
        
        return result
    
    def test_connection(self) -> bool:
        """Test if the API connection is working."""
        try:
            # Create a simple test image
            test_img = Image.new('RGB', (100, 100), color='white')
            response = self.model.generate_content(["What color is this?", test_img])
            return bool(response.text)
        except Exception as e:
            logger.error(f"API connection test failed: {str(e)}")
            return False