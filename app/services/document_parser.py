"""Document parsing service for various file formats.

Supports PDF, DOCX, and TXT file parsing with error handling.
"""

import logging
import os
import re
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from docx import Document

from app.exceptions import GraphRAGError

logger = logging.getLogger(__name__)


def _content_looks_like_plain_utf8_text(content: bytes) -> bool:
    """Return True if bytes look like UTF-8 prose, not PDF/DOCX binary."""
    if len(content) < 32:
        return False
    if content.startswith(b"%PDF-") or content.startswith(b"PK\x03\x04"):
        return False
    body = content[3:] if content.startswith(b"\xef\xbb\xbf") else content
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return False
    sample = text[:2000]
    if not sample.strip():
        return False
    printable = sum(1 for c in sample if c.isprintable() or c in "\n\r\t\u3000")
    return printable / len(sample) > 0.88


def _utf8_text_mismatch_hint(content: bytes) -> str:
    if not _content_looks_like_plain_utf8_text(content):
        return ""
    return (
        " Content appears to be UTF-8 text, not this binary format "
        "(often a misnamed .txt file or a placeholder). Use a real export or rename to .txt."
    )


class DocumentParseError(GraphRAGError):
    """Raised when document parsing fails."""
    pass


class DocumentParser:
    """Service for parsing documents in various formats."""

    SUPPORTED_FORMATS = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.txt': 'text/plain',
    }

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

    @classmethod
    def detect_file_type(cls, filename: str) -> str:
        """Detect file type from filename extension.

        Args:
            filename: Name of the file

        Returns:
            MIME type string

        Raises:
            DocumentParseError: If file type is not supported
        """
        ext = Path(filename).suffix.lower()
        if ext not in cls.SUPPORTED_FORMATS:
            raise DocumentParseError(
                message=f"Unsupported file type: {ext}. Supported types: {', '.join(cls.SUPPORTED_FORMATS.keys())}"
            )
        return cls.SUPPORTED_FORMATS[ext]

    @classmethod
    def parse_pdf(cls, file_content: bytes) -> tuple[str, dict[str, Any]]:
        """Parse PDF file and extract text.

        Args:
            file_content: Raw PDF file bytes

        Returns:
            Tuple of (extracted_text, metadata_dict)

        Raises:
            DocumentParseError: If parsing fails
        """
        try:
            # Validate PDF magic number
            if not file_content.startswith(b"%PDF-"):
                raise DocumentParseError(
                    message=(
                        "Invalid PDF file: missing PDF magic number."
                        + _utf8_text_mismatch_hint(file_content)
                    )
                )

            if len(file_content) < 100:
                raise DocumentParseError(message="PDF file is too small, possibly corrupted")

            # Try pdfplumber first (better text extraction)
            try:
                import pdfplumber

                with pdfplumber.open(BytesIO(file_content)) as pdf:
                    text = ""
                    metadata = {}
                    if pdf.metadata:
                        metadata = {
                            'title': pdf.metadata.get('Title', ''),
                            'author': pdf.metadata.get('Author', ''),
                            'creator': pdf.metadata.get('Creator', ''),
                            'producer': pdf.metadata.get('Producer', ''),
                            'subject': pdf.metadata.get('Subject', ''),
                        }
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                    if not text.strip():
                        logger.warning("PDF extracted text is empty")
                    return cls._clean_text(text), metadata
            except ImportError:
                # Fall back to PyPDF2
                from PyPDF2 import PdfReader

                reader = PdfReader(BytesIO(file_content))
                text = ""
                metadata = {}
                if reader.metadata:
                    metadata = {
                        'title': reader.metadata.get('/Title', ''),
                        'author': reader.metadata.get('/Author', ''),
                        'creator': reader.metadata.get('/Creator', ''),
                        'producer': reader.metadata.get('/Producer', ''),
                        'subject': reader.metadata.get('/Subject', ''),
                    }
                for page in reader.pages:
                    text += page.extract_text() or ""
                if not text.strip():
                    logger.warning("PDF extracted text is empty")
                return cls._clean_text(text), metadata

        except DocumentParseError:
            raise
        except Exception as e:
            logger.error("Failed to parse PDF: %s", e, exc_info=True)
            error_msg = str(e)
            if "No /Root object" in error_msg or "not a pdf" in error_msg.lower():
                error_msg = "Invalid or corrupted PDF file - ensure the file is a valid PDF document"
            raise DocumentParseError(message=f"PDF parsing failed: {error_msg}") from e

    @classmethod
    def parse_docx(cls, file_content: bytes) -> tuple[str, dict[str, Any]]:
        """Parse DOCX file and extract text.

        Args:
            file_content: Raw DOCX file bytes

        Returns:
            Tuple of (extracted_text, metadata_dict)

        Raises:
            DocumentParseError: If parsing fails
        """
        try:
            # Validate file size
            if len(file_content) < 100:
                raise DocumentParseError(message="DOCX file is too small, possibly corrupted")

            if not zipfile.is_zipfile(BytesIO(file_content)):
                raise DocumentParseError(
                    message=(
                        "Invalid DOCX file: not a ZIP/OOXML (Word) package."
                        + _utf8_text_mismatch_hint(file_content)
                    )
                )

            # DOCX files are ZIP archives, so python-docx needs a file path
            # Write bytes to temporary file and ensure it's fully written
            tmp_path = None
            try:
                # Create temp file, write content, and close it properly
                with tempfile.NamedTemporaryFile(delete=False, suffix='.docx', mode='wb') as tmp:
                    tmp.write(file_content)
                    tmp.flush()
                    os.fsync(tmp.fileno())  # Ensure data is written to disk
                    tmp_path = tmp.name

                # Verify file exists and has content
                if not os.path.exists(tmp_path):
                    raise DocumentParseError(message="Temporary file creation failed")

                file_size = os.path.getsize(tmp_path)
                if file_size != len(file_content):
                    raise DocumentParseError(
                        message=f"File size mismatch: expected {len(file_content)}, got {file_size}"
                    )

                # Parse the document
                doc = Document(tmp_path)
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs])

                # Extract core properties
                core_props = doc.core_properties
                metadata = {
                    'title': core_props.title or '',
                    'author': core_props.author or '',
                    'created': str(core_props.created) if core_props.created else '',
                    'modified': str(core_props.modified) if core_props.modified else '',
                    'subject': core_props.subject or '',
                    'keywords': core_props.keywords or '',
                }

                return cls._clean_text(text), metadata

            finally:
                # Clean up temporary file
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except Exception as cleanup_error:
                        logger.warning("Failed to cleanup temp file: %s", cleanup_error)

        except DocumentParseError:
            raise
        except Exception as e:
            logger.error("Failed to parse DOCX: %s", e, exc_info=True)
            error_msg = str(e)
            if "Package not found" in error_msg or "not a zip file" in error_msg.lower():
                error_msg = "Invalid or corrupted DOCX file - ensure the file is a valid Word document"
            raise DocumentParseError(message=f"DOCX parsing failed: {error_msg}") from e

    @classmethod
    def parse_txt(cls, file_content: bytes) -> tuple[str, dict[str, Any]]:
        """Parse TXT file and extract text.

        Args:
            file_content: Raw TXT file bytes

        Returns:
            Tuple of (extracted_text, metadata_dict)
        """
        try:
            # Try common encodings
            for encoding in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                try:
                    text = file_content.decode(encoding)
                    return cls._clean_text(text), {}
                except UnicodeDecodeError:
                    continue

            # If all encodings fail, use utf-8 with error handling
            text = file_content.decode('utf-8', errors='ignore')
            return cls._clean_text(text), {}

        except Exception as e:
            logger.error("Failed to parse TXT: %s", e)
            raise DocumentParseError(message=f"TXT parsing failed: {str(e)}") from e

    @classmethod
    def _clean_text(cls, text: str) -> str:
        """Clean extracted text.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text

    @classmethod
    def parse_document(cls, filename: str, file_content: bytes) -> tuple[str, dict[str, Any], str]:
        """Parse document based on file type.

        Args:
            filename: Name of the file
            file_content: Raw file bytes

        Returns:
            Tuple of (extracted_text, metadata_dict, file_type)

        Raises:
            DocumentParseError: If parsing fails or file type is unsupported
        """
        # Validate file size
        if len(file_content) > cls.MAX_FILE_SIZE:
            raise DocumentParseError(
                message=f"File size {len(file_content)} bytes exceeds maximum {cls.MAX_FILE_SIZE} bytes"
            )

        # Detect file type
        file_type = cls.detect_file_type(filename)

        # Parse based on file type
        if file_type == 'application/pdf':
            text, metadata = cls.parse_pdf(file_content)
        elif file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            text, metadata = cls.parse_docx(file_content)
        elif file_type == 'text/plain':
            text, metadata = cls.parse_txt(file_content)
        else:
            raise DocumentParseError(message=f"Unsupported file type: {file_type}")

        if not text or len(text.strip()) < 10:
            raise DocumentParseError(message="Extracted text is empty or too short")

        return text, metadata, file_type

    @classmethod
    def validate_file(cls, filename: str, file_size: int) -> None:
        """Validate file before parsing.

        Args:
            filename: Name of the file
            file_size: Size of the file in bytes

        Raises:
            DocumentParseError: If validation fails
        """
        # Check file type
        try:
            cls.detect_file_type(filename)
        except DocumentParseError as e:
            raise e

        # Check file size
        if file_size > cls.MAX_FILE_SIZE:
            raise DocumentParseError(
                message=f"File size {file_size} bytes exceeds maximum {cls.MAX_FILE_SIZE} bytes"
            )

        # Check minimum file size
        if file_size < 10:  # Minimum 10 bytes
            raise DocumentParseError(message="File is too small")
