import streamlit as st
import google.generativeai as genai
import PyPDF2
import docx
from io import BytesIO

# --- Configuration & Setup ---
st.set_page_config(page_title="Sandesh News Article Generator", layout="wide")

# Initialize session state variables to store the drafts
if "current_article" not in st.session_state:
    st.session_state.current_article = ""

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
st.markdown("Upload a document or paste text, generate a draft, refine it, and export to Word.")

# --- Step 1: Input Section ---
st.header("1. Provide Source Content")
input_method = st.radio("Choose input method:", ["Copy & Paste Text", "Upload PDF"])

source_text = ""

if input_method == "Copy & Paste Text":
    source_text = st.text_area("Paste your English or Gujarati text here:", height=200)
elif input_method == "Upload PDF":
    uploaded_file = st.file_uploader("Upload an English or Gujarati PDF", type=["pdf"])
    if uploaded_file is not None:
        source_text = extract_text_from_pdf(uploaded_file)
        st.success("PDF text extracted successfully!")

# --- Step 2: Generation Section ---
st.header("2. Generate Initial Draft")
if st.button("Generate Sandesh Article"):
    if not api_key:
        st.error("Please enter your Gemini API Key in the sidebar.")
    elif not source_text.strip():
        st.warning("Please provide some source text first.")
    else:
        with st.spinner("Drafting article for Sandesh News..."):
            genai.configure(api_key=api_key)
            # Using the standard API model name for Gemini 1.5 Pro
            model = genai.GenerativeModel('gemini-3.1-pro-preview-customtools') 
            
            prompt = f"""
            You are an expert agricultural journalist writing for 'Sandesh News' in Gujarat.
            Read the following source text and write an engaging, practical agricultural extension article in fluent Gujarati.
            
            Strict Rules:
            1. DO NOT mention any university, college, or institute name.
            2. Write in a journalistic, informative tone suitable for a daily newspaper's agriculture page.
            3. Use accurate agricultural and entomological terminology.
            4. Format with a catchy headline and continuous, flowing paragraphs. DO NOT use any bullet points, numbered lists, or dashes for lists. Write it as a narrative essay or traditional news article.
            5. The output must be entirely in Gujarati.
            
            Source Text:
            {source_text[:20000]}
            """
            
            response = model.generate_content(prompt)
            st.session_state.current_article = response.text

# Display the current draft if it exists
if st.session_state.current_article:
    st.markdown("### 📝 Current Draft")
    st.info(st.session_state.current_article)

    # --- Step 3: Refinement Section ---
    st.header("3. Suggest Changes & Rewrite")
    suggestion = st.text_area("What should be changed, added, or removed?", placeholder="e.g., Make the chemical control section shorter, or emphasize organic methods more.")
    
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
                st.rerun() # Refresh the app to show the updated draft

    # --- Step 4: Export Section ---
    st.header("4. Export Options")
    word_file = create_word_docx(st.session_state.current_article)
    
    st.download_button(
        label="📄 Download as Word Document (.docx)",
        data=word_file,
        file_name="Sandesh_Agri_Article.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
