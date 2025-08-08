import streamlit as st
import io
from pdf_analyzer_focused import PDFFormAnalyzerFocused as PDFFormAnalyzer
import pandas as pd
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
from field_visualizer import FieldVisualizer

# Set page configuration
st.set_page_config(
    page_title="PDF Form Field Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def highlight_fields_on_page(pdf_document, page_num, fields, zoom_factor=1.5):
    """
    Highlight form fields on a PDF page using comprehensive field detection.
    """
    # Filter fields for this page - only interactive fields for fillable PDFs
    # All fields for static PDFs
    page_fields = []
    is_fillable = False
    
    # Check if this is a fillable PDF (has interactive fields)
    interactive_fields = [f for f in fields if f.get('is_interactive', False)]
    if len(interactive_fields) > 50:
        is_fillable = True
        # For fillable PDFs, only highlight interactive fields
        page_fields = [f for f in fields if f.get("page") == page_num + 1 and f.get('is_interactive', False)]
    else:
        # For static PDFs, highlight all detected fields
        page_fields = [f for f in fields if f.get("page") == page_num + 1]
    
    # Render page to image
    page = pdf_document[page_num]
    mat = fitz.Matrix(zoom_factor, zoom_factor)
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))
    
    # Create overlay for highlighting
    overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Color mapping for field types
    field_colors = {
        'Text Field': (255, 107, 107),      # Red
        'Checkbox': (78, 205, 196),         # Teal  
        'Radio Button': (69, 183, 209),     # Blue
        'Dropdown': (150, 206, 180),        # Green
        'Signature Field': (255, 234, 167), # Yellow
        'Button': (221, 160, 221),          # Plum
        'List Box': (152, 216, 200),        # Mint
        'Unknown Field': (255, 105, 180),   # Hot Pink
    }
    
    # Draw highlights for each field
    field_highlights = 0
    for field in page_fields:
        rect = field.get('rect', [0, 0, 0, 0])
        
        # Skip invalid rectangles
        if len(rect) != 4 or (rect[0] == 0 and rect[1] == 792 and rect[2] == 0 and rect[3] == 792):
            continue
            
        # Scale rectangle coordinates
        x1, y1, x2, y2 = [coord * zoom_factor for coord in rect]
        
        # Skip tiny fields
        if abs(x2 - x1) < 2 or abs(y2 - y1) < 2:
            continue
        
        # Get field type and color
        field_type = field.get('type', 'Unknown Field')
        color_rgb = field_colors.get(field_type, field_colors['Unknown Field'])
        
        # Draw semi-transparent rectangle
        fill_color = (*color_rgb, 40)   # Semi-transparent fill
        outline_color = (*color_rgb, 200)  # More opaque outline
        
        draw.rectangle([x1, y1, x2, y2], 
                      fill=fill_color, 
                      outline=outline_color, 
                      width=2)
        field_highlights += 1
    
    # Combine base image with overlay
    result = Image.alpha_composite(img.convert('RGBA'), overlay)
    
    return result.convert('RGB'), field_highlights

def process_single_pdf(pdf_file, analyzer, file_index=0, total_files=1):
    """Process a single PDF file and return analysis results."""
    try:
        # Progress indicator for batch processing
        if total_files > 1:
            with st.spinner(f"Analyzing {pdf_file.name} ({file_index+1}/{total_files})..."):
                pdf_bytes = pdf_file.read()
                analysis_result = analyzer.analyze_pdf(pdf_bytes)
        else:
            with st.spinner("Analyzing PDF form fields..."):
                pdf_bytes = pdf_file.read()
                analysis_result = analyzer.analyze_pdf(pdf_bytes)
        
        # Add file metadata to result
        analysis_result["filename"] = pdf_file.name
        analysis_result["file_size"] = pdf_file.size
        analysis_result["pdf_bytes"] = pdf_bytes
        
        return analysis_result
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "filename": pdf_file.name,
            "file_size": pdf_file.size
        }

def display_batch_summary(results):
    """Display summary table and statistics for batch processing."""
    st.markdown("### Batch Analysis Summary")
    
    # Create summary data
    summary_data = []
    total_fields = 0
    
    for result in results:
        if result["success"]:
            field_count = len(result["fields"])
            total_fields += field_count
            
            # Get field types breakdown
            field_types = [field.get("type", "Unknown") for field in result["fields"]]
            unique_types = len(set(field_types))
            
            summary_data.append({
                "Filename": result["filename"],
                "Status": "✅ Success",
                "Fields Found": field_count,
                "Field Types": unique_types,
                "File Size": f"{result['file_size']:,} bytes"
            })
        else:
            summary_data.append({
                "Filename": result["filename"],
                "Status": "❌ Failed",
                "Fields Found": 0,
                "Field Types": 0,
                "File Size": f"{result['file_size']:,} bytes"
            })
    
    # Display summary table
    if summary_data:
        df = pd.DataFrame(summary_data)
        st.dataframe(df, use_container_width=True)
        
        # Overall statistics
        successful_files = sum(1 for result in results if result["success"])
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Files Processed", len(results))
        with col2:
            st.metric("Successful", successful_files)
        with col3:
            st.metric("Total Fields Found", total_fields)
        with col4:
            avg_fields = total_fields / successful_files if successful_files > 0 else 0
            st.metric("Avg Fields per PDF", f"{avg_fields:.1f}")

def display_pdf_analysis(result, file_index, total_files):
    """Display detailed analysis for a single PDF."""
    fields = result["fields"]
    field_count = len(fields)
    pdf_bytes = result["pdf_bytes"]
    
    # Header for individual file in batch
    if total_files > 1:
        st.markdown(f"### 📄 {result['filename']}")
    else:
        st.markdown("### Analysis Results")
    
    # Display document type and comprehensive field analysis
    if "document_type" in result:
        doc_type = result["document_type"]
        total_count = result.get("total_field_count", field_count)
        advanced_count = result.get("advanced_field_count", 0)
        visual_count = result.get("visual_field_count", 0) 
        interactive_count = result.get("interactive_field_count", 0)
        
        # Header with document type
        st.info(f"📄 Document Type: **{doc_type}**")
        
        # Show appropriate metrics based on PDF type
        is_fillable = result.get("is_fillable_pdf", False)
        
        if is_fillable:
            # For fillable PDFs, show only interactive field count to match highlighted fields
            st.metric("📝 Fillable Fields", interactive_count, help="Interactive PDF form fields (these are highlighted below)")
        else:
            # For static PDFs, show advanced detection prominently
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🎯 Form Fields", total_count, help="All detected fillable areas")
            with col2:
                st.metric("🔍 Advanced Detection", advanced_count, help="Fields found via layout analysis")  
            with col3:
                st.metric("👁️ Visual Patterns", visual_count, help="Pattern-based visual fields")
        
        # Detection quality analysis
        if total_count > 0:
            if advanced_count >= total_count * 0.7:
                st.success(f"✅ **High Accuracy Detection**: {advanced_count} fields detected via advanced layout analysis")
            elif interactive_count > 50:
                st.success(f"✅ **Modern Interactive Form**: {interactive_count} digital form widgets detected")
            else:
                st.info(f"📊 **Mixed Detection**: Combined {total_count} fields from multiple detection methods")
            
            # Show detection method breakdown and field types
            with st.expander("🔍 Detection Method Details", expanded=False):
                # Count field types
                fields = result.get("fields", [])
                field_types = {}
                for field in fields:
                    ftype = field.get('type', 'Unknown')
                    field_types[ftype] = field_types.get(ftype, 0) + 1
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Detection Methods:**")
                    st.markdown(f"""
                    • **Advanced Layout Analysis**: {advanced_count} fields  
                      - Text positioning and form patterns  
                    • **Interactive Widgets**: {interactive_count} fields  
                      - Native PDF form elements  
                    • **Visual Pattern Detection**: {visual_count} fields  
                      - Checkbox symbols and underlines  
                    """)
                
                with col2:
                    st.markdown("**Field Types Found:**")
                    for ftype, count in sorted(field_types.items()):
                        if ftype == 'Unknown Field':
                            st.markdown(f"• **{ftype}**: {count} 🔍 (highlighted in pink)")
                        else:
                            st.markdown(f"• **{ftype}**: {count}")
                
                # Show warning if unknown fields exist
                unknown_count = field_types.get('Unknown Field', 0)
                if unknown_count > 0:
                    st.warning(f"⚠️ {unknown_count} fields could not be classified and are highlighted in pink for review")
        else:
            st.warning("⚠️ No form fields detected - this may be a non-interactive document")
    
    
    if field_count > 0:
        # Enhanced PDF Preview Section (collapsible)
        with st.expander("📄 Enhanced PDF Form Preview", expanded=False):
            # Add visualization options
            col1, col2 = st.columns(2)
            
            with col1:
                checkbox_key = f"highlight_{file_index}_{result['filename']}" if total_files > 1 else "highlight_fields"
                highlight_fields = st.checkbox(
                    "🎯 Enhanced Field Highlighting", 
                    value=True, 
                    help="Show advanced field detection overlays",
                    key=checkbox_key
                )
            
            with col2:
                show_legend_key = f"legend_{file_index}_{result['filename']}" if total_files > 1 else "show_legend"
                show_legend = st.checkbox(
                    "📋 Show Field Legend",
                    value=True,
                    help="Display field type color legend",
                    key=show_legend_key
                )
            
            if highlight_fields and show_legend:
                # Create and show field legend
                visualizer = FieldVisualizer()
                legend_img = visualizer.create_field_legend()
                st.image(legend_img, caption="Field Type Legend", width=300)
            
            if highlight_fields:
                st.info("💡 Colored rectangles highlight fillable form fields. Colors indicate field types.")
            
            try:
                # Convert PDF to images using PyMuPDF
                with st.spinner("Rendering PDF preview..."):
                    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
                page_count = len(pdf_document)
                
                # Limit to first 3 pages for performance
                pages_to_show = min(3, page_count)
                page_images = []
                highlighted_counts = []
                
                for page_num in range(pages_to_show):
                    if highlight_fields:
                        img, highlighted_count = highlight_fields_on_page(pdf_document, page_num, fields)
                        highlighted_counts.append(highlighted_count)
                    else:
                        page = pdf_document[page_num]
                        mat = fitz.Matrix(1.5, 1.5)
                        pix = page.get_pixmap(matrix=mat)
                        img_data = pix.tobytes("png")
                        img = Image.open(io.BytesIO(img_data))
                        highlighted_counts.append(0)
                    
                    page_images.append(img)
                
                if page_images:
                    # Group fields by page for display - count only what will be highlighted
                    page_field_counts = {}
                    is_fillable = result.get("is_fillable_pdf", False)
                    
                    for field in fields:
                        page = field.get("page", "Unknown")
                        if page != "Unknown":
                            # For fillable PDFs, only count interactive fields
                            # For static PDFs, count all fields
                            if is_fillable:
                                if field.get('is_interactive', False):
                                    page_field_counts[page] = page_field_counts.get(page, 0) + 1
                            else:
                                page_field_counts[page] = page_field_counts.get(page, 0) + 1
                    
                    # Display PDF pages
                    if len(page_images) == 1:
                        page_fields = page_field_counts.get(1, 0)
                        if highlight_fields and len(highlighted_counts) > 0:
                            caption = f"Page 1 - {page_fields} fields ({highlighted_counts[0]} highlighted)"
                        else:
                            caption = f"Page 1 - {page_fields} fillable fields detected"
                        st.image(page_images[0], caption=caption, use_container_width=True)
                    else:
                        cols = st.columns(min(len(page_images), 3))
                        for i, page_img in enumerate(page_images):
                            with cols[i]:
                                page_num = i + 1
                                page_fields = page_field_counts.get(page_num, 0)
                                if highlight_fields and i < len(highlighted_counts):
                                    caption = f"Page {page_num} - {page_fields} fields ({highlighted_counts[i]} highlighted)"
                                else:
                                    caption = f"Page {page_num} - {page_fields} fields"
                                st.image(page_img, caption=caption, use_container_width=True)
                        
                        if page_count > 3:
                            st.info(f"Showing first 3 pages. PDF contains {page_count} total pages.")
                
                    pdf_document.close()
                    
            except ImportError as e:
                st.error("PDF visualization library not available. The field analysis will continue to work.")
                st.info("Note: PDF preview feature is temporarily unavailable.")
            except Exception as e:
                st.warning(f"PDF preview unavailable: {str(e)}")
                st.info("The field counting and analysis features are still working normally.")
        
        # Display summary metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Fields", field_count)
        
        with col2:
            field_types = [field.get("type", "Unknown") for field in fields]
            unique_types = len(set(field_types))
            st.metric("Field Types", unique_types)
        
        with col3:
            required_fields = sum(1 for field in fields if field.get("required", False))
            st.metric("Required Fields", required_fields)
        
        # Field Analysis Section (collapsible)
        with st.expander("📊 Field Analysis", expanded=False):
            # Create tabs for different analysis views
            tab_key_prefix = f"tabs_{file_index}_" if total_files > 1 else "tabs_"
            analysis_tab1, analysis_tab2 = st.tabs(["📊 Field Types", "📄 By Page"])
            
            with analysis_tab1:
                st.markdown("**Field Type Breakdown**")
                type_counts = {}
                for field in fields:
                    field_type = field.get("type", "Unknown")
                    type_counts[field_type] = type_counts.get(field_type, 0) + 1
                
                # Create a dataframe for the breakdown
                breakdown_df = pd.DataFrame([
                    {"Field Type": field_type, "Count": count}
                    for field_type, count in type_counts.items()
                ])
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.dataframe(breakdown_df, use_container_width=True)
                
                with col2:
                    if len(breakdown_df) > 0:
                        st.bar_chart(breakdown_df.set_index("Field Type"))
            
            with analysis_tab2:
                st.markdown("**Fields by Page**")
                page_breakdown = {}
                for field in fields:
                    page = field.get("page", "Unknown")
                    page_breakdown[f"Page {page}"] = page_breakdown.get(f"Page {page}", 0) + 1
                
                page_df = pd.DataFrame([
                    {"Page": page, "Field Count": count}
                    for page, count in page_breakdown.items()
                ])
                
                if len(page_df) > 0:
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.dataframe(page_df, use_container_width=True)
                    with col2:
                        st.bar_chart(page_df.set_index("Page"))
        
        # Individual Page Details Section (collapsible)
        with st.expander("📄 Individual Page Details", expanded=False):
            st.info("Click on any page below to view it in high resolution with detailed field information.")
            
            # Group fields by page for the individual sections
            page_field_counts = {}
            for field in fields:
                page = field.get("page", "Unknown")
                if page != "Unknown":
                    page_field_counts[page] = page_field_counts.get(page, 0) + 1
            
            # Create expandable sections for each page
            try:
                # Open PDF to get actual page count
                pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
                actual_page_count = len(pdf_document)
                pdf_document.close()
            except:
                actual_page_count = max(page_field_counts.keys()) if page_field_counts else 1
            
            # Show all pages, limited to reasonable number for performance
            max_pages_to_show = min(actual_page_count, 10)
            for page_num in range(1, max_pages_to_show + 1):
                page_fields = page_field_counts.get(page_num, 0)
                
                # Create expander title with page info
                expander_title = f"📄 Page {page_num}"
                if page_fields > 0:
                    expander_title += f" - {page_fields} fillable fields"
                else:
                    expander_title += " - No fillable fields detected"
                
                with st.expander(expander_title, expanded=False):
                    # Two columns: image and field details
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"**High Resolution View - Page {page_num}**")
                        try:
                            # Render this specific page on demand with higher resolution
                            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
                            if page_num <= len(pdf_document):
                                if st.session_state.get(checkbox_key, True):  # Check if highlighting is enabled
                                    page_img, highlighted_count = highlight_fields_on_page(pdf_document, page_num-1, fields, zoom_factor=2.0)
                                    st.image(page_img, caption=f"Page {page_num} - {page_fields} fields ({highlighted_count} highlighted)", use_container_width=True)
                                else:
                                    page = pdf_document[page_num-1]
                                    mat = fitz.Matrix(2.0, 2.0)  # Higher zoom for detailed view
                                    pix = page.get_pixmap(matrix=mat)
                                    img_data = pix.tobytes("png")
                                    img = Image.open(io.BytesIO(img_data))
                                    st.image(img, caption=f"Page {page_num} - {page_fields} fields", use_container_width=True)
                            else:
                                st.info(f"Page {page_num} not found in the PDF.")
                            pdf_document.close()
                        except Exception as e:
                            st.warning(f"Could not render page {page_num}: {str(e)}")
                    
                    with col2:
                        st.markdown(f"**Page {page_num} Summary**")
                        
                        # Show fields specific to this page
                        page_specific_fields = [f for f in fields if f.get("page") == page_num]
                        if page_specific_fields:
                            st.metric("Fields on this page", len(page_specific_fields))
                            
                            # Group by field type
                            field_types_on_page = {}
                            for field in page_specific_fields:
                                field_type = field.get('type', 'Unknown')
                                field_types_on_page[field_type] = field_types_on_page.get(field_type, 0) + 1
                            
                            st.markdown("**Field Types:**")
                            for field_type, count in field_types_on_page.items():
                                st.write(f"• {field_type}: {count}")
                            
                            st.markdown("**Field Details:**")
                            for i, field in enumerate(page_specific_fields, 1):
                                field_name = field.get('name', f'Field_{i}')
                                field_type = field.get('type', 'Unknown')
                                required = "Required" if field.get('required', False) else "Optional"
                                st.write(f"{i}. **{field_name}**")
                                st.write(f"   Type: {field_type}")
                                st.write(f"   Status: {required}")
                                if field.get('default_value'):
                                    st.write(f"   Default: {field.get('default_value')}")
                                if i < len(page_specific_fields):
                                    st.write("---")
                        else:
                            st.info("No fillable fields detected on this page.")
                            st.write("This page may contain:")
                            st.write("• Static text content")
                            st.write("• Images or graphics") 
                            st.write("• Non-interactive elements")
    
    else:
        st.info("No fillable fields detected in this PDF.")
        st.write("This PDF may contain:")
        st.write("• Static text content only")
        st.write("• Images or graphics")
        st.write("• Non-interactive elements")

def main():
    st.title("📄 PDF Form Field Analyzer")
    st.markdown("Upload PDF forms to analyze and count fillable fields")
    
    # Create two columns for better layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Upload PDF Files")
        
        # Toggle between single and batch mode
        upload_mode = st.radio(
            "Upload Mode:",
            ["Single PDF", "Multiple PDFs (Batch Analysis)"],
            horizontal=True
        )
        
        if upload_mode == "Single PDF":
            uploaded_files = st.file_uploader(
                "Choose a PDF file",
                type="pdf",
                help="Upload a PDF form to analyze its fillable fields"
            )
            if uploaded_files:
                uploaded_files = [uploaded_files]  # Convert to list for consistent processing
        else:
            uploaded_files = st.file_uploader(
                "Choose PDF files", 
                type="pdf",
                accept_multiple_files=True,
                help="Upload multiple PDF forms to analyze and compare their fillable fields"
            )
    
    with col2:
        st.markdown("### Supported Field Types")
        st.markdown("""
        - Text fields
        - Checkboxes  
        - Radio buttons
        - Dropdown lists
        - Signature fields
        - Button fields
        """)
    
    if uploaded_files is not None and len(uploaded_files) > 0:
        # Display file information and batch summary
        st.markdown("---")
        
        if len(uploaded_files) == 1:
            st.markdown("### Single PDF Analysis")
            file_details = {
                "Filename": uploaded_files[0].name,
                "File size": f"{uploaded_files[0].size:,} bytes"
            }
            
            col1, col2 = st.columns(2)
            with col1:
                for key, value in file_details.items():
                    st.write(f"**{key}:** {value}")
        else:
            st.markdown("### Batch PDF Analysis")
            st.info(f"Analyzing {len(uploaded_files)} PDF files...")
            
            # Show summary of files
            total_size = sum(f.size for f in uploaded_files)
            st.write(f"**Total files:** {len(uploaded_files)}")
            st.write(f"**Total size:** {total_size:,} bytes")
        
        # Initialize the analyzer
        analyzer = PDFFormAnalyzer()
        
        # Process all uploaded files
        all_results = []
        
        for i, uploaded_file in enumerate(uploaded_files):
            result = process_single_pdf(uploaded_file, analyzer, i, len(uploaded_files))
            if not result["success"]:
                st.error(f"Error processing {uploaded_file.name}: {result.get('error', 'Unknown error')}")
            all_results.append(result)
        
        # Display batch summary if multiple files
        if len(uploaded_files) > 1:
            st.markdown("---")
            display_batch_summary(all_results)
        
        # Display detailed analysis for each successful file
        for i, result in enumerate(all_results):
            if result["success"]:
                st.markdown("---")
                display_pdf_analysis(result, i, len(uploaded_files))
        
        # Explanation of what's being counted
        st.markdown("---")
        with st.expander("ℹ️ What counts as a fillable field?", expanded=False):
            st.markdown("""
            **Fillable fields detected by this analyzer include:**
            - **Text Fields** 📝: Input boxes where users can type text, numbers, or dates
            - **Checkboxes** ☑️: Square boxes that can be checked or unchecked
            - **Radio Buttons** 🔘: Circular buttons for selecting one option from a group
            - **Dropdown Lists** 📋: Menus that expand to show multiple choice options
            - **Signature Fields** ✍️: Areas designated for digital signatures
            - **Push Buttons** 🔲: Interactive buttons that trigger actions
            
            **Note:** Only interactive form elements are counted. Regular text, images, or non-interactive content is not included in the count.
            """)
    
    else:
        st.info("👆 Upload one or more PDF files above to get started!")

if __name__ == "__main__":
    main()