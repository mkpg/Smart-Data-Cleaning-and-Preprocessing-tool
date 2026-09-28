import fitz

def test():
    pdf_path = "patient_intake_reportCLD.pdf"
    doc = fitz.open(pdf_path)
    for page in doc:
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: (b[1], b[0]))
        text = "\n".join([b[4] for b in blocks if len(b) >= 5])
        print("Blocks output:")
        print("unspecified2024-10-04" in text)
        print("unspecified 2024-10-04" in text)

if __name__ == "__main__":
    test()
