import streamlit as st
import google.generativeai as genai
import PyPDF2
import docx
import pandas as pd
import json
from io import BytesIO

# --- Configuration & Setup ---
st.set_page_config(page_title="Sandesh News Article Generator", layout="wide")

# Initialize session state variables to store the drafts and table data
if "current_article" not in st.session_state:
    st.session_state.current_article = ""
if "pesticide_data" not in st.session_state:
    st.session_state.pesticide_data = pd.DataFrame()

# --- Helper Functions ---
def extract_text_from_pdf(uploaded_file):
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        if page.extract_text():
            text += page.extract_text()
    return text

def create_word_docx(text):
    """Creates a Word document in memory for downloading."""
    doc = docx.Document()
    # Add a title
    doc.add_heading('કૃષિ લેખ (Sandesh News Draft)', 0)
    # Add the text content
    doc.add_paragraph(text)
    
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- Sidebar: API Key ---
st.sidebar.title("API Configuration")
api_key = st.sidebar.text_input("Gemini API Key", type="password")

# --- Main UI ---
st.title("📰 Sandesh News: Agri-Entomology Article Generator")
st.markdown("Extract label claims, select your chemicals, and generate a continuous paragraph article for Sandesh News.")

# --- Step 1: Label Claim Extraction Section ---
st.header("1. Upload Label Claim PDFs & Calculate Dose")
st.markdown("Upload up to 5 PDFs containing pesticide label claims to extract crops, pests, and calculate the 10-Liter pump dose.")

label_pdfs = st.file_uploader("Upload Label Claim PDFs (Max 5)", type=["pdf"], accept_multiple_files=True)

if label_pdfs:
    if len(label_pdfs) > 5:
        st.error("Please upload a maximum of 5 files.")
    else:
        if st.button("Extract Recommendations"):
            if not api_key:
                st.error("Please enter your Gemini API Key in the sidebar.")
            else:
                with st.spinner("Analyzing label claims and calculating doses..."):
                    genai.configure(api_key=api_key)
                    # Using Flash for fast data extraction. Update to 'gemini-3-flash-preview' when available in your tier.
                    model = genai.GenerativeModel('gemini-3-flash-preview', 
                                                  generation_config=genai.GenerationConfig(response_mime_type="application/json"))
                    
                    combined_label_text = ""
                    for pdf in label_pdfs:
                        combined_label_text += extract_text_from_pdf(pdf) + "\n"
                    
                    extraction_prompt = f"""
                    You are an agricultural data extractor. Read the provided pesticide label claim text.
                    Extract the pesticide recommendations into a JSON array of objects.
                    
                    Each object MUST have exactly these keys:
                    "chemical_name": (string, name of the pesticide/formulation)
                    "crop": (string, target crop)
                    "pest": (string, target insect or mite)
                    "dose_formulation": (number, the formulation amount in g/ml. If a range is given like 500-600, use the average, e.g., 550)
                    "water_liters": (number, the water requirement in liters. If a range is given like 500-1000, use the average, e.g., 750)
                    
                    Text: {combined_label_text[:40000]}
                    """
                    
                    try:
                        response = model.generate_content(extraction_prompt)
                        extracted_json = json.loads(response.text)
                        
                        # Process calculations
                        processed_data = []
                        for item in extracted_json:
                            try:
                                dose = float(item['dose_formulation'])
                                water = float(item['water_liters'])
                                # Calculation: (Dose / Water Requirement) * 10
                                pump_dose = round((dose / water) * 10, 2)
                                
                                processed_data.append({
                                    "Select": False,
                                    "Chemical": item['chemical_name'],
                                    "Crop": item['crop'],
                                    "Pest": item['pest'],
                                    "Formulation (g/ml)": dose,
                                    "Water (L)": water,
                                    "10L Pump Dose (g/ml)": pump_dose
                                })
                            except (ValueError, TypeError, ZeroDivisionError):
                                continue # Skip invalid rows
                                
                        st.session_state.pesticide_data = pd.DataFrame(processed_data)
                        st.success("Extraction and calculation complete!")
                    except Exception as e:
                        st.error(f"Failed to parse data. Ensure the PDF contains readable label claims. Error: {e}")

# Display data editor if data exists
selected_chemicals_text = ""
if not st.session_state.pesticide_data.empty:
    st.markdown("### 🧪 Select Chemicals to Include")
    st.markdown("Check the boxes in the 'Select' column to include those specific chemicals in your final article.")
    
    # Use st.data_editor to allow checkbox selection
    edited_df = st.data_editor(
        st.session_state.pesticide_data,
        column_config={"Select": st.column_config.CheckboxColumn("Select", required=True)},
        disabled=["Chemical", "Crop", "Pest", "Formulation (g/ml)", "Water (L)", "10L Pump Dose (g/ml)"],
        hide_index=True
    )
    
    # Filter selected rows
    selected_rows = edited_df[edited_df["Select"] == True]
    if not selected_rows.empty:
        selected_chemicals_text = "Integrate the following chemical recommendations smoothly into the text:\n"
        for _, row in selected_rows.iterrows():
            selected_chemicals_text += f"- Chemical: {row['Chemical']}, Crop: {row['Crop']}, Pest: {row['Pest']}, Recommended Dose per 10-Liter Pump: {row['10L Pump Dose (g/ml)']} g/ml\n"

# --- Step 2: Main Article Source ---
st.header("2. Provide Main Source Content")
input_method = st.radio("Choose input method for the main article content:", ["Copy & Paste Text", "Upload PDF"])

source_text = ""

if input_method == "Copy & Paste Text":
    source_text = st.text_area("Paste your main English or Gujarati text here:", height=200)
elif input_method == "Upload PDF":
    uploaded_source = st.file_uploader("Upload an English or Gujarati PDF for the article body", type=["pdf"], key="source_pdf")
    if uploaded_source is not None:
        source_text = extract_text_from_pdf(uploaded_source)
        st.success("Main PDF text extracted successfully!")

# --- Step 3: Generation Section ---
st.header("3. Generate Initial Draft")
if st.button("Generate Sandesh Article"):
    if not api_key:
        st.error("Please enter your Gemini API Key in the sidebar.")
    elif not source_text.strip():
        st.warning("Please provide some source text first.")
    else:
        with st.spinner("Drafting article for Sandesh News..."):
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-3-pro-preview') 
            
            prompt = f"""
            You are an expert agricultural journalist writing for 'Sandesh News' in Gujarat.
            Read the following source text and write an engaging, practical agricultural extension article in fluent Gujarati.
            
            Strict Rules:
            1. DO NOT mention any university, college, or institute name.
            2. Write in a journalistic, informative tone suitable for a daily newspaper's agriculture page.
            3. Use accurate agricultural and entomological terminology.
            4. Format with a catchy headline and continuous, flowing paragraphs. DO NOT use any bullet points, numbered lists, or dashes for lists. Write it as a narrative essay or traditional news article.
            5. The output must be entirely in Gujarati.
            6. {selected_chemicals_text if selected_chemicals_text else "Focus only on the main text provided."} If chemicals are listed here, weave them seamlessly into the chemical management paragraph. Ensure the '10-Liter pump' dose is explicitly mentioned for farmers.
            
            Source Text:
            {source_text[:20000]}
            """
            
            response = model.generate_content(prompt)
            st.session_state.current_article = response.text

# Display the current draft
if st.session_state.current_article:
    st.markdown("### 📝 Current Draft")
    st.info(st.session_state.current_article)

    # --- Step 4: Refinement Section ---
    st.header("4. Suggest Changes & Rewrite")
    suggestion = st.text_area("What should be changed, added, or removed?", placeholder="e.g., Make the chemical control section shorter, or emphasize organic methods more.")
    
    if st.button("Rewrite Article"):
        if not api_key:
            st.error("Please enter your Gemini API Key.")
        elif not suggestion.strip():
            st.warning("Please enter a suggestion first.")
        else:
            with st.spinner("Rewriting based on your suggestions..."):
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-3-pro-preview')
                
                rewrite_prompt = f"""
                You are an expert agricultural journalist. I have a draft article in Gujarati, but it needs some revisions.
                
                Here is the current draft:
                {st.session_state.current_article}
                
                Please rewrite the article by applying the following instructions:
                {suggestion}
                
                Strict Rules for the Rewrite:
                1. Maintain the 'Sandesh News' journalistic tone.
                2. Keep it entirely in Gujarati.
                3. DO NOT mention any institute names.
                4. The entire text MUST remain in continuous paragraph format. Strictly NO bullet points or numbered lists.
                """
                
                response = model.generate_content(rewrite_prompt)
                st.session_state.current_article = response.text
                st.rerun() 

    # --- Step 5: Export Section ---
    st.header("5. Export Options")
    word_file = create_word_docx(st.session_state.current_article)
    
    st.download_button(
        label="📄 Download as Word Document (.docx)",
        data=word_file,
        file_name="Sandesh_Agri_Article.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
