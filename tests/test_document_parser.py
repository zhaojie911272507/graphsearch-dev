"""DocumentParser format validation and UTF-8 mismatch hints."""

import pytest

from app.services.document_parser import DocumentParseError, DocumentParser


def test_parse_pdf_rejects_utf8_text_with_hint() -> None:
    fake = "这是假装成 PDF 的纯文本。\n第二行。".encode()
    with pytest.raises(DocumentParseError) as exc_info:
        DocumentParser.parse_pdf(fake)
    assert "magic number" in exc_info.value.message
    assert "UTF-8 text" in exc_info.value.message


def test_parse_docx_rejects_utf8_text_with_hint() -> None:
    fake = "假装是 docx 的纯文本内容。\n" * 20
    with pytest.raises(DocumentParseError) as exc_info:
        DocumentParser.parse_docx(fake.encode("utf-8"))
    assert "ZIP/OOXML" in exc_info.value.message
    assert "UTF-8 text" in exc_info.value.message
