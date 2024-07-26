import pymupdf  # PyMuPDF

def extract_pages_and_paragraphs(pdf_path):
    # Open the PDF file
    doc = pymupdf.open(pdf_path)
    
    # Initialize a dictionary to hold the pages and paragraphs
    pdf_content = {}
    
    # Iterate through each page
    for page_num in range(len(doc)):
        # Load the page
        page = doc.load_page(page_num)
        
        # Extract text from the page
        text = page.get_text("text")
        
        # Split the text into paragraphs
        paragraphs = text.split("\n\n")
        
        # Store the paragraphs in the dictionary
        pdf_content[page_num + 1] = paragraphs
    
    return pdf_content

def main():
    pdf_path = "test.pdf"
    pdf_content = extract_pages_and_paragraphs(pdf_path)
    
    # Print the extracted pages and paragraphs
    for page_num, paragraphs in pdf_content.items():
        print(f"Page {page_num}:")
        for i, paragraph in enumerate(paragraphs):
            print(f"  Paragraph {i + 1}: {paragraph}")
        print()

if __name__ == "__main__":
    main()

