from flask import Flask, render_template, request, flash, redirect, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
# Thêm thư viện mã hóa mật khẩu để bảo mật tài khoản
from werkzeug.security import generate_password_hash, check_password_hash
# Import các hàm xử lý AI từ ai_helper
from ai_helper import generate_summary, generate_flashcards
# Import thư viện đọc file PDF
import PyPDF2
import io

app = Flask(__name__)

# Cấu hình SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///studybuddy.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "key_bi_mat_cua_nhom"
# Cấu hình giới hạn kích thước file upload (50MB)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

db = SQLAlchemy(app)


# Xử lý lỗi 413 khi file upload vượt quá giới hạn cho phép
@app.errorhandler(413)
def request_entity_too_large(error):
    flash("File quá lớn! Kích thước tối đa cho phép là 50MB.", "error")
    return redirect(url_for('upload_doc'))


# ==============================================================================
# 1. MODEL DATABASE
# ==============================================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    documents = db.relationship('Document', backref='author', lazy=True)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    original_text = db.Column(db.Text, nullable=False)
    summary_text = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Mối quan hệ giúp lấy danh sách flashcards của tài liệu
    flashcards = db.relationship('Flashcard', backref='document', lazy=True)

class Flashcard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.String(500), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)


# ==============================================================================
# 2. CÁC ROUTE XỬ LÝ
# ==============================================================================

@app.route('/')
def index():
    return render_template('index.html', active_page='index')


@app.route('/upload_doc', methods=['GET', 'POST'])
def upload_doc():
    try:
        print(f"Người dùng hiện tại: {session.get('username', 'Chưa đăng nhập')}")  # Debug thông tin người dùng

        # Kiểm tra đăng nhập
        if 'user_id' not in session:
            flash("Bạn cần đăng nhập để sử dụng tính năng tải lên tài liệu!", "warning")
            return redirect(url_for('login'))

        if request.method == 'POST':
            original_text = ""
            print(f"Form dữ liệu nhận được: {request.form}")  # Debug dữ liệu form
            uploaded_file = request.files.get('fileInput')

            print(f"Người dùng {session.get('username')} đang tải lên tài liệu: {uploaded_file.filename if uploaded_file else 'Không có tệp'}")
            # Xử lý nếu người dùng tải file lên
            if uploaded_file and uploaded_file.filename != '':
                # Kiểm tra nếu file là PDF thì dùng PyPDF2 để trích xuất text
                if uploaded_file.filename.lower().endswith('.pdf'):
                    try:
                        pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
                        original_text = ""
                        for page in pdf_reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                original_text += page_text + "\n"
                    except Exception as e:
                        flash(f"Không thể đọc file PDF: {str(e)}", "error")
                        return redirect(url_for('upload_doc'))
                else:
                    # Xử lý file text thông thường (.txt, .md, ...)
                    raw_bytes = uploaded_file.read()
                    try:
                        original_text = raw_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        original_text = raw_bytes.decode("utf-8-sig")
            else:
                # Nếu không có file, lấy nội dung từ ô Textarea
                original_text = request.form.get('study_content', '')

            if original_text.strip():
                try:
                    print(f"Nội dung tài liệu gốc: {original_text[:100]}...")  # In ra 100 ký tự đầu tiên để kiểm tra
                    # 1. Tóm tắt tài liệu bằng Gemini AI
                    ai_summary = generate_summary(original_text)
                    print(f"Tóm tắt từ Gemini AI: {ai_summary}")

                    # 2. Lưu thông tin Document vào DB
                    doc = Document(
                        title="Bài học mới",
                        original_text=original_text,
                        summary_text=ai_summary,
                        user_id=session['user_id']
                    )

                    db.session.add(doc)
                    db.session.commit() # Commit trước để lấy doc.id

                    # 3. Gọi AI sinh danh sách Flashcards (dạng JSON)
                    flashcards_list = generate_flashcards(original_text)

                    # 4. Duyệt vòng lặp lưu các Flashcard vào Database
                    if flashcards_list and isinstance(flashcards_list, list):
                        for item in flashcards_list:
                            if isinstance(item, dict) and 'question' in item and 'answer' in item:
                                card = Flashcard(
                                    question=item['question'],
                                    answer=item['answer'],
                                    document_id=doc.id
                                )
                                db.session.add(card)

                        db.session.commit() # Commit các thẻ ghi nhớ vào DB

                    flash("Tài liệu đã được tóm tắt và tạo bộ Flashcard thành công!", "success")
                    return redirect(url_for('dashboard'))

                except Exception as e:
                    db.session.rollback() # Khôi phục lại trạng thái DB nếu xảy ra lỗi
                    print(f"Lỗi hệ thống chi tiết: {e}")
                    flash(f"Lỗi xử lý tài liệu: {str(e)}", "error")
                    return redirect(url_for('upload_doc'))

            else:
                flash("Vui lòng cung cấp nội dung tài liệu hoặc tải tệp lên!", "warning")
                return redirect(url_for('upload_doc'))

        return render_template("upload.html", active_page='upload_doc')
    except Exception as e:
        print(f"Lỗi hệ thống chi tiết: {e}")
        flash(f"Lỗi hệ thống: {str(e)}", "error")
        return render_template("upload.html", active_page='upload_doc')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash("Email này đã được đăng ký trước đó rồi!", "warning")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Đăng ký thành công! Vui lòng đăng nhập.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username

            flash(f"Đăng nhập thành công! Chào mừng {user.username} quay trở lại.", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Email hoặc mật khẩu không đúng. Vui lòng kiểm tra lại!", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("Bạn đã đăng xuất thành công.", "info")
    return redirect(url_for('index'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Vui lòng đăng nhập để truy cập trang chủ!", "warning")
        return redirect(url_for('login'))

    # Lấy toàn bộ tài liệu thuộc về người dùng đang đăng nhập
    user_docs = Document.query.filter_by(user_id=session['user_id']).all()
    return render_template('dashboard.html', documents=user_docs, active_page='dashboard')

@app.route('/document/<int:doc_id>')
def view_document(doc_id):
    # Kiểm tra người dùng đã đăng nhập chưa
    if 'user_id' not in session:
        flash("Vui lòng đăng nhập để xem nội dung tài liệu!", "warning")
        return redirect(url_for('login'))
        
    # Lấy tài liệu theo doc_id và đảm bảo tài liệu thuộc về user đang đăng nhập
    doc = Document.query.filter_by(id=doc_id, user_id=session['user_id']).first_or_404()
    
    return render_template('detail.html', doc=doc)

@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html', active_page='aboutus')

import google.generativeai as genai
from flask import jsonify, request, session

@app.route('/api/chat', methods=['POST'])
def api_chat():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Bạn cần đăng nhập để thực hiện'}), 401
            
        data = request.get_json()
        doc_id = data.get('doc_id')
        question = data.get('question')

        if not question:
            return jsonify({'error': 'Câu hỏi không được để trống'}), 400
            
        doc = Document.query.filter_by(id=doc_id, user_id=session['user_id']).first()
        if not doc:
            return jsonify({'error': 'Không tìm thấy tài liệu'}), 404

        # 1. Khởi tạo model AI trực tiếp (không dùng hàm tóm tắt cũ)
        model = genai.GenerativeModel('gemini-3.6-flash')
        
        # 2. Xây dựng prompt rõ ràng
        prompt = f"""
        Bạn là một trợ lý AI thông minh. Hãy trả lời trực tiếp, chính xác câu hỏi của người dùng.

        [Nội dung tài liệu đính kèm để tham khảo]:
        {doc.original_text[:3000]}

        [Lưu ý]: 
        - Trả lời thẳng vào câu hỏi dưới đây. 
        - Không tự ý tóm tắt bài học trừ khi người dùng yêu cầu.
        
        Câu hỏi của người dùng: {question}
        """

        # 3. Gửi cho Gemini tạo câu trả lời
        response = model.generate_content(prompt)
        ai_response = response.text

        return jsonify({'answer': ai_response})

    except Exception as e:
        print(f"Lỗi API Chat: {e}")
        return jsonify({'error': f'Lỗi hệ thống: {str(e)}'}), 500

# Đảm bảo phần khởi chạy app phải nằm ở dưới cùng
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
