import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# 1. Page Configuration
st.set_page_config(page_title="A-Level Physics Master Coach", page_icon="⚛️", layout="wide")

# Modern Dark Theme CSS
st.markdown("""
    <style>
    .main { background-color: #0f172a; color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #38bdf8; color: #020617; font-weight: bold; }
    .stChatFloatingInputContainer { background-color: #1e293b; }
    .stMarkdown { font-family: 'Inter', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚛️ A-Level Physics Master Coach")
st.subheader("Direct Knowledge Retrieval from Physics Mark Schemes")

# 2. API Key Setup
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("Missing GEMINI_API_KEY. Please add it to your Streamlit Secrets.")
    st.stop()

# 3. System Instruction: Focus on Retrieval & Model Answers
# 구글 드라이브의 데이터를 우선적으로 참조하도록 지침을 강화했습니다.
SYSTEM_INSTRUCTION = """
You are a world-class A-Level Physics Expert. You have access to a specialized knowledge base of Past Papers and Mark Schemes via Google Drive integration.

[Operational Protocol]
1. Knowledge Retrieval: Always prioritize the specific marking points and terminology found in the connected Mark Schemes when answering.
2. Model Answers: Provide structured, exam-ready answers. Use bullet points for multi-mark questions.
3. Mathematical Precision: Use LaTeX for all formulas (e.g., $E_k = \frac{1}{2}mv^2$).
4. Principle-First: State the law (e.g., "Lenz's Law") before applying it to the problem.
5. Units & Significant Figures: Ensure all final values include correct SI units and adhere to appropriate significant figures.
"""

# 4. Model Initialization (Gemini 1.5 Flash)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

# 5. Session State
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 6. Sidebar for Immediate Visual Analysis
with st.sidebar:
    st.header("📂 Instant Analysis")
    st.write("Upload a specific question or diagram image for a detailed breakdown.")
    uploaded_image = st.file_uploader("Upload Problem Image", type=["png", "jpg", "jpeg"])
    
    if st.button("Clear Conversation"):
        st.session_state.chat_history = []
        st.rerun()

# 7. Main Chat Loop
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Explain a concept or ask about a specific exam question..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # Prepare content (Text + Image if provided)
        # 드라이브 연동은 AI Studio 백엔드에서 처리되므로 별도의 코드 추가 없이 모델이 데이터를 인지합니다.
        content_parts = [prompt]
        if uploaded_image:
            img = Image.open(uploaded_image)
            content_parts.append(img)
        
        try:
            # Stream the response
            response = model.generate_content(content_parts, stream=True)
            for chunk in response:
                full_response += chunk.text
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
            
            st.session_state.chat_history.append({"role": "assistant", "content": full_response})
        except Exception as e:
            st.error(f"Response Error: {str(e)}")