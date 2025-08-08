#!/usr/bin/env python3

import fitz
from pdf_analyzer_focused import PDFFormAnalyzerFocused

def test_pdf_detection():
    # Test with the W9 form that has 23+ fields
    pdf_path = "attached_assets/CPM_W9_1754516338906.pdf"
    
    try:
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        print(f"Testing PDF: {pdf_path}")
        print(f"File size: {len(pdf_bytes)} bytes")
        
        # Test raw PyMuPDF detection
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = pdf_doc[0]
        widgets = list(page.widgets())
        print(f"Raw PyMuPDF finds {len(widgets)} widgets on page 1")
        
        # Test our analyzer
        analyzer = PDFFormAnalyzerFocused()
        result = analyzer.analyze_pdf(pdf_bytes)
        
        if result["success"]:
            print(f"Our analyzer found {len(result['fields'])} fields total")
            for i, field in enumerate(result['fields'][:10]):  # Show first 10
                print(f"  {i+1}. {field['name']} ({field['type']}) - Page {field['page']}")
        else:
            print(f"Analyzer failed: {result.get('error')}")
        
        pdf_doc.close()
        
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_pdf_detection()