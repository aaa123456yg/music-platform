import os
from werkzeug.utils import secure_filename
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
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost:3306/MusicPlatform' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# 設定上傳存檔路徑
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'music')
app.config['COVER_FOLDER'] = os.path.join(app.static_folder, 'covers')
app.config['ARTIST_FOLDER'] = os.path.join(app.static_folder, 'artists') # ★ 新增這行
app.config['ALLOWED_EXTENSIONS'] = {'mp3', 'wav', 'ogg', 'png', 'jpg', 'jpeg'}

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

class Employees(db.Model):
    __tablename__ = 'employees'
    eId = db.Column(db.String(10), primary_key=True)
    e_name = db.Column(db.String(20), nullable=False)
    e_password = db.Column(db.String(20), nullable=False)

class Song(db.Model):
    __tablename__ = 'songs'
    song_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    audio_file_url = db.Column(db.String(255))
    duration_minutes = db.Column(db.Integer)
    duration_seconds = db.Column(db.Integer)
    album_id = db.Column(db.Integer, db.ForeignKey('albums.album_id'), nullable=False)
    
    # ★★★ 補上這兩行 ★★★
    eId = db.Column(db.String(10), db.ForeignKey('employees.eId'))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    # ★★★★★★★★★★★★★★★

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
    if current_user.is_authenticated:
        # ★★★ 修改這裡：從資料庫撈出真實專輯 ★★★
        # 這裡示範撈出最新的 6 張專輯 (依 album_id 倒序排列)
        recent_albums = Album.query.order_by(Album.album_id.desc()).limit(6).all()
        
        # 也可以順便撈出隨機推薦的演出者 (選用)
        # import random
        # all_artists = Artist.query.all()
        # recommended_artists = random.sample(all_artists, min(len(all_artists), 5))

        return render_template('index.html', albums=recent_albums) 
    else:
        return redirect(url_for('login'))

# app.py 新增搜尋路由

@app.route('/search')
@login_required
def search():
    q = request.args.get('q', '') # 取得網址上的 ?q=關鍵字
    
    if not q:
        return redirect(url_for('index'))

    # 使用 ilike 進行模糊搜尋 (不分大小寫)
    # 搜尋 歌曲、專輯、演出者
    songs = Song.query.filter(Song.title.ilike(f'%{q}%')).all()
    albums = Album.query.filter(Album.title.ilike(f'%{q}%')).all()
    artists = Artist.query.filter(Artist.name.ilike(f'%{q}%')).all()

    return render_template('search_results.html', q=q, songs=songs, albums=albums, artists=artists)

# app.py 新增專輯詳情頁路由

@app.route('/album/<int:album_id>')
@login_required
def album_detail(album_id):
    # get_or_404 會自動處理「找不到專輯」的情況，顯示 404 錯誤頁
    album = Album.query.get_or_404(album_id)
    
    # 計算總時長 (分鐘) - 這是個貼心的小功能
    total_seconds = sum(s.duration_minutes * 60 + s.duration_seconds for s in album.songs)
    total_duration = f"{total_seconds // 60} 分 {total_seconds % 60} 秒"

    return render_template('album_detail.html', album=album, total_duration=total_duration)

# app.py
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    # 初始化變數
    error = False
    email_value = ''

    if request.method == 'POST':
        email_value = request.form.get('email', '')
        password = request.form.get('password')

        user = User.query.filter_by(email=email_value).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            # 登入失敗：設定錯誤旗標
            error = True
            flash('用戶名稱或密碼不正確。', 'danger')

    # 將 error 和 email_value 傳給前端
    return render_template('login.html', error=error, email_value=email_value)


# 確認 app.py 有這一段
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已登出。', 'info') # 登出後會回到登入頁顯示這行
    return redirect(url_for('login'))


# app.py 的 register 路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        display_name = request.form.get('display_name')

        if User.query.filter_by(email=email).first():
            flash('此 Email 已經註冊過了。', 'warning')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(email=email, password_hash=hashed_password, display_name=display_name)
        
        db.session.add(new_user)
        db.session.commit()

        # ★★★ 修改這裡 ★★★
        # 1. 確保訊息類別是 'success' (對應綠色框)
        flash('註冊成功！你可以直接登入或繼續註冊其他帳號。', 'success')
        
        # 2. 關鍵：把 'login' 改成 'register'
        # 這樣才會重新載入註冊頁面，並顯示上方的成功訊息
        return redirect(url_for('register')) 

    return render_template('register.html')
# --- 後台管理系統路由 ---

# 1. 後台登入
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        eid = request.form.get('eid')
        password = request.form.get('password')
        
        # 查詢員工表 (因為是後台，這裡直接明文比對示範，實際專案建議也要加密)
        employee = Employees.query.filter_by(eId=eid).first()
        
        if employee and employee.e_password == password:
            # 使用 Session 記住管理員登入狀態 (與一般 User 分開)
            from flask import session
            session['admin_id'] = employee.eId
            return redirect(url_for('admin_dashboard'))
        else:
            flash('管理員帳號或密碼錯誤', 'danger')
            
    return render_template('admin_login.html')

# 2. 後台儀表板 (上架頁面)
@app.route('/admin/dashboard')
def admin_dashboard():
    from flask import session
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    # 撈出所有演出者與專輯，供下拉選單使用
    artists = Artist.query.all()
    albums = Album.query.all()
    
    return render_template('admin.html', artists=artists, albums=albums)

# 3. 新增演出者功能
# app.py 更新版 add_artist 路由

@app.route('/admin/add_artist', methods=['POST'])
def add_artist():
    name = request.form.get('name')
    bio = request.form.get('bio')
    
    # 處理演出者照片上傳
    image_path = None # 預設為空 (如果沒上傳就留空)
    
    if 'artist_file' in request.files:
        file = request.files['artist_file']
        if file.filename != '':
            filename = secure_filename(file.filename)
            # 存到 static/artists/ 資料夾
            file.save(os.path.join(app.config['ARTIST_FOLDER'], filename))
            # 記錄路徑
            image_path = f'/static/artists/{filename}'
    
    # 寫入資料庫 (加入 artist_image_url)
    new_artist = Artist(name=name, bio=bio, artist_image_url=image_path)
    db.session.add(new_artist)
    db.session.commit()
    
    flash(f'演出者 {name} 新增成功！', 'success')
    return redirect(url_for('admin_dashboard'))

# app.py 更新版 add_album 路由

@app.route('/admin/add_album', methods=['POST'])
def add_album():
    title = request.form.get('title')
    artist_id = request.form.get('artist_id')
    release_date_str = request.form.get('release_date')
    
    # 1. 處理日期
    release_date = datetime.strptime(release_date_str, '%Y-%m-%d').date() if release_date_str else None
    
    # 2. 處理封面圖片上傳
    cover_path = None # 預設為空
    
    if 'cover_file' in request.files:
        file = request.files['cover_file']
        if file.filename != '':
            filename = secure_filename(file.filename)
            # 存到 static/covers/ 資料夾
            file.save(os.path.join(app.config['COVER_FOLDER'], filename))
            # 記錄路徑供前端使用
            cover_path = f'/static/covers/{filename}'

    # 3. 寫入資料庫 (加入 cover_art_url)
    new_album = Album(
        title=title, 
        artist_id=artist_id, 
        release_date=release_date,
        cover_art_url=cover_path  # ★★★ 這裡存入路徑 ★★★
    )
    db.session.add(new_album)
    db.session.commit()
    
    flash(f'專輯 {title} 新增成功！', 'success')
    return redirect(url_for('admin_dashboard'))

# 5. 上架歌曲功能 (最重要！)
@app.route('/admin/add_song', methods=['POST'])
def add_song():
    from flask import session
    title = request.form.get('title')
    album_id = request.form.get('album_id')
    duration_m = request.form.get('duration_minutes')
    duration_s = request.form.get('duration_seconds')
    
    # 處理檔案上傳
    if 'audio_file' not in request.files:
        flash('沒有上傳檔案', 'danger')
        return redirect(url_for('admin_dashboard'))
        
    file = request.files['audio_file']
    
    if file.filename == '':
        flash('未選擇檔案', 'danger')
        return redirect(url_for('admin_dashboard'))

    if file:
        filename = secure_filename(file.filename)
        # 存檔到 static/music/
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        # 資料庫存的路徑 (給前端 <audio src="..."> 用的)
        db_path = f'/static/music/{filename}'
        
        # 寫入資料庫
        new_song = Song(
            title=title,
            album_id=album_id,
            duration_minutes=duration_m,
            duration_seconds=duration_s,
            audio_file_url=db_path,
            eId=session['admin_id'], # 記錄是誰上架的
            upload_date=datetime.utcnow()
        )
        db.session.add(new_song)
        db.session.commit()
        
        flash(f'歌曲 {title} 上架成功！', 'success')

    return redirect(url_for('admin_dashboard'))

# 6. 後台登出
@app.route('/admin/logout')
def admin_logout():
    from flask import session
    session.pop('admin_id', None)
    return redirect(url_for('admin_login'))
# --- 啟動程式 ---
if __name__ == '__main__':
    # 建立資料庫表格 (第一次執行時需要)
    with app.app_context():
        db.create_all()
        print("資料庫與表格已建立/檢查完成。")
        
    app.run(debug=True)