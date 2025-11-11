"""
Book OCR - Convert PDF books to markdown using Gemini API
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from .book_processor import BookProcessor
from .gemini_client import GeminiClient
from .pdf_handler import PDFHandler
from .context_manager import ContextManager
from .markdown_stitcher import MarkdownStitcher

__all__ = [
    'BookProcessor',
    'GeminiClient',
    'PDFHandler',
    'ContextManager',
    'MarkdownStitcher'
]