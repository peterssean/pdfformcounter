import PyPDF2
import io
from typing import Dict, List, Any, Optional

class PDFFormAnalyzer:
    """
    A class to analyze PDF forms and extract fillable field information.
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
        Analyze a PDF file and extract form field information.
        
        Args:
            pdf_bytes: The PDF file content as bytes
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Create a BytesIO object from the bytes
            pdf_stream = io.BytesIO(pdf_bytes)
            
            # Read the PDF
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            
            # Check if the PDF has form fields
            root_obj = pdf_reader.trailer["/Root"]
            if "/AcroForm" not in root_obj:
                return {
                    "success": True,
                    "fields": [],
                    "message": "No form fields found in this PDF"
                }
            
            # Extract form fields
            fields = self._extract_form_fields(pdf_reader)
            
            return {
                "success": True,
                "fields": fields,
                "message": f"Found {len(fields)} form fields"
            }
            
        except Exception as e:
            return {
                "success": False,
                "fields": [],
                "error": str(e)
            }
    
    def _extract_form_fields(self, pdf_reader: PyPDF2.PdfReader) -> List[Dict[str, Any]]:
        """
        Extract detailed information about form fields from the PDF.
        
        Args:
            pdf_reader: PyPDF2 PdfReader object
            
        Returns:
            List of dictionaries containing field information
        """
        fields = []
        
        try:
            # Get the AcroForm
            root_obj = pdf_reader.trailer["/Root"]
            if "/AcroForm" in root_obj:
                acro_form = root_obj["/AcroForm"]
                
                if "/Fields" in acro_form:
                    form_fields = acro_form["/Fields"]
                    
                    for field_ref in form_fields:
                        field_obj = field_ref.get_object()
                        field_info = self._parse_field(field_obj)
                        if field_info:
                            fields.append(field_info)
                            
                            # Check for child fields (for hierarchical forms)
                            if "/Kids" in field_obj:
                                kids = field_obj["/Kids"]
                                for kid_ref in kids:
                                    kid_obj = kid_ref.get_object()
                                    kid_info = self._parse_field(kid_obj, parent_name=field_info.get("name"))
                                    if kid_info:
                                        fields.append(kid_info)
            
        except Exception as e:
            # If field extraction fails, try alternative method
            fields.extend(self._extract_fields_alternative_method(pdf_reader))
        
        return fields
    
    def _parse_field(self, field_obj: Any, parent_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Parse a single form field object and extract its properties.
        
        Args:
            field_obj: The field object from PyPDF2
            parent_name: Name of parent field if this is a child field
            
        Returns:
            Dictionary containing field information or None if parsing fails
        """
        try:
            field_info = {}
            
            # Get field name
            field_name = ""
            if "/T" in field_obj:
                field_name = str(field_obj["/T"])
            
            if parent_name and field_name:
                field_name = f"{parent_name}.{field_name}"
            elif parent_name:
                field_name = parent_name
                
            field_info["name"] = field_name
            
            # Get field type
            field_type = "Unknown"
            if "/FT" in field_obj:
                ft = field_obj["/FT"]
                field_type = self.field_type_mapping.get(str(ft), str(ft))
                
                # For button fields, determine if it's checkbox or radio
                if str(ft) == "/Btn":
                    if "/Ff" in field_obj:
                        flags = field_obj["/Ff"]
                        if isinstance(flags, int):
                            if flags & 32768:  # Radio button flag
                                field_type = "Radio Button"
                            elif flags & 65536:  # Pushbutton flag
                                field_type = "Push Button"
                            else:
                                field_type = "Checkbox"
            
            field_info["type"] = field_type
            
            # Check if field is required
            required = False
            if "/Ff" in field_obj:
                flags = field_obj["/Ff"]
                if isinstance(flags, int):
                    required = bool(flags & 2)  # Required flag
            field_info["required"] = required
            
            # Get default value
            default_value = ""
            if "/DV" in field_obj:
                default_value = str(field_obj["/DV"])
            elif "/V" in field_obj:
                default_value = str(field_obj["/V"])
            field_info["default_value"] = default_value
            
            # Get options for choice fields
            options = []
            if "/Opt" in field_obj:
                opt_list = field_obj["/Opt"]
                for opt in opt_list:
                    if isinstance(opt, list) and len(opt) > 0:
                        options.append(str(opt[0]))
                    else:
                        options.append(str(opt))
            field_info["options"] = options
            
            # Get field description/tooltip
            description = ""
            if "/TU" in field_obj:
                description = str(field_obj["/TU"])
            field_info["description"] = description
            
            return field_info
            
        except Exception:
            return None
    
    def _extract_fields_alternative_method(self, pdf_reader: PyPDF2.PdfReader) -> List[Dict[str, Any]]:
        """
        Alternative method to extract fields by iterating through pages.
        
        Args:
            pdf_reader: PyPDF2 PdfReader object
            
        Returns:
            List of field dictionaries
        """
        fields = []
        
        try:
            for page_num, page in enumerate(pdf_reader.pages):
                if "/Annots" in page:
                    annotations = page["/Annots"]
                    
                    for annot_ref in annotations:
                        try:
                            annot = annot_ref.get_object()
                            
                            # Check if this is a widget annotation (form field)
                            if "/Subtype" in annot and str(annot["/Subtype"]) == "/Widget":
                                field_info = self._parse_field(annot)
                                if field_info and field_info not in fields:
                                    field_info["page"] = page_num + 1
                                    fields.append(field_info)
                                    
                        except Exception:
                            continue
                            
        except Exception:
            pass
        
        return fields
