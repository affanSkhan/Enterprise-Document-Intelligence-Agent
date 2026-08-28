import pymupdf

from .base_parser import BaseParser


class PDFParser(BaseParser):
    def parse(self, file_path: str) -> str:
        text = ""
        try:
            doc = pymupdf.open(file_path)
            try:
                for page_num, page in enumerate(doc):
                    page_text = page.get_text()
                    text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
            finally:
                doc.close()
        except Exception as exc:
            raise ValueError(f"Error parsing PDF {file_path}: {exc}") from exc
        return text
