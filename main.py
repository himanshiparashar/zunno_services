#!/usr/bin/env python3
"""
Main application for RFQ data extraction using LLM.
This service extracts RFQ data from PDF, DOC, and TXT files and returns it in JSON format.
"""

import json
import argparse
import sys
from pathlib import Path
from services.aksum_services import extract_aksum_data_from_RFQ

def main():
    """Main function to handle command line arguments and execute RFQ extraction."""
    parser = argparse.ArgumentParser(
        description="Extract RFQ data from PDF, DOC, and TXT files using LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract RFQ data from PDF (output is pretty-printed by default)
  python main.py /path/to/rfq.pdf
  
  # Extract RFQ data from DOC file
  python main.py /path/to/rfq.doc
  
  # Extract RFQ data from TXT file
  python main.py /path/to/rfq.txt
  
  # Save results to file with pretty formatting
  python main.py /path/to/rfq.pdf --output results.json --pretty
        """
    )
    
    parser.add_argument(
        "file_path", 
        type=str, 
        help="Path to the RFQ file (PDF, DOC, or TXT)"
    )
    
    parser.add_argument(
        "--output", 
        type=str, 
        help="Output file for JSON results (default: stdout)"
    )
    
    parser.add_argument(
        "--pretty", 
        action="store_true",
        help="Pretty print JSON output (output is always pretty-printed by default)"
    )
    
    args = parser.parse_args()
    
    # Check if file exists
    if not Path(args.file_path).exists():
        print(f"Error: File not found: {args.file_path}")
        sys.exit(1)
    
    # Check file extension
    file_extension = Path(args.file_path).suffix.lower()
    if file_extension not in ['.pdf', '.doc', '.docx', '.txt']:
        print(f"Error: Unsupported file format: {file_extension}")
        print("Supported formats: PDF, DOC, DOCX, TXT")
        sys.exit(1)
    
    try:
        # Extract RFQ data
        result = extract_aksum_data_from_RFQ(args.file_path)
        output_result(result, args.output, args.pretty)
        
    except Exception as e:
        print(f"Error extracting RFQ data: {e}")
        sys.exit(1)

def output_result(result: dict, output_file: str = None, pretty: bool = False):
    """Output the extraction result to file or stdout."""
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(result, f, indent=2, ensure_ascii=False)
            else:
                json.dump(result, f, ensure_ascii=False)
        print(f"Results saved to: {output_file}")
    else:
        # Always pretty print to stdout for better readability
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
