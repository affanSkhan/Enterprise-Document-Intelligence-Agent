import fitz # PyMuPDF
from .base_parser import BaseParser

class PDFParser(BaseParser):
    def parse(self, file_path: str) -> str:
        text = ""
        try:
            doc = fitz.open(file_path)
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                # Store page number explicitly for chunking later if needed
                text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
        except Exception as e:
            print(f"Error parsing PDF {file_path}: {e}")
        return text
