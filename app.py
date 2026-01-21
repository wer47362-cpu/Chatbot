import os
import google.generativeai as genai
from pypdf import PdfReader
import streamlit as st
from prompt import PROMPT_WORKAW
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import dotenv

# โหลด Environment Variables
dotenv.load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# ตั้งค่า API Key
if not GOOGLE_API_KEY:
    st.error("ไม่พบ GOOGLE_API_KEY ในไฟล์ .env")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# ตั้งค่าการตอบ (ปรับ Temperature เป็น 0 เพื่อลดความมั่ว)
generation_config = {
    "temperature": 0.0, 
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 2048,
    "response_mime_type": "text/plain",
}

SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
}

# --- ส่วนอ่านไฟล์ PDF (เพิ่มตัวเช็คว่าอ่านออกไหม) ---
pdf_filename = "Graphic.pdf" 
pdf_content = ""

try:
    if os.path.exists(pdf_filename):
        reader = PdfReader(pdf_filename)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pdf_content += text + "\n"
        
        # --- เช็คความยาวตัวอักษร ---
        print("--------------------------------------------------")
        print(f"✅ อ่านไฟล์สำเร็จ! ความยาวตัวอักษร: {len(pdf_content)} ตัว")
        if len(pdf_content) < 100:
            print("⚠️  คำเตือน: เนื้อหาไฟล์น้อยผิดปกติ! อาจเป็นไฟล์สแกน (รูปภาพ) AI จะอ่านไม่ออก")
        print("--------------------------------------------------")

    else:
        st.error(f"❌ ไม่พบไฟล์ {pdf_filename} กรุณาตรวจสอบตำแหน่งไฟล์")
except Exception as e:
    st.error(f"❌ เกิดข้อผิดพลาดในการอ่านไฟล์ PDF: {e}")

# --- รวม Prompt ---
FULL_SYSTEM_INSTRUCTION = f"""
{PROMPT_WORKAW}

----------------------------------------
CONTEXT / KNOWLEDGE BASE (ข้อมูลอ้างอิงจากเอกสาร):
{pdf_content}
----------------------------------------
"""

# ... (โค้ดส่วนบนเหมือนเดิม) ...

# สร้าง Model (เลือกรุ่นที่ระบบรองรับแน่นอน)
try:
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash", # ลองใช้ตัวนี้ก่อน
        safety_settings=SAFETY_SETTINGS,
        generation_config=generation_config,
        system_instruction=FULL_SYSTEM_INSTRUCTION 
    )
except:
    # ถ้าตัวบนพัง ให้ใช้ตัวสำรอง gemini-pro
    print("⚠️ หา gemini-1.5-flash ไม่เจอ กำลังสลับไปใช้ gemini-pro")
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-001",
        safety_settings=SAFETY_SETTINGS,
        generation_config=generation_config,
        # system_instruction=FULL_SYSTEM_INSTRUCTION # gemini-pro บางรุ่นไม่รับ system_instruction บรรทัดนี้อาจต้องลบถ้า error
    )

# --- ส่วนตกแต่งพื้นหลัง (CSS) ---
page_bg_img = """
<style>
[data-testid="stAppViewContainer"] {
    background-image: linear-gradient(to bottom right, #E0C3FC, #FFD1DC, #BDE0FE);
}
[data-testid="stHeader"] {
    background-color: rgba(0, 0, 0, 0);
}
[data-testid="stSidebar"] {
    background-color: #F3E5F5;
}
</style>
"""
st.markdown(page_bg_img, unsafe_allow_html=True)

# --- User Interface ---
def clear_history():
    st.session_state["messages"] = [
        {"role": "model", "content": "สวัสดีค่ะ น้อง Graphic Bot พร้อมให้บริการความรู้เรื่องกราฟิกแล้วค่า 🎨✨"}
    ]
    st.rerun()

with st.sidebar:
    if st.button("🗑️ ล้างประวัติการคุย"):
        clear_history()

st.title("✨ น้อง Graphic Bot 🎨")

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "model", "content": "สวัสดีค่ะ น้อง Graphic Bot พร้อมให้บริการความรู้เรื่องกราฟิกแล้วค่า 🎨✨"}
    ]

# แสดงประวัติ
for msg in st.session_state["messages"]:
    avatar_icon = "🐰" if msg["role"] == "user" else "🦄"
    st.chat_message(msg["role"], avatar=avatar_icon).write(msg["content"])

# รับ Input
if prompt := st.chat_input():
    st.session_state["messages"].append({"role": "user", "content": prompt})
    st.chat_message("user", avatar="🐰").write(prompt)

    def generate_response():
        # สร้าง History
        history_api = [
            {"role": msg["role"], "parts": [{"text": msg["content"]}]}
            for msg in st.session_state["messages"]
        ]

        try:
            chat_session = model.start_chat(history=history_api)
            
            # --- 🔥 จุดแก้เผ็ด AI มั่ว: บังคับคำสั่งแนบท้ายทุกครั้ง (Suffix Prompting) 🔥 ---
            # เราแอบส่งคำสั่งนี้ไปพร้อมคำถาม แต่ User จะไม่เห็น
            strict_prompt = f"""
            {prompt}
            
            (IMPORTANT COMMAND FOR AI: 
            1. Answer purely based on the provided CONTEXT above.
            2. If the answer is NOT in the CONTEXT, you MUST say "ขออภัยค่ะ ไม่มีข้อมูลเรื่องนี้ในเอกสารค่ะ 🥺"
            3. DO NOT use outside knowledge to answer.)
            """
            
            response = chat_session.send_message(strict_prompt)
            
            st.session_state["messages"].append({"role": "model", "content": response.text})
            st.chat_message("model", avatar="🦄").write(response.text)

        except Exception as e:
            st.error(f"ระบบขัดข้องชั่วคราว: {e}")

    generate_response()