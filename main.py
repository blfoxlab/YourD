import json
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
import os
import uuid
from datetime import datetime
from collections import OrderedDict

app = Flask(__name__)
app.secret_key = 'your_very_secret_key_that_should_be_changed'
app.config['UPLOAD_FOLDER'] = 'uploads'

# --- Utility Functions ---
def read_json(file_path):
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- Routes ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat')
def chat():
    if 'user' not in session:
        return redirect(url_for('login', next=request.path))
    return render_template('chat.html')

@app.route('/order')
def order():
    if 'user' not in session:
        flash('Будь ласка, увійдіть, щоб оформити замовлення.', 'error')
        return redirect(url_for('login'))
    return render_template('order.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        users = read_json('users.json')
        
        user = next((u for u in users if u['email'] == email), None)
        
        if user and check_password_hash(user['password_hash'], password):
            session['user'] = {'id': user['id'], 'name': user['name'], 'email': user['email']}
            if user.get('is_admin'):
                session['is_admin'] = True
            flash('Ви успішно увійшли!', 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('cabinet'))
        else:
            flash('Неправильний email або пароль.', 'error')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')

        if not all([name, email, phone, password]):
            flash('Будь ласка, заповніть усі поля.', 'error')
            return redirect(url_for('register'))

        users = read_json('users.json')
        if any(u['email'] == email for u in users):
            flash('Користувач з таким email вже існує.', 'error')
            return redirect(url_for('register'))

        new_user = {
            "id": str(uuid.uuid4()),
            "name": name,
            "email": email,
            "phone": phone,
            "password_hash": generate_password_hash(password),
            "is_admin": False
        }
        
        users.append(new_user)
        write_json('users.json', users)
        
        flash('Реєстрація успішна! Тепер ви можете увійти.', 'success')
        return redirect(url_for('login'))

    return render_template('login.html', is_register=True)

@app.route('/cabinet')
def cabinet():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = session['user']['id']
    
    all_orders = read_json('orders.json')
    my_orders = [order for order in all_orders if order.get('user_id') == user_id]
    
    all_messages = read_json('messages.json')
    # In a private chat model, a user's messages are where their ID is the user_id
    my_messages = [msg for msg in all_messages if msg.get('user_id') == user_id]

    return render_template('cabinet.html', my_orders=my_orders, my_messages=my_messages)

@app.route('/admin')
def admin():
    if 'user' not in session or not session.get('is_admin'):
        return "Access Denied", 403
    
    orders = read_json('orders.json')
    all_users = read_json('users.json')
    messages = read_json('messages.json')
    
    # Create a list of users who have sent messages
    chat_user_ids = set(msg['user_id'] for msg in messages)
    chat_partners = [user for user in all_users if user['id'] in chat_user_ids and not user.get('is_admin')]

    return render_template('admin.html', orders=orders, chat_partners=chat_partners)

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('is_admin', None)
    flash('Ви вийшли з акаунту.', 'success')
    return redirect(url_for('home'))

# --- API Endpoints ---

@app.route('/api/get_session')
def get_session():
    if 'user' in session:
        return jsonify({'user': session['user'], 'is_admin': session.get('is_admin', False)})
    return jsonify({'user': None})

@app.route('/api/get_messages')
def get_messages():
    if 'user' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    all_messages = read_json('messages.json')
    user_id_to_fetch = None

    # If admin requests a specific user's chat
    if session.get('is_admin'):
        user_id_to_fetch = request.args.get('user_id')

    # If it's a regular user, they can only fetch their own messages
    if not session.get('is_admin'):
        user_id_to_fetch = session['user']['id']

    if user_id_to_fetch:
        # A conversation consists of all messages associated with that user's ID
        conversation = [msg for msg in all_messages if msg.get('user_id') == user_id_to_fetch]
        return jsonify(conversation)

    # Admin default view (or if no user_id specified) - can be empty or a welcome message
    return jsonify([])

@app.route('/api/send_message', methods=['POST'])
def send_message():
    if 'user' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    data = request.get_json()
    if not data or 'text' not in data or not data['text'].strip():
        return jsonify({"status": "error", "message": "Message text is required"}), 400

    messages = read_json('messages.json')
    
    user_id_for_message = session['user']['id']
    
    # If admin is sending, they must specify which user's conversation this message belongs to
    if session.get('is_admin'):
        recipient_id = data.get('recipient_user_id')
        if not recipient_id:
            return jsonify({"status": "error", "message": "Recipient user ID is required for admin"}), 400
        user_id_for_message = recipient_id

    new_message = {
        "id": str(uuid.uuid4()),
        "user_id": user_id_for_message, # This links the message to a specific conversation thread
        "author_id": session['user']['id'], # The actual sender
        "author_name": session['user']['name'],
        "is_admin_sender": session.get('is_admin', False),
        "text": data['text'],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    messages.append(new_message)
    write_json('messages.json', messages)
    
    return jsonify({"status": "success", "message": new_message})

@app.route('/api/create_order', methods=['POST'])
def create_order():
    if 'user' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    data = request.get_json()
    if not data or not data.get('product_type'):
        return jsonify({"status": "error", "message": "Product type is required"}), 400

    orders = read_json('orders.json')
    
    new_order_id = str(uuid.uuid4())
    new_order = {
        "id": new_order_id,
        "user_id": session['user']['id'],
        "user_name": session['user']['name'],
        "product_type": data.get('product_type'),
        "quantity": data.get('quantity'),
        "comment": data.get('comment', ''),
        "file_upload": data.get('file_upload'), # In a real app, this would be a file path
        "status": "Нове",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    orders.append(new_order)
    write_json('orders.json', orders)

    # Add a system message to the chat
    messages = read_json('messages.json')
    system_message = {
        "id": str(uuid.uuid4()),
        "user_id": session['user']['id'],
        "author_name": "Система",
        "is_admin_sender": True,
        "author_id": "system",
        "text": f"Ваше замовлення #{new_order_id[:8]} на '{new_order['product_type']}' прийнято в обробку.",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    messages.append(system_message)
    write_json('messages.json', messages)

    return jsonify({"status": "success", "order_id": new_order_id})

@app.route('/api/update_order_status', methods=['POST'])
def update_order_status():
    if 'user' not in session or not session.get('is_admin'):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    data = request.get_json()
    order_id = data.get('order_id')
    new_status = data.get('status')

    if not all([order_id, new_status]):
        return jsonify({"status": "error", "message": "Order ID and status are required"}), 400

    orders = read_json('orders.json')
    order_found = False
    for order in orders:
        if order['id'] == order_id:
            order['status'] = new_status
            order_found = True
            break
    
    if order_found:
        write_json('orders.json', orders)
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Order not found"}), 404

# --- Initial Setup ---
def initial_setup():
    # Ensure all data files exist
    for f in ['users.json', 'orders.json', 'messages.json']:
        if not os.path.exists(f):
            write_json(f, [])
            
    # Create Admin User if it doesn't exist
    users = read_json('users.json')
    if not any(u.get('is_admin') for u in users):
        admin_user = {
            "id": "admin_user_001", # Fixed ID for simplicity
            "name": "Admin",
            "email": "admin@printmaster.com",
            "phone": "0000000000",
            "password_hash": generate_password_hash("admin"),
            "is_admin": True
        }
        users.append(admin_user)
        write_json('users.json', users)
        print("Admin user created with email: admin@printmaster.com, password: admin")

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    initial_setup()
    app.run(debug=True, port=5002)
