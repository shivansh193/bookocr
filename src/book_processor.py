import logging
import json
import os
from pathlib import Path
from tqdm import tqdm
from typing import Optional

from .gemini_client import GeminiClient
from .pdf_handler import PDFHandler
from .context_manager import ContextManager
from .markdown_stitcher import MarkdownStitcher

logger = logging.getLogger(__name__)


class BookProcessor:
    """
    Main orchestrator for processing PDF books into markdown.
    
    Handles:
    - Page-by-page processing
    - Context carryover between pages
    - Progress tracking and resume capability
    - Cache management
    """
    
    def __init__(
        self,
        gemini_api_key: str,
        gemini_model: str = "gemini-1.5-flash-latest",
        cache_dir: str = "./cache",
        dpi: int = 300,
        image_quality: int = 85
    ):
        self.gemini_client = GeminiClient(gemini_api_key, gemini_model)
        self.pdf_handler = PDFHandler(dpi, image_quality)
        self.context_manager = ContextManager()
        self.markdown_stitcher = MarkdownStitcher()
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        logger.info("BookProcessor initialized")
    
    def process_book(
        self,
        pdf_path: str,
        output_path: str,
        start_page: int = 1,
        end_page: Optional[int] = None,
        resume: bool = True
    ) -> dict:
        """
        Process a PDF book into markdown format.
        
        Args:
            pdf_path: Path to input PDF
            output_path: Path for output markdown file
            start_page: First page to process (1-indexed)
            end_page: Last page to process (None = all)
            resume: Whether to resume from cache if available
            
        Returns:
            Statistics dictionary
        """
        logger.info(f"Starting book processing: {pdf_path}")
        
        # Validate PDF
        if not self.pdf_handler.validate_pdf(pdf_path):
            raise ValueError(f"Invalid PDF file: {pdf_path}")
        
        total_pages = self.pdf_handler.get_page_count(pdf_path)
        if end_page is None:
            end_page = total_pages
        
        logger.info(f"Processing pages {start_page} to {end_page} of {total_pages}")
        
        # Load cache if resuming
        cache_file = self._get_cache_file(pdf_path)
        processed_pages = self._load_cache(cache_file) if resume else {}
        
        # Process pages
        stats = {
            'total_pages': end_page - start_page + 1,
            'processed': 0,
            'cached': len(processed_pages),
            'errors': 0
        }
        
        try:
            with tqdm(total=stats['total_pages'], desc="Processing pages") as pbar:
                for page_num, page_image in self.pdf_handler.extract_pages(
                    pdf_path, start_page, end_page
                ):
                    # Check cache first
                    if str(page_num) in processed_pages:
                        logger.debug(f"Using cached result for page {page_num}")
                        result = processed_pages[str(page_num)]
                    else:
                        # Process page
                        result = self._process_single_page(
                            page_image,
                            page_num,
                            self.context_manager.get_context_for_next_page()
                        )
                        
                        if result:
                            # Cache the result
                            processed_pages[str(page_num)] = result
                            self._save_cache(cache_file, processed_pages)
                        else:
                            stats['errors'] += 1
                            logger.error(f"Failed to process page {page_num}")
                            pbar.update(1)
                            continue
                    
                    # Add to stitcher
                    self.markdown_stitcher.add_page(
                        result['markdown'],
                        page_num
                    )
                    
                    # Update context for next page
                    if result['ends_incomplete'] and result['incomplete_text']:
                        self.context_manager.set_incomplete_text(
                            result['incomplete_text'],
                            page_num
                        )
                    else:
                        self.context_manager.clear_context()
                    
                    stats['processed'] += 1
                    pbar.update(1)
            
            # Stitch all pages together
            logger.info("Stitching pages into final document...")
            final_markdown = self.markdown_stitcher.stitch_all()
            
            # Save output
            self._save_output(output_path, final_markdown)
            
            # Update stats
            stats.update(self.markdown_stitcher.get_stats())
            stats.update({
                'context_transitions': len(self.context_manager.get_context_history())
            })
            
            logger.info(f"Processing complete! Output saved to: {output_path}")
            self._print_stats(stats)
            
            return stats
            
        except KeyboardInterrupt:
            logger.warning("Processing interrupted by user")
            logger.info(f"Progress saved to cache: {cache_file}")
            raise
        except Exception as e:
            logger.error(f"Processing failed: {str(e)}")
            raise
    
    def _process_single_page(
        self,
        page_image,
        page_number: int,
        context: Optional[str]
    ) -> Optional[dict]:
        """Process a single page with Gemini."""
        try:
            # Optimize image
            optimized = self.pdf_handler.optimize_image(page_image)
            
            # Call Gemini
            result = self.gemini_client.extract_page_markdown(
                optimized,
                context_from_previous=context,
                page_number=page_number
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing page {page_number}: {str(e)}")
            return None
    
    def _get_cache_file(self, pdf_path: str) -> Path:
        """Generate cache file path based on PDF name."""
        pdf_name = Path(pdf_path).stem
        return self.cache_dir / f"{pdf_name}_cache.json"
    
    def _load_cache(self, cache_file: Path) -> dict:
        """Load cached results."""
        if not cache_file.exists():
            return {}
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded cache with {len(data)} pages")
            return data
        except Exception as e:
            logger.warning(f"Could not load cache: {str(e)}")
            return {}
    
    def _save_cache(self, cache_file: Path, data: dict):
        """Save results to cache."""
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Could not save cache: {str(e)}")
    
    def _save_output(self, output_path: str, markdown: str):
        """Save final markdown to file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        logger.info(f"Saved {len(markdown)} characters to {output_path}")
    
    def _print_stats(self, stats: dict):
        """Print processing statistics."""
        logger.info("=" * 50)
        logger.info("PROCESSING STATISTICS")
        logger.info("=" * 50)
        for key, value in stats.items():
            logger.info(f"{key.replace('_', ' ').title()}: {value}")
        logger.info("=" * 50)