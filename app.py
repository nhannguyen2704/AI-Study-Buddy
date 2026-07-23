from flask import Flask, render_template, request, flash, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
# Thêm thư viện mã hóa mật khẩu để bảo mật tài khoản
from werkzeug.security import generate_password_hash, check_password_hash
from ai_helper import generate_summary
from ai_helper import generate_summary, generate_flashcards
app = Flask(__name__)

# Cấu hình SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///studybuddy.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "key_bi_mat_cua_nhom"

db = SQLAlchemy(app)


# ==============================================================================
# 1. CẬP NHẬT MODEL DATABASE
# ==============================================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    # Định nghĩa mối quan hệ (Tùy chọn, giúp lấy danh sách tài liệu từ user dễ hơn)
    documents = db.relationship('Document', backref='author', lazy=True)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    original_text = db.Column(db.Text, nullable=False)
    summary_text = db.Column(db.Text)
    # [✓] THÀNH PHẦN MỚI: Liên kết Document với User cụ thể sở hữu nó
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

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


# [✓] CẬP NHẬT ROUTE UPLOAD: Đổi tên thành /upload để khớp với form HTML cũ
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    # [✓] KIỂM TRA QUYỀN TRUY CẬP: Chặn người dùng vãng lai
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
            # Nếu không có file, thử lấy nội dung từ ô Textarea nhập tay
            original_text = request.form.get('study_content', '')

        # Kiểm tra nội dung có rỗng hay không trước khi gọi AI
        if original_text.strip():
            ai_summary = generate_summary(original_text)

            # [✓] CẬP NHẬT LƯU VÀO DB: Gắn kèm user_id lấy từ phiên đăng nhập (session)
            doc = Document(
                title="Bài học mới",
                original_text=original_text,
                summary_text=ai_summary,
                user_id=session['user_id'] 
            )

    db.session.add(doc)
    db.session.commit()

    # Tạo flashcard bằng AI
    flashcards = generate_flashcards()(original_text)

    for card in flashcards:
        new_card = Flashcard(
            question=card["question"],
            answer=card["answer"],
            document_id=doc.id
        )
        db.session.add(new_card)

    db.session.commit()

    flash("Tài liệu đã được tải lên thành công!", "success")
    return "Tải tài liệu thành công"

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