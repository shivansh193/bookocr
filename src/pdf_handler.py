from pdf2image import convert_from_path
from PIL import Image
import PyPDF2
import logging
import os
from typing import Generator, Tuple

logger = logging.getLogger(__name__)


class PDFHandler:
    """Handles PDF loading and page-by-page image extraction."""
    
    def __init__(self, dpi: int = 300, image_quality: int = 85):
        self.dpi = dpi
        self.image_quality = image_quality
        logger.info(f"Initialized PDFHandler (DPI: {dpi}, Quality: {image_quality})")
    
    def get_page_count(self, pdf_path: str) -> int:
        """Get total number of pages in PDF."""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                return len(pdf_reader.pages)
        except Exception as e:
            logger.error(f"Error reading PDF metadata: {str(e)}")
            raise
    
    def extract_pages(
        self,
        pdf_path: str,
        start_page: int = 1,
        end_page: int = None
    ) -> Generator[Tuple[int, Image.Image], None, None]:
        """
        Generator that yields (page_number, image) tuples one at a time.
        
        This approach minimizes memory usage by converting one page at a time.
        
        Args:
            pdf_path: Path to the PDF file
            start_page: First page to process (1-indexed)
            end_page: Last page to process (None = all pages)
            
        Yields:
            Tuple of (page_number, PIL.Image)
        """
        total_pages = self.get_page_count(pdf_path)
        
        if end_page is None:
            end_page = total_pages
        
        logger.info(f"Extracting pages {start_page} to {end_page} from {pdf_path}")
        
        for page_num in range(start_page, end_page + 1):
            try:
                # Convert single page to image
                images = convert_from_path(
                    pdf_path,
                    dpi=self.dpi,
                    first_page=page_num,
                    last_page=page_num,
                    fmt='JPEG',
                    jpegopt={'quality': self.image_quality, 'optimize': True}
                )
                
                if images:
                    logger.debug(f"Extracted page {page_num}/{total_pages}")
                    yield page_num, images[0]
                else:
                    logger.warning(f"No image extracted for page {page_num}")
                    
            except Exception as e:
                logger.error(f"Error extracting page {page_num}: {str(e)}")
                raise
    
    def optimize_image(self, image: Image.Image) -> Image.Image:
        """
        Optimize image for OCR while keeping file size reasonable.
        
        - Convert to RGB if needed
        - Ensure reasonable dimensions (max 4000px width)
        """
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Limit maximum dimensions to prevent huge uploads
        max_width = 4000
        if image.width > max_width:
            ratio = max_width / image.width
            new_height = int(image.height * ratio)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
            logger.debug(f"Resized image to {max_width}x{new_height}")
        
        return image
    
    def validate_pdf(self, pdf_path: str) -> bool:
        """Check if PDF is valid and readable."""
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return False
        
        if not pdf_path.lower().endswith('.pdf'):
            logger.error(f"File is not a PDF: {pdf_path}")
            return False
        
        try:
            with open(pdf_path, 'rb') as file:
                PyPDF2.PdfReader(file)
            return True
        except Exception as e:
            logger.error(f"Invalid PDF file: {str(e)}")
            return False