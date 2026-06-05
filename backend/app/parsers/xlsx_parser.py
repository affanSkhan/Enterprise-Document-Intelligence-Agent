import openpyxl
from .base_parser import BaseParser

class XlsxParser(BaseParser):
    def parse(self, file_path: str) -> str:
        text = ""
        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            for sheet in wb.worksheets:
                text += f"\n--- Sheet: {sheet.title} ---\n"
                for row in sheet.iter_rows(values_only=True):
                    row_text = "\t".join([str(cell) if cell is not None else "" for cell in row])
                    if row_text.strip():
                        text += row_text + "\n"
        except Exception as e:
            print(f"Error parsing XLSX {file_path}: {e}")
        return text
