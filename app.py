from flask import Flask, render_template, request, flash, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
# Thêm thư viện mã hóa mật khẩu để bảo mật tài khoản
from werkzeug.security import generate_password_hash, check_password_hash
# [✓] CẬP NHẬT: Import thêm hàm generate_flashcards từ ai_helper
from ai_helper import generate_summary, generate_flashcards

app = Flask(__name__)

# Cấu hình SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///studybuddy.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "key_bi_mat_cua_nhom"

db = SQLAlchemy(app)


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
    # Mối quan hệ giúp lấy danh sách flashcards của tài liệu dễ dàng
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
    return render_template('index.html')


@app.route('/upload_doc', methods=['GET', 'POST'])
def upload():
    # Kiểm tra đăng nhập
    if 'user_id' not in session:
        flash("Bạn cần đăng nhập để sử dụng tính năng tải lên tài liệu!", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        original_text = ""
        uploaded_file = request.files.get('fileInput')

        # Xử lý nếu người dùng tải file lên
        if uploaded_file and uploaded_file.filename != '':
            raw_bytes = uploaded_file.read()
            try:
                original_text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                original_text = raw_bytes.decode("utf-8-sig")
        else:
            # Nếu không có file, lấy nội dung từ ô Textarea
            original_text = request.form.get('study_content', '')

        if original_text.strip():
            # 1. Tóm tắt tài liệu bằng Gemini AI
            ai_summary = generate_summary(original_text)

            # 2. Lưu thông tin Document vào DB
            doc = Document(
                title="Bài học mới",
                original_text=original_text,
                summary_text=ai_summary,
                user_id=session['user_id'] 
            )

            db.session.add(doc)
            db.session.commit() # Commit trước để khởi tạo doc.id

            # 3. [✓] MỚI: Gọi AI sinh danh sách Flashcards (dạng JSON)
            flashcards_list = generate_flashcards(original_text)

            # 4. [✓] MỚI: Duyệt vòng lặp lưu các Flashcard vào Database
            if flashcards_list:
                for item in flashcards_list:
                    if 'question' in item and 'answer' in item:
                        card = Flashcard(
                            question=item['question'],
                            answer=item['answer'],
                            document_id=doc.id
                        )
                        db.session.add(card)
                
                db.session.commit() # Commit tất cả các thẻ ghi nhớ vào DB

            flash("Tài liệu đã được tóm tắt và tạo bộ Flashcard thành công!", "success")
            return redirect(url_for('upload'))
        else:
            flash("Vui lòng cung cấp nội dung tài liệu hoặc tải tệp lên!", "warning")
            return redirect(url_for('upload'))

    return render_template("upload.html")


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
            return redirect(url_for('index'))
        else:
            flash("Email hoặc mật khẩu không đúng. Vui lòng kiểm tra lại!", "danger")
            return redirect(url_for('login'))
            
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear() 
    flash("Bạn đã đăng xuất thành công.", "info")
    return redirect(url_for('index'))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)