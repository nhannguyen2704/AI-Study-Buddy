from xml.dom.xmlbuilder import DocumentLS

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



# Model User (Đã thêm để sửa lỗi NameError)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Model Document
class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    original_text = db.Column(db.Text, nullable=False)
    summary_text = db.Column(db.Text)

    # Thêm dòng này
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
# Model Flashcard
class Flashcard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.String(500), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    # Kiểm tra đăng nhập
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập trước.')
        return redirect(url_for('login'))

    # Lấy danh sách tài liệu của user hiện tại
    documents = Document.query.filter_by(user_id=session['user_id']).all()

    # Hiển thị dashboard
    return render_template('dashboard.html', documents=documents)

@app.route('/upload_doc', methods=['GET', 'POST'])
def upload_doc():
    if 'user_id' not in session:
        flash("Bạn cần đăng nhập để sử dụng tính năng tải lên tài liệu!", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        uploaded_file = request.files.get('fileInput')

        if uploaded_file:
            original_text = uploaded_file.read().decode("utf-8")

            ai_summary = generate_summary(original_text)

            doc = Document(
                title="Bài học mới",
                original_text=original_text,
                summary_text=ai_summary,
                user_id=session["user_id"]
            )

            db.session.add(doc)
            db.session.commit()

            # Tạo flashcard bằng AI
            flashcards = generate_flashcards(original_text)

            for card in flashcards:
                new_card = Flashcard(
                    question=card["question"],
                    answer=card["answer"],
                    document_id=doc.id
                )
                db.session.add(new_card)

            db.session.commit()

            flash("Tài liệu đã được tải lên thành công!", "success")
            return redirect(url_for("dashboard"))

    return render_template("upload.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Kiểm tra trùng lặp email
        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash("Email này đã được đăng ký trước đó rồi!", "warning")
            return redirect(url_for('register'))
            
        # Mã hóa mật khẩu an toàn
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        # Lưu thông tin tài khoản vào database
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
        
        # Tìm tài khoản theo email
        user = User.query.filter_by(email=email).first()
        
        # Xác thực tài khoản và kiểm tra mật khẩu đã mã hóa
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username # Lưu lại tên hiển thị lên giao diện
            
            flash(f"Đăng nhập thành công! Chào mừng {user.username} quay trở lại.", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Email hoặc mật khẩu không đúng. Vui lòng kiểm tra lại!", "danger")
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear() # Xóa sạch trạng thái phiên đăng nhập
    flash("Bạn đã đăng xuất thành công.", "info")
    return redirect(url_for('index'))

document = Document.query.filter_by(user_id=session['user_id']).all()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)