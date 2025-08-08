import PyPDF2
import io
import fitz
from typing import Dict, List, Any, Optional

class PDFFormAnalyzerFocused:
    """
    Focused PDF Form Analyzer that prioritizes accurate field detection over quantity.
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
        Analyze PDF using focused detection methods.
        """
        try:
            fields = []
            
            # Method 1: Enhanced PyMuPDF detection
            pymupdf_fields = self._extract_with_pymupdf_focused(pdf_bytes)
            print(f"PyMuPDF focused method found {len(pymupdf_fields)} fields")
            fields.extend(pymupdf_fields)
            
            # Method 2: Enhanced PyPDF2 with better handling
            pypdf2_fields = self._extract_with_pypdf2_enhanced(pdf_bytes)
            print(f"PyPDF2 enhanced method found {len(pypdf2_fields)} fields")
            
            # Merge without duplicates based on coordinates and names
            for field in pypdf2_fields:
                if not self._is_duplicate_field(field, fields):
                    fields.append(field)
            
            # Method 3: Direct annotation processing with better filtering
            annot_fields = self._extract_annotations_focused(pdf_bytes)
            print(f"Focused annotation method found {len(annot_fields)} fields")
            
            for field in annot_fields:
                if not self._is_duplicate_field(field, fields):
                    fields.append(field)
            
            # Add document type detection and analysis insights
            doc_type, visual_field_count = self._analyze_document_type(pdf_bytes)
            
            message = f"Found {len(fields)} interactive form fields using focused detection"
            if visual_field_count > len(fields):
                message += f" (detected {visual_field_count} visual form elements that aren't interactive)"
            
            return {
                "success": True,
                "fields": fields,
                "message": message,
                "document_type": doc_type,
                "visual_field_count": visual_field_count,
                "interactive_field_count": len(fields)
            }
            
        except Exception as e:
            return {
                "success": False,
                "fields": [],
                "error": str(e)
            }
    
    def _extract_with_pymupdf_focused(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """Extract fields using PyMuPDF with focused detection."""
        fields = []
        try:
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                
                # Get form fields using the most reliable method
                widgets = list(page.widgets())
                print(f"Page {page_num + 1}: {len(widgets)} interactive widgets found")
                
                for i, widget in enumerate(widgets):
                    try:
                        # Get field name, handling complex nested names
                        field_name = widget.field_name or f"field_{page_num+1}_{i}"
                        # Simplify the name for better readability
                        if field_name and '.' in field_name:
                            # Extract the meaningful part from complex names
                            parts = field_name.split('.')
                            simple_name = parts[-1]  # Get the last part like 'f1_01[0]'
                            if '[' in simple_name:
                                simple_name = simple_name.split('[')[0]  # Remove [0] suffix
                            field_name = simple_name
                        
                        # Get field type using the widget type code
                        field_type = self._get_pymupdf_widget_type(widget)
                        
                        field_info = {
                            "name": field_name,
                            "type": field_type,
                            "page": page_num + 1,
                            "required": False,
                            "rect": [widget.rect.x0, widget.rect.y0, widget.rect.x1, widget.rect.y1]
                        }
                        
                        # Get field value if available
                        try:
                            if hasattr(widget, 'field_value') and widget.field_value:
                                field_info["default_value"] = str(widget.field_value)
                        except:
                            pass
                        
                        # Store the widget type code for debugging
                        try:
                            if hasattr(widget, 'field_type'):
                                field_info["widget_type_code"] = widget.field_type
                        except:
                            pass
                            
                        fields.append(field_info)
                        print(f"  Widget {i}: {field_name} ({field_type}) at {field_info['rect']}")
                        
                    except Exception as e:
                        print(f"Error processing widget {i} on page {page_num}: {e}")
                        continue
                
                # Also check for any form fields that might not be widgets
                try:
                    # Look for form field annotations specifically
                    annotations = list(page.annots())
                    form_annotations = []
                    for annot in annotations:
                        if hasattr(annot, 'type') and len(annot.type) > 1:
                            if annot.type[1] == 'Widget' and annot not in [w for w in widgets]:
                                form_annotations.append(annot)
                    
                    print(f"Page {page_num + 1}: {len(form_annotations)} additional form annotations found")
                    
                    for i, annot in enumerate(form_annotations):
                        try:
                            field_info = {
                                "name": f"form_annot_{page_num+1}_{i}",
                                "type": "Form Annotation",
                                "page": page_num + 1,
                                "required": False,
                                "rect": [annot.rect.x0, annot.rect.y0, annot.rect.x1, annot.rect.y1]
                            }
                            fields.append(field_info)
                        except Exception as e:
                            print(f"Error processing form annotation {i}: {e}")
                            continue
                            
                except Exception as e:
                    print(f"Error checking form annotations on page {page_num}: {e}")
            
            pdf_doc.close()
            
        except Exception as e:
            print(f"PyMuPDF focused extraction error: {e}")
        
        return fields
    
    def _get_pymupdf_widget_type(self, widget) -> str:
        """Get widget type from PyMuPDF widget."""
        try:
            if hasattr(widget, 'field_type'):
                # Map the actual type codes we're seeing
                type_map = {
                    0: 'Button',
                    1: 'Checkbox', 
                    2: 'Checkbox',  # Type 2 is also checkbox
                    3: 'Radio Button',
                    4: 'List Box',
                    5: 'Combo Box',
                    6: 'Signature Field',
                    7: 'Text Field'  # Type 7 is text field
                }
                
                # Try to get the constant names too
                try:
                    const_map = {
                        fitz.PDF_WIDGET_TYPE_TEXT: 'Text Field',
                        fitz.PDF_WIDGET_TYPE_CHECKBOX: 'Checkbox',
                        fitz.PDF_WIDGET_TYPE_RADIOBUTTON: 'Radio Button',
                        fitz.PDF_WIDGET_TYPE_LISTBOX: 'List Box',
                        fitz.PDF_WIDGET_TYPE_COMBOBOX: 'Combo Box',
                        fitz.PDF_WIDGET_TYPE_SIGNATURE: 'Signature Field',
                        fitz.PDF_WIDGET_TYPE_BUTTON: 'Button'
                    }
                    if widget.field_type in const_map:
                        return const_map[widget.field_type]
                except:
                    pass
                
                return type_map.get(widget.field_type, f'Widget Type {widget.field_type}')
        except:
            pass
        return 'Interactive Widget'
    
    def _extract_with_pypdf2_enhanced(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """Enhanced PyPDF2 extraction with better error handling."""
        fields = []
        try:
            pdf_stream = io.BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            
            # Get root and handle indirect objects properly
            root = pdf_reader.trailer.get("/Root")
            if hasattr(root, 'get_object'):
                root = root.get_object()
            
            if not root or "/AcroForm" not in root:
                return fields
            
            acro_form = root["/AcroForm"]
            if hasattr(acro_form, 'get_object'):
                acro_form = acro_form.get_object()
            
            if "/Fields" not in acro_form:
                return fields
            
            form_fields = acro_form["/Fields"]
            print(f"AcroForm contains {len(form_fields)} top-level field entries")
            
            for i, field_ref in enumerate(form_fields):
                try:
                    field_obj = field_ref.get_object() if hasattr(field_ref, 'get_object') else field_ref
                    self._process_acroform_field(field_obj, fields, f"acro_field_{i}")
                except Exception as e:
                    print(f"Error processing AcroForm field {i}: {e}")
                    continue
            
        except Exception as e:
            print(f"PyPDF2 enhanced extraction error: {e}")
        
        return fields
    
    def _process_acroform_field(self, field_obj, fields, field_id):
        """Process AcroForm field with enhanced handling."""
        try:
            # Get basic field info
            field_name = field_id
            if "/T" in field_obj:
                name_value = field_obj["/T"]
                if name_value:
                    field_name = str(name_value)
            
            field_type = "Unknown"
            if "/FT" in field_obj:
                ft_value = field_obj["/FT"]
                if ft_value:
                    field_type = self.field_type_mapping.get(str(ft_value), str(ft_value))
            
            # Create field info
            field_info = {
                "name": field_name,
                "type": field_type,
                "page": 1,  # Default, will try to find actual page
                "required": False
            }
            
            # Try to get additional properties
            if "/V" in field_obj:
                try:
                    field_info["default_value"] = str(field_obj["/V"])
                except:
                    pass
            
            # Check if field is required
            if "/Ff" in field_obj:
                try:
                    flags = int(field_obj["/Ff"])
                    field_info["required"] = bool(flags & 2)  # Required flag
                except:
                    pass
            
            fields.append(field_info)
            
            # Process children if they exist
            if "/Kids" in field_obj:
                kids = field_obj["/Kids"]
                for j, kid_ref in enumerate(kids):
                    try:
                        kid_obj = kid_ref.get_object() if hasattr(kid_ref, 'get_object') else kid_ref
                        self._process_acroform_field(kid_obj, fields, f"{field_name}_child_{j}")
                    except Exception as e:
                        print(f"Error processing child field: {e}")
                        continue
                        
        except Exception as e:
            print(f"Error processing AcroForm field: {e}")
    
    def _extract_annotations_focused(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """Extract annotations with focused filtering."""
        fields = []
        try:
            pdf_stream = io.BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            
            for page_num, page in enumerate(pdf_reader.pages):
                if "/Annots" not in page:
                    continue
                
                annotations = page["/Annots"]
                widget_count = 0
                
                for annot_ref in annotations:
                    try:
                        annot = annot_ref.get_object()
                        
                        # Only process widget annotations
                        if "/Subtype" in annot and str(annot["/Subtype"]) == "/Widget":
                            widget_count += 1
                            
                            field_name = f"widget_page{page_num+1}_{widget_count}"
                            if "/T" in annot:
                                field_name = str(annot["/T"])
                            
                            field_type = "Widget"
                            if "/FT" in annot:
                                ft = str(annot["/FT"])
                                field_type = self.field_type_mapping.get(ft, ft)
                            
                            field_info = {
                                "name": field_name,
                                "type": field_type,
                                "page": page_num + 1,
                                "required": False
                            }
                            
                            fields.append(field_info)
                            
                    except Exception as e:
                        print(f"Error processing annotation: {e}")
                        continue
                
                print(f"Page {page_num + 1}: Found {widget_count} widget annotations")
                        
        except Exception as e:
            print(f"Focused annotation extraction error: {e}")
        
        return fields
    
    def _is_duplicate_field(self, field, existing_fields) -> bool:
        """Check if field is a duplicate based on name and location."""
        field_name = field.get("name", "")
        field_page = field.get("page", 0)
        field_rect = field.get("rect", [])
        
        for existing in existing_fields:
            existing_name = existing.get("name", "")
            existing_page = existing.get("page", 0)
            existing_rect = existing.get("rect", [])
            
            # Check if names match
            if field_name == existing_name and field_page == existing_page:
                return True
            
            # Check if rectangles overlap (same field, different detection method)
            if field_rect and existing_rect and len(field_rect) >= 4 and len(existing_rect) >= 4:
                if (abs(field_rect[0] - existing_rect[0]) < 5 and 
                    abs(field_rect[1] - existing_rect[1]) < 5 and
                    field_page == existing_page):
                    return True
        
        return False
    
    def _analyze_document_type(self, pdf_bytes: bytes) -> tuple[str, int]:
        """Analyze document type and count visual form elements."""
        doc_type = "Unknown Document"
        visual_field_count = 0
        
        try:
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            if len(pdf_doc) > 0:
                first_page_text = pdf_doc[0].get_text()
                
                # Detect document type
                if "W-9" in first_page_text or "Form W-9" in first_page_text:
                    doc_type = "IRS Form W-9"
                elif "Autorisation de transfert" in first_page_text:
                    doc_type = "Fidelity Transfer Authorization Form"
                elif "1099" in first_page_text:
                    doc_type = "IRS Form 1099"
                elif "fidelity" in first_page_text.lower():
                    doc_type = "Fidelity Form"
                
                # Count visual form elements (rectangles that look like form fields)
                page = pdf_doc[0]
                drawings = page.get_drawings()
                
                # Count rectangles that could be form fields
                rectangular_elements = 0
                for drawing in drawings:
                    try:
                        if 'items' in drawing:
                            for item in drawing['items']:
                                if item[0] == 're':  # Rectangle command
                                    rect = item[1:]
                                    if len(rect) >= 4:
                                        width = abs(rect[2] - rect[0])
                                        height = abs(rect[3] - rect[1])
                                        # Check if it looks like a form field (reasonable size, not too thin)
                                        if 10 < width < 400 and 5 < height < 50:
                                            rectangular_elements += 1
                    except:
                        continue
                
                visual_field_count = rectangular_elements
                print(f"Document type: {doc_type}, Visual elements: {visual_field_count}")
            
            pdf_doc.close()
            
        except Exception as e:
            print(f"Document analysis error: {e}")
        
        return doc_type, visual_field_count