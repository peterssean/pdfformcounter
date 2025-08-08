import fitz
from PIL import Image, ImageDraw, ImageFont
import io
from typing import List, Dict, Tuple

class FieldVisualizer:
    """Creates visual overlays showing detected form fields on PDF pages."""
    
    def __init__(self):
        self.field_colors = {
            'Text Field': '#FF6B6B',      # Red
            'Checkbox': '#4ECDC4',        # Teal  
            'Radio Button': '#45B7D1',    # Blue
            'Dropdown': '#96CEB4',        # Green
            'Signature Field': '#FFEAA7', # Yellow
            'Button': '#DDA0DD',          # Plum
            'List Box': '#98D8C8',        # Mint
            'Unknown Field': '#FF69B4',   # Hot Pink - makes unknown fields very visible
            'Date Field': '#F7DC6F'       # Light yellow
        }
        
        self.detection_method_styles = {
            'interactive_widget': {'width': 3, 'alpha': 0.8},
            'checkbox_symbol_positioned': {'width': 2, 'alpha': 0.7},
            'label_based_positioning': {'width': 2, 'alpha': 0.6},
            'rectangle_analysis': {'width': 2, 'alpha': 0.6},
            'line_analysis': {'width': 2, 'alpha': 0.5},
            'section_pattern': {'width': 1, 'alpha': 0.4},
            'underline_pattern': {'width': 1, 'alpha': 0.5}
        }
    
    def create_field_overlay(self, pdf_bytes: bytes, fields: List[Dict], page_num: int = 0, 
                           zoom_factor: float = 1.5) -> Tuple[Image.Image, int]:
        """Create a PDF page image with field overlays."""
        try:
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            if page_num >= len(pdf_doc):
                return None, 0
            
            page = pdf_doc[page_num]
            
            # Render page to image
            mat = fitz.Matrix(zoom_factor, zoom_factor)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Create overlay for fields
            overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Filter fields for this page
            page_fields = [f for f in fields if f.get('page') == page_num + 1]
            
            print(f"Page {page_num + 1} visualization: {len(page_fields)} fields to draw")
            
            # Draw field overlays
            fields_drawn = 0
            for field in page_fields:
                if self._draw_field_overlay(draw, field, zoom_factor):
                    fields_drawn += 1
            
            # Combine base image with overlay
            result = Image.alpha_composite(img.convert('RGBA'), overlay)
            
            pdf_doc.close()
            return result.convert('RGB'), fields_drawn
            
        except Exception as e:
            print(f"Visualization error: {e}")
            return None, 0
    
    def _draw_field_overlay(self, draw: ImageDraw.Draw, field: Dict, zoom_factor: float) -> bool:
        """Draw a single field overlay."""
        try:
            rect = field.get('rect', [0, 0, 0, 0])
            field_type = field.get('type', 'Unknown Field')
            detection_method = field.get('detection_method', 'unknown')
            confidence = field.get('confidence', 0.5)
            
            # Skip fields with invalid rectangles
            if len(rect) != 4:
                return False
                
            # Check for completely invalid rectangles (like signature envelope fields)
            if (rect[0] == 0.0 and rect[1] == 792.0 and rect[2] == 0.0 and rect[3] == 792.0) or all(coord == 0 for coord in rect):
                return False
            
            # Scale rectangle coordinates
            x1, y1, x2, y2 = [coord * zoom_factor for coord in rect]
            
            # Make sure rectangle has valid dimensions after scaling
            if abs(x2 - x1) < 1 or abs(y2 - y1) < 1:
                return False
            
            # Get color and style
            color = self.field_colors.get(field_type, self.field_colors['Unknown Field'])
            style = self.detection_method_styles.get(detection_method, {'width': 2, 'alpha': 0.5})
            
            # Adjust alpha based on confidence
            alpha = int(255 * style['alpha'] * confidence)
            
            # Convert hex color to RGBA
            color_rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
            fill_color = (*color_rgb, alpha // 4)  # Semi-transparent fill
            outline_color = (*color_rgb, alpha)     # More opaque outline
            
            # Draw field rectangle
            draw.rectangle([x1, y1, x2, y2], 
                         fill=fill_color, 
                         outline=outline_color, 
                         width=style['width'])
            
            # Add field type label for larger fields
            if (x2 - x1) > 40 and (y2 - y1) > 15:
                try:
                    # Try to use a small font for labels
                    font_size = max(8, min(12, int((y2 - y1) / 3)))
                    
                    # Create label text
                    label = field_type
                    if len(label) > 10:
                        label = label[:8] + "..."
                    
                    # Calculate text position
                    text_x = x1 + 2
                    text_y = y1 + 1
                    
                    # Draw text background
                    text_bg_color = (*color_rgb, alpha // 2)
                    draw.rectangle([text_x-1, text_y-1, text_x + len(label)*6, text_y + font_size+1],
                                 fill=text_bg_color)
                    
                    # Draw text
                    draw.text((text_x, text_y), label, 
                             fill=outline_color)
                             
                except Exception:
                    pass  # Skip text if font issues
            
            return True
            
        except Exception as e:
            print(f"Field drawing error: {e}")
            return False
    
    def create_detection_summary_image(self, fields: List[Dict], page_num: int) -> Image.Image:
        """Create a summary image showing field detection statistics."""
        try:
            # Create summary image
            img_width, img_height = 400, 300
            img = Image.new('RGB', (img_width, img_height), 'white')
            draw = ImageDraw.Draw(img)
            
            # Filter fields for this page
            page_fields = [f for f in fields if f.get('page') == page_num]
            
            # Count fields by type
            type_counts = {}
            method_counts = {}
            
            for field in page_fields:
                ftype = field.get('type', 'Unknown')
                method = field.get('detection_method', 'unknown')
                
                type_counts[ftype] = type_counts.get(ftype, 0) + 1
                method_counts[method] = method_counts.get(method, 0) + 1
            
            # Draw title
            draw.text((10, 10), f"Page {page_num} Field Summary", fill='black')
            draw.text((10, 30), f"Total Fields: {len(page_fields)}", fill='black')
            
            # Draw field type breakdown
            y_offset = 60
            draw.text((10, y_offset), "Field Types:", fill='black')
            y_offset += 20
            
            for ftype, count in sorted(type_counts.items()):
                color = self.field_colors.get(ftype, '#000000')
                color_rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
                
                # Draw color square
                draw.rectangle([15, y_offset, 25, y_offset+10], fill=color_rgb)
                
                # Draw text
                draw.text((30, y_offset-2), f"{ftype}: {count}", fill='black')
                y_offset += 15
            
            # Draw detection method breakdown
            y_offset += 10
            draw.text((10, y_offset), "Detection Methods:", fill='black')
            y_offset += 20
            
            for method, count in sorted(method_counts.items()):
                if method.startswith('merged_'):
                    method_display = "merged"
                else:
                    method_display = method.replace('_', ' ')
                
                draw.text((15, y_offset), f"{method_display}: {count}", fill='black')
                y_offset += 15
                
                if y_offset > img_height - 20:
                    break
            
            return img
            
        except Exception as e:
            print(f"Summary image error: {e}")
            # Return blank image on error
            return Image.new('RGB', (400, 300), 'white')
    
    def create_field_legend(self) -> Image.Image:
        """Create a legend showing field type colors."""
        try:
            img_width, img_height = 300, 250
            img = Image.new('RGB', (img_width, img_height), 'white')
            draw = ImageDraw.Draw(img)
            
            # Draw title
            draw.text((10, 10), "Field Type Legend", fill='black')
            
            y_offset = 35
            for field_type, color in self.field_colors.items():
                if y_offset > img_height - 20:
                    break
                    
                # Convert hex to RGB
                color_rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
                
                # Draw color rectangle
                draw.rectangle([15, y_offset, 35, y_offset+15], 
                             fill=color_rgb, outline='black')
                
                # Draw field type name
                draw.text((45, y_offset+2), field_type, fill='black')
                
                y_offset += 20
            
            return img
            
        except Exception as e:
            print(f"Legend creation error: {e}")
            return Image.new('RGB', (300, 250), 'white')