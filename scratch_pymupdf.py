import fitz
import sys

def test():
    pdf_path = "patient_intake_reportCLD.pdf"
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return
        
    for page in doc:
        print("--- PAGE ---")
        tables = page.find_tables()
        print(f"Tables: {len(tables.tables)}")
        for table in tables.tables:
            print("Table bbox:", table.bbox)
            print("Table content:", table.extract())
        
        # Test get_text
        print("\nText with sort=True:")
        text = page.get_text(sort=True)
        print("unspecified2024-10-04" in text)

if __name__ == "__main__":
    test()
