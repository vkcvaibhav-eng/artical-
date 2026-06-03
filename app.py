import json
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

import docx
import PyPDF2
import requests
import streamlit as st

try:
    import google.generativeai as genai
except ImportError:
    genai = None


APP_TITLE = "Advanced Gujarati Newspaper Article Writer"
DEFAULT_GEMINI_MODEL = "gemini-3.1-pro-preview"
DEFAULT_PERPLEXITY_MODEL = "sonar-deep-research"


st.set_page_config(page_title=APP_TITLE, layout="wide")


def today_india():
    return datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")


def ensure_state():
    defaults = {
        "topic_ideas": "",
        "selected_topic": "",
        "research_brief": "",
        "source_text": "",
        "draft_article": "",
        "editor_report": "",
        "final_article": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def extract_text_from_pdf(uploaded_file):
    reader = PyPDF2.PdfReader(uploaded_file)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def extract_text_from_docx(uploaded_file):
    document = docx.Document(uploaded_file)
    return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())


def create_word_docx(article_text, title="Gujarati Newspaper Article"):
    document = docx.Document()
    document.add_heading(title, 0)
    document.add_paragraph(article_text)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def call_gemini(api_key, model_name, prompt, temperature=0.45):
    if genai is None:
        raise RuntimeError("google-generativeai package is not installed.")
    if not api_key:
        raise RuntimeError("Gemini API key is missing.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(
        prompt,
        generation_config={"temperature": temperature},
    )
    return response.text.strip()


def call_perplexity(api_key, model_name, prompt):
    if not api_key:
        raise RuntimeError("Perplexity API key is missing.")

    response = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a careful research assistant for an Indian Gujarati "
                        "newspaper agriculture column. Prefer current, source-grounded facts."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        },
        timeout=90,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def build_topic_prompt(date_text, beat, region, crop_focus):
    return f"""
Today is {date_text} in India.

Find 5 timely article topics for a Gujarati daily newspaper agriculture page.

Editorial beat: {beat}
Region: {region}
Crop or pest focus: {crop_focus}

Choose topics that matter right now because of season, weather, pest pressure,
farmer decision timing, market/policy relevance, or public interest.

For each topic include:
1. Gujarati headline idea
2. Why it is important today
3. What farmers can practically learn
4. What facts should be verified before publishing

Keep the answer concise.
"""


def build_research_prompt(date_text, topic, region, source_text):
    return f"""
Today is {date_text} in India.

Research this Gujarati newspaper agriculture article topic:
{topic}

Region: {region}

Extra source material from user:
{source_text[:12000]}

Prepare a research brief with:
- Current relevance
- Key verified facts
- Farmer impact
- Practical guidance
- Risks, cautions, or uncertainty
- Source names or URLs where available
- Questions that still need human verification

Do not write the final article yet.
"""


def build_draft_prompt(topic, research_brief, source_text, word_count, style_rules):
    return f"""
You are an experienced Gujarati agriculture newspaper journalist.

Write a polished Gujarati newspaper article for this topic:
{topic}

Target length: about {word_count} words.

Research brief:
{research_brief[:16000]}

Additional source material:
{source_text[:12000]}

Mandatory writing rules:
1. Entire output must be in fluent Gujarati.
2. Write in newspaper style for farmers and general readers.
3. Use a strong Gujarati headline.
4. Use flowing paragraphs only. Do not use bullet points, numbered lists, or dash lists.
5. Do not mention university, college, institute, or department names unless the editor explicitly asks.
6. Do not invent facts, figures, pesticide doses, scheme details, or quotes.
7. If a technical recommendation is uncertain, write it cautiously and advise local expert/label guidance.
8. Keep the language practical, clear, and suitable for publication.

Extra editor rules:
{style_rules}
"""


def build_editor_prompt(topic, article, research_brief):
    return f"""
You are a senior Gujarati newspaper editor and fact-checker.

Review this Gujarati agriculture article before publication.

Topic:
{topic}

Research brief:
{research_brief[:10000]}

Article:
{article[:16000]}

Give a concise editorial report in Gujarati with:
1. Fact risks
2. Weak or unclear parts
3. Tone/readability issues
4. Missing practical farmer value
5. Final rewrite instructions

Do not rewrite the article in this step.
"""


def build_final_rewrite_prompt(article, editor_report):
    return f"""
Rewrite the article below into a final Gujarati newspaper-ready version.

Current article:
{article[:16000]}

Editorial report and rewrite instructions:
{editor_report[:8000]}

Final rules:
1. Entire output must be Gujarati.
2. Keep a newspaper tone.
3. Use one strong headline.
4. Use continuous paragraphs only.
5. No bullet points, numbered lists, or dash lists.
6. Remove unsupported claims.
7. Improve clarity, flow, and farmer usefulness.
"""


ensure_state()

st.title(APP_TITLE)
st.caption("Topic selection, deep research, Gujarati drafting, editor review, rewrite, and Word export.")

with st.sidebar:
    st.header("API Keys")
    gemini_api_key = st.text_input("Gemini API Key", type="password")
    perplexity_api_key = st.text_input("Perplexity API Key (optional, for live deep research)", type="password")

    st.header("Models")
    gemini_model = st.text_input("Gemini model", DEFAULT_GEMINI_MODEL)
    perplexity_model = st.text_input("Perplexity model", DEFAULT_PERPLEXITY_MODEL)

    st.header("Article Settings")
    region = st.text_input("Region", "Gujarat, India")
    beat = st.text_input("Beat", "Agriculture, crops, pests, farmer advisory")
    crop_focus = st.text_input("Crop/pest focus", "Current season crops and pest problems")
    word_count = st.slider("Approx word count", 450, 1300, 750, 50)
    style_rules = st.text_area(
        "Extra rules",
        "Keep it suitable for Sandesh-style daily newspaper agriculture readers.",
        height=90,
    )

tab_topic, tab_sources, tab_research, tab_write, tab_export = st.tabs(
    ["1. Topic", "2. Sources", "3. Research", "4. Write & Edit", "5. Export"]
)

with tab_topic:
    st.subheader("Find today's important topic")
    st.write("Use Perplexity for live topic research, or Gemini for non-live topic brainstorming.")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Find Topics With Perplexity", use_container_width=True):
            try:
                prompt = build_topic_prompt(today_india(), beat, region, crop_focus)
                st.session_state.topic_ideas = call_perplexity(perplexity_api_key, perplexity_model, prompt)
            except Exception as exc:
                st.error(f"Perplexity topic search failed: {exc}")

    with col_b:
        if st.button("Brainstorm Topics With Gemini", use_container_width=True):
            try:
                prompt = build_topic_prompt(today_india(), beat, region, crop_focus)
                prompt += "\nImportant: If you do not have live web access, clearly say these are non-live suggestions."
                st.session_state.topic_ideas = call_gemini(gemini_api_key, gemini_model, prompt)
            except Exception as exc:
                st.error(f"Gemini topic brainstorm failed: {exc}")

    st.text_area("Topic ideas", key="topic_ideas", height=260)
    st.text_input("Selected topic for article", key="selected_topic")

with tab_sources:
    st.subheader("Add source material")
    pasted = st.text_area(
        "Paste research notes, article links, English text, Gujarati text, or official advisory text",
        height=240,
    )

    uploaded_files = st.file_uploader(
        "Upload PDF or DOCX source files",
        type=["pdf", "docx"],
        accept_multiple_files=True,
    )

    if st.button("Save Sources", use_container_width=True):
        collected = [pasted.strip()] if pasted.strip() else []
        for uploaded_file in uploaded_files:
            try:
                if uploaded_file.name.lower().endswith(".pdf"):
                    collected.append(extract_text_from_pdf(uploaded_file))
                elif uploaded_file.name.lower().endswith(".docx"):
                    collected.append(extract_text_from_docx(uploaded_file))
            except Exception as exc:
                st.warning(f"Could not read {uploaded_file.name}: {exc}")
        st.session_state.source_text = "\n\n".join(text for text in collected if text.strip())
        st.success("Sources saved.")

    st.text_area("Saved source text", key="source_text", height=260)

with tab_research:
    st.subheader("Create research brief")
    st.write("For current news and today's importance, Perplexity or another live research source is recommended.")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Deep Research With Perplexity", use_container_width=True):
            try:
                prompt = build_research_prompt(
                    today_india(),
                    st.session_state.selected_topic,
                    region,
                    st.session_state.source_text,
                )
                st.session_state.research_brief = call_perplexity(perplexity_api_key, perplexity_model, prompt)
            except Exception as exc:
                st.error(f"Perplexity research failed: {exc}")

    with col_b:
        if st.button("Summarize Sources With Gemini", use_container_width=True):
            try:
                prompt = build_research_prompt(
                    today_india(),
                    st.session_state.selected_topic,
                    region,
                    st.session_state.source_text,
                )
                prompt += "\nOnly use the supplied source material if live web access is unavailable."
                st.session_state.research_brief = call_gemini(gemini_api_key, gemini_model, prompt)
            except Exception as exc:
                st.error(f"Gemini research summary failed: {exc}")

    st.text_area("Research brief", key="research_brief", height=360)

with tab_write:
    st.subheader("Draft, check, and rewrite")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("Generate Gujarati Draft", use_container_width=True):
            try:
                prompt = build_draft_prompt(
                    st.session_state.selected_topic,
                    st.session_state.research_brief,
                    st.session_state.source_text,
                    word_count,
                    style_rules,
                )
                st.session_state.draft_article = call_gemini(gemini_api_key, gemini_model, prompt)
            except Exception as exc:
                st.error(f"Draft generation failed: {exc}")

    with col_b:
        if st.button("Editor Check", use_container_width=True):
            try:
                prompt = build_editor_prompt(
                    st.session_state.selected_topic,
                    st.session_state.draft_article,
                    st.session_state.research_brief,
                )
                st.session_state.editor_report = call_gemini(gemini_api_key, gemini_model, prompt, temperature=0.25)
            except Exception as exc:
                st.error(f"Editor check failed: {exc}")

    with col_c:
        if st.button("Final Rewrite", use_container_width=True):
            try:
                prompt = build_final_rewrite_prompt(
                    st.session_state.draft_article,
                    st.session_state.editor_report,
                )
                st.session_state.final_article = call_gemini(gemini_api_key, gemini_model, prompt, temperature=0.35)
            except Exception as exc:
                st.error(f"Final rewrite failed: {exc}")

    st.markdown("#### Draft Article")
    st.text_area("Draft", key="draft_article", height=260)

    st.markdown("#### Editor Report")
    st.text_area("Report", key="editor_report", height=180)

    st.markdown("#### Final Article")
    st.text_area("Final", key="final_article", height=320)

with tab_export:
    st.subheader("Export")
    final_text = st.session_state.final_article.strip() or st.session_state.draft_article.strip()

    if final_text:
        st.download_button(
            "Download Final Article as Word",
            data=create_word_docx(final_text, "Gujarati Newspaper Article"),
            file_name="Gujarati_Newspaper_Article.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
        st.markdown("#### Preview")
        st.info(final_text)
    else:
        st.warning("Generate a draft or final article first.")

    with st.expander("Saved workflow data as JSON"):
        st.code(
            json.dumps(
                {
                    "date": today_india(),
                    "region": region,
                    "selected_topic": st.session_state.selected_topic,
                    "research_brief": st.session_state.research_brief,
                    "draft_article": st.session_state.draft_article,
                    "editor_report": st.session_state.editor_report,
                    "final_article": st.session_state.final_article,
                },
                ensure_ascii=False,
                indent=2,
            ),
            language="json",
        )
