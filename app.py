from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime

import cloudinary
import cloudinary.uploader
import cloudinary.api

cloudinary.config(
    cloud_name="dwhqxqd6f",
    api_key="442426661533797",
    api_secret="dUGLN7iPxGo1Zq5A6JgRpKdnG-0"
)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///blog.db')  # Usa PostgreSQL su Render
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def home():
    posts = Post.query.order_by(Post.id.desc()).all()
    return render_template('home.html', posts=posts)

@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'Nessun file fornito'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Nessun file selezionato'}), 400

    try:
        result = cloudinary.uploader.upload(file)
        return jsonify({'url': result['secure_url']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        flash('Accesso negato. Solo l\'admin può registrare nuovi utenti.')
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        role = request.form.get('role', 'user')
        user = User(username=username, password=password, role=role)
        db.session.add(user)
        db.session.commit()
        flash('Utente registrato con successo!')
        return redirect(url_for('home'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.role == 'admin' and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_role'] = user.role
            flash('Login effettuato con successo!')
            return redirect(url_for('dashboard'))
        else:
            flash('Accesso negato. Solo l\'admin può accedere.')
    return render_template('login.html')

@app.route('/delete/<int:post_id>')
def delete_post(post_id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        flash('Accesso negato. Solo l\'admin può cancellare i post.')
        return redirect(url_for('home'))

    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Post cancellato con successo!')
    return redirect(url_for('home'))

@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        flash('Accesso negato. Solo l\'admin può modificare i post.')
        return redirect(url_for('home'))

    post = Post.query.get_or_404(post_id)
    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']
        db.session.commit()
        flash('Post modificato con successo!')
        return redirect(url_for('home'))

    return render_template('edit_post.html', post=post)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logout effettuato con successo!')
    return redirect(url_for('home'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        flash('Per favore, accedi prima!')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image = request.files['image']

        image_url = None
        if image and allowed_file(image.filename):
            result = cloudinary.uploader.upload(image)
            image_url = result['secure_url']

        post = Post(title=title, content=content, image_url=image_url)
        db.session.add(post)
        db.session.commit()
        flash('Post creato con successo!')
        return redirect(url_for('home'))

    return render_template('dashboard.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Crea le tabelle se non esistono
    app.run(debug=True)