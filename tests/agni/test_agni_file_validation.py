"""
Property-based tests for Agni file validation.

Tests file type validation using property-based testing to ensure
the system correctly accepts and rejects file types.
"""

import pytest
from hypothesis import given, strategies as st

from agni.utils import validate_file_type


class TestFileTypeValidation:
    """Property-based tests for file type validation."""
    
    @given(st.sampled_from(['.txt', '.md', '.doc', '.docx', '.pdf']))
    def test_valid_file_extensions_are_accepted(self, extension):
        """
        **Property 1: File Type Validation**
        *For any* file upload, the system SHALL accept only files with extensions in {.txt, .md, .doc, .docx, .pdf} and reject all others
        **Validates: Requirements 1.2**
        """
        # Create a filename with valid extension
        filename = f"test_document{extension}"
        
        # Validation should pass for valid extensions
        result = validate_file_type(filename)
        assert result is True, f"Valid extension {extension} should be accepted"
    
    @given(st.sampled_from(['.exe', '.jpg', '.png', '.zip', '.rar', '.mp4', '.avi', '.html', '.css', '.js']))
    def test_invalid_file_extensions_are_rejected(self, invalid_extension):
        """
        **Property 1: File Type Validation**
        *For any* file upload, the system SHALL accept only files with extensions in {.txt, .md, .doc, .docx, .pdf} and reject all others
        **Validates: Requirements 1.2**
        """
        # Create a filename with invalid extension
        filename = f"test_document{invalid_extension}"
        
        # Validation should fail for invalid extensions
        result = validate_file_type(filename)
        assert result is False, f"Invalid extension {invalid_extension} should be rejected"
    
    @given(st.sampled_from(['', 'no_extension', 'file.', '.']))
    def test_files_without_valid_extensions_are_rejected(self, invalid_filename):
        """
        **Property 1: File Type Validation**
        *For any* file upload, the system SHALL accept only files with extensions in {.txt, .md, .doc, .docx, .pdf} and reject all others
        **Validates: Requirements 1.2**
        """
        # Files without proper extensions should be rejected
        result = validate_file_type(invalid_filename)
        assert result is False, f"File without valid extension '{invalid_filename}' should be rejected"
    
    @given(st.sampled_from(['.TXT', '.MD', '.DOC', '.DOCX', '.PDF']))
    def test_uppercase_extensions_are_accepted(self, uppercase_extension):
        """
        **Property 1: File Type Validation**
        *For any* file upload, the system SHALL accept only files with extensions in {.txt, .md, .doc, .docx, .pdf} and reject all others
        **Validates: Requirements 1.2**
        """
        # Create a filename with uppercase extension
        filename = f"test_document{uppercase_extension}"
        
        # Validation should pass for uppercase extensions (case insensitive)
        result = validate_file_type(filename)
        assert result is True, f"Uppercase extension {uppercase_extension} should be accepted"