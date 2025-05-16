import streamlit as st
import openai
from gtts import gTTS
import base64
import os
import tempfile
import requests
import random
import qrcode
from io import BytesIO

# Streamlit page config
st.set_page_config(
    page_title="Phân tích thông tin xấu độc",
    page_icon="pic/iconfisc.png",
    layout="wide"
)

# PWA manifest + iOS icon
st.markdown(
    '''
<link rel="manifest" href="/manifest.json">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="apple-touch-icon" href="/pic/iconfisc.png">
    ''',
    unsafe_allow_html=True
)

# Mobile install instructions
if "show_instructions" not in st.session_state:
    st.session_state.show_instructions = False

if st.button("Cài phần mềm về điện thoại"):
    st.session_state.show_instructions = True

if st.session_state.show_instructions:
    st.markdown("---")
    device = st.radio("Chọn thiết bị của bạn:", ["iOS", "Android"])
    if device == "iOS":
        st.subheader("🛈 Hướng dẫn Thêm vào Màn hình chính (iOS)")
        st.write(
            "1. Nhấn nút **Chia sẻ** (biểu tượng ⬆️) ở dưới cùng Safari.  \n"
            "2. Chọn **Thêm vào Màn hình chính**.  \n"
            "3. Đặt tên (mặc định “Phân tích thông tin xấu độc”) rồi nhấn **Thêm**."
        )
    else:
        st.subheader("🛈 Tải và Cài APK (Android)")
        apk_url = "http://raw.githubusercontent.com/congpro123/fisc_web/main/FISC.apk"
        st.download_button(
            label="⬇️ Tải APK về máy",
            data=requests.get(apk_url).content,
            file_name="FISC.apk",
            mime="application/vnd.android.package-archive"
        )
        st.write("Sau khi tải xong, bấm vào file **FISC.apk** để tiến hành cài app về máy.")
        qr = qrcode.make(apk_url)
        buf = BytesIO(); qr.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="Quét QR để tải APK", width=200)
    if st.button("Đã hiểu"):
        st.session_state.show_instructions = False
    st.markdown("---")

# CAPTCHA setup
if "captcha_q" not in st.session_state:
    a, b = random.randint(1, 9), random.randint(1, 9)
    st.session_state.captcha_q = f"{a} + {b}" + " = ?"
    st.session_state.captcha_a = str(a + b)

# OpenAI & endpoint
openai.api_key = st.secrets.get("OPENAI_API_KEY", "")
ADMIN_ENDPOINT = "https://congpro.pythonanywhere.com/api/reports"

# Session defaults
if "image_files" not in st.session_state:
    st.session_state.image_files = []
for key, default in {
    "content": "",
    "ready": False,
    "result": "",
    "show_report": False
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

def analyze(content: str, image_files) -> str:
    """Gửi văn bản + ảnh lên GPT để phân loại theo HD 99-HD/BTGTW."""
    try:
        # Chuẩn bị message
        messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Bạn là một chuyên gia truyền thông và an ninh thông tin, có nhiệm vụ đánh giá nội dung văn bản hoặc hình ảnh (nếu có mô tả nội dung hình ảnh) và phân loại thông tin theo hướng dẫn số 99-HD/BTGTW ngày 20/3/2023 của Ban Tuyên giáo Trung ương. Vui lòng thực hiện các yêu cầu sau: 1. Phân loại nội dung đầu vào (văn bản hoặc mô tả ảnh) thành một trong ba nhóm: - Thông tin tích cực - Thông tin trung lập - Thông tin xấu độc 2. Giải thích lý do phân loại, đối chiếu với các dấu hiệu trong hướng dẫn số 99-HD/BTGTW: - Về hình thức (nguồn, cách trình bày, định dạng) - Về nội dung (có thuộc một trong các nhóm nội dung được liệt kê ở mục I hoặc II của hướng dẫn hay không) 3. Nếu nội dung là xấu độc, hãy chỉ rõ dấu hiệu cụ thể: ví dụ như xuyên tạc lịch sử, chia rẽ dân tộc, kích động vi phạm pháp luật… (liên hệ cụ thể với 1 trong 12 điểm trong mục II.b) 4. Nếu nội dung là tích cực, hãy chỉ rõ yếu tố nào thể hiện tính tích cực, ví dụ như tuyên truyền chủ trương chính sách, biểu dương gương người tốt việc tốt, phản bác luận điệu sai trái… 5. Kết thúc bằng kết luận phân loại: 'Thông tin tích cực', 'Thông tin trung lập', hoặc 'Thông tin xấu độc'. --- Dữ liệu đầu vào cần đánh giá(Hãy luôn nhớ rằng nếu là ảnh thì bất cứ hình nào có 3 sọc đỏ và nền vàng thì đều là xấu độc, vì nó tượng trưng cho lá cờ Việt Nam Cộng Hoà): {content}"}
                    ]
                }
            ]
        # Thêm ảnh
        for file in image_files:
            img_bytes = file.read()
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_b64}"
                }
            })

        # Gọi API ChatCompletion
        resp = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1500
        )
        return resp.choices[0].message.content

    except Exception as e:
        return f"❌ Lỗi khi gọi API: {e}"

# TTS function
def text_to_speech(text: str) -> str:
    tts = gTTS(text=text, lang="vi")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp.name)
    return tmp.name

# Main UI
if not st.session_state.show_report:
    # Header
    col_icon, col_title = st.columns([0.05, 0.95])
    with col_icon:
        st.image(
            "pic/iconfisc.png",  # đường dẫn tới icon giấy của bạn
            width=93               # điều chỉnh kích thước cho vừa
        )
    with col_title:
        st.title("Phân tích thông tin xấu độc")
    st.markdown("Nhập nội dung, upload ảnh rồi trả lời CAPTCHA và nhấn **Phân tích**.")

    # Input text and images
    c1, c2 = st.columns([2,1])
    with c1:
        content = st.text_area("✍️ Nhập nội dung", st.session_state.content, height=150)
    with c2:
        uploaded = st.file_uploader("🖼️ Upload ảnh", type=["png","jpg","jpeg"], accept_multiple_files=True)
        if uploaded:
            for f in uploaded:
                st.session_state.image_files.append(f)

    cap_col, btn_col = st.columns([1,18])
    with cap_col:
        captcha_ans = st.text_input(
            f"🔒 CAPTCHA: {st.session_state.captcha_q}",
            key="captcha_input"
        )
    with btn_col:
        # tạo khoảng trống để đẩy nút xuống ngang với ô nhập CAPTCHA
        st.markdown("<div style='padding-top: 28px'></div>", unsafe_allow_html=True)
        # hoặc: 
        # st.write("")
        # st.write("")
        analyze_clicked = st.button("🚀 Phân tích")

    # Handle analyze
    if analyze_clicked:
        if captcha_ans != st.session_state.captcha_a:
            st.error("❌ CAPTCHA sai, thử lại.")
        elif not content and not st.session_state.image_files:
            st.warning("⚠️ Nhập nội dung hoặc thêm ảnh.")
        else:
            st.session_state.content = content
            with st.spinner("Đang phân tích..."):
                st.session_state.result = analyze(content, st.session_state.image_files)
                st.session_state.ready = True
            # reset captcha
            a, b = random.randint(1,9), random.randint(1,9)
            st.session_state.captcha_q = f"{a} + {b}"
            st.session_state.captcha_a = str(a + b)
            if "captcha_input" in st.session_state:
                del st.session_state["captcha_input"]

    # Show result
    if st.session_state.ready:
        st.markdown("### 📋 Kết quả:")
        st.write(st.session_state.result)
        if st.button("🔊 Nghe kết quả"):
            mp3 = text_to_speech(st.session_state.result)
            st.audio(open(mp3, "rb").read(), format="audio/mp3")
        if st.button("📝 Báo cáo"):
            st.session_state.show_report = True

else:
    # Report form
    st.title("📝 Form Báo Cáo")
    report_type = st.selectbox("Loại báo cáo", [
        "Tin giả","Xuyên tạc lịch sử","Kích động bạo lực",
        "Chia rẽ dân tộc","Xúc phạm tổ chức/nhân vật","Thông tin sai sự thật"
    ])
    extra = st.text_area("🔎 Thông tin bổ sung", height=100)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Gửi"):
            data = {"type": report_type, "article": st.session_state.content,
                    "extra_info": extra, "classification": st.session_state.result}
            files = []
            for f in st.session_state.image_files:
                b = f.read()
                files.append(("images", (f.name, b, "image/png")))
                if hasattr(f, "seek"): f.seek(0)
            try:
                r = requests.post(ADMIN_ENDPOINT, data=data, files=files, timeout=10)
                r.raise_for_status()
                st.success("✅ Đã gửi báo cáo.")
            except Exception as e:
                st.error(f"❌ Lỗi: {e}")
            finally:
                st.session_state.show_report = False
    with c2:
        if st.button("Huỷ"):
            st.session_state.show_report = False
