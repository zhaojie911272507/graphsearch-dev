# Test business files

Binary samples under this directory are **valid** PDF (fpdf2 stubs) and DOCX (python-docx) used for upload and parsing tests.

- **PDFs**: Extracted text is short English boilerplate; full Chinese narrative used in development lives in `sources/<same basename>.txt`.
- **DOCX**: `SOP_001_*.docx` contains the full UTF-8 narrative inline (OOXML).

To rebuild PDFs and the SOP docx from UTF-8 placeholders (if you replace them with text fixtures again):

```bash
pip install -r requirements.txt
python scripts/build_test_business_fixtures.py
```
