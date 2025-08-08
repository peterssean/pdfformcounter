import fitz
import re
from typing import List, Dict, Tuple, Set
import numpy as np
from collections import defaultdict

class AdvancedFieldDetector:
    """Advanced PDF field detection using layout analysis and pattern recognition."""
    
    def __init__(self):
        self.min_field_width = 20
        self.min_field_height = 8
        self.checkbox_size_range = (5, 25)
        self.text_field_height_range = (8, 40)
        
    def detect_form_fields(self, pdf_bytes: bytes) -> Dict:
        """Main method to detect form fields using advanced layout analysis."""
        try:
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            all_fields = []
            
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                page_fields = self._analyze_page_layout(page, page_num + 1)
                all_fields.extend(page_fields)
            
            pdf_doc.close()
            
            return {
                "success": True,
                "fields": all_fields,
                "field_count": len(all_fields),
                "message": f"Advanced detection found {len(all_fields)} form fields"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Advanced detection error: {str(e)}",
                "fields": [],
                "field_count": 0
            }
    
    def _analyze_page_layout(self, page, page_num: int) -> List[Dict]:
        """Comprehensive page layout analysis for form field detection."""
        fields = []
        
        # Get page dimensions
        page_rect = page.rect
        
        # Method 1: Text-based field detection with precise positioning
        text_fields = self._detect_text_positioned_fields(page, page_num)
        fields.extend(text_fields)
        
        # Method 2: Enhanced drawing analysis
        drawing_fields = self._detect_drawing_elements(page, page_num)
        fields.extend(drawing_fields)
        
        # Method 3: Layout pattern recognition
        pattern_fields = self._detect_layout_patterns(page, page_num)
        fields.extend(pattern_fields)
        
        # Method 4: Interactive widget integration
        widget_fields = self._detect_interactive_widgets(page, page_num)
        fields.extend(widget_fields)
        
        # Remove duplicates and merge nearby fields
        unique_fields = self._consolidate_fields(fields)
        
        print(f"Page {page_num}: Found {len(unique_fields)} fields via advanced detection")
        return unique_fields
    
    def _detect_text_positioned_fields(self, page, page_num: int) -> List[Dict]:
        """Detect form fields based on text positioning and context."""
        fields = []
        
        try:
            # Get text with detailed positioning
            text_dict = page.get_text("dict")
            
            # Build text layout map
            text_blocks = []
            for block in text_dict["blocks"]:
                if "lines" not in block:
                    continue
                
                for line in block["lines"]:
                    for span in line["spans"]:
                        text_blocks.append({
                            'text': span["text"],
                            'bbox': span["bbox"],
                            'font': span.get("font", ""),
                            'size': span.get("size", 12)
                        })
            
            # Detect form field indicators
            field_indicators = []
            checkbox_count = 0
            
            for block in text_blocks:
                text = block['text']
                bbox = block['bbox']
                
                # Checkbox symbols
                if '■' in text:
                    for i, char in enumerate(text):
                        if char == '■':
                            checkbox_count += 1
                            # Calculate position for this specific checkbox
                            char_width = (bbox[2] - bbox[0]) / len(text) if len(text) > 0 else 10
                            char_x = bbox[0] + (i * char_width)
                            
                            fields.append({
                                'name': f"checkbox_{checkbox_count}",
                                'type': 'Checkbox',
                                'page': page_num,
                                'rect': [char_x, bbox[1], char_x + 12, bbox[3]],
                                'detection_method': 'checkbox_symbol_positioned',
                                'confidence': 0.9
                            })
                
                # Text field indicators (labels followed by spaces)
                elif ':' in text and text.strip().endswith(':'):
                    # This is likely a field label - look for nearby input area
                    label_rect = bbox
                    
                    # Create expected input field area to the right or below
                    input_width = 200
                    input_height = max(16, bbox[3] - bbox[1])
                    
                    # Try horizontal layout first
                    input_rect = [
                        bbox[2] + 5,  # Start after label
                        bbox[1],
                        bbox[2] + input_width,
                        bbox[3]
                    ]
                    
                    fields.append({
                        'name': f"text_field_after_{text.replace(':', '').strip().lower().replace(' ', '_')}",
                        'type': 'Text Field',
                        'page': page_num,
                        'rect': input_rect,
                        'detection_method': 'label_based_positioning',
                        'confidence': 0.7,
                        'label': text.strip()
                    })
            
            # Detect underline patterns with positioning
            full_text = page.get_text()
            underline_patterns = [
                r'_{3,}',  # Multiple underscores
                r'\.{5,}', # Multiple dots
                r'-{5,}'   # Multiple dashes
            ]
            
            for pattern in underline_patterns:
                matches = re.finditer(pattern, full_text)
                for match in matches:
                    # Try to find the position of this text
                    context = full_text[max(0, match.start()-20):match.end()+20]
                    
                    # Create estimated field based on pattern length
                    field_width = len(match.group()) * 8  # Approximate character width
                    
                    fields.append({
                        'name': f"underline_field_{len(fields)+1}",
                        'type': 'Text Field',
                        'page': page_num,
                        'rect': [100, 100, 100 + field_width, 120],  # Placeholder position
                        'detection_method': 'underline_pattern',
                        'confidence': 0.6,
                        'pattern': match.group()
                    })
        
        except Exception as e:
            print(f"Text positioning error: {e}")
        
        return fields
    
    def _detect_drawing_elements(self, page, page_num: int) -> List[Dict]:
        """Enhanced drawing element analysis for form fields."""
        fields = []
        
        try:
            drawings = page.get_drawings()
            
            rectangles = []
            lines = []
            
            for drawing in drawings:
                if 'items' not in drawing:
                    continue
                
                for item in drawing['items']:
                    if item[0] == 're' and len(item) >= 5:  # Rectangle
                        x1, y1, x2, y2 = item[1:5]
                        width = abs(x2 - x1)
                        height = abs(y2 - y1)
                        rectangles.append((x1, y1, x2, y2, width, height))
                    
                    elif item[0] == 'l' and len(item) >= 5:  # Line
                        x1, y1, x2, y2 = item[1:5]
                        length = ((x2-x1)**2 + (y2-y1)**2)**0.5
                        lines.append((x1, y1, x2, y2, length))
            
            # Analyze rectangles for form fields
            for rect in rectangles:
                x1, y1, x2, y2, width, height = rect
                
                if self._is_form_field_rectangle(width, height):
                    field_type = self._classify_rectangle_by_size(width, height)
                    
                    fields.append({
                        'name': f"rect_field_{len(fields)+1}",
                        'type': field_type,
                        'page': page_num,
                        'rect': [x1, y1, x2, y2],
                        'detection_method': 'rectangle_analysis',
                        'confidence': 0.8,
                        'dimensions': {'width': width, 'height': height}
                    })
            
            # Analyze lines for underline fields
            horizontal_lines = [line for line in lines if abs(line[3] - line[1]) < 3 and line[4] > 30]
            
            # Group nearby horizontal lines
            line_groups = self._group_nearby_lines(horizontal_lines)
            
            for group in line_groups:
                if len(group) == 1:
                    x1, y1, x2, y2, length = group[0]
                    
                    fields.append({
                        'name': f"line_field_{len(fields)+1}",
                        'type': 'Text Field',
                        'page': page_num,
                        'rect': [x1, y1-5, x2, y1+15],
                        'detection_method': 'line_analysis',
                        'confidence': 0.7,
                        'line_length': length
                    })
        
        except Exception as e:
            print(f"Drawing analysis error: {e}")
        
        return fields
    
    def _detect_layout_patterns(self, page, page_num: int) -> List[Dict]:
        """Detect form fields based on common layout patterns."""
        fields = []
        
        try:
            # Get text blocks for pattern analysis
            text_dict = page.get_text("dict")
            
            # Look for common form patterns
            form_sections = []
            
            for block in text_dict["blocks"]:
                if "lines" not in block:
                    continue
                
                block_text = ""
                block_bbox = None
                
                for line in block["lines"]:
                    for span in line["spans"]:
                        block_text += span["text"] + " "
                        if block_bbox is None:
                            block_bbox = list(span["bbox"])
                        else:
                            # Expand bbox to include this span
                            block_bbox[0] = min(block_bbox[0], span["bbox"][0])
                            block_bbox[1] = min(block_bbox[1], span["bbox"][1])
                            block_bbox[2] = max(block_bbox[2], span["bbox"][2])
                            block_bbox[3] = max(block_bbox[3], span["bbox"][3])
                
                # Detect form section patterns
                if self._is_form_section(block_text.strip()):
                    form_sections.append({
                        'text': block_text.strip(),
                        'bbox': block_bbox,
                        'type': self._classify_form_section(block_text.strip())
                    })
            
            # Generate fields based on detected patterns
            for section in form_sections:
                section_fields = self._generate_fields_from_section(section, page_num)
                fields.extend(section_fields)
        
        except Exception as e:
            print(f"Pattern analysis error: {e}")
        
        return fields
    
    def _detect_interactive_widgets(self, page, page_num: int) -> List[Dict]:
        """Detect interactive PDF widgets."""
        fields = []
        
        try:
            widgets = list(page.widgets())
            
            for widget in widgets:
                field_name = widget.field_name or f"widget_{len(fields)+1}"
                field_type = self._get_widget_type(widget)
                
                fields.append({
                    'name': field_name,
                    'type': field_type,
                    'page': page_num,
                    'rect': list(widget.rect),
                    'detection_method': 'interactive_widget',
                    'confidence': 1.0,
                    'widget_info': {
                        'field_type': widget.field_type,
                        'field_value': widget.field_value
                    }
                })
        
        except Exception as e:
            print(f"Widget detection error: {e}")
        
        return fields
    
    def _consolidate_fields(self, fields: List[Dict]) -> List[Dict]:
        """Remove duplicates and merge nearby fields."""
        if not fields:
            return fields
        
        # Sort fields by position for easier processing
        fields.sort(key=lambda f: (f['page'], f['rect'][1], f['rect'][0]))
        
        consolidated = []
        skip_indices = set()
        
        for i, field in enumerate(fields):
            if i in skip_indices:
                continue
            
            # Look for nearby fields to merge
            merged = False
            for j in range(i + 1, len(fields)):
                if j in skip_indices:
                    continue
                
                other_field = fields[j]
                
                # Check if fields are close enough to merge
                if (field['page'] == other_field['page'] and 
                    self._fields_should_merge(field, other_field)):
                    
                    # Merge the fields
                    merged_field = self._merge_fields(field, other_field)
                    field = merged_field
                    skip_indices.add(j)
                    merged = True
            
            consolidated.append(field)
        
        return consolidated
    
    def _is_form_field_rectangle(self, width: float, height: float) -> bool:
        """Determine if rectangle dimensions suggest a form field."""
        return (width >= self.min_field_width and 
                height >= self.min_field_height and
                height <= 100 and  # Not too tall
                width <= 500)     # Not too wide
    
    def _classify_rectangle_by_size(self, width: float, height: float) -> str:
        """Classify field type based on rectangle dimensions."""
        aspect_ratio = width / height if height > 0 else 0
        
        # Small squares are likely checkboxes
        if (self.checkbox_size_range[0] <= width <= self.checkbox_size_range[1] and
            self.checkbox_size_range[0] <= height <= self.checkbox_size_range[1] and
            0.7 <= aspect_ratio <= 1.3):
            return 'Checkbox'
        
        # Wide rectangles are text fields
        elif aspect_ratio > 3:
            return 'Text Field'
        
        # Medium rectangles could be various field types
        else:
            return 'Text Field'
    
    def _group_nearby_lines(self, lines: List[Tuple]) -> List[List[Tuple]]:
        """Group horizontal lines that are close to each other."""
        if not lines:
            return []
        
        # Sort lines by y-coordinate
        sorted_lines = sorted(lines, key=lambda l: l[1])
        
        groups = []
        current_group = [sorted_lines[0]]
        
        for i in range(1, len(sorted_lines)):
            current_line = sorted_lines[i]
            last_line = current_group[-1]
            
            # If lines are close vertically, add to current group
            if abs(current_line[1] - last_line[1]) < 10:
                current_group.append(current_line)
            else:
                # Start new group
                groups.append(current_group)
                current_group = [current_line]
        
        groups.append(current_group)
        return groups
    
    def _is_form_section(self, text: str) -> bool:
        """Check if text indicates a form section."""
        form_indicators = [
            'name', 'address', 'phone', 'email', 'date', 'signature',
            'client', 'account', 'number', 'institution', 'contact',
            'information', 'authorization', 'transfer', 'instructions'
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in form_indicators)
    
    def _classify_form_section(self, text: str) -> str:
        """Classify the type of form section."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['name', 'client']):
            return 'name_section'
        elif any(word in text_lower for word in ['address']):
            return 'address_section'
        elif any(word in text_lower for word in ['phone', 'contact']):
            return 'contact_section'
        elif any(word in text_lower for word in ['signature', 'sign']):
            return 'signature_section'
        else:
            return 'general_section'
    
    def _generate_fields_from_section(self, section: Dict, page_num: int) -> List[Dict]:
        """Generate expected fields based on section type."""
        fields = []
        section_type = section['type']
        bbox = section['bbox']
        
        # Generate fields based on section type
        if section_type == 'name_section':
            # Expect name fields after this section
            field_height = 20
            field_y = bbox[3] + 5
            
            fields.append({
                'name': 'name_field',
                'type': 'Text Field',
                'page': page_num,
                'rect': [bbox[0], field_y, bbox[0] + 200, field_y + field_height],
                'detection_method': 'section_pattern',
                'confidence': 0.6,
                'section_type': section_type
            })
        
        elif section_type == 'address_section':
            # Expect multiple address lines
            field_height = 20
            for i in range(3):  # Typical address has 2-3 lines
                field_y = bbox[3] + 5 + (i * 25)
                fields.append({
                    'name': f'address_line_{i+1}',
                    'type': 'Text Field',
                    'page': page_num,
                    'rect': [bbox[0], field_y, bbox[0] + 300, field_y + field_height],
                    'detection_method': 'section_pattern',
                    'confidence': 0.6,
                    'section_type': section_type
                })
        
        return fields
    
    def _fields_should_merge(self, field1: Dict, field2: Dict) -> bool:
        """Check if two fields should be merged."""
        rect1 = field1['rect']
        rect2 = field2['rect']
        
        # Calculate distance between field centers
        center1 = [(rect1[0] + rect1[2])/2, (rect1[1] + rect1[3])/2]
        center2 = [(rect2[0] + rect2[2])/2, (rect2[1] + rect2[3])/2]
        
        distance = ((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)**0.5
        
        # Merge if very close and similar types
        return (distance < 15 and 
                field1['type'] == field2['type'] and
                field1['detection_method'] != 'interactive_widget' and
                field2['detection_method'] != 'interactive_widget')
    
    def _merge_fields(self, field1: Dict, field2: Dict) -> Dict:
        """Merge two overlapping fields."""
        rect1 = field1['rect']
        rect2 = field2['rect']
        
        # Create merged rectangle
        merged_rect = [
            min(rect1[0], rect2[0]),
            min(rect1[1], rect2[1]),
            max(rect1[2], rect2[2]),
            max(rect1[3], rect2[3])
        ]
        
        # Use higher confidence field as base
        base_field = field1 if field1.get('confidence', 0.5) >= field2.get('confidence', 0.5) else field2
        
        merged_field = base_field.copy()
        merged_field['rect'] = merged_rect
        merged_field['detection_method'] = f"merged_{field1['detection_method']}_{field2['detection_method']}"
        merged_field['confidence'] = max(field1.get('confidence', 0.5), field2.get('confidence', 0.5))
        
        return merged_field
    
    def _get_widget_type(self, widget) -> str:
        """Get human-readable widget type."""
        type_mapping = {
            0: 'Text Field',
            1: 'Button',
            2: 'Checkbox', 
            3: 'Radio Button',
            4: 'Dropdown',
            5: 'List Box',
            6: 'Signature Field'
        }
        
        return type_mapping.get(widget.field_type, 'Unknown Field')