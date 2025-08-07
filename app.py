import streamlit as st
import io
from pdf_analyzer import PDFFormAnalyzer
import pandas as pd
import fitz  # PyMuPDF
from PIL import Image, ImageDraw

# Set page configuration
st.set_page_config(
    page_title="PDF Form Field Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for modern UI
st.markdown("""
<style>
/* Import Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Global Variables - Light Theme */
:root {
    --primary-color: #3b82f6;
    --primary-hover: #2563eb;
    --primary-light: #dbeafe;
    --secondary-color: #6b7280;
    --success-color: #10b981;
    --warning-color: #f59e0b;
    --error-color: #ef4444;
    --background: #ffffff;
    --card-background: #ffffff;
    --surface: #f9fafb;
    --border-color: #e5e7eb;
    --border-light: #f3f4f6;
    --text-primary: #111827;
    --text-secondary: #6b7280;
    --text-muted: #9ca3af;
    --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
    --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
    --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
    --radius-sm: 0.375rem;
    --radius-md: 0.5rem;
    --radius-lg: 0.75rem;
}

/* Main App Styling */
.main .block-container {
    padding-top: 2rem;
    max-width: 1200px;
    font-family: 'Inter', sans-serif;
}

/* Header Styling */
h1 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    font-size: 2.5rem !important;
    color: var(--text-primary) !important;
    margin-bottom: 0.5rem !important;
    text-align: center !important;
    background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}

h2, h3, h4 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
}

/* Upload Area Styling - Light Theme */
.stFileUploader > div > div {
    border: 2px dashed var(--border-color) !important;
    border-radius: var(--radius-lg) !important;
    background: var(--surface) !important;
    padding: 3rem !important;
    text-align: center !important;
    transition: all 0.2s ease !important;
    position: relative !important;
}

.stFileUploader > div > div:hover {
    border-color: var(--primary-color) !important;
    background: var(--primary-light) !important;
    transform: translateY(-2px) !important;
}

.stFileUploader > div > div::before {
    content: "📄";
    font-size: 3rem;
    display: block;
    margin-bottom: 1rem;
}

/* Metrics Card Container */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
    margin: 2rem 0;
}

/* Status Badges */
.status-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.status-success {
    background: #d1fae5;
    color: var(--success-color);
}

.status-error {
    background: #fee2e2;
    color: var(--error-color);
}

/* Table Styling */
.stDataFrame {
    border-radius: var(--radius-md) !important;
    overflow: hidden !important;
    box-shadow: var(--shadow-sm) !important;
    border: 1px solid var(--border-color) !important;
}

/* Tab Styling - Light Theme */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    background: var(--surface);
    padding: 0.25rem;
    border-radius: var(--radius-lg);
    border: 1px solid var(--border-light);
}

.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    padding: 0.75rem 1rem !important;
    transition: all 0.2s ease !important;
    border: none !important;
}

.stTabs [aria-selected="true"] {
    background: var(--card-background) !important;
    color: var(--text-primary) !important;
    box-shadow: var(--shadow-sm) !important;
    border: 1px solid var(--border-color) !important;
}

/* Expander Styling - Light Theme */
.streamlit-expanderHeader {
    background: var(--surface) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: var(--radius-md) !important;
    font-weight: 500 !important;
    color: var(--text-primary) !important;
    margin-bottom: 0.5rem !important;
    padding: 1rem !important;
    transition: all 0.2s ease !important;
}

.streamlit-expanderHeader:hover {
    background: var(--card-background) !important;
    box-shadow: var(--shadow-sm) !important;
    border-color: var(--primary-color) !important;
}

.streamlit-expanderContent {
    background: var(--card-background) !important;
    border: 1px solid var(--border-color) !important;
    border-top: none !important;
    border-radius: 0 0 var(--radius-md) var(--radius-md) !important;
    padding: 1.5rem !important;
    box-shadow: var(--shadow-sm) !important;
}

/* Button Styling */
.stButton > button {
    background: var(--primary-color) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius-md) !important;
    font-weight: 500 !important;
    padding: 0.75rem 1.5rem !important;
    transition: all 0.2s ease !important;
    box-shadow: var(--shadow-sm) !important;
    font-family: 'Inter', sans-serif !important;
}

.stButton > button:hover {
    background: var(--primary-hover) !important;
    box-shadow: var(--shadow-md) !important;
    transform: translateY(-1px) !important;
}

/* Progress Bar */
.stProgress > div > div {
    background: linear-gradient(90deg, var(--primary-color), var(--primary-hover)) !important;
    border-radius: 9999px !important;
    height: 0.75rem !important;
}

.stProgress > div {
    background: var(--border-color) !important;
    border-radius: 9999px !important;
}

/* Alert Styling */
.stAlert {
    border-radius: var(--radius-md) !important;
    border: none !important;
    box-shadow: var(--shadow-sm) !important;
    font-family: 'Inter', sans-serif !important;
}

/* Chart Container */
.chart-container {
    background: white;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    box-shadow: var(--shadow-sm);
    margin: 1rem 0;
}

/* Custom spacing */
.section-spacing {
    margin: 2rem 0;
}

.divider {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--border-color), transparent);
    margin: 2rem 0;
}

/* Hide Streamlit Branding */
.css-1rs6os, .css-17ziqus, #MainMenu, footer, header {
    visibility: hidden !important;
}

/* Custom metric cards - Light Theme */
[data-testid="metric-container"] {
    background: var(--card-background);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    box-shadow: var(--shadow-sm);
    transition: all 0.2s ease;
}

[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
    border-color: var(--primary-color);
}

[data-testid="metric-container"] [data-testid="metric-label"] {
    color: var(--text-secondary) !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

[data-testid="metric-container"] [data-testid="metric-value"] {
    color: var(--primary-color) !important;
    font-size: 2rem !important;
    font-weight: 700 !important;
}
</style>
""", unsafe_allow_html=True)

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
    
    if field_count > 0:
        # Display PDF visualization
        st.markdown("#### PDF Form Preview")
        
        # Add toggle for field highlighting (unique key for each file)
        checkbox_key = f"highlight_{file_index}_{result['filename']}" if total_files > 1 else "highlight_fields"
        highlight_fields = st.checkbox(
            "🎯 Highlight fillable fields", 
            value=True, 
            help="Show colored rectangles around detected form fields",
            key=checkbox_key
        )
        
        if highlight_fields:
            st.markdown("**Legend:** 🔴 Text Fields | 🔵 Buttons/Checkboxes | 🟢 Dropdowns | 🟠 Other Fields")
            st.info("💡 Colored rectangles will appear around fillable form fields on the PDF pages below.")
        
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
                    # Group fields by page for display
                    page_field_counts = {}
                    for field in fields:
                        page = field.get("page", "Unknown")
                        if page != "Unknown":
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
        
        # Field analysis section
        st.markdown("#### Field Analysis")
        
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
        
        # Add expandable individual page sections
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
    # Modern header with improved design
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="margin-bottom: 0.5rem;">📄 PDF Form Field Analyzer</h1>
        <p style="font-size: 1.25rem; color: var(--text-secondary); margin-bottom: 0; font-weight: 400;">
            Upload PDF forms to analyze and count fillable fields with precision
        </p>
        <div style="width: 60px; height: 4px; background: linear-gradient(90deg, var(--primary-color), var(--primary-hover)); 
                    margin: 1rem auto; border-radius: 2px;"></div>
    </div>
    """, unsafe_allow_html=True)
    
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
        # Modern info card
        st.markdown("""
        <div style="background: var(--card-background); 
                    border: 1px solid var(--border-color); 
                    border-radius: var(--radius-lg); 
                    padding: 1.5rem; 
                    margin-bottom: 1rem;
                    box-shadow: var(--shadow-sm);">
            <h3 style="color: var(--text-primary); margin-bottom: 1rem; font-size: 1.125rem; font-weight: 600;">✨ Supported Field Types</h3>
        """, unsafe_allow_html=True)
        
        field_types = [
            ("📝", "Text Fields"), ("☑️", "Checkboxes"), ("🔘", "Radio Buttons"),
            ("📋", "Dropdown Lists"), ("✍️", "Signature Fields"), ("🖱️", "Button Fields")
        ]
        
        for icon, name in field_types:
            st.markdown(f"""
            <div style="margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1.1rem;">{icon}</span>
                <span style="color: var(--text-primary); font-weight: 500;">{name}</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Help section
        st.markdown("""
        <div style="background: var(--primary-light); 
                    border: 1px solid var(--primary-color); 
                    border-radius: var(--radius-lg); 
                    padding: 1.25rem;
                    box-shadow: var(--shadow-sm);">
            <h4 style="color: var(--primary-color); margin-bottom: 0.75rem; font-size: 0.95rem; font-weight: 600;">💡 Field Counting</h4>
            <p style="font-size: 0.85rem; color: var(--text-primary); margin: 0; line-height: 1.5;">
                Each interactive element counts as one field. Groups of radio buttons are counted individually.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
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