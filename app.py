import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mohannad_family_secure_2026'
app.config["MONGO_URI"] = "mongodb+srv://mohannad:family123@cluster0.arkrscx.mongodb.net/chat_db?retryWrites=true&w=majority"

mongo = PyMongo(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']

@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        return User(user_data) if user_data else None
    except: return None

# تحديث حالة الاتصال تلقائياً
@app.route('/update_presence')
@login_required
def update_presence():
    mongo.db.users.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": {"last_seen": datetime.utcnow()}}
    )
    return jsonify({"status": "ok"})

# جلب حالات الاتصال للجميع
@app.route('/get_statuses')
@login_required
def get_statuses():
    users = mongo.db.users.find({}, {"username": 1, "last_seen": 1})
    statuses = {}
    now = datetime.utcnow()
    for u in users:
        is_online = False
        if 'last_seen' in u:
            # إذا كان آخر نشاط خلال الـ 30 ثانية الماضية
            is_online = u['last_seen'] > (now - timedelta(seconds=30))
        statuses[u['username']] = "online" if is_online else "offline"
    return jsonify(statuses)

@app.route('/')
@login_required
def index():
    # عرض قائمة المستخدمين فقط (الشاشة الرئيسية)
    users = list(mongo.db.users.find({"username": {"$ne": current_user.username}}))
    return render_template('chat.html', users=users, chat_view="list")

@app.route('/chat/<type>/<target>')
@login_required
def chat_room(type, target):
    # عرض نافذة الدردشة لشخص معين أو العام
    users = list(mongo.db.users.find({"username": {"$ne": current_user.username}}))
    return render_template('chat.html', users=users, chat_view="room", chat_type=type, recipient=target)

@app.route('/get_messages/<chat_type>/<receiver>')
@login_required
def get_messages(chat_type, receiver):
    query = {"type": "public"} if chat_type == "public" else {
        "type": "private",
        "$or": [{"sender": current_user.username, "receiver": receiver}, 
                {"sender": receiver, "receiver": current_user.username}]
    }
    messages = list(mongo.db.messages.find(query).sort("timestamp", 1))
    output = []
    for msg in messages:
        output.append({
            "sender": msg['sender'],
            "content": msg.get('content', ''),
            "file_url": msg.get('file_url'),
            "file_type": msg.get('file_type'),
            "timestamp": msg['timestamp'].strftime('%I:%M %p') if 'timestamp' in msg else ""
        })
    return jsonify({"messages": output, "current_user": current_user.username})

@app.route('/send', methods=['POST'])
@login_required
def send():
    content = request.form.get('content', '')
    chat_type = request.form.get('chat_type', 'public')
    receiver = request.form.get('receiver', 'Group')
    file = request.files.get('file')
    
    file_url, file_type = None, None
    if file and file.filename != '':
        filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
        os.makedirs('static/uploads', exist_ok=True)
        file.save(os.path.join('static/uploads', filename))
        file_url = f"/static/uploads/{filename}"
        ext = filename.rsplit('.', 1)[1].lower()
        if ext in ['jpg', 'jpeg', 'png', 'gif']: file_type = 'image'
        elif ext in ['mp4', 'mov', 'avi']: file_type = 'video'
        else: file_type = 'audio'

    if content or file_url:
        mongo.db.messages.insert_one({
            "sender": current_user.username, "receiver": receiver,
            "content": content, "file_url": file_url, "file_type": file_type,
            "type": chat_type, "timestamp": datetime.utcnow()
        })
    return jsonify({"status": "sent"})

@app.route('/change_password', methods=['POST'])
@login_required
def change_pw():
    new_p = request.form.get('new_password')
    if new_p:
        mongo.db.users.update_one({"_id": ObjectId(current_user.id)}, {"$set": {"password": new_p}})
        return jsonify({"message": "تم التغيير بنجاح"})
    return jsonify({"message": "خطأ"}), 400

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = mongo.db.users.find_one({"username": request.form.get('username'), "password": request.form.get('password')})
        if user:
            login_user(User(user))
            return redirect(url_for('index'))
    return render_template('login.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
