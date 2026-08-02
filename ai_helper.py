import json
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

# Tải các biến môi trường từ file .env
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("⚠️ CẢNH BÁO: Chưa tìm thấy GEMINI_API_KEY trong file .env!")
    client = None
else:
    # 🟢 Khởi tạo Client theo chuẩn SDK mới
    client = genai.Client(api_key=GEMINI_API_KEY)


# Định nghĩa cấu trúc JSON đầu ra cho Flashcard
class Flashcard(BaseModel):
    question: str
    answer: str


def generate_summary(original_text):
    if not original_text or not original_text.strip():
        return "Không có nội dung để tóm tắt."

    if not client:
        return "Lỗi: Chưa cấu hình API Key."

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        
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

        # 🟢 Gọi API thông qua client.models.generate_content
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        return response.text

    except Exception as e:
        print(f"Lỗi khi gọi Gemini AI tóm tắt: {e}")
        return f"Lỗi Gemini: {str(e)}"


def generate_flashcards(text):
    """Gửi nội dung văn bản tới Gemini để tạo danh sách flashcards dạng JSON."""
    if not text or not text.strip():
        return []

    if not client:
        print("Lỗi: Chưa cấu hình API Key.")
        return []

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        prompt = f"""
        Dựa vào nội dung văn bản dưới đây, hãy tạo các thẻ ghi nhớ (flashcards) tóm tắt các kiến thức cốt lõi.

        Nội dung văn bản:
        \"\"\"
        {text}
        \"\"\"
        """

        # 🟢 Ép Gemini trả về đúng cấu trúc danh sách Flashcard bằng response_schema
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=list[Flashcard],
            ),
        )

        # Kết quả chắc chắn là chuỗi JSON hợp lệ
        flashcards_data = json.loads(response.text)
        return flashcards_data

    except json.JSONDecodeError as e:
        print(f"Lỗi bóc tách JSON từ Gemini: {e}")
        return []
    except Exception as e:
        print(f"Lỗi khi gọi Gemini AI tạo flashcards: {e}")
        return []