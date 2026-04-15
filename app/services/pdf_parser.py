from markitdown import MarkItDown
import io

md = MarkItDown(enable_plugins=False)

def extract_text(file_bytes: bytes) -> str:
  file_like = io.BytesIO(file_bytes)
  result = md.convert_stream(file_like, file_extension='.pdf')
  return result.text_content