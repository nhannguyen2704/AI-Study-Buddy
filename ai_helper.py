import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv

# Tải các biến môi trường từ file .env
load_dotenv()

# Lấy API Key từ biến môi trường
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
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        # [✓] CẬP NHẬT PROMPT KHẮT KHE ĐÚNG CHECKLIST
        prompt = f"""
        Bạn là một gia sư tận tâm và thông minh.
        Hãy đọc và tóm tắt nội dung văn bản dưới đây theo các quy tắc khắt khe sau:
        1. Bắt buộc trình bày dưới dạng các gạch đầu dòng (-) ngắn gọn, súc tích.
        2. Giới hạn độ dài tóm tắt trong khoảng 100 đến 150 từ.
        3. Tập trung vào các khái niệm và kiến thức cốt lõi nhất để học sinh dễ nhớ.

        Văn bản gốc:
        \"\"\"
        {original_text}
        \"\"\"
        """
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        print(f"Lỗi khi gọi Gemini AI: {e}")
        return "Đã xảy ra lỗi trong quá trình AI tóm tắt văn bản."

def generate_flashcards(text):
    """
    Gửi nội dung văn bản tới Gemini để tạo danh sách các câu hỏi - câu trả lời dạng mảng JSON
    """
    if not text or not text.strip():
        return []

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""
        Bạn là một trợ lý học tập thông minh.
        Dựa vào nội dung văn bản dưới đây, hãy tạo các thẻ ghi nhớ (flashcards) tóm tắt các kiến thức cốt lõi.

        Nội dung văn bản:
        \"\"\"
        {text}
        \"\"\"

        YÊU CẦU ĐỊNH DẠNG BẮT BỤC:
        - Chỉ trả về một mảng JSON thuần túy (JSON array).
        - KHÔNG chèn thêm bất kỳ đoạn văn bản giải thích, ký tự thừa hay khối định dạng Markdown (như ```json ... ```).
        - Mỗi phần tử trong mảng là một đối tượng chứa đúng 2 key: "question" và "answer".

        Ví dụ mẫu:
        [
            {{"question": "Khái niệm A là gì?", "answer": "Là..."}},
            {{"question": "Đặc điểm chính của B?", "answer": "Gồm..."}}
        ]
        """

        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # Làm sạch chuỗi JSON phòng trường hợp AI tự động bọc thẻ ```json ... ```
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
            raw_text = re.sub(r"\n?```$", "", raw_text)

        # Bóc tách dữ liệu chuỗi JSON thành Python list/dict
        flashcards_data = json.loads(raw_text.strip())

        if isinstance(flashcards_data, list):
            return flashcards_data
        return []

    except json.JSONDecodeError as e:
        print(f"Lỗi bóc tách JSON từ Gemini: {e}")
        print("Dữ liệu thô AI trả về:", raw_text)
        return []
    except Exception as e:
        print(f"Lỗi khi gọi Gemini AI tạo flashcards: {e}")
        return []