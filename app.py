import streamlit as st
from openai import OpenAI
import google.generativeai as genai
from docx import Document
import io

st.set_page_config(page_title="SAU Extension Article Generator", layout="wide")

st.title("🕷️ Acarology Extension Article Generator")
st.markdown("Fetch the latest mite management trends from Gujarat SAUs and generate Gujarati articles.")

# --- Sidebar for API Keys ---
st.sidebar.header("API Configuration")
perplexity_key = st.sidebar.text_input("Perplexity API Key", type="password")
gemini_key = st.sidebar.text_input("Gemini API Key", type="password")

# --- Helper Function: Generate Word Doc ---
def create_word_docx(title, content, source_link):
    """Generates an in-memory Word document."""
    doc = Document()
    doc.add_heading(title, level=1)
    
    # Add the main article content
    doc.add_paragraph(content)
    
    # Add references
    doc.add_heading("સંદર્ભ (Source):", level=2)
    doc.add_paragraph(source_link)
    
    # Save to BytesIO stream instead of a local file
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream

# --- Main App Logic ---
if st.button("🔍 Research & Write Article"):
    if not perplexity_key or not gemini_key:
        st.error("Please provide both Perplexity and Gemini API keys in the sidebar.")
    else:
        with st.status("Initializing the research pipeline...", expanded=True) as status:
            
            try:
                # STEP 1: Research with Perplexity
                status.update(label="Searching NAU, AAU, and Krushi Prabhat for the latest mite trends...")
                
                # Perplexity uses the OpenAI SDK format
                perplexity_client = OpenAI(api_key=perplexity_key, base_url="https://api.perplexity.ai")
                
                search_prompt = """
                Search for the latest agricultural trends, advisories, or research regarding 'mites' (કથીરી). 
                You MUST focus your search strictly on sources from Navsari Agricultural University (NAU), 
                Anand Agricultural University (AAU / Krushi Govidya), and Krushi Prabhat.
                
                Provide:
                1. A specific topic title.
                2. A detailed summary of the pest management advisory or research finding.
                3. The direct URL/Link to the PDF or source web page.
                """
                
                perplexity_response = perplexity_client.chat.completions.create(
                    model="sonar", # Perplexity's search model
                    messages=[{"role": "user", "content": search_prompt}]
                )
                
                research_data = perplexity_response.choices[0].message.content
                
                # STEP 2: Write with Gemini
                status.update(label="Drafting the extension article in Gujarati with Gemini...")
                
                genai.configure(api_key=gemini_key)
                gemini_model = genai.GenerativeModel('gemini-2.5-pro')
                
                writing_prompt = f"""
                You are an expert Agricultural Entomologist writing a practical extension article for farmers.
                Based on the following research data gathered from Gujarat State Agricultural Universities, write a comprehensive article about mite management in fluent Gujarati.
                
                Rules:
                1. Write ONLY the Gujarati article text. No robotic intro/outro (e.g., "Here is the article").
                2. Write it entirely in continuous paragraph form, avoiding heavy bullet points so it reads like a magazine article.
                3. Ensure agricultural terminology is perfectly localized for South Gujarat.
                
                Research Data to translate and expand upon:
                {research_data}
                """
                
                article_content = gemini_model.generate_content(writing_prompt).text
                
                status.update(label="Pipeline complete!", state="complete")
                
                # --- Display Results ---
                st.subheader("Generated Gujarati Article")
                st.write(article_content)
                
                st.subheader("Underlying Research & Sources (From Perplexity)")
                st.info(research_data)
                
                # STEP 3: Export to Word
                word_file = create_word_docx(
                    title="કથીરી જીવાત વ્યવસ્થાપન", 
                    content=article_content, 
                    source_link="Perplexity Search Data"
                )
                
                st.download_button(
                    label="📄 Download Article as Word Document",
                    data=word_file,
                    file_name="Mite_Management_Article.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

            except Exception as e:
                status.update(label="An error occurred.", state="error")
                st.error(f"Error details: {e}")
