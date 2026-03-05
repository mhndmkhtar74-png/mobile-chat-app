import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mohannad_final_2026'
app.config["MONGO_URI"] = "mongodb+srv://mohannad:family123@cluster0.arkrscx.mongodb.net/chat_db?retryWrites=true&w=majority&appName=Cluster0"

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

@app.route('/')
@login_required
def index():
    users = list(mongo.db.users.find({"username": {"$ne": current_user.username}}))
    return render_template('chat.html', users=users, chat_type="public")

@app.route('/private/<recipient>')
@login_required
def private_chat(recipient):
    users = list(mongo.db.users.find({"username": {"$ne": current_user.username}}))
    return render_template('chat.html', users=users, chat_type="private", recipient=recipient)

# جلب الرسائل بصيغة JSON للتحديث الصامت
@app.route('/get_messages/<chat_type>/<receiver>')
@login_required
def get_messages(chat_type, receiver):
    query = {"type": "public"} if chat_type == "public" else {
        "type": "private",
        "$or": [{"sender": current_user.username, "receiver": receiver}, 
                {"sender": receiver, "receiver": current_user.username}]
    }
    messages = list(mongo.db.messages.find(query).sort("timestamp", 1))
    
    # تجهيز الرسائل للإرسال للمتصفح
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
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        file_url = f"/static/uploads/{filename}"
        ext = filename.rsplit('.', 1)[1].lower()
        if ext in ['jpg', 'jpeg', 'png', 'gif']: file_type = 'image'
        elif ext in ['mp4', 'mov', 'avi']: file_type = 'video'
        else: file_type = 'audio'

    if content or file_url:
        mongo.db.messages.insert_one({
            "sender": current_user.username,
            "receiver": receiver,
            "content": content,
            "file_url": file_url,
            "file_type": file_type,
            "type": chat_type,
            "timestamp": datetime.utcnow()
        })
    return redirect(url_for('private_chat', recipient=receiver) if chat_type == "private" else url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_data = mongo.db.users.find_one({"username": request.form.get('username'), "password": request.form.get('password')})
        if user_data:
            login_user(User(user_data))
            return redirect(url_for('index'))
    return render_template('login.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
