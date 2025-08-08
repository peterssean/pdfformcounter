import fitz
import re
from typing import List, Dict, Tuple
from collections import defaultdict

class VisualFieldDetector:
    """Detects visual form elements in PDFs including non-interactive fields."""
    
    def __init__(self):
        self.field_types = {
            'text_field': 'Text Field',
            'checkbox': 'Checkbox', 
            'signature_field': 'Signature Field',
            'date_field': 'Date Field',
            'radio_button': 'Radio Button',
            'dropdown': 'Dropdown Field'
        }
    
    def detect_visual_fields(self, pdf_bytes: bytes) -> Dict:
        """Main method to detect all visual form fields in a PDF."""
        try:
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            all_fields = []
            
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                page_fields = self._analyze_page_visual_elements(page, page_num + 1)
                all_fields.extend(page_fields)
            
            pdf_doc.close()
            
            return {
                "success": True,
                "fields": all_fields,
                "message": f"Found {len(all_fields)} visual form elements",
                "field_count": len(all_fields)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Visual detection error: {str(e)}",
                "fields": [],
                "field_count": 0
            }
    
    def _analyze_page_visual_elements(self, page, page_num: int) -> List[Dict]:
        """Analyze a single page for visual form elements."""
        fields = []
        
        # Get page dimensions for relative positioning
        page_rect = page.rect
        
        # Method 1: Analyze drawing paths for rectangles and shapes
        drawing_fields = self._detect_drawing_fields(page, page_num)
        fields.extend(drawing_fields)
        
        # Method 2: Analyze text patterns and layout
        text_fields = self._detect_text_based_fields(page, page_num)
        fields.extend(text_fields)
        
        # Method 3: Find checkbox-like squares
        checkbox_fields = self._detect_checkbox_patterns(page, page_num)
        fields.extend(checkbox_fields)
        
        # Method 4: Detect signature lines and date patterns  
        signature_fields = self._detect_signature_and_date_fields(page, page_num)
        fields.extend(signature_fields)
        
        # Remove duplicates based on position
        unique_fields = self._remove_duplicate_fields(fields)
        
        return unique_fields
    
    def _detect_drawing_fields(self, page, page_num: int) -> List[Dict]:
        """Detect form fields from PDF drawing commands."""
        fields = []
        
        try:
            drawings = page.get_drawings()
            
            for drawing in drawings:
                if 'items' not in drawing:
                    continue
                
                rectangles = []
                lines = []
                
                # Parse drawing items
                for item in drawing['items']:
                    if item[0] == 're':  # Rectangle
                        if len(item) >= 5:
                            x1, y1, x2, y2 = item[1:5]
                            rectangles.append((x1, y1, x2, y2))
                    elif item[0] == 'l':  # Line
                        if len(item) >= 5:
                            lines.append((item[1], item[2], item[3], item[4]))
                
                # Analyze rectangles for form fields
                for rect in rectangles:
                    x1, y1, x2, y2 = rect
                    width = abs(x2 - x1)
                    height = abs(y2 - y1)
                    
                    # Check if rectangle looks like a form field
                    if self._is_form_field_rectangle(width, height):
                        field_type = self._classify_rectangle_field(width, height)
                        
                        fields.append({
                            'name': f"visual_field_{len(fields)+1}",
                            'type': field_type,
                            'page': page_num,
                            'rect': [x1, y1, x2, y2],
                            'detection_method': 'drawing_analysis'
                        })
                
                # Analyze lines for underline fields
                for line in lines:
                    x1, y1, x2, y2 = line
                    length = abs(x2 - x1)
                    
                    # Horizontal lines that could be form field underlines
                    if abs(y2 - y1) < 2 and length > 30:
                        fields.append({
                            'name': f"underline_field_{len(fields)+1}",
                            'type': 'Text Field',
                            'page': page_num,
                            'rect': [x1, y1-5, x2, y2+5],
                            'detection_method': 'underline_detection'
                        })
        
        except Exception as e:
            print(f"Drawing analysis error: {e}")
        
        return fields
    
    def _detect_text_based_fields(self, page, page_num: int) -> List[Dict]:
        """Detect form fields based on text patterns and layout."""
        fields = []
        
        try:
            # Get text with formatting information
            text_dict = page.get_text("dict")
            
            # Look for form field indicators in text
            for block in text_dict["blocks"]:
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"]
                        bbox = span["bbox"]
                        
                        # Look for form field patterns
                        if self._is_form_field_text_pattern(text):
                            field_type = self._classify_text_field_type(text)
                            
                            fields.append({
                                'name': f"text_pattern_{len(fields)+1}",
                                'type': field_type,
                                'page': page_num,
                                'rect': list(bbox),
                                'detection_method': 'text_pattern',
                                'text_content': text
                            })
        
        except Exception as e:
            print(f"Text analysis error: {e}")
        
        return fields
    
    def _detect_checkbox_patterns(self, page, page_num: int) -> List[Dict]:
        """Detect checkbox-like square patterns."""
        fields = []
        
        try:
            drawings = page.get_drawings()
            
            for drawing in drawings:
                if 'items' not in drawing:
                    continue
                
                for item in drawing['items']:
                    if item[0] == 're' and len(item) >= 5:
                        x1, y1, x2, y2 = item[1:5]
                        width = abs(x2 - x1)
                        height = abs(y2 - y1)
                        
                        # Square shapes that could be checkboxes
                        if 5 <= width <= 25 and 5 <= height <= 25 and abs(width - height) < 5:
                            fields.append({
                                'name': f"checkbox_{len(fields)+1}",
                                'type': 'Checkbox',
                                'page': page_num,
                                'rect': [x1, y1, x2, y2],
                                'detection_method': 'checkbox_shape'
                            })
        
        except Exception as e:
            print(f"Checkbox detection error: {e}")
        
        return fields
    
    def _detect_signature_and_date_fields(self, page, page_num: int) -> List[Dict]:
        """Detect signature lines and date field patterns."""
        fields = []
        
        try:
            text_dict = page.get_text("dict")
            
            # Look for signature and date related text
            signature_keywords = ['signature', 'sign', 'date', 'signed', 'signer']
            date_patterns = [r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}', r'__/__/____']
            
            for block in text_dict["blocks"]:
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].lower()
                        bbox = span["bbox"]
                        
                        # Check for signature keywords
                        if any(keyword in text for keyword in signature_keywords):
                            fields.append({
                                'name': f"signature_area_{len(fields)+1}",
                                'type': 'Signature Field',
                                'page': page_num,
                                'rect': list(bbox),
                                'detection_method': 'signature_text'
                            })
                        
                        # Check for date patterns
                        for pattern in date_patterns:
                            if re.search(pattern, span["text"]):
                                fields.append({
                                    'name': f"date_field_{len(fields)+1}",
                                    'type': 'Date Field',
                                    'page': page_num,
                                    'rect': list(bbox),
                                    'detection_method': 'date_pattern'
                                })
        
        except Exception as e:
            print(f"Signature/date detection error: {e}")
        
        return fields
    
    def _is_form_field_rectangle(self, width: float, height: float) -> bool:
        """Determine if a rectangle looks like a form field."""
        # Form fields are typically:
        # - Wide enough to contain text (min 20px)
        # - Not too tall (max 50px for single line)
        # - Not too thin (min 8px height)
        # - Reasonable aspect ratio
        
        if width < 20 or height < 8:
            return False
            
        if height > 100:  # Too tall for most form fields
            return False
            
        aspect_ratio = width / height if height > 0 else 0
        
        # Most form fields have aspect ratio between 1:1 and 15:1
        return 0.5 <= aspect_ratio <= 15.0
    
    def _classify_rectangle_field(self, width: float, height: float) -> str:
        """Classify the type of form field based on dimensions."""
        aspect_ratio = width / height if height > 0 else 0
        
        if width <= 25 and height <= 25 and 0.7 <= aspect_ratio <= 1.3:
            return 'Checkbox'
        elif aspect_ratio > 8:
            return 'Text Field'
        elif 2 <= aspect_ratio <= 8:
            return 'Text Field'
        else:
            return 'Text Field'  # Default
    
    def _is_form_field_text_pattern(self, text: str) -> bool:
        """Check if text indicates a form field."""
        patterns = [
            r'_{3,}',  # Multiple underscores
            r'\[\s*\]',  # Empty brackets
            r'\(\s*\)',  # Empty parentheses
            r'\.{3,}',  # Multiple dots
            r'\s+:\s*$',  # Colon at end (label)
        ]
        
        return any(re.search(pattern, text) for pattern in patterns)
    
    def _classify_text_field_type(self, text: str) -> str:
        """Classify field type based on text content."""
        text_lower = text.lower()
        
        if 'date' in text_lower or '/' in text or '__/__' in text:
            return 'Date Field'
        elif '[]' in text or '[ ]' in text:
            return 'Checkbox'
        elif 'signature' in text_lower or 'sign' in text_lower:
            return 'Signature Field'
        else:
            return 'Text Field'
    
    def _remove_duplicate_fields(self, fields: List[Dict]) -> List[Dict]:
        """Remove duplicate fields based on position overlap."""
        if not fields:
            return fields
        
        unique_fields = []
        
        for field in fields:
            is_duplicate = False
            field_rect = field['rect']
            
            for existing_field in unique_fields:
                existing_rect = existing_field['rect']
                
                # Check for significant overlap
                if self._rectangles_overlap(field_rect, existing_rect, threshold=0.7):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_fields.append(field)
        
        return unique_fields
    
    def _rectangles_overlap(self, rect1: List[float], rect2: List[float], threshold: float = 0.5) -> bool:
        """Check if two rectangles overlap significantly."""
        x1_1, y1_1, x2_1, y2_1 = rect1
        x1_2, y1_2, x2_2, y2_2 = rect2
        
        # Calculate intersection
        left = max(x1_1, x1_2)
        top = max(y1_1, y1_2) 
        right = min(x2_1, x2_2)
        bottom = min(y2_1, y2_2)
        
        if left >= right or top >= bottom:
            return False  # No overlap
        
        intersection_area = (right - left) * (bottom - top)
        
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        
        min_area = min(area1, area2)
        
        return intersection_area / min_area >= threshold