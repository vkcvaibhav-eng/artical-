import streamlit as st
import google.generativeai as genai
import PyPDF2
import datetime

# --- Configuration & Setup ---
st.set_page_config(page_title="Agri-Entomology Content Creator", layout="wide")

# --- Helper Functions ---
def get_current_gujarat_context():
    """Returns the current month and timely pest context for South Gujarat."""
    months = ["January", "February", "March", "April", "May", "June", 
              "July", "August", "September", "October", "November", "December"]
    current_month = months[datetime.datetime.now().month - 1]
    
    # Context specific to South Gujarat pest dynamics
    pest_context = {
        "February": "Mango hoppers on new flush/flowering, aphids and thrips on rabi pulses/brinjal, coconut mites.",
        "March": "Mango fruit flies starting, jassids and whiteflies peaking on summer crops.",
        "April": "Fruit borers, heavy sucking pest pressure on summer vegetables."
        # You can expand this dictionary for all 12 months
    }
    
    current_pests = pest_context.get(current_month, "Seasonal insect pests of major crops.")
    return current_month, current_pests

def extract_text_from_pdf(uploaded_file):
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

# --- Sidebar: API Keys ---
st.sidebar.title("API Configuration")
st.sidebar.markdown("Enter your available API keys below:")
gemini_key = st.sidebar.text_input("Gemini API Key", type="password")
openai_key = st.sidebar.text_input("ChatGPT API Key", type="password")
claude_key = st.sidebar.text_input("Claude API Key", type="password")
deepseek_key = st.sidebar.text_input("DeepSeek API Key", type="password")

selected_model = st.sidebar.selectbox("Choose Model", ["Gemini", "ChatGPT (Coming Soon)"])

# --- Main App ---
st.title("🌱 Agri-Entomology Gujarati Content Creator")
st.markdown("Generate human-like Gujarati extension articles or translate English research PDFs.")

tab1, tab2 = st.tabs(["✍️ Write Seasonal Article", "📄 Translate English PDF"])

with tab1:
    st.header("Generate Topic-Based Article")
    current_month, local_pests = get_current_gujarat_context()
    
    st.info(f"**Current Month:** {current_month}\n\n**Active Pests:** {local_pests}")
    
    topic = st.text_input("Specific Topic (Optional):", placeholder="e.g., Management of Coconut Mites (એરીફાઈડ કથીરી)")
    
    if st.button("Generate Gujarati Article"):
        if not gemini_key and selected_model == "Gemini":
            st.error("Please enter your Gemini API Key in the sidebar.")
        else:
            with st.spinner("Drafting article like a human expert..."):
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-2.5-pro')
                
                # The System Prompt: This prevents the "AI tone"
                prompt = f"""
                You are an expert Agricultural Entomologist working in South Gujarat. 
                Write an extension article in fluent, natural Gujarati for local farmers.
                
                Context:
                - Month: {current_month}
                - Common pests right now: {local_pests}
                - Specific topic to focus on: {topic}
                
                Strict Rules:
                1. DO NOT use generic AI structures like "Here is an article", "In conclusion", or "It is important to note".
                2. Write in a conversational, authoritative, and practical tone, exactly like a university extension bulletin or farm magazine.
                3. Use accurate Gujarati agricultural and entomological terminology (e.g., 'જીવાત' for pests, 'સંકલિત જીવાત નિયંત્રણ' for IPM).
                4. Focus heavily on practical management (cultural, biological, and chemical) suited for the region.
                """
                
                response = model.generate_content(prompt)
                st.subheader("Generated Article:")
                st.write(response.text)

with tab2:
    st.header("Translate English PDF to Gujarati")
    uploaded_file = st.file_uploader("Upload English PDF", type="pdf")
    
    if st.button("Translate to Gujarati"):
        if uploaded_file is not None:
            if not gemini_key:
                st.error("Please enter your Gemini API Key.")
            else:
                with st.spinner("Extracting and Translating..."):
                    english_text = extract_text_from_pdf(uploaded_file)
                    
                    genai.configure(api_key=gemini_key)
                    model = genai.GenerativeModel('gemini-2.5-pro')
                    
                    translation_prompt = f"""
                    You are an expert Agricultural Entomologist. Translate the following English agricultural text into fluent, natural Gujarati.
                    
                    Strict Rules:
                    1. The output must NOT sound like a machine translation. 
                    2. Use correct local terminology for South Gujarat farming.
                    3. Preserve the academic/technical accuracy but make it readable for the local agricultural community.
                    
                    English Text:
                    {english_text[:15000]} 
                    """
                    
                    response = model.generate_content(translation_prompt)
                    st.subheader("Gujarati Translation:")
                    st.write(response.text)
        else:
            st.warning("Please upload a PDF first.")
