import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecretkey123' # يمكنك تغييره لاحقاً

# إعداد قاعدة البيانات لتناسب Koyeb
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'chat.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- جداول قاعدة البيانات ---

# جدول المستخدمين
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)

# جدول الرسائل (نصوص وروابط الوسائط)
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(50), nullable=False)
    receiver = db.Column(db.String(50), nullable=False) # 'Group' أو اسم مستخدم للخاص
    content = db.Column(db.Text, nullable=False)
    msg_type = db.Column(db.String(20), default='text') # text, image, voice, video
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- المسارات (Routes) ---

# الصفحة الرئيسية (واجهة الشات)
@app.route('/')
@login_required
def index():
    # جلب رسائل المجموعة
    group_messages = Message.query.filter_by(receiver='Group').order_by(Message.timestamp.asc()).all()
    return render_template('chat.html', messages=group_messages)

# صفحة تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('index'))
        else:
            return "خطأ في اسم المستخدم أو كلمة المرور"
    return render_template('login.html')

# مسار خاص بك لإضافة المستخدمين العشرة يدوياً من المتصفح
# الرابط سيكون: your-app.koyeb.app/add_user/name/password
@app.route('/add_user/<name>/<pwd>')
def add_user(name, pwd):
    # التأكد من عدم تكرار المستخدم
    exists = User.query.filter_by(username=name).first()
    if not exists:
        new_user = User(username=name, password=pwd)
        db.session.add(new_user)
        db.session.commit()
        return f"تمت إضافة المستخدم {name} بنجاح!"
    return "المستخدم موجود مسبقاً"

# مسار إرسال الرسائل (نصية حالياً)
@app.route('/send', methods=['POST'])
@login_required
def send():
    content = request.form.get('content')
    receiver = request.form.get('receiver', 'Group')
    if content:
        msg = Message(sender=current_user.username, receiver=receiver, content=content)
        db.session.add(msg)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# إنشاء الجداول عند تشغيل التطبيق لأول مرة
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
