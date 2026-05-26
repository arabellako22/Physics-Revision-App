import streamlit as st
import google.generativeai as genai
from PIL import Image
import os
from supabase import create_client

@st.cache_resource
def get_supabase():
    url = os.environ.get("SUPABASE_URL") or st.secrets["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_ANON_KEY") or st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)

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
    st.set_page_config(page_title="A-Level Physics Solver", layout="centered")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("## ⚛️ Physics Solver")
        st.markdown("*A-Level Physics Revision*")
        st.markdown("---")
        st.markdown("#### Enter your details")
        email = st.text_input("Email used at checkout", placeholder="student@email.com", label_visibility="collapsed")
        code = st.text_input("Access Code", placeholder="e.g. PHYS-A001", label_visibility="collapsed")
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
        try:
            purchase_url = st.secrets.get("PHYS_PAYMENT_URL", "")
        except Exception:
            purchase_url = ""
        if purchase_url:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align:center'><a href='{purchase_url}' target='_blank'>🎟 Get Physics Access</a></div>", unsafe_allow_html=True)
        with st.expander("Having trouble logging in?"):
            st.markdown("""
            - Use the **exact email** from your PayPal receipt
            - Check for spaces before/after your code
            - Codes are case-insensitive
            - Still stuck? Email: **support@kodari.co.uk**
            """)

if not is_authenticated():
    show_access_gate()
    st.stop()

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error("API Key missing! Check your Streamlit Secrets settings.")

@st.cache_resource
def load_physics_model():
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
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

model = load_physics_model()

st.title("⚛️ A-Level Physics Revision Tool")
st.write(f"Connected to Model: **{model.model_name}**")

uploaded_file = st.file_uploader("Upload a physics question photo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption='Question Preview', use_container_width=True)
    if st.button('Generate Model Answer'):
        with st.spinner('Accessing Physics Database...'):
            try:
                response = model.generate_content([
                    "Provide the A-level model answer for this physics question. Reference the mark schemes in my drive.",
                    image
                ])
                st.success("Analysis Complete!")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Technical Error: {e}")

with st.sidebar:
    st.markdown("---")
    if st.button("Log out", use_container_width=True):
        st.session_state["phys_auth"] = False
        st.rerun()
