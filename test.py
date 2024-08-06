import pymupdf

def extract_paragraphs_excluding_headers(pdf_path, spacing_threshold=10, font_size_threshold=14, header_y_threshold=100, min_paragraph_length=20):
    doc = pymupdf.open(pdf_path)
    pdf_content = {}

    for page_number, page in enumerate(doc, start=1):
        text_dict = page.get_text("dict")
        blocks = text_dict['blocks']
        
        paragraphs = []
        current_paragraph = []
        previous_bottom = None

        for block in blocks:
            # Only process text blocks
            if 'lines' not in block:
                continue

            for line in block['lines']:
                for span in line['spans']:
                    top = span['bbox'][1]
                    bottom = span['bbox'][3]
                    text = span['text']
                    font_size = span['size']

                    # Exclude blocks that are likely headers based on font size, position, and length
                    if (font_size > font_size_threshold and top < header_y_threshold) or len(text.strip()) < min_paragraph_length:
                        continue

                    if previous_bottom is not None and (top - previous_bottom) > spacing_threshold:
                        if len(" ".join(current_paragraph).strip()) >= min_paragraph_length:
                            paragraphs.append(" ".join(current_paragraph).strip())
                        current_paragraph = []

                    current_paragraph.append(text)
                    previous_bottom = bottom

        if current_paragraph and len(" ".join(current_paragraph).strip()) >= min_paragraph_length:
            paragraphs.append(" ".join(current_paragraph).strip())

        pdf_content[page_number] = paragraphs

    return pdf_content

def main():
    pdf_path = "test.pdf"
    pdf_content = extract_paragraphs_excluding_headers(pdf_path)
    
    # Print the extracted pages and paragraphs
    for page_num, paragraphs in pdf_content.items():
        print(f"Page {page_num}:")
        for i, paragraph in enumerate(paragraphs):
            print(f"  Paragraph {i + 1}: {paragraph}")
        print()

if __name__ == "__main__":
    main()

