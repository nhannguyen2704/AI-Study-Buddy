import os
import google.generativeai as genai
from dotenv import load_dotenv

# Tải các biến môi trường từ file .env
load_dotenv()

# Lấy API Key từ biến môi trường (Bài trước đã cấu hình trong file .env)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Cấu hình API Key cho Gemini AI
genai.configure(api_key=GEMINI_API_KEY)

def generate_summary(original_text):
    """
    Hàm nhận vào văn bản gốc và trả về đoạn tóm tắt từ Gemini AI
    """
    if not original_text or not original_text.strip():
        return "Không có nội dung để tóm tắt."
    try:
        # Sử dụng mô hình gemini-2.5-flash để tóm tắt tối ưu nhất
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = (
            "Hãy đóng vai là một trợ lý học tập thông minh. "
            "Đọc và tóm tắt ngắn gọn, đọng lại các ý chính của văn bản sau bằng Tiếng Việt:\n\n"
            f"{original_text}"
        )
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        print(f"Lỗi khi gọi Gemini AI: {e}")
        return "Đã xảy ra lỗi trong quá trình AI tóm tắt văn bản."