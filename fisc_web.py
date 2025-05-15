import streamlit as st
import openai
from gtts import gTTS
import base64
import os
import tempfile
import requests

st.set_page_config(
    page_title="Phân tích thông tin xấu độc", 
    page_icon="pic/iconfisc.png",       # hoặc "static/my_logo.png"
    layout="wide"
)

st.markdown(
    """
<link rel="manifest" href="/manifest.json">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="apple-touch-icon" href="/pic/iconfisc.png">
    """,
    unsafe_allow_html=True
)

# —————————————— CẤU HÌNH ——————————————
openai.api_key = st.secrets["OPENAI_API_KEY"]
ADMIN_ENDPOINT = "https://congpro.pythonanywhere.com/api/reports"

# —————————————— Khởi tạo session state ——————————————
for key, default in {
    "result": "",
    "ready": False,
    "content": "",
    "image_files": [],
    "show_report": False
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# —————————————— Hàm phụ trợ ——————————————

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

def text_to_speech(text: str) -> str:
    """Chuyển text sang mp3, trả về đường dẫn tạm thời."""
    tts = gTTS(text=text, lang="vi")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp.name)
    return tmp.name

# —————————————— Giao diện Streamlit ——————————————

if not st.session_state.show_report:

    col_icon, col_title = st.columns([0.05, 0.95])
    with col_icon:
        st.image(
            "pic/iconfisc.png",  # đường dẫn tới icon giấy của bạn
            width=93               # điều chỉnh kích thước cho vừa
        )
    with col_title:
        st.title("Phân tích thông tin xấu độc")

    st.markdown("Nhập nội dung hoặc upload ảnh, nhấn **Phân tích** rồi **Nghe** hoặc **Báo cáo**.")

    col1, col2 = st.columns([2,1])
    with col1:
        content = st.text_area(
            "✍️ Nhập nội dung cần phân tích",
            height=200,
            value=st.session_state.content
        )
    with col2:
        image_files = st.file_uploader(
            "🖼️ Upload ảnh (jpg/png)",
            type=["jpg","jpeg","png"],
            accept_multiple_files=True,
            key="uploader"
        )

    if st.button("🚀 Phân tích"):
        if not content and not image_files:
            st.warning("⚠️ Vui lòng nhập nội dung hoặc upload ảnh.")
        else:
            st.session_state.content = content
            st.session_state.image_files = image_files
            with st.spinner("⏳ Đang phân tích..."):
                st.session_state.result = analyze(content, image_files)
                st.session_state.ready = True

    if st.session_state.ready:
        st.markdown("### 📋 Kết quả phân loại:")
        st.write(st.session_state.result)

        # Nút nghe
        if st.button("🔊 Nghe kết quả"):
            mp3_path = text_to_speech(st.session_state.result)
            audio_bytes = open(mp3_path, "rb").read()
            st.audio(audio_bytes, format="audio/mp3")

        # Nút Báo cáo chuyển qua form báo cáo
        if st.button("📝 Báo cáo"):
            st.session_state.show_report = True

else:
    # Form Báo Cáo
    st.title("📝 Form Báo Cáo")
    st.markdown("Chọn loại, thêm thông tin và gửi về server quản trị.")

    with st.form("report_form"):
        report_type = st.selectbox(
            "Loại báo cáo",
            options=[
                "Tin giả", "Xuyên tạc lịch sử", "Kích động bạo lực",
                "Chia rẽ dân tộc", "Xúc phạm tổ chức/nhân vật", "Thông tin sai sự thật"
            ]
        )
        extra_info = st.text_area(
            "🔎 Thông tin bổ sung",
            height=150
        )

        col_a, col_b = st.columns(2)
        with col_a:
            submitted = st.form_submit_button("Gửi")
        with col_b:
            cancelled = st.form_submit_button("Huỷ")

    if cancelled:
        # Trở về màn phân tích
        st.session_state.show_report = False

    if submitted:
        # Chuẩn bị payload
        data = {
            "type": report_type,
            "article": st.session_state.content,
            "extra_info": extra_info,
            "classification": st.session_state.result
        }
        files = []
        for file in st.session_state.image_files:
            file_bytes = file.read()
            files.append((
                "images",
                (file.name, file_bytes, file.type)
            ))
            file.seek(0)

        try:
            r = requests.post(ADMIN_ENDPOINT, data=data, files=files, timeout=10)
            r.raise_for_status()
            st.success("✅ Đã gửi báo cáo lên hệ thống quản trị.")
        except Exception as e:
            st.error(f"❌ Không gửi được: {e}")
        finally:
            # Quay lại màn phân tích (giữ nguyên kết quả)
            st.session_state.show_report = False
