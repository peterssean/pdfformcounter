import PyPDF2
import io
from typing import Dict, List, Any, Optional
import fitz  # PyMuPDF

class PDFFormAnalyzerDebug:
    """
    Enhanced PDF Form Analyzer with comprehensive field detection.
    """
    
    def __init__(self):
        self.field_type_mapping = {
            '/Tx': 'Text Field',
            '/Btn': 'Button/Checkbox/Radio',
            '/Ch': 'Choice/Dropdown',
            '/Sig': 'Signature Field'
        }
    
    def analyze_pdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Analyze a PDF file using multiple detection methods.
        """
        try:
            fields = []
            
            # Method 1: PyPDF2 AcroForm extraction
            pypdf2_fields = self._extract_with_pypdf2(pdf_bytes)
            print(f"PyPDF2 found {len(pypdf2_fields)} fields")
            fields.extend(pypdf2_fields)
            
            # Method 2: PyMuPDF extraction
            pymupdf_fields = self._extract_with_pymupdf(pdf_bytes)
            print(f"PyMuPDF found {len(pymupdf_fields)} fields")
            
            # Merge without duplicates
            existing_names = {f.get("name", "") for f in fields}
            for field in pymupdf_fields:
                if field.get("name", "") not in existing_names:
                    fields.append(field)
            
            # Method 3: Annotation scanning
            annotation_fields = self._extract_annotations(pdf_bytes)
            print(f"Annotation scanning found {len(annotation_fields)} fields")
            
            # Merge annotation fields
            for field in annotation_fields:
                field_name = field.get("name", "")
                if field_name and field_name not in existing_names:
                    fields.append(field)
                    existing_names.add(field_name)
            
            return {
                "success": True,
                "fields": fields,
                "message": f"Found {len(fields)} form fields using enhanced detection"
            }
            
        except Exception as e:
            return {
                "success": False,
                "fields": [],
                "error": str(e)
            }
    
    def _extract_with_pypdf2(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """Extract fields using PyPDF2."""
        fields = []
        try:
            pdf_stream = io.BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            
            # Check for AcroForm
            root_obj = pdf_reader.trailer.get("/Root")
            if not root_obj or "/AcroForm" not in root_obj:
                return fields
            
            acro_form = root_obj["/AcroForm"]
            if "/Fields" not in acro_form:
                return fields
            
            form_fields = acro_form["/Fields"]
            for i, field_ref in enumerate(form_fields):
                try:
                    field_obj = field_ref.get_object()
                    self._process_field_recursive(field_obj, fields, f"pypdf2_field_{i}")
                except Exception as e:
                    print(f"Error processing field {i}: {e}")
                    continue
                    
        except Exception as e:
            print(f"PyPDF2 extraction error: {e}")
        
        return fields
    
    def _process_field_recursive(self, field_obj: Any, fields: List[Dict[str, Any]], fallback_name: str):
        """Process field recursively to handle nested structures."""
        try:
            # Parse current field
            field_info = self._parse_field_pypdf2(field_obj, fallback_name)
            if field_info:
                fields.append(field_info)
            
            # Process kids
            if "/Kids" in field_obj:
                kids = field_obj["/Kids"]
                for j, kid_ref in enumerate(kids):
                    try:
                        kid_obj = kid_ref.get_object()
                        kid_name = f"{fallback_name}_kid_{j}"
                        self._process_field_recursive(kid_obj, fields, kid_name)
                    except:
                        continue
                        
        except Exception as e:
            print(f"Recursive processing error: {e}")
    
    def _parse_field_pypdf2(self, field_obj: Any, fallback_name: str) -> Optional[Dict[str, Any]]:
        """Parse a field object using PyPDF2."""
        try:
            field_info = {}
            
            # Get name
            name = fallback_name
            if "/T" in field_obj:
                name = str(field_obj["/T"]) or fallback_name
            field_info["name"] = name
            
            # Get type
            field_type = "Unknown"
            if "/FT" in field_obj:
                ft = str(field_obj["/FT"])
                field_type = self.field_type_mapping.get(ft, ft)
            field_info["type"] = field_type
            
            # Get other properties
            field_info["required"] = "/Ff" in field_obj and bool(field_obj.get("/Ff", 0) & 2)
            field_info["page"] = 1  # Default to page 1
            
            # Try to get value
            if "/V" in field_obj:
                field_info["default_value"] = str(field_obj["/V"])
            
            return field_info
            
        except Exception as e:
            print(f"Field parsing error: {e}")
            return None
    
    def _extract_with_pymupdf(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """Extract fields using PyMuPDF."""
        fields = []
        try:
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                widgets = page.widgets()
                
                for i, widget in enumerate(widgets):
                    try:
                        field_info = {
                            "name": widget.field_name or f"pymupdf_field_page{page_num+1}_{i}",
                            "type": self._get_widget_type(widget),
                            "page": page_num + 1,
                            "required": False,
                            "rect": [widget.rect.x0, widget.rect.y0, widget.rect.x1, widget.rect.y1]
                        }
                        
                        if hasattr(widget, 'field_value') and widget.field_value:
                            field_info["default_value"] = str(widget.field_value)
                        
                        fields.append(field_info)
                        
                    except Exception as e:
                        print(f"Widget processing error on page {page_num}: {e}")
                        continue
            
            pdf_doc.close()
            
        except Exception as e:
            print(f"PyMuPDF extraction error: {e}")
        
        return fields
    
    def _get_widget_type(self, widget) -> str:
        """Determine widget type from PyMuPDF widget."""
        try:
            if hasattr(widget, 'field_type'):
                type_map = {
                    fitz.PDF_WIDGET_TYPE_TEXT: 'Text Field',
                    fitz.PDF_WIDGET_TYPE_CHECKBOX: 'Checkbox',
                    fitz.PDF_WIDGET_TYPE_RADIOBUTTON: 'Radio Button',
                    fitz.PDF_WIDGET_TYPE_LISTBOX: 'List Box',
                    fitz.PDF_WIDGET_TYPE_COMBOBOX: 'Combo Box',
                    fitz.PDF_WIDGET_TYPE_SIGNATURE: 'Signature Field',
                    fitz.PDF_WIDGET_TYPE_BUTTON: 'Button'
                }
                return type_map.get(widget.field_type, 'Unknown Widget')
        except:
            pass
        return 'Unknown Widget'
    
    def _extract_annotations(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """Extract fields by scanning all annotations."""
        fields = []
        try:
            pdf_stream = io.BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            
            for page_num, page in enumerate(pdf_reader.pages):
                if "/Annots" not in page:
                    continue
                
                annotations = page["/Annots"]
                for i, annot_ref in enumerate(annotations):
                    try:
                        annot = annot_ref.get_object()
                        
                        # Check for widget annotations
                        if "/Subtype" in annot and str(annot["/Subtype"]) == "/Widget":
                            field_info = {
                                "name": f"annotation_page{page_num+1}_{i}",
                                "type": "Widget Annotation",
                                "page": page_num + 1,
                                "required": False
                            }
                            
                            # Try to get more specific info
                            if "/T" in annot:
                                field_info["name"] = str(annot["/T"])
                            
                            if "/FT" in annot:
                                ft = str(annot["/FT"])
                                field_info["type"] = self.field_type_mapping.get(ft, ft)
                            
                            fields.append(field_info)
                            
                    except Exception as e:
                        print(f"Annotation processing error: {e}")
                        continue
                        
        except Exception as e:
            print(f"Annotation extraction error: {e}")
        
        return fields