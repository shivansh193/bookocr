import logging
import re
from typing import List

logger = logging.getLogger(__name__)


class MarkdownStitcher:
    """
    Assembles individual page markdowns into a cohesive document.
    
    Handles:
    - Removing duplicate headers across page breaks
    - Cleaning up excessive whitespace
    - Ensuring proper markdown structure
    """
    
    def __init__(self):
        self.pages = []
        logger.info("Initialized MarkdownStitcher")
    
    def add_page(self, markdown: str, page_number: int):
        """Add a processed page to the collection."""
        self.pages.append({
            'number': page_number,
            'content': markdown
        })
        logger.debug(f"Added page {page_number} to stitcher")
    
    def stitch_all(self) -> str:
        """
        Combine all pages into final markdown document.
        
        Returns:
            Complete markdown document
        """
        if not self.pages:
            logger.warning("No pages to stitch")
            return ""
        
        logger.info(f"Stitching {len(self.pages)} pages together...")
        
        # Sort pages by number (in case they were added out of order)
        self.pages.sort(key=lambda x: x['number'])
        
        stitched = []
        previous_last_line = None
        
        for i, page in enumerate(self.pages):
            content = page['content']
            
            # Clean up the content
            content = self._clean_page_content(content)
            
            # Handle page transitions
            if i > 0:
                content = self._handle_page_transition(
                    previous_last_line,
                    content
                )
            
            stitched.append(content)
            
            # Remember last line for next iteration
            lines = content.strip().split('\n')
            previous_last_line = lines[-1] if lines else ""
        
        # Join all pages
        final_markdown = '\n\n'.join(stitched)
        
        # Final cleanup
        final_markdown = self._final_cleanup(final_markdown)
        
        logger.info("Stitching complete")
        return final_markdown
    
    def _clean_page_content(self, content: str) -> str:
        """Clean up individual page content."""
        # Remove excessive newlines (more than 2)
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Remove trailing/leading whitespace
        content = content.strip()
        
        return content
    
    def _handle_page_transition(
        self,
        previous_last_line: str,
        current_content: str
    ) -> str:
        """
        Handle the transition between pages to avoid duplicates.
        
        Args:
            previous_last_line: Last line from previous page
            current_content: Content of current page
            
        Returns:
            Cleaned current content
        """
        if not previous_last_line or not current_content:
            return current_content
        
        current_lines = current_content.split('\n')
        if not current_lines:
            return current_content
        
        current_first_line = current_lines[0].strip()
        previous_cleaned = previous_last_line.strip()
        
        # Check for duplicate headers
        if (self._is_header(previous_cleaned) and 
            self._is_header(current_first_line) and
            self._similar_text(previous_cleaned, current_first_line)):
            # Remove duplicate header from current page
            logger.debug(f"Removing duplicate header: {current_first_line}")
            current_lines = current_lines[1:]
            return '\n'.join(current_lines)
        
        return current_content
    
    def _is_header(self, line: str) -> bool:
        """Check if a line is a markdown header."""
        return bool(re.match(r'^#{1,6}\s+', line))
    
    def _similar_text(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
        """
        Check if two texts are similar (for duplicate detection).
        
        Simple character-based similarity check.
        """
        # Remove markdown symbols for comparison
        clean1 = re.sub(r'[#*_\[\]]', '', text1).lower()
        clean2 = re.sub(r'[#*_\[\]]', '', text2).lower()
        
        if not clean1 or not clean2:
            return False
        
        # Simple similarity: check if one contains most of the other
        longer = max(clean1, clean2, key=len)
        shorter = min(clean1, clean2, key=len)
        
        if shorter in longer:
            return True
        
        # Character overlap ratio
        common = sum(1 for a, b in zip(clean1, clean2) if a == b)
        similarity = common / max(len(clean1), len(clean2))
        
        return similarity >= threshold
    
    def _final_cleanup(self, markdown: str) -> str:
        """Final cleanup of the complete document."""
        # Remove excessive blank lines
        markdown = re.sub(r'\n{4,}', '\n\n\n', markdown)
        
        # Ensure consistent spacing around headers
        markdown = re.sub(r'\n(#{1,6}\s+)', r'\n\n\1', markdown)
        
        # Clean up list formatting
        markdown = re.sub(r'\n([•\-\*])\s+', r'\n\1 ', markdown)
        
        # Remove any remaining page artifacts (common OCR noise)
        markdown = re.sub(r'\n\s*\d+\s*\n', '\n', markdown)  # Lone page numbers
        
        # Trim
        markdown = markdown.strip()
        
        return markdown
    
    def get_stats(self) -> dict:
        """Get statistics about the stitched document."""
        if not self.pages:
            return {'total_pages': 0, 'total_chars': 0, 'total_words': 0}
        
        all_content = ' '.join(p['content'] for p in self.pages)
        
        return {
            'total_pages': len(self.pages),
            'total_chars': len(all_content),
            'total_words': len(all_content.split()),
            'avg_chars_per_page': len(all_content) // len(self.pages)
        }