import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. API Configuration
try:
    # Streamlit Secrets에 저장된 API 키를 불러옵니다.
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error("API Key missing! Check your Streamlit Secrets settings.")

# 2. Smart Model Selection Logic (Physics Optimized)
@st.cache_resource
def load_physics_model():
    # 사용 가능한 모델 목록을 가져옵니다.
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    # Gemini 3 Flash를 우선 찾고, 없으면 1.5 Flash를 선택하는 로직입니다.
    target_model = next((m for m in available_models if "gemini-3-flash" in m), 
                    next((m for m in available_models if "gemini-1.5-flash" in m), 
                    available_models[0]))
    
    return genai.GenerativeModel(
        model_name=target_model,
        system_instruction=(
            "You are an expert A-Level Physics Examiner. "
            "Use the provided Google Drive documents to provide definitive model answers. "
            "Focus on mark scheme accuracy, bold essential keywords, and use LaTeX for all equations and physical symbols."
        )
    )

# 물리 모델 초기화
model = load_physics_model()

# 3. User Interface (Physics Theme)
st.set_page_config(page_title="A-Level Physics Solver", layout="centered")
st.title("⚛️ A-Level Physics Revision Tool")
st.write(f"Connected to Model: **{model.model_name}**")

# 질문 사진 업로드 (이미지 전용)
uploaded_file = st.file_uploader("Upload a physics question photo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption='Question Preview', use_container_width=True)
    
    if st.button('Generate Model Answer'):
        with st.spinner('Accessing Physics Database...'):
            try:
                # AI Studio에 연동된 구글 드라이브 문서를 참조하여 답변을 생성합니다.
                response = model.generate_content([
                    "Provide the A-level model answer for this physics question. Reference the mark schemes in my drive.", 
                    image
                ])
                st.success("Analysis Complete!")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Technical Error: {e}")