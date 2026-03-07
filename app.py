import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mohannad_ultimate_2026'
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

# تحديث النشاط وحالة الاتصال
@app.route('/update_presence')
@login_required
def update_presence():
    mongo.db.users.update_one({"_id": ObjectId(current_user.id)}, {"$set": {"last_seen": datetime.utcnow()}})
    return jsonify({"status": "ok"})

# جلب تحديثات النظام (الحالات والرسائل الجديدة)
@app.route('/get_system_update')
@login_required
def get_system_update():
    users = mongo.db.users.find({}, {"username": 1, "last_seen": 1})
    now = datetime.utcnow()
    res = {"statuses": {}, "unread": {}}
    for u in users:
        is_online = u.get('last_seen') > (now - timedelta(seconds=30)) if u.get('last_seen') else False
        res["statuses"][u['username']] = "online" if is_online else "offline"
        unread_count = mongo.db.messages.count_documents({"sender": u['username'], "receiver": current_user.username, "read": False})
        res["unread"][u['username']] = unread_count
    return jsonify(res)

@app.route('/')
@login_required
def index():
    all_users = list(mongo.db.users.find({"username": {"$ne": current_user.username}}))
    for u in all_users:
        last_msg = mongo.db.messages.find_one({"$or": [{"sender": current_user.username, "receiver": u['username']}, {"sender": u['username'], "receiver": current_user.username}]}, sort=[("timestamp", -1)])
        u['last_ts'] = last_msg['timestamp'] if last_msg else datetime.min
    all_users.sort(key=lambda x: x['last_ts'], reverse=True)
    return render_template('chat.html', users=all_users, chat_view="list")

@app.route('/chat/<type>/<target>')
@login_required
def chat_room(type, target):
    # بمجرد دخول الغرفة، نحدد رسائل الطرف الآخر كـ "مقروءة"
    if type == "private":
        mongo.db.messages.update_many({"sender": target, "receiver": current_user.username, "read": False}, {"$set": {"read": True}})
    return render_template('chat.html', chat_view="room", chat_type=type, recipient=target)

@app.route('/get_messages/<chat_type>/<receiver>')
@login_required
def get_messages(chat_type, receiver):
    # تحديث مستمر للقراءة أثناء التواجد داخل المحادثة
    if chat_type == "private":
        mongo.db.messages.update_many({"sender": receiver, "receiver": current_user.username, "read": False}, {"$set": {"read": True}})
    
    query = {"type": "public"} if chat_type == "public" else {"type": "private", "$or": [{"sender": current_user.username, "receiver": receiver}, {"sender": receiver, "receiver": current_user.username}]}
    messages = list(mongo.db.messages.find(query).sort("timestamp", 1))
    output = []
    for m in messages:
        output.append({
            "id": str(m['_id']), "sender": m['sender'], "content": m.get('content', ''),
            "file_url": m.get('file_url'), "file_type": m.get('file_type'),
            "timestamp": m['timestamp'].strftime('%I:%M %p'), "read": m.get('read', False)
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
        file_type = 'image' if ext in ['jpg','jpeg','png','gif'] else 'video' if ext in ['mp4','mov'] else 'audio'
    
    mongo.db.messages.insert_one({
        "sender": current_user.username, "receiver": receiver, "content": content,
        "file_url": file_url, "file_type": file_type, "type": chat_type, 
        "timestamp": datetime.utcnow(), "read": False
    })
    return jsonify({"status": "sent"})

@app.route('/delete_msg/<id>', methods=['POST'])
@login_required
def delete_msg(id):
    mongo.db.messages.delete_one({"_id": ObjectId(id), "sender": current_user.username})
    return jsonify({"status": "ok"})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = mongo.db.users.find_one({"username": request.form.get('username'), "password": request.form.get('password')})
        if user: login_user(User(user)); return redirect(url_for('index'))
    return render_template('login.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
