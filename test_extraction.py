#!/usr/bin/env python3
"""
Test file for the RFQ Data Extraction Service.
This file tests the basic functionality without requiring actual files or LLM modules.
"""

import json
import sys
import os

# Test only the functions that don't require external modules
def test_text_cleaning():
    """Test the text cleaning functionality."""
    print("Testing text cleaning...")
    
    # Sample text with common document artifacts
    sample_text = """
    Page 1 of 5
    
    This is a sample RFQ document with    excessive   whitespace.
    
    It contains special characters: @#$%^&*()_+{}|:"<>?[]\\|;'",./<>?
    
    Page 2 of 5
    
    More RFQ content here...
    """
    
    # Import here to avoid module import errors
    try:
        from services.aksum_services import clean_text
        cleaned = clean_text(sample_text)
        
        print("Original text:")
        print(repr(sample_text))
        print("\nCleaned text:")
        print(repr(cleaned))
        
        # Verify cleaning worked
        assert "Page 1 of 5" not in cleaned
        assert "Page 2 of 5" not in cleaned
        assert "   excessive   " not in cleaned
        assert "@#$%^&*()_+{}|:\"<>?[]\\|;'\",./<>?" not in cleaned
        
        print("✓ Text cleaning test passed!")
        return True
        
    except ImportError as e:
        print(f"✗ Cannot import clean_text function: {e}")
        return False
    except Exception as e:
        print(f"✗ Text cleaning test failed: {e}")
        return False

def test_prompt_creation():
    """Test the RFQ extraction prompt creation."""
    print("\nTesting RFQ prompt creation...")
    
    sample_text = "AKSUM Trademart Pvt Ltd is requesting quotations for IT services project."
    
    try:
        from services.aksum_services import create_extraction_prompt
        prompt = create_extraction_prompt(sample_text)
        
        print("Generated prompt:")
        print("=" * 50)
        print(prompt)
        print("=" * 50)
        
        # Verify prompt contains required elements
        assert "RFQ (Request for Quotation)" in prompt
        assert "TEXT TO ANALYZE:" in prompt
        assert "INSTRUCTIONS:" in prompt
        assert "AKSUM Trademart" in prompt
        assert "rfq_number" in prompt
        assert "company_name" in prompt
        
        print("✓ RFQ prompt creation test passed!")
        return True
        
    except ImportError as e:
        print(f"✗ Cannot import create_extraction_prompt function: {e}")
        return False
    except Exception as e:
        print(f"✗ RFQ prompt creation test failed: {e}")
        return False

def test_txt_extraction():
    """Test TXT file text extraction."""
    print("\nTesting TXT file extraction...")
    
    # Create a temporary test file
    test_content = "This is a test RFQ document.\nIt contains multiple lines.\nCompany: Test Corp"
    
    try:
        from services.aksum_services import extract_text_from_txt
        
        # Test with a temporary file
        with open("test_rfq.txt", "w", encoding="utf-8") as f:
            f.write(test_content)
        
        # Extract text
        extracted_text = extract_text_from_txt("test_rfq.txt")
        
        # Verify extraction
        assert "This is a test RFQ document" in extracted_text
        assert "Company: Test Corp" in extracted_text
        
        print("✓ TXT extraction test passed!")
        
        # Clean up
        os.remove("test_rfq.txt")
        return True
        
    except ImportError as e:
        print(f"✗ Cannot import extract_text_from_txt function: {e}")
        return False
    except Exception as e:
        print(f"✗ TXT extraction test failed: {e}")
        return False

def test_json_parsing():
    """Test JSON parsing functionality."""
    print("\nTesting JSON parsing...")
    
    # Test valid JSON
    valid_json = '{"rfq_number": "RFQ001", "company_name": "Test Corp"}'
    try:
        parsed = json.loads(valid_json)
        assert parsed["rfq_number"] == "RFQ001"
        assert parsed["company_name"] == "Test Corp"
        print("✓ Valid JSON parsing test passed!")
    except Exception as e:
        print(f"✗ Valid JSON parsing test failed: {e}")
        return False
    
    # Test invalid JSON
    invalid_json = '{"rfq_number": "RFQ001", "company_name": "Test Corp"'  # Missing closing brace
    try:
        json.loads(invalid_json)
        print("✗ Invalid JSON parsing test failed - should have raised an error")
        return False
    except json.JSONDecodeError:
        print("✓ Invalid JSON parsing test passed!")
    
    return True

def test_file_format_detection():
    """Test file format detection logic."""
    print("\nTesting file format detection...")
    
    try:
        # Test with sample file paths
        test_paths = [
            "document.pdf",
            "document.doc", 
            "document.docx",
            "document.txt",
            "document.unknown"
        ]
        
        expected_extensions = ['.pdf', '.doc', '.docx', '.txt', '.unknown']
        
        for i, path in enumerate(test_paths):
            detected_extension = os.path.splitext(path)[1].lower()
            expected = expected_extensions[i]
            
            assert detected_extension == expected, f"Expected {expected}, got {detected_extension}"
        
        print("✓ File format detection test passed!")
        return True
        
    except Exception as e:
        print(f"✗ File format detection test failed: {e}")
        return False

def run_all_tests():
    """Run all tests."""
    print("Running RFQ Extraction Service Tests")
    print("=" * 40)
    
    tests = [
        test_text_cleaning,
        test_prompt_creation,
        test_txt_extraction,
        test_json_parsing,
        test_file_format_detection
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with error: {e}")
    
    print(f"\n" + "=" * 40)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed!")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
