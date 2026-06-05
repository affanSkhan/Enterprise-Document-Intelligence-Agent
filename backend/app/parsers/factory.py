import os
from .pdf_parser import PDFParser
from .docx_parser import DocxParser
from .pptx_parser import PptxParser
from .xlsx_parser import XlsxParser

def get_parser(file_path: str):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return PDFParser()
    elif ext == ".docx":
        return DocxParser()
    elif ext == ".pptx":
        return PptxParser()
    elif ext in [".xlsx", ".xls"]:
        return XlsxParser()
    elif ext in [".txt", ".csv"]:
        class TxtParser:
            def parse(self, file_path: str) -> str:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
        return TxtParser()
    else:
        raise ValueError(f"Unsupported file extension: {ext}")
