import streamlit as st
from openai import OpenAI
from gtts import gTTS
import base64
import os
import tempfile
import requests
import random
import qrcode
from io import BytesIO

# --- Page config ---
st.set_page_config(
    page_title="Phân tích thông tin xấu độc",
    page_icon="pic/iconfisc.png",
    layout="wide"
)

# --- PWA & iOS ---
st.markdown(
    """
<link rel="manifest" href="/manifest.json">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="apple-touch-icon" href="/pic/iconfisc.png">
    """,
    unsafe_allow_html=True
)

# --- State flags ---
for flag in ("play_audio", "audio_embed", "captcha_reset", "show_instructions"):
    if flag not in st.session_state:
        st.session_state[flag] = False

# --- Audio state defaults ---
if "audio_embed" not in st.session_state:
    st.session_state.audio_embed = ""

# --- CAPTCHA init ---
if "captcha_q" not in st.session_state or st.session_state.captcha_reset:
    a, b = random.randint(1, 9), random.randint(1, 9)
    st.session_state.captcha_q = f"{a} + {b} = ?"
    st.session_state.captcha_a = str(a + b)
    st.session_state.captcha_reset = False

# --- Config & secrets ---
ADMIN_ENDPOINT = "https://congpro.pythonanywhere.com/api/reports"
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
# --- Session defaults ---
for key, default in {
    "content": "",
    "image_files": [],
    "result": "",
    "ready": False,
    "show_report": False
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- Helper functions ---
def analyze(content: str, image_files) -> str:
    """Gửi văn bản + ảnh lên GPT-4o để phân loại theo HD 99-HD/BTGTW."""
    # 1️⃣ Build một message duy nhất với các phần text + image
    parts = [
        {
            "type": "text",
            "text": (
                "Bạn là một chuyên gia truyền thông và an ninh thông tin, có nhiệm vụ đánh giá "
                "nội dung văn bản hoặc hình ảnh (nếu có mô tả nội dung hình ảnh) và phân loại "
                "thông tin theo hướng dẫn số 99-HD/BTGTW ngày 20/3/2023 của Ban Tuyên giáo Trung ương. "
                "Vui lòng thực hiện các yêu cầu sau:\n"
                "1. Phân loại nội dung đầu vào thành một trong ba nhóm: "
                "- Thông tin tích cực; - Thông tin trung lập; - Thông tin xấu độc.\n"
                "2. Giải thích lý do phân loại, đối chiếu với các dấu hiệu trong hướng dẫn:\n"
                "   • Về hình thức (nguồn, cách trình bày, định dạng)\n"
                "   • Về nội dung (có thuộc danh mục I hoặc II của hướng dẫn hay không)\n"
                "3. Nếu xấu độc, chỉ rõ dấu hiệu cụ thể (ví dụ xuyên tạc lịch sử, chia rẽ dân tộc…).\n"
                "4. Nếu tích cực, chỉ rõ yếu tố tích cực (ví dụ tuyên truyền chính sách, biểu dương gương tốt…).\n"
                "5. Kết luận cuối cùng: 'Thông tin tích cực', 'Thông tin trung lập' hoặc 'Thông tin xấu độc'.\n"
                f"---\nDữ liệu đầu vào cần đánh giá: {content}"
            )
        }
    ]

    # 2️⃣ Thêm phần hình ảnh vào cùng message
    for file in image_files:
        img_bytes = file.read()
        file.seek(0)
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        parts.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{file.type};base64,{img_b64}"
            }
        })

    # 3️⃣ Gọi API với client mới
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": parts}],
        max_tokens=1500
    )

    return resp.choices[0].message.content

def text_to_speech(text: str) -> str:
    clean = text.replace("*", "")
    tts = gTTS(text=clean, lang="vi")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp.name)
    return tmp.name

# --- Mobile install instructions ---
if st.button("Cài phần mềm về điện thoại"):
    st.session_state.show_instructions = True

if st.session_state.show_instructions:
    st.markdown("---")
    device = st.radio("Chọn thiết bị của bạn:", ["iOS", "Android"])
    if device == "iOS":
        st.subheader("🛈 Thêm vào Màn hình chính (iOS)")
        st.write("""
1. Nhấn **Chia sẻ** (biểu tượng ⬆️) dưới cùng Safari.  
2. Chọn **Thêm vào Màn hình chính**.  
3. Nhấn **Thêm**.
""")
    else:
        st.subheader("🛈 Tải & Cài APK (Android)")
        apk_url = "http://raw.githubusercontent.com/congpro123/fisc_web/main/FISC.apk"
        st.download_button("⬇️ Tải APK về máy",
            data=requests.get(apk_url).content,
            file_name="FISC.apk",
            mime="application/vnd.android.package-archive",
        )
        st.write("Sau khi tải, mở file **FISC.apk** để cài.")
        qr = qrcode.make(apk_url)
        buf = BytesIO(); qr.save(buf, "PNG")
        st.image(buf.getvalue(), caption="Quét QR để tải APK", width=200)
    if st.button("Đã hiểu"):
        st.session_state.show_instructions = False
    st.markdown("---")

# --- Main analysis UI ---
if not st.session_state.show_report:
    # Header
    c1, c2 = st.columns([0.05,0.95])
    with c1: st.image("pic/iconfisc.png", width=64)
    with c2: st.title("Phân tích thông tin xấu độc")
    st.markdown("Nhập nội dung, upload ảnh, trả lời CAPTCHA rồi bấm **Phân tích**.")

    # Content & images
    c1, c2 = st.columns([2,1])
    with c1:
        content = st.text_area(
            "✍️ Nhập nội dung", st.session_state.content, height=200
        )
    with c2:
        uploaded = st.file_uploader(
            "🖼️ Upload ảnh", type=["png","jpg","jpeg"], accept_multiple_files=True
        )
        if uploaded:
            for f in uploaded:
                st.session_state.image_files.append(f)

    # CAPTCHA + Analyze on one row
    cap_col, btn_col = st.columns([1,16])
    with cap_col:
        captcha_ans = st.text_input(
            f"🔒 CAPTCHA: {st.session_state.captcha_q}",
            key="captcha_input"
        )
    with btn_col:
        st.markdown("<div style='padding-top: 28px'></div>", unsafe_allow_html=True)
        analyze_clicked = st.button("🚀 Phân tích")

    if analyze_clicked:
        # 1) CAPTCHA check
        if not captcha_ans:
            st.warning("⚠️ Vui lòng nhập CAPTCHA.")
        elif captcha_ans != st.session_state.captcha_a:
            st.error("❌ CAPTCHA không đúng.")
        # 2) content/img
        elif not content and not st.session_state.image_files:
            st.warning("⚠️ Nhập nội dung hoặc upload ảnh.")
        else:
            # reset audio flag
            st.session_state.play_audio = False
            # save inputs
            st.session_state.content = content
            # analyze
            with st.spinner("⏳ Đang phân tích..."):
                st.session_state.result = analyze(content, st.session_state.image_files)
                st.session_state.ready = True
            # reset CAPTCHA
            st.session_state.captcha_reset = True
            if "captcha_input" in st.session_state:
                del st.session_state["captcha_input"]

    # show result
    if st.session_state.ready:
        st.markdown("### 📋 Kết quả phân loại:")
        st.write(st.session_state.result)

        # nghe kết quả
        if st.button("🔊 Nghe kết quả"):
            mp3 = text_to_speech(st.session_state.result)
            data = open(mp3,"rb").read()
            b64 = base64.b64encode(data).decode()
            st.session_state.audio_embed = (
                f"<audio controls style='width:100%;'>"
                f"<source src='data:audio/mp3;base64,{b64}' type='audio/mp3'>"
                "Trình duyệt không hỗ trợ audio."
                "</audio>"
            )
            st.session_state.play_audio = True

        if st.session_state.play_audio:
            st.markdown(st.session_state.audio_embed, unsafe_allow_html=True)

        # báo cáo
        if st.button("📝 Báo cáo"):
            st.session_state.show_report = True

# --- Report form ---
else:
    st.title("📝 Form Báo Cáo")
    st.markdown("Chọn loại, thêm thông tin và gửi về server.")

    with st.form("report_form"):
        report_type = st.selectbox("Loại báo cáo", [
            "Tin giả","Xuyên tạc lịch sử","Kích động bạo lực",
            "Chia rẽ dân tộc","Xúc phạm tổ chức/nhân vật","Thông tin sai sự thật"
        ])
        extra = st.text_area("🔎 Thông tin bổ sung", height=150)
        c1,c2 = st.columns(2)
        with c1: submitted = st.form_submit_button("Gửi")
        with c2: cancelled = st.form_submit_button("Huỷ")

    if cancelled:
        st.session_state.show_report = False
    if submitted:
        payload = {
            "type": report_type,
            "article": st.session_state.content,
            "extra_info": extra,
            "classification": st.session_state.result
        }
        files=[]
        for f in st.session_state.image_files:
            b = f.read()
            files.append(("images",(f.name,b,f.type)))
            f.seek(0)
        try:
            r = requests.post(ADMIN_ENDPOINT,data=payload,files=files,timeout=10)
            r.raise_for_status()
            st.success("✅ Đã gửi báo cáo lên hệ thống.")
        except Exception as e:
            st.error(f"❌ Lỗi gửi: {e}")
        finally:
            st.session_state.show_report = False
