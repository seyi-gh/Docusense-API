from markitdown import MarkItDown
import io
import pdfplumber

md = MarkItDown(enable_plugins=False)

def extract_text(file_bytes: bytes) -> str:
  file_like = io.BytesIO(file_bytes)

  # First try markitdown for broad format handling.
  try:
    result = md.convert_stream(file_like, file_extension='.pdf')
    text = (result.text_content or '').strip()
    if text:
      return text
  except Exception:
    pass

  # Fallback for PDFs that markitdown cannot parse reliably.
  with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
    pages = [(page.extract_text() or '') for page in pdf.pages]
  return '\n'.join(pages)