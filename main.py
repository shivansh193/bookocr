#!/usr/bin/env python3
"""
Book OCR CLI - Convert PDF books to markdown using Gemini API
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

from src.book_processor import BookProcessor

# Load environment variables
load_dotenv()


def setup_logging(log_level: str):
    """Configure logging."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('book_ocr.log')
        ]
    )


def main():
    parser = argparse.ArgumentParser(
        description='Convert PDF books to markdown using Gemini API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process entire book
  python main.py --input book.pdf --output book.md

  # Process specific page range
  python main.py --input book.pdf --output book.md --start-page 10 --end-page 50

  # Resume interrupted processing
  python main.py --input book.pdf --output book.md --resume

Environment Variables:
  GEMINI_API_KEY          Your Gemini API key (required)
  GEMINI_MODEL           Model to use (default: gemini-1.5-flash-latest)
  LOG_LEVEL              Logging level (default: INFO)
        """
    )
    
    # Required arguments
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Path to input PDF file'
    )
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Path to output markdown file'
    )
    
    # Optional arguments
    parser.add_argument(
        '--start-page',
        type=int,
        default=1,
        help='First page to process (default: 1)'
    )
    parser.add_argument(
        '--end-page',
        type=int,
        default=None,
        help='Last page to process (default: all)'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from cached progress'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable caching (process from scratch)'
    )
    parser.add_argument(
        '--cache-dir',
        default='./cache',
        help='Directory for cache files (default: ./cache)'
    )
    parser.add_argument(
        '--dpi',
        type=int,
        default=300,
        help='DPI for PDF to image conversion (default: 300)'
    )
    parser.add_argument(
        '--image-quality',
        type=int,
        default=85,
        help='JPEG quality for images (default: 85)'
    )
    parser.add_argument(
        '--log-level',
        default=os.getenv('LOG_LEVEL', 'INFO'),
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Validate API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable not set!")
        logger.error("Please set it in .env file or export it:")
        logger.error("  export GEMINI_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    # Validate input file
    if not Path(args.input).exists():
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)
    
    try:
        # Initialize processor
        logger.info("Initializing Book Processor...")
        processor = BookProcessor(
            gemini_api_key=api_key,
            gemini_model=os.getenv('GEMINI_MODEL', 'gemini-1.5-flash-latest'),
            cache_dir=args.cache_dir,
            dpi=args.dpi,
            image_quality=args.image_quality
        )
        
        # Test API connection
        logger.info("Testing Gemini API connection...")
        if not processor.gemini_client.test_connection():
            logger.error("Failed to connect to Gemini API. Check your API key.")
            sys.exit(1)
        logger.info("✓ API connection successful")
        
        # Process the book
        stats = processor.process_book(
            pdf_path=args.input,
            output_path=args.output,
            start_page=args.start_page,
            end_page=args.end_page,
            resume=args.resume and not args.no_cache
        )
        
        logger.info("✓ Processing completed successfully!")
        logger.info(f"Output saved to: {args.output}")
        
        # Success
        sys.exit(0)
        
    except KeyboardInterrupt:
        logger.warning("\n✗ Processing interrupted by user")
        logger.info("Progress has been saved. Use --resume to continue.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"✗ Processing failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()