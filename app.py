import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# 初始化 Flask App
app = Flask(__name__)

# --- 設定區 (Config) ---
# 設定密鑰 (用於 Session 和 Flash 訊息)，正式上線請改用複雜亂數
app.config['SECRET_KEY'] = 'your_secret_key_here'

# 設定資料庫連線 (這裡使用 SQLite 方便測試，如果要用 MySQL 請改連線字串)
# MySQL 範例: 'mysql+pymysql://帳號:密碼@localhost/MusicPlatform'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///music.db' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化擴充套件
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # 若未登入，導向到的頁面名稱

# --- 資料庫模型 (Models) ---
# 這裡對應我們設計的 ERD 和 SQL Schema

# 多對多關聯表 (Junction Tables)
song_artists = db.Table('song_artists',
    db.Column('song_id', db.Integer, db.ForeignKey('songs.song_id'), primary_key=True),
    db.Column('artist_id', db.Integer, db.ForeignKey('artists.artist_id'), primary_key=True),
    db.Column('role', db.String(20))
)

playlist_songs = db.Table('playlist_songs',
    db.Column('playlist_id', db.Integer, db.ForeignKey('playlists.playlist_id'), primary_key=True),
    db.Column('song_id', db.Integer, db.ForeignKey('songs.song_id'), primary_key=True),
    db.Column('track_order', db.Integer),
    db.Column('added_at', db.DateTime, default=datetime.utcnow)
)

user_liked_songs = db.Table('user_liked_songs',
    db.Column('user_id', db.Integer, db.ForeignKey('users.user_id'), primary_key=True),
    db.Column('song_id', db.Integer, db.ForeignKey('songs.song_id'), primary_key=True),
    db.Column('liked_at', db.DateTime, default=datetime.utcnow)
)

user_followed_artists = db.Table('user_followed_artists',
    db.Column('user_id', db.Integer, db.ForeignKey('users.user_id'), primary_key=True),
    db.Column('artist_id', db.Integer, db.ForeignKey('artists.artist_id'), primary_key=True),
    db.Column('followed_at', db.DateTime, default=datetime.utcnow)
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    display_name = db.Column(db.String(50))
    subscription_type = db.Column(db.String(10), default='Free')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 關聯
    playlists = db.relationship('Playlist', backref='owner', lazy=True)
    liked_songs = db.relationship('Song', secondary=user_liked_songs, backref='liked_by_users')
    followed_artists = db.relationship('Artist', secondary=user_followed_artists, backref='followers')

    # Flask-Login 需要的方法 (因為我們 PK 叫 user_id 不是 id)
    def get_id(self):
        return str(self.user_id)

class Artist(db.Model):
    __tablename__ = 'artists'
    artist_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    bio = db.Column(db.String(255))
    artist_image_url = db.Column(db.String(255))

    albums = db.relationship('Album', backref='artist', lazy=True)

class Album(db.Model):
    __tablename__ = 'albums'
    album_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    release_date = db.Column(db.Date)
    cover_art_url = db.Column(db.String(255))
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.artist_id'), nullable=False)

    songs = db.relationship('Song', backref='album', lazy=True)

class Song(db.Model):
    __tablename__ = 'songs'
    song_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    audio_file_url = db.Column(db.String(255))
    duration_minutes = db.Column(db.Integer)
    duration_seconds = db.Column(db.Integer)
    album_id = db.Column(db.Integer, db.ForeignKey('albums.album_id'), nullable=False)
    
    # 這裡簡化處理，若要完整功能可加上 upload_date 等

    artists = db.relationship('Artist', secondary=song_artists, backref='songs')

class Playlist(db.Model):
    __tablename__ = 'playlists'
    playlist_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)

    songs = db.relationship('Song', secondary=playlist_songs, backref='playlists')


# --- Flask-Login載入使用者 ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- 路由區 (Routes) ---

@app.route('/')
def index():
    # 首頁：顯示一些專輯或是歡迎訊息
    if current_user.is_authenticated:
        # 如果已登入，顯示個人的歌單或推薦
        recent_albums = Album.query.limit(5).all()
        return render_template('index.html', albums=recent_albums) # 需自行建立 index.html
    else:
        # 未登入，導向登入頁 (或是顯示 Landing Page)
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # 查詢使用者
        user = User.query.filter_by(email=email).first()

        # 驗證密碼
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('登入成功！', 'success')
            return redirect(url_for('index'))
        else:
            flash('登入失敗，請檢查信箱或密碼。', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已登出。', 'info')
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        display_name = request.form.get('display_name')

        # 檢查 Email 是否重複
        if User.query.filter_by(email=email).first():
            flash('此 Email 已經註冊過了。', 'warning')
            return redirect(url_for('register'))

        # 建立新使用者
        hashed_password = generate_password_hash(password)
        new_user = User(email=email, password_hash=hashed_password, display_name=display_name)
        
        db.session.add(new_user)
        db.session.commit()

        flash('註冊成功！請登入。', 'success')
        return redirect(url_for('login'))

    return render_template('register.html') # 需自行建立 register.html

# --- 啟動程式 ---
if __name__ == '__main__':
    # 建立資料庫表格 (第一次執行時需要)
    with app.app_context():
        db.create_all()
        print("資料庫與表格已建立/檢查完成。")
        
    app.run(debug=True)