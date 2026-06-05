import docx
from .base_parser import BaseParser

class DocxParser(BaseParser):
    def parse(self, file_path: str) -> str:
        text = ""
        try:
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                if para.text.strip():
                    text += para.text + "\n"
        except Exception as e:
            print(f"Error parsing DOCX {file_path}: {e}")
        return text
