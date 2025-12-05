import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import or_
from sqlalchemy.sql.expression import func
# 初始化 Flask App
app = Flask(__name__)

# --- 設定區 (Config) ---
# 設定密鑰 (用於 Session 和 Flash 訊息)，正式上線請改用複雜亂數
app.config['SECRET_KEY'] = 'your_secret_key_here'

# 嘗試從環境變數取得資料庫網址 (Render 會自動提供 DATABASE_URL)
database_url = os.environ.get('DATABASE_URL')

# Render 的網址可能是 postgres:// 開頭，但 SQLAlchemy 需要 postgresql://，所以要修正
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# 如果有抓到雲端網址就用雲端的，否則用你本機的連線字串 (請確認這裡填的是你本機正確的 PostgreSQL 帳密)
#app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'postgresql://postgres:admin123@localhost:5432/MusicPlatform'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:admin123@localhost:5432/MusicPlatform'
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
user_liked_albums = db.Table('user_liked_albums',
    db.Column('user_id', db.Integer, db.ForeignKey('users.user_id'), primary_key=True),
    db.Column('album_id', db.Integer, db.ForeignKey('albums.album_id'), primary_key=True),
    db.Column('liked_at', db.DateTime, default=datetime.utcnow)
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
    liked_albums = db.relationship('Album', secondary=user_liked_albums, backref='liked_by_users')

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
    eid = db.Column(db.String(10), primary_key=True)
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
    eid = db.Column(db.String(10), db.ForeignKey('employees.eid'))
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
        random_artists = Artist.query.order_by(func.random()).limit(6).all()
        if request.headers.get('HX-Request'):
            # 記得把 artists 傳進去
            return render_template('content_area.html', albums=recent_albums, artists=random_artists)
        # 也可以順便撈出隨機推薦的演出者 (選用)
        # import random
        # all_artists = Artist.query.all()
        # recommended_artists = random.sample(all_artists, min(len(all_artists), 5))

        return render_template('index.html', albums=recent_albums, artists=random_artists) 
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
    # 4. ★★★ 新增：搜尋播放清單 (公開的 OR 我自己的) ★★★
    playlists = Playlist.query.filter(
        Playlist.name.ilike(f'%{q}%'),
        or_(Playlist.is_public == True, Playlist.user_id == current_user.user_id)
    ).all()

    return render_template('search_results.html', q=q, songs=songs, albums=albums, artists=artists, playlists=playlists)

@app.route('/toggle_like/<int:song_id>', methods=['POST'])
@login_required
def toggle_like(song_id):
    song = Song.query.get_or_404(song_id)
    
    # 判斷邏輯：如果已經收藏就移除，沒收藏就加入
    if song in current_user.liked_songs:
        current_user.liked_songs.remove(song)
        is_liked = False
    else:
        current_user.liked_songs.append(song)
        is_liked = True
        
    db.session.commit()
    
    # 回傳新的 HTML 片段給 HTMX 替換
    # 這樣前端不用刷新頁面，愛心就會自動變色
    if is_liked:
        # 狀態：已收藏 (實心綠色愛心)
        return f'''
            <i class="fa-solid fa-heart like-btn" 
               style="color: #1ed760; cursor: pointer;" 
               hx-post="/toggle_like/{song.song_id}" 
               hx-swap="outerHTML">
            </i>
        '''
    else:
        # 狀態：未收藏 (空心愛心)
        return f'''
            <i class="fa-regular fa-heart like-btn" 
               style="cursor: pointer;" 
               hx-post="/toggle_like/{song.song_id}" 
               hx-swap="outerHTML">
            </i>
        '''


# app.py - 收藏/取消收藏專輯

@app.route('/toggle_album_like/<int:album_id>', methods=['POST'])
@login_required
def toggle_album_like(album_id):
    album = Album.query.get_or_404(album_id)
    
    # 判斷邏輯
    if album in current_user.liked_albums:
        current_user.liked_albums.remove(album)
        is_liked = False
    else:
        current_user.liked_albums.append(album)
        is_liked = True
        
    db.session.commit()
    
    # 回傳按鈕 HTML (跟歌曲愛心一樣，只是大一點)
    if is_liked:
        return f'''
            <button class="action-icon" 
                    title="取消收藏"
                    style="color: #1ed760;"
                    hx-post="/toggle_album_like/{album.album_id}" 
                    hx-swap="outerHTML">
                <i class="fa-solid fa-heart"></i>
            </button>
        '''
    else:
        return f'''
            <button class="action-icon" 
                    title="收藏專輯"
                    hx-post="/toggle_album_like/{album.album_id}" 
                    hx-swap="outerHTML">
                <i class="fa-regular fa-heart"></i>
            </button>
        '''

# app.py - 追蹤/取消追蹤演出者

@app.route('/toggle_follow/<int:artist_id>', methods=['POST'])
@login_required
def toggle_follow(artist_id):
    artist = Artist.query.get_or_404(artist_id)
    
    # 判斷邏輯：已追蹤就取消，沒追蹤就加入
    if artist in current_user.followed_artists:
        current_user.followed_artists.remove(artist)
        is_following = False
    else:
        current_user.followed_artists.append(artist)
        is_following = True
        
    db.session.commit()
    
    # 回傳按鈕 HTML 給 HTMX 替換
    if is_following:
        # 狀態：正在追蹤 (顯示為實心或亮色邊框，文字變更)
        return f'''
            <button class="follow-btn following" 
                    hx-post="/toggle_follow/{artist.artist_id}" 
                    hx-swap="outerHTML">
                正在追蹤
            </button>
        '''
    else:
        # 狀態：未追蹤 (原本的空心樣式)
        return f'''
            <button class="follow-btn" 
                    hx-post="/toggle_follow/{artist.artist_id}" 
                    hx-swap="outerHTML">
                追蹤
            </button>
        '''

# app.py

@app.route('/collection/tracks')
@login_required
def liked_songs():
    # ★★★ 修改查詢：同時抓取 Song 物件和 user_liked_songs 表裡的 liked_at 時間 ★★★
    # 這會回傳一個列表，裡面每一項都是 (Song, datetime) 的 Tuple
    results = db.session.query(Song, user_liked_songs.c.liked_at)\
        .join(user_liked_songs)\
        .filter(user_liked_songs.c.user_id == current_user.user_id)\
        .order_by(user_liked_songs.c.liked_at.desc())\
        .all()
    
    song_count = len(results)
    
    # HTMX 請求
    if request.headers.get('HX-Request'):
        return render_template('liked_content.html', songs=results, song_count=song_count)
    
    # 一般請求
    return render_template('liked_songs.html', songs=results, song_count=song_count)

# app.py 新增專輯詳情頁路由

@app.route('/album/<int:album_id>')
@login_required
def album_detail(album_id):
    album = Album.query.get_or_404(album_id)
    total_seconds = sum(s.duration_minutes * 60 + s.duration_seconds for s in album.songs)
    total_duration = f"{total_seconds // 60} 分 {total_seconds % 60} 秒"

    # ★★★ 加入這段：如果是 HTMX 請求，只回傳局部內容 ★★★
    if request.headers.get('HX-Request'):
        return render_template('album_content.html', album=album, total_duration=total_duration)

    # 否則回傳完整頁面
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

@app.context_processor
def inject_playlists():
    if current_user.is_authenticated:
        # 撈出使用者建立的所有清單 (依建立時間排序)
        my_playlists = Playlist.query.filter_by(user_id=current_user.user_id).order_by(Playlist.created_at.desc()).all()
        return dict(my_playlists=my_playlists)
    return dict(my_playlists=[])

# ★★★ 2. 建立播放清單路由 ★★★
@app.route('/create_playlist', methods=['POST'])
@login_required
def create_playlist():
    # 1. 檢查 Free 會員限制
    if current_user.subscription_type == 'Free':
        user_playlist_count = Playlist.query.filter_by(user_id=current_user.user_id).count()
        
        if user_playlist_count >= 3:
            # ★★★ 修正這裡：不要只回傳 script，要回傳完整的清單模板 ★★★
            
            # (A) 重新撈取原本的清單 (確保側邊欄有東西顯示)
            current_playlists = Playlist.query.filter_by(user_id=current_user.user_id).order_by(Playlist.created_at.desc()).all()
            
            # (B) 回傳模板，並多傳一個 error_message
            return render_template('actions/create_playlist_response.html', 
                                   my_playlists=current_playlists,
                                   error_message='免費會員最多只能建立 3 個播放清單，請升級 Premium 解鎖無限建立！')

    # --- 以下是原本的新增邏輯 (保持不變) ---
    name = request.form.get('name')
    description = request.form.get('description')
    is_public = True if request.form.get('is_public') == 'on' else False
    
    if name:
        new_playlist = Playlist(
            name=name,
            description=description,
            is_public=is_public,
            user_id=current_user.user_id
        )
        db.session.add(new_playlist)
        db.session.commit()
        
        # 成功建立後，正常回傳更新的列表
        updated_playlists = Playlist.query.filter_by(user_id=current_user.user_id).order_by(Playlist.created_at.desc()).all()
        return render_template('actions/create_playlist_response.html', my_playlists=updated_playlists)
        
    return '', 204

# app.py - 加入歌曲到播放清單

# app.py

@app.route('/add_to_playlist/<int:playlist_id>/<int:song_id>', methods=['POST'])
@login_required
def add_to_playlist(playlist_id, song_id):
    playlist = Playlist.query.filter_by(playlist_id=playlist_id, user_id=current_user.user_id).first()
    song = Song.query.get_or_404(song_id)
    
    if not playlist:
        return jsonify({'error': 'Permission denied'}), 403

    added = False
    # 檢查是否重複
    if song not in playlist.songs:
        playlist.songs.append(song)
        db.session.commit()
        added = True
    
    # ★★★ 修改：簡化回傳內容，只需回傳是否加入成功 ★★★
    # 前端 JS 只需要知道 'added' 是 True 還是 False 來決定要不要跳 Alert
    return jsonify({
        'added': added
    })
# app.py

# app.py - 播放清單詳情頁

@app.route('/playlist/<int:playlist_id>')
@login_required
def playlist_detail(playlist_id):
    # 1. 取得清單，若找不到則 404
    playlist = Playlist.query.get_or_404(playlist_id)
    
    # 2. 權限檢查：如果是私人清單且不是自己的，就禁止訪問
    if not playlist.is_public and playlist.user_id != current_user.user_id:
        flash('您沒有權限查看此清單', 'danger')
        return redirect(url_for('index'))

    # 3. 取得歌曲列表
    songs = playlist.songs
    song_count = len(songs)
    
    # 計算總時長
    total_seconds = sum(s.duration_minutes * 60 + s.duration_seconds for s in songs)
    total_duration = f"{total_seconds // 60} 分 {total_seconds % 60} 秒"

    # 4. HTMX 判斷
    if request.headers.get('HX-Request'):
        return render_template('playlist_content.html', playlist=playlist, songs=songs, song_count=song_count, total_duration=total_duration)
    
    return render_template('playlist_detail.html', playlist=playlist, songs=songs, song_count=song_count, total_duration=total_duration)

# app.py

# 1. 移除清單內的歌曲
@app.route('/playlist/<int:playlist_id>/remove_song/<int:song_id>', methods=['DELETE'])
@login_required
def remove_song_from_playlist(playlist_id, song_id):
    playlist = Playlist.query.filter_by(playlist_id=playlist_id, user_id=current_user.user_id).first()
    song = Song.query.get_or_404(song_id)
    
    if not playlist:
        return "Permission Denied", 403
        
    if song in playlist.songs:
        playlist.songs.remove(song)
        db.session.commit()
    
    # ★★★ 修改：直接回傳空字串 ★★★
    # 因為你的 playlist_content.html 裡的刪除按鈕是用 hx-target="closest tr"
    # 回傳空字串 = 把那一整行 tr 內容清空 = 視覺上的刪除
    return ''

# 2. 刪除整個播放清單
@app.route('/delete_playlist/<int:playlist_id>', methods=['DELETE'])
@login_required
def delete_playlist(playlist_id):
    playlist = Playlist.query.filter_by(playlist_id=playlist_id, user_id=current_user.user_id).first()
    
    if not playlist:
        return "無權限", 403
        
    db.session.delete(playlist)
    db.session.commit()
    
    # 1. 重新撈取最新的清單
    updated_playlists = Playlist.query.filter_by(user_id=current_user.user_id).order_by(Playlist.created_at.desc()).all()
    
    # 2. 回傳模板，並多傳一個 deleted_id (轉成字串傳比較保險)
    return render_template('actions/create_playlist_response.html', 
                           my_playlists=updated_playlists, 
                           deleted_id=playlist_id)

# app.py - 你的資料庫頁面

@app.route('/library')
@login_required
def library():
    # 1. 撈取所有相關資料
    my_playlists = Playlist.query.filter_by(user_id=current_user.user_id).order_by(Playlist.created_at.desc()).all()
    liked_albums = current_user.liked_albums
    followed_artists = current_user.followed_artists
    liked_songs_count = len(current_user.liked_songs)
    
    # 2. HTMX 請求：回傳局部內容
    if request.headers.get('HX-Request'):
        return render_template('library_content.html', 
                               playlists=my_playlists, 
                               albums=liked_albums, 
                               artists=followed_artists,
                               liked_songs_count=liked_songs_count)
    
    # 3. 一般請求：回傳完整頁面
    return render_template('library.html', 
                           playlists=my_playlists, 
                           albums=liked_albums, 
                           artists=followed_artists,
                           liked_songs_count=liked_songs_count)

# 1. 後台登入
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        eid = request.form.get('eid')
        password = request.form.get('password')
        
        # 查詢員工表 (因為是後台，這裡直接明文比對示範，實際專案建議也要加密)
        employee = Employees.query.filter_by(eid=eid).first()
        
        if employee and employee.e_password == password:
            # 使用 Session 記住管理員登入狀態 (與一般 User 分開)
            from flask import session
            session['admin_id'] = employee.eid
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

# app.py

@app.route('/admin/add_single', methods=['POST'])
def add_single():
    from flask import session
    title = request.form.get('title')
    artist_id = request.form.get('artist_id')
    duration_m = request.form.get('duration_minutes')
    duration_s = request.form.get('duration_seconds')
    
    # 1. 檢查檔案
    if 'audio_file' not in request.files or 'cover_file' not in request.files:
        flash('請上傳音檔和封面', 'danger')
        return redirect(url_for('admin_dashboard'))
        
    audio = request.files['audio_file']
    cover = request.files['cover_file']
    
    if audio.filename == '' or cover.filename == '':
        flash('檔案未選擇', 'danger')
        return redirect(url_for('admin_dashboard'))

    # 2. 存檔
    audio_filename = secure_filename(audio.filename)
    cover_filename = secure_filename(cover.filename)
    
    audio.save(os.path.join(app.config['UPLOAD_FOLDER'], audio_filename))
    cover.save(os.path.join(app.config['COVER_FOLDER'], cover_filename))
    
    audio_path = f'/static/music/{audio_filename}'
    cover_path = f'/static/covers/{cover_filename}'

    # 3. ★★★ 自動建立專輯 ★★★
    # 專輯名稱 = 歌名, 發行日 = 今天
    new_album = Album(
        title=title,
        artist_id=artist_id,
        release_date=datetime.utcnow().date(),
        cover_art_url=cover_path
    )
    db.session.add(new_album)
    db.session.commit() # 先 commit 才能拿到 new_album.album_id

    # 4. ★★★ 建立歌曲並連結到剛建好的專輯 ★★★
    new_song = Song(
        title=title,
        album_id=new_album.album_id, # 自動連結
        duration_minutes=duration_m,
        duration_seconds=duration_s,
        audio_file_url=audio_path,
        eid=session.get('admin_id'),
        upload_date=datetime.utcnow()
    )
    
    # (選用) 自動填入 Song_Artists
    artist = Artist.query.get(artist_id)
    if artist:
        new_song.artists.append(artist)

    db.session.add(new_song)
    db.session.commit()
    
    flash(f'單曲《{title}》發行成功！', 'success')
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
            eid=session['admin_id'], # 記錄是誰上架的
            upload_date=datetime.utcnow()
        )
        db.session.add(new_song)
        db.session.commit()
        
        flash(f'歌曲 {title} 上架成功！', 'success')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/manage')
def admin_manage():
    # 檢查是否登入 (假設你用 session['admin_id'] 判斷)
    if 'admin_id' not in session:
        return redirect(url_for('admin_login')) # 或是你登入頁面的 function name
    
    # 查詢所有資料
    artists = Artist.query.order_by(Artist.artist_id.desc()).all()
    albums = Album.query.order_by(Album.album_id.desc()).all()
    songs = Song.query.order_by(Song.song_id.desc()).all()
    users = User.query.order_by(User.user_id.desc()).all()
    return render_template('admin_manage.html', artists=artists, albums=albums, songs=songs, users=users)

# 2. 編輯藝人
@app.route('/admin/edit/artist/<int:id>', methods=['GET', 'POST'])
def edit_artist(id):
    if 'admin_id' not in session: return redirect(url_for('admin_login'))
    
    artist = Artist.query.get_or_404(id)
    
    if request.method == 'POST':
        artist.name = request.form['name']
        artist.bio = request.form['bio']
        artist.artist_image_url = request.form['image_url']
        
        db.session.commit()
        flash('藝人資料更新成功！', 'success')
        return redirect(url_for('admin_manage'))
        
    return render_template('admin_edit.html', type='artist', item=artist)

# 3. 編輯專輯
@app.route('/admin/edit/album/<int:id>', methods=['GET', 'POST'])
def edit_album(id):
    if 'admin_id' not in session: return redirect(url_for('admin_login'))
    
    album = Album.query.get_or_404(id)
    
    if request.method == 'POST':
        album.title = request.form['title']
        album.cover_art_url = request.form['cover_url']
        # 注意：這裡假設你表單送來的日期是字串，如果要嚴謹一點可能要轉 date 物件
        album.release_date = request.form['release_date'] 
        
        db.session.commit()
        flash('專輯資料更新成功！', 'success')
        return redirect(url_for('admin_manage'))
        
    return render_template('admin_edit.html', type='album', item=album)

# 4. 編輯歌曲
@app.route('/admin/edit/song/<int:id>', methods=['GET', 'POST'])
def edit_song(id):
    if 'admin_id' not in session: return redirect(url_for('admin_login'))
    
    song = Song.query.get_or_404(id)
    
    if request.method == 'POST':
        song.title = request.form['title']
        song.audio_file_url = request.form['audio_url']
        
        db.session.commit()
        flash('歌曲資料更新成功！', 'success')
        return redirect(url_for('admin_manage'))
        
    return render_template('admin_edit.html', type='song', item=song)
@app.route('/admin/edit/user/<int:id>', methods=['GET', 'POST'])
def edit_user(id):
    if 'admin_id' not in session: return redirect(url_for('admin_login'))
    
    user = User.query.get_or_404(id)
    
    if request.method == 'POST':
        # 更新會員等級 (Free / Premium)
        user.subscription_type = request.form['subscription_type']
        
        db.session.commit()
        flash(f'會員 {user.display_name} 的權限已更新為 {user.subscription_type}！', 'success')
        return redirect(url_for('admin_manage'))
        
    return render_template('admin_edit.html', type='user', item=user)

# 6. 後台登出
@app.route('/admin/logout')
def admin_logout():
    from flask import session
    session.pop('admin_id', None)
    return redirect(url_for('admin_login'))

# app.py - 個人檔案頁面

@app.route('/user/<int:user_id>')
@login_required
def user_profile(user_id):
    # 1. 抓取使用者資料
    user = User.query.get_or_404(user_id)
    
    # 2. 抓取該使用者的「公開」播放清單
    # (如果是看自己的檔案，你也可以考慮顯示全部，但這裡我們先只顯示公開的)
    public_playlists = Playlist.query.filter_by(user_id=user.user_id, is_public=True).all()
    
    # 3. 抓取該使用者追蹤的演出者
    followed_artists = user.followed_artists
    
    # 4. 回傳頁面
    if request.headers.get('HX-Request'):
        return render_template('profile_content.html', user=user, playlists=public_playlists, artists=followed_artists)
    
    return render_template('profile_detail.html', user=user, playlists=public_playlists, artists=followed_artists)

# app.py

@app.route('/artist/<int:artist_id>')
@login_required
def artist_detail(artist_id):
    # 1. 抓取歌手資料
    artist = Artist.query.get_or_404(artist_id)
    
    # 2. 抓取該歌手的所有專輯
    albums = Album.query.filter_by(artist_id=artist_id).all()
    
    # 3. ★★★ 抓取熱門歌曲 (邏輯修正) ★★★
    # 方法：把這位歌手所有專輯裡的歌都拿出來，然後依照「上架日期」從新到舊排序
    all_songs = []
    for album in albums:
        for song in album.songs:
            all_songs.append(song)
    
    # 使用 Python 進行排序 (最新的在前面)，並只取前 5 首
    # 如果沒有 upload_date，就用最小日期代替，避免報錯
    popular_songs = sorted(
        all_songs, 
        key=lambda x: x.upload_date if x.upload_date else datetime.min, 
        reverse=True
    )[:5]
    
    # 4. 回傳頁面 (HTMX 邏輯保持不變)
    if request.headers.get('HX-Request'):
        return render_template('artist_content.html', artist=artist, albums=albums, popular_songs=popular_songs)
    
    return render_template('artist_detail.html', artist=artist, albums=albums, popular_songs=popular_songs)

# --- 啟動程式 ---
if __name__ == '__main__':
    # 建立資料庫表格 (第一次執行時需要)
    with app.app_context():
        db.create_all()
        print("資料庫與表格已建立/檢查完成。")
        
    app.run(debug=True)