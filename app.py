import streamlit as st
import pandas as pd
import io
from pdf_analyzer import PDFFormAnalyzer
import fitz  # PyMuPDF
from PIL import Image, ImageDraw

# Set page configuration
st.set_page_config(
    page_title="PDF Form Field Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def highlight_fields_on_page(pdf_document, page_num, fields, zoom_factor=1.5):
    """
    Highlight form fields on a PDF page by drawing colored rectangles around them.
    """
    page = pdf_document[page_num]
    
    # Render page to image with good quality
    mat = fitz.Matrix(zoom_factor, zoom_factor)
    pix = page.get_pixmap(matrix=mat)
    
    # Convert to PIL Image
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))
    
    # Create drawing context
    draw = ImageDraw.Draw(img)
    
    # Get page fields for this specific page
    page_fields = [f for f in fields if f.get("page") == page_num + 1]
    
    # Try to get field rectangles from the page
    field_highlights = 0
    try:
        # Get all widgets (form fields) on this page
        widgets = page.widgets()
        
        for widget in widgets:
            # Get widget rectangle
            rect = widget.rect
            
            # Scale rectangle coordinates by zoom factor
            x1, y1, x2, y2 = rect.x0 * zoom_factor, rect.y0 * zoom_factor, rect.x1 * zoom_factor, rect.y1 * zoom_factor
            
            # Choose color based on field type
            field_type = getattr(widget, 'field_type', 0)
            if field_type == 1:  # Text field
                color = "red"
            elif field_type == 2:  # Button/Checkbox
                color = "blue"
            elif field_type == 3:  # Choice/Dropdown
                color = "green"
            else:
                color = "orange"
            
            # Draw rectangle around the field
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
            field_highlights += 1
    
    except Exception:
        # If we can't extract widget positions, just return the original image
        pass
    
    return img, field_highlights

def main():
    st.title("📄 PDF Form Field Analyzer")
    st.markdown("Upload PDF forms to analyze and count fillable fields")
    
    # Create two columns for better layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Upload PDF File")
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type="pdf",
            help="Upload a PDF form to analyze its fillable fields"
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
    
    if uploaded_file is not None:
        # Display file information
        st.markdown("---")
        file_details = {
            "Filename": uploaded_file.name,
            "File size": f"{uploaded_file.size:,} bytes"
        }
        
        col1, col2 = st.columns(2)
        with col1:
            for key, value in file_details.items():
                st.write(f"**{key}:** {value}")
        
        # Process the PDF
        try:
            with st.spinner("Analyzing PDF form fields..."):
                # Read the uploaded file
                pdf_bytes = uploaded_file.read()
                
                # Initialize the analyzer
                analyzer = PDFFormAnalyzer()
                
                # Analyze the PDF
                analysis_result = analyzer.analyze_pdf(pdf_bytes)
                
                if analysis_result["success"]:
                    fields = analysis_result["fields"]
                    field_count = len(fields)
                    
                    # Display results
                    st.markdown("---")
                    st.markdown("### Analysis Results")
                    
                    if field_count > 0:
                        # Display PDF visualization
                        st.markdown("#### PDF Form Preview")
                        
                        # Add toggle for field highlighting
                        highlight_fields = st.checkbox(
                            "🎯 Highlight fillable fields", 
                            value=True, 
                            help="Show colored rectangles around detected form fields"
                        )
                        
                        if highlight_fields:
                            st.markdown("**Legend:** 🔴 Text Fields | 🔵 Buttons/Checkboxes | 🟢 Dropdowns | 🟠 Other Fields")
                            st.info("💡 Colored rectangles will appear around fillable form fields on the PDF pages below.")
                        
                        try:
                            # Convert PDF to images using PyMuPDF
                            with st.spinner("Rendering PDF preview..."):
                                # Open PDF from bytes
                                pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
                                page_count = len(pdf_document)
                                
                                # Limit to first 3 pages for performance
                                pages_to_show = min(3, page_count)
                                page_images = []
                                highlighted_counts = []
                                
                                for page_num in range(pages_to_show):
                                    if highlight_fields:
                                        # Use highlighting function
                                        img, highlighted_count = highlight_fields_on_page(pdf_document, page_num, fields)
                                        highlighted_counts.append(highlighted_count)
                                    else:
                                        # Render normal page
                                        page = pdf_document[page_num]
                                        mat = fitz.Matrix(1.5, 1.5)  # zoom factor
                                        pix = page.get_pixmap(matrix=mat)
                                        img_data = pix.tobytes("png")
                                        img = Image.open(io.BytesIO(img_data))
                                        highlighted_counts.append(0)
                                    
                                    page_images.append(img)
                                
                                if page_images:
                                    st.success(f"✅ Successfully rendered {len(page_images)} page(s)")
                                    
                                    # Group fields by page for display
                                    page_field_counts = {}
                                    for field in fields:
                                        page = field.get("page", "Unknown")
                                        if page != "Unknown":
                                            page_field_counts[page] = page_field_counts.get(page, 0) + 1
                                    
                                    # Display PDF pages in columns
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
                                
                                    # Close the PDF document after all processing
                                    pdf_document.close()
                                
                                else:
                                    st.warning("Could not render PDF preview - no pages generated.")
                        except ImportError as e:
                            st.error("PDF visualization library not available. The field analysis will continue to work.")
                            st.info("Note: PDF preview feature is temporarily unavailable.")
                        except Exception as e:
                            st.warning(f"PDF preview unavailable: {str(e)}")
                            st.info("The field counting and analysis features are still working normally.")
                        
                        # Add expandable individual page sections
                        if field_count > 0:
                            st.markdown("---")
                            st.markdown("#### Individual Page Details")
                            st.info("Click on any page below to view it in high resolution with detailed field information.")
                            
                            # Group fields by page for the individual sections
                            page_field_counts = {}
                            for field in fields:
                                page = field.get("page", "Unknown")
                                if page != "Unknown":
                                    page_field_counts[page] = page_field_counts.get(page, 0) + 1
                            
                            # Create expandable sections for each page
                            for page_num in range(1, 7):  # Show up to 6 pages
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
                                                if highlight_fields:
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
                                                st.write("---")
                                        else:
                                            st.info("No fillable fields detected on this page.")
                                            st.write("This page may contain:")
                                            st.write("• Static text content")
                                            st.write("• Images or graphics") 
                                            st.write("• Non-interactive elements")
                                
                                # Stop creating expanders if we've reached the end of the PDF
                                if page_num > 6:  # Limit to reasonable number of pages
                                    break
                        
                        st.markdown("---")
                        
                        # Explanation of what's being counted
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
                        
                        # Summary metrics
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
                        
                        # Field analysis section
                        st.markdown("#### Field Analysis")
                        
                        # Create tabs for different analysis views
                        analysis_tab1, analysis_tab2, analysis_tab3 = st.tabs(["📊 Field Types", "📄 By Page", "📈 Summary"])
                        
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
                                st.bar_chart(breakdown_df.set_index("Field Type"))
                        
                        with analysis_tab2:
                            st.markdown("**Fields by Page**")
                            # Group fields by page
                            page_counts = {}
                            for field in fields:
                                page = field.get("page", "Unknown")
                                if page not in page_counts:
                                    page_counts[page] = []
                                page_counts[page].append(field)
                            
                            if len(page_counts) > 1:
                                for page, page_fields in sorted(page_counts.items()):
                                    if page != "Unknown":
                                        st.markdown(f"**Page {page}** - {len(page_fields)} fields")
                                        page_field_types = {}
                                        for field in page_fields:
                                            field_type = field.get("type", "Unknown")
                                            page_field_types[field_type] = page_field_types.get(field_type, 0) + 1
                                        
                                        # Show field types on this page
                                        for field_type, count in page_field_types.items():
                                            st.write(f"  • {field_type}: {count}")
                                        st.markdown("---")
                            else:
                                st.info("Page information is not available for this PDF.")
                        
                        with analysis_tab3:
                            st.markdown("**Summary Statistics**")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.metric("Total Pages with Fields", len([p for p in page_counts.keys() if p != "Unknown"]) if 'page_counts' in locals() else "N/A")
                                st.metric("Text Fields", sum(1 for f in fields if f.get("type") == "Text Field"))
                                st.metric("Choice Fields", sum(1 for f in fields if "Choice" in f.get("type", "") or "Dropdown" in f.get("type", "")))
                            
                            with col2:
                                st.metric("Button/Checkbox Fields", sum(1 for f in fields if "Button" in f.get("type", "") or "Checkbox" in f.get("type", "")))
                                st.metric("Required Fields", sum(1 for f in fields if f.get("required", False)))
                                st.metric("Fields with Options", sum(1 for f in fields if f.get("options")))
                        
                        # Interactive field explorer
                        st.markdown("#### Interactive Field Explorer")
                        
                        # Create tabs for different views
                        tab1, tab2 = st.tabs(["📋 Field List", "🔍 Field Details"])
                        
                        with tab1:
                            # Create a detailed dataframe
                            detailed_data = []
                            for i, field in enumerate(fields, 1):
                                detailed_data.append({
                                    "#": i,
                                    "Field Name": field.get("name", f"Field_{i}"),
                                    "Type": field.get("type", "Unknown"),
                                    "Required": "Yes" if field.get("required", False) else "No",
                                    "Page": field.get("page", "N/A"),
                                    "Default Value": field.get("default_value", ""),
                                    "Options": ", ".join(field.get("options", [])) if field.get("options") else ""
                                })
                            
                            detailed_df = pd.DataFrame(detailed_data)
                            st.dataframe(detailed_df, use_container_width=True)
                        
                        with tab2:
                            # Field selector for detailed view
                            if fields:
                                field_names = [f"{i+1}. {field.get('name', f'Field_{i+1}')} ({field.get('type', 'Unknown')})" for i, field in enumerate(fields)]
                                selected_field_idx = st.selectbox(
                                    "Select a field to view details:",
                                    range(len(field_names)),
                                    format_func=lambda x: field_names[x]
                                )
                                
                                if selected_field_idx is not None:
                                    selected_field = fields[selected_field_idx]
                                    
                                    # Display selected field details
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        st.markdown("**Field Properties:**")
                                        st.write(f"**Name:** {selected_field.get('name', 'N/A')}")
                                        st.write(f"**Type:** {selected_field.get('type', 'Unknown')}")
                                        st.write(f"**Required:** {'Yes' if selected_field.get('required', False) else 'No'}")
                                        st.write(f"**Page:** {selected_field.get('page', 'N/A')}")
                                        
                                        if selected_field.get('default_value'):
                                            st.write(f"**Default Value:** {selected_field.get('default_value')}")
                                        
                                        if selected_field.get('description'):
                                            st.write(f"**Description:** {selected_field.get('description')}")
                                    
                                    with col2:
                                        if selected_field.get('options'):
                                            st.markdown("**Available Options:**")
                                            for opt in selected_field.get('options', []):
                                                st.write(f"• {opt}")
                                        
                                        # Additional field information
                                        if selected_field.get('type') == 'Text Field':
                                            st.info("💡 This is a text input field where users can type information.")
                                        elif 'Checkbox' in selected_field.get('type', ''):
                                            st.info("💡 This is a checkbox that users can check or uncheck.")
                                        elif 'Radio' in selected_field.get('type', ''):
                                            st.info("💡 This is a radio button for selecting one option from a group.")
                                        elif 'Choice' in selected_field.get('type', '') or 'Dropdown' in selected_field.get('type', ''):
                                            st.info("💡 This is a dropdown menu where users can select from predefined options.")
                                        elif 'Signature' in selected_field.get('type', ''):
                                            st.info("💡 This is a signature field for digital signatures.")
                                        elif 'Button' in selected_field.get('type', ''):
                                            st.info("💡 This is an interactive button element.")
                        
                        # Download option for results
                        csv = detailed_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Field Analysis (CSV)",
                            data=csv,
                            file_name=f"{uploaded_file.name}_field_analysis.csv",
                            mime="text/csv"
                        )
                        
                    else:
                        st.warning("No fillable fields found in this PDF.")
                        st.info("This might be because:")
                        st.markdown("""
                        - The PDF is not a form (just a regular document)
                        - The form fields are not properly defined
                        - The PDF is an image-based scan without interactive fields
                        - The PDF structure is not supported
                        """)
                
                else:
                    st.error(f"Error analyzing PDF: {analysis_result['error']}")
                    st.info("Please ensure the uploaded file is a valid PDF with form fields.")
        
        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")
            st.info("Please try uploading a different PDF file or contact support if the issue persists.")
    
    else:
        # Instructions when no file is uploaded
        st.markdown("---")
        st.markdown("### How to Use")
        st.markdown("""
        1. **Upload a PDF file** using the file uploader above
        2. **Wait for analysis** - the app will process your PDF automatically
        3. **View results** - see the total count and details of fillable fields
        4. **Download analysis** - export the results as a CSV file
        
        **Note:** This tool works best with PDF forms that contain interactive fillable fields.
        Scanned documents or PDFs without form fields may not show any results.
        """)

if __name__ == "__main__":
    main()
