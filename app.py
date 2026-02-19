import streamlit as st
import google.generativeai as genai
import PyPDF2
import docx
from io import BytesIO

# --- Configuration & Setup ---
st.set_page_config(page_title="Sandesh News Article Generator", layout="wide")

# Initialize session state variables
if "extracted_topics" not in st.session_state:
    st.session_state.extracted_topics = []
if "current_article" not in st.session_state:
    st.session_state.current_article = ""
if "source_text" not in st.session_state:
    st.session_state.source_text = ""

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
    doc.add_heading('કૃષિ લેખ (Sandesh News Draft)', 0)
    doc.add_paragraph(text)
    
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- Sidebar: API Key ---
st.sidebar.title("API Configuration")
api_key = st.sidebar.text_input("Gemini API Key", type="password")

# --- Main UI ---
st.title("📰 Sandesh News: Agri-Entomology Article Generator")
st.markdown("Upload a document, extract crop-pest topics, select your focus, and generate a draft.")

# --- Step 1: Input Section ---
st.header("1. Provide Source Content")
input_method = st.radio("Choose input method:", ["Copy & Paste Text", "Upload PDF"])

raw_text = ""

if input_method == "Copy & Paste Text":
    raw_text = st.text_area("Paste your English or Gujarati text here:", height=200)
elif input_method == "Upload PDF":
    uploaded_file = st.file_uploader("Upload an English or Gujarati PDF", type=["pdf"])
    if uploaded_file is not None:
        raw_text = extract_text_from_pdf(uploaded_file)
        st.success("PDF text extracted successfully!")

# Save to session state so it doesn't vanish on rerun
if raw_text:
    st.session_state.source_text = raw_text

# --- Step 2: Extraction Section ---
st.header("2. Extract Crop & Pest Information")
if st.button("Identify Crop-Pest Combinations"):
    if not api_key:
        st.error("Please enter your Gemini API Key in the sidebar.")
    elif not st.session_state.source_text.strip():
        st.warning("Please provide some source text first.")
    else:
        with st.spinner("Analyzing document for crops and insect pests..."):
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-pro')
            
            extraction_prompt = f"""
            Analyze the following agricultural text and identify all combinations of crops and insect pests (or diseases) mentioned.
            
            Return ONLY a simple list where each line is formatted exactly like this:
            [Crop Name] - [Insect Pest/Disease Name]
            
            Do not use bullet points, numbers, or introductory text. Just the list. 
            If no specific combinations are found, return "General Agriculture - Overview".
            
            Source Text:
            {st.session_state.source_text[:15000]}
            """
            
            response = model.generate_content(extraction_prompt)
            # Clean up the response into a python list
            topics = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
            st.session_state.extracted_topics = topics

# --- Step 3: Selection & Generation Section ---
if st.session_state.extracted_topics:
    st.header("3. Select Topic & Generate")
    selected_topic = st.selectbox("Select the specific Crop-Pest recommendation you want to write about:", st.session_state.extracted_topics)
    
    if st.button("Generate Sandesh Article"):
        with st.spinner(f"Drafting article about '{selected_topic}'..."):
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-pro') 
            
            generation_prompt = f"""
            You are an expert agricultural journalist writing for 'Sandesh News' in Gujarat.
            Read the following source text and write an engaging, practical agricultural extension article in fluent Gujarati.
            
            Crucially, focus ONLY on the management and recommendations for this specific combination: {selected_topic}.
            
            Strict Rules:
            1. DO NOT mention any university, college, or institute name.
            2. Write in a journalistic, informative tone suitable for a daily newspaper's agriculture page.
            3. Use accurate agricultural and entomological terminology in Gujarati.
            4. Format with a catchy headline and continuous, flowing paragraphs. DO NOT use any bullet points, numbered lists, or dashes for lists. Write it as a narrative essay.
            5. The output must be entirely in Gujarati.
            
            Source Text:
            {st.session_state.source_text[:20000]}
            """
            
            response = model.generate_content(generation_prompt)
            st.session_state.current_article = response.text

# --- Step 4: Refinement & Export Section ---
if st.session_state.current_article:
    st.markdown("### 📝 Current Draft")
    st.info(st.session_state.current_article)

    st.header("4. Suggest Changes & Export")
    suggestion = st.text_area("What should be changed, added, or removed?", placeholder="e.g., Make the chemical control section shorter.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Rewrite Article"):
            if not api_key:
                st.error("Please enter your Gemini API Key.")
            elif not suggestion.strip():
                st.warning("Please enter a suggestion first.")
            else:
                with st.spinner("Rewriting based on your suggestions..."):
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-1.5-pro')
                    
                    rewrite_prompt = f"""
                    You are an expert agricultural journalist. I have a draft article in Gujarati, but it needs revisions.
                    
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

    with col2:
        word_file = create_word_docx(st.session_state.current_article)
        st.download_button(
            label="📄 Download as Word Document (.docx)",
            data=word_file,
            file_name="Sandesh_Agri_Article.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
