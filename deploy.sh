#!/bin/bash

# Book OCR Deployment Script
# This script sets up and runs the Book OCR system

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Setup function
setup() {
    log_info "Setting up Book OCR..."
    
    # Create necessary directories
    mkdir -p input output cache logs
    log_info "Created directories: input, output, cache, logs"
    
    # Check if .env exists
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            log_warn ".env file created from .env.example"
            log_warn "Please edit .env and add your GEMINI_API_KEY"
            exit 1
        else
            log_error ".env.example not found"
            exit 1
        fi
    fi
    
    # Check for API key
    if grep -q "your_api_key_here" .env; then
        log_error "Please set your GEMINI_API_KEY in .env file"
        exit 1
    fi
    
    log_info "✓ Setup complete"
}

# Docker deployment
deploy_docker() {
    log_info "Deploying with Docker..."
    
    if ! command_exists docker; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Build image
    log_info "Building Docker image..."
    docker-compose build
    
    log_info "✓ Docker image built successfully"
    log_info "Ready to process books!"
    echo ""
    echo "Usage:"
    echo "  docker-compose run --rm book-ocr -i /app/input/your-book.pdf -o /app/output/output.md"
}

# Local deployment
deploy_local() {
    log_info "Setting up local environment..."
    
    # Check Python
    if ! command_exists python3; then
        log_error "Python 3 is not installed"
        exit 1
    fi
    
    # Check Tesseract
    if ! command_exists tesseract; then
        log_warn "Tesseract OCR is not installed"
        log_info "Install it with:"
        log_info "  macOS: brew install tesseract poppler"
        log_info "  Ubuntu: sudo apt-get install tesseract-ocr poppler-utils"
        exit 1
    fi
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate and install dependencies
    log_info "Installing dependencies..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    log_info "✓ Local environment ready"
    log_info "Activate with: source venv/bin/activate"
    log_info "Run with: python main.py -i input/book.pdf -o output/book.md"
}

# Run tests
run_tests() {
    log_info "Running tests..."
    
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    python -m pytest tests/ -v || python tests/test_processor.py
    
    log_info "✓ Tests complete"
}

# Process a book (convenience function)
process_book() {
    local input_file="$1"
    local output_file="$2"
    
    if [ -z "$input_file" ] || [ -z "$output_file" ]; then
        log_error "Usage: ./deploy.sh process <input.pdf> <output.md>"
        exit 1
    fi
    
    if [ ! -f "$input_file" ]; then
        log_error "Input file not found: $input_file"
        exit 1
    fi
    
    log_info "Processing: $input_file → $output_file"
    
    # Check if Docker or local
    if command_exists docker && [ -f "docker-compose.yml" ]; then
        # Copy file to input directory
        cp "$input_file" input/
        filename=$(basename "$input_file")
        
        docker-compose run --rm book-ocr \
            -i "/app/input/$filename" \
            -o "/app/output/$(basename "$output_file")"
        
        # Copy result back
        cp "output/$(basename "$output_file")" "$output_file"
        
    else
        # Local execution
        if [ -d "venv" ]; then
            source venv/bin/activate
        fi
        
        python main.py -i "$input_file" -o "$output_file"
    fi
    
    log_info "✓ Processing complete: $output_file"
}

# Clean cache
clean_cache() {
    log_info "Cleaning cache..."
    rm -rf cache/*
    rm -rf output/*
    log_info "✓ Cache cleaned"
}

# Show help
show_help() {
    cat << EOF
Book OCR Deployment Script

Usage: ./deploy.sh [command]

Commands:
    setup           Initialize directories and configuration
    docker          Build and deploy with Docker
    local           Setup local Python environment
    test            Run tests
    process         Process a book (usage: ./deploy.sh process input.pdf output.md)
    clean           Clean cache and output directories
    help            Show this help message

Examples:
    # Initial setup
    ./deploy.sh setup
    
    # Deploy with Docker
    ./deploy.sh docker
    
    # Deploy locally
    ./deploy.sh local
    
    # Process a book
    ./deploy.sh process my-book.pdf my-book.md
    
    # Run tests
    ./deploy.sh test

EOF
}

# Main script logic
main() {
    local command="${1:-help}"
    
    case "$command" in
        setup)
            setup
            ;;
        docker)
            setup
            deploy_docker
            ;;
        local)
            setup
            deploy_local
            ;;
        test)
            run_tests
            ;;
        process)
            process_book "$2" "$3"
            ;;
        clean)
            clean_cache
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"