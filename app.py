from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate  # Aggiungi questa importazione
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime  # Aggiungi questa importazione

import cloudinary
import cloudinary.uploader
import cloudinary.api

# Configura Cloudinary
cloudinary.config(
    cloud_name="dwhqxqd6f",  # Sostituisci con il tuo Cloud Name
    api_key="442426661533797",        # Sostituisci con la tua API Key
    api_secret="dUGLN7iPxGo1Zq5A6JgRpKdnG-0"   # Sostituisci con la tua API Secret
)

# Configurazione dell'app Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'  # Database SQLite
app.config['SECRET_KEY'] = 'supersecretkey'  # Chiave segreta per le sessioni
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Cartella per salvare le immagini
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}  # Estensioni consentite per le immagini

# Inizializzazione di SQLAlchemy
db = SQLAlchemy(app)

# Inizializzazione di Flask-Migrate
migrate = Migrate(app, db)  # Assicurati che `app` e `db` siano già definiti

# Modello per gli utenti
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')  # Campo per il ruolo (admin/user)

# Modello per i post
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))  # URL dell'immagine su Cloudinary
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Aggiungi questa colonna

# Funzione per verificare le estensioni dei file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Route per la home page
@app.route('/')
def home():
    # Recupera tutti i post dal database, ordinati per ID (dal più recente)
    posts = Post.query.order_by(Post.id.desc()).all()
    return render_template('home.html', posts=posts)

# Route per il caricamento delle immagini su Cloudinary
@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'Nessun file fornito'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Nessun file selezionato'}), 400

    try:
        # Carica l'immagine su Cloudinary
        result = cloudinary.uploader.upload(file)
        return jsonify({'url': result['secure_url']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route per la registrazione
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Registrazione completata con successo!')
        return redirect(url_for('login'))
    return render_template('register.html')

# Route per il login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            session['user_role'] = user.role  # Memorizza il ruolo nella sessione
            flash('Login effettuato con successo!')
            return redirect(url_for('dashboard'))
        flash('Credenziali non valide')
    return render_template('login.html')

# Route per cancellare un post
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

# Route per modificare un post
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

# Route per il logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logout effettuato con successo!')
    return redirect(url_for('home'))

# Route per la dashboard (creazione di nuovi post)
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        flash('Per favore, accedi prima!')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image = request.files['image']

        # Gestisci il caricamento dell'immagine su Cloudinary
        image_url = None
        if image and allowed_file(image.filename):
            result = cloudinary.uploader.upload(image)
            image_url = result['secure_url']  # URL pubblico dell'immagine

        # Crea il post nel database
        post = Post(title=title, content=content, image_url=image_url)
        db.session.add(post)
        db.session.commit()
        flash('Post creato con successo!')
        return redirect(url_for('home'))

    return render_template('dashboard.html')

# Avvio dell'applicazione
if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists('blog.db'):
            db.create_all()  # Crea il database se non esiste
    app.run(debug=True)
