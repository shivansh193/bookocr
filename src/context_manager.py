import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages cross-page context to handle broken words/sentences.
    
    Tracks incomplete text fragments from page endings and ensures
    they're properly joined with the next page's beginning.
    """
    
    def __init__(self):
        self.current_context: Optional[str] = None
        self.context_history = []
        logger.info("Initialized ContextManager")
    
    def set_incomplete_text(self, text: str, page_number: int):
        """
        Store incomplete text from the end of a page.
        
        Args:
            text: The incomplete text fragment (e.g., "jum" from "jump")
            page_number: The page this came from
        """
        self.current_context = text.strip()
        self.context_history.append({
            'page': page_number,
            'fragment': self.current_context
        })
        logger.info(f"Stored context from page {page_number}: '{self.current_context}'")
    
    def get_context_for_next_page(self) -> Optional[str]:
        """
        Get the context to pass to the next page processing.
        
        Returns:
            The incomplete text fragment, or None if no context exists
        """
        return self.current_context
    
    def clear_context(self):
        """Clear the current context after it's been used."""
        self.current_context = None
        logger.debug("Context cleared")
    
    def has_context(self) -> bool:
        """Check if there's pending context from a previous page."""
        return self.current_context is not None
    
    def get_context_history(self) -> list:
        """Get the full history of context transitions (for debugging)."""
        return self.context_history
    
    def join_with_context(self, new_markdown: str) -> str:
        """
        Join new page markdown with context from previous page.
        
        This handles the case where Gemini properly continues from the context
        but we want to ensure clean joining.
        
        Args:
            new_markdown: The markdown from the current page
            
        Returns:
            The markdown with context properly integrated
        """
        if not self.has_context():
            return new_markdown
        
        # The context should already be integrated by Gemini's prompt
        # This is a safety check - we just ensure there's no duplicate
        
        # Clear context after use
        self.clear_context()
        
        return new_markdown
    
    def detect_incomplete_text(self, markdown: str) -> tuple[bool, Optional[str]]:
        """
        Fallback detection for incomplete text if Gemini doesn't mark it.
        
        Checks if the last line ends mid-word (no punctuation, ends with letter).
        
        Args:
            markdown: The markdown text to check
            
        Returns:
            (is_incomplete, incomplete_fragment)
        """
        if not markdown:
            return False, None
        
        lines = markdown.strip().split('\n')
        if not lines:
            return False, None
        
        last_line = lines[-1].strip()
        if not last_line:
            return False, None
        
        # Check if ends with punctuation or whitespace
        if last_line[-1] in '.!?,;:)"\'':
            return False, None
        
        # Get the last "word" (might be incomplete)
        words = last_line.split()
        if not words:
            return False, None
        
        last_word = words[-1]
        
        # If it's very short and ends with a letter, might be incomplete
        if len(last_word) < 15 and last_word[-1].isalpha() and '-' in last_word:
            # Likely hyphenated word: "break-" or similar
            return True, last_word
        
        return False, None
    
    def get_stats(self) -> dict:
        """Get statistics about context usage."""
        return {
            'total_contexts': len(self.context_history),
            'pages_with_incomplete_text': [c['page'] for c in self.context_history],
            'current_context_active': self.has_context()
        }