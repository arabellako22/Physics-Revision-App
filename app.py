import streamlit as st
import google.generativeai as genai
from PIL import Image
import os
from supabase import create_client

# ── Supabase 연결 ────────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    url = os.environ.get("SUPABASE_URL") or st.secrets["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_ANON_KEY") or st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)

# ── Access Control ───────────────────────────────────────────────────────────────
def is_authenticated():
    return st.session_state.get("phys_auth", False)

@st.cache_data(ttl=300)
def verify_user(email: str, code: str):
    try:
        supabase = get_supabase()
        result = supabase.table("users")\
            .select("*")\
            .eq("code", code.upper().strip())\
            .eq("subject", "physics")\
            .eq("status", "active")\
            .execute()
        if not result.data:
            return False, "invalid_code"
        user = result.data[0]
        if user["email"].lower() != email.lower().strip():
            return False, "email_mismatch"
        supabase.table("users")\
            .update({"usage_count": user["usage_count"] + 1})\
            .eq("id", user["id"])\
            .execute()
        return True, "success"
    except Exception as e:
        return False, "error"

def show_access_gate():
    # Streamlit 페이지 설정은 전체 앱 실행 중 단 한 번만 호출되도록 흐름을 보장합니다.
    try:
        st.set_page_config(page_title="Kodari Physics", layout="centered")
    except Exception:
        pass

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("## ⚛️ Kodari Physics")
        st.markdown("*A-Level Physics Revision*")
        st.markdown("---")
        st.markdown("#### Enter your details")
        email = st.text_input(
            label="Email used at checkout",
            placeholder="student@email.com",
            label_visibility="collapsed",
        )
        code = st.text_input(
            label="Access Code",
            placeholder="e.g. PHYS-A001",
            label_visibility="collapsed",
        )
        if st.button("Access →", type="primary", use_container_width=True):
            if not email or not code:
                st.warning("Please enter both your email and access code.")
            else:
                with st.spinner("Verifying..."):
                    success, reason = verify_user(email, code)
                if success:
                    st.session_state["phys_auth"] = True
                    st.rerun()
                elif reason == "invalid_code":
                    st.error("❌ Access code not found. Please check your code.")
                elif reason == "email_mismatch":
                    st.error("❌ Email doesn't match. Use the email from your PayPal receipt.")
                else:
                    st.error("⚠️ System error. Please try again.")
        
        # ── PayPal 결제 URL 예외 처리 ─────────────────────────────────────────────
        # Secrets에 PHYS_PAYMENT_URL이 아직 없어도 앱이 터지지 않도록 안전하게 방어막을 칩니다.
        try:
            purchase_url = st.secrets.get("PHYS_PAYMENT_URL", "")
        except Exception:
            purchase_url = ""
            
        # 나중에 Secrets에 링크를 기입하면, 그제서야 화면에 결제 버튼이 나타납니다.
        if purchase_url:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                f"<div style='text-align:center'>"
                f"<a href='{purchase_url}' target='_blank'>🛒 Get Physics Access</a>"
                f"</div>",
                unsafe_allow_html=True
            )
            
        with st.expander("Having trouble logging in?"):
            st.markdown("""
            - Use the **exact email** from your PayPal receipt
            - Check for spaces before/after your code
            - Codes are case-insensitive
            - Still stuck? Email: **support@kodari.co.uk**
            """)

# ── Gate Check ───────────────────────────────────────────────────────────────────
if not is_authenticated():
    show_access_gate()
    st.stop()

# ── 원본 흐름 유지 (최신 모델 및 프롬프트 최적화 적용) ──────────────────────────────

# 1. API Configuration
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error("API Key missing! Check your Streamlit Secrets settings.")

# 2. Smart Model Selection Logic (Physics Optimized - 최신화)
@st.cache_resource
def load_physics_model():
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    # 1순위: gemini-3.5-flash (최상위 비전/추론 매칭)
    # 2순위: gemini-3.1-flash-lite (가성비 백업)
    # 3순위: 리스트 내 사용 가능한 첫 모델 Fallback
    target_model = next((m for m in available_models if "gemini-3.5-flash" in m), 
                    next((m for m in available_models if "gemini-3.1-flash-lite" in m), 
                    available_models[0]))
    
    return genai.GenerativeModel(
        model_name=target_model,
        system_instruction=(
            "You are an expert A-Level Physics Examiner. "
            "Analyze the provided exam question image carefully and provide a definitive model answer "
            "that aligns perfectly with standard official mark schemes. "
            "Structure your points logically, bold essential keywords/phrases required for full marks, "
            "and use LaTeX for all equations, physical symbols, and variables."
        )
    )

model = load_physics_model()

# 3. User Interface (Physics Theme)
# 페이지 설정 중복 호출 방지를 위해 예외 처리 구조화
try:
    st.set_page_config(page_title="A-Level Physics Solver", layout="centered")
except Exception:
    pass

st.title("⚛️ A-Level Physics Revision Tool")
st.write(f"Connected to Model: **{model.model_name}**")

uploaded_file = st.file_uploader("Upload a physics question photo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption='Question Preview', use_container_width=True)
    if st.button('Generate Model Answer'):
        with st.spinner('Analyzing Physics Question...'):
            try:
                # 작동하지 않는 Drive 참조를 지우고 시험 분석 목적에 부합하게 프롬프트 보완
                response = model.generate_content([
                    "Strictly generate a comprehensive A-Level model answer and breakdown grading points for this physics question.", 
                    image
                ])
                st.success("Analysis Complete!")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Technical Error: {e}")

# ── Logout ───────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    if st.button("Log out", use_container_width=True):
        st.session_state["phys_auth"] = False
        st.rerun()
