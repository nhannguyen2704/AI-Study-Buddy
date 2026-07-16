from flask import Flask, render_template, request, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Cấu hình SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///studybuddy.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "key_bi_mat_cua_nhom"

db = SQLAlchemy(app)

# Model Document
class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    original_text = db.Column(db.Text, nullable=False)
    summary_text = db.Column(db.Text)
# Model Flashcard
class Flashcard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.String(500), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_doc', methods=['GET', 'POST'])
def upload_doc():
    if request.method == 'POST':
        flash("Tài liệu đã được tải lên thành công!", "success")
        uploaded_file = request.files.get('fileInput')
        original_text = uploaded_file.read().decode('utf-8')
        doc = Document(title="Bài học mới", original_text=original_text, summary_text="")
        db.session.add(doc)
        db.session.commit()
        if uploaded_file:
            van_ban_thuan_tuy = uploaded_file.read().decode('utf-8')
            print("Đã đọc thành công: ",van_ban_thuan_tuy[:100], "...")
            return "Tải tài liệu thành công"
    return render_template('upload.html')



if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)