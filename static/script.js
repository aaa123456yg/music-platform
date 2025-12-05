/* static/script.js */

// --- 1. 下拉選單控制 ---
function toggleDropdown() { 
    const dropdown = document.getElementById("userDropdown");
    if (dropdown) dropdown.classList.toggle("show"); 
}

window.onclick = function(event) {
    if (!event.target.closest('.user-btn')) {
        var dropdowns = document.getElementsByClassName("dropdown-content");
        for (var i = 0; i < dropdowns.length; i++) {
            if (dropdowns[i].classList.contains('show')) dropdowns[i].classList.remove('show');
        }
    }
}

// --- 2. 播放器變數 ---
function getPlayerElements() {
    return {
        audio: document.getElementById('audio-player'),
        icon: document.getElementById('main-play-icon'),
        bar: document.getElementById('progress-bar'),
        //volBar: document.getElementById('volume-bar'), // 確保這裡有名稱
        currTime: document.getElementById('current-time'),
        totTime: document.getElementById('total-duration'),
        cover: document.getElementById('player-cover'),
        title: document.getElementById('player-title'),
        artist: document.getElementById('player-artist'),
        repeatBtn: document.getElementById('repeat-btn')
    };
}

let currentQueue = [];
let currentSongIndex = -1;
let repeatState = 0; 

// ★★★ 視覺優化函式 ★★★
function updateRangeVisuals(el) {
    if (!el) return;
    const val = parseFloat(el.value);
    const min = parseFloat(el.min || 0);
    const max = parseFloat(el.max || 100);
    const percent = (val - min) / (max - min) * 100;
    el.style.background = `linear-gradient(to right, #1ed760 0%, #1ed760 ${percent}%, #535353 ${percent}%, #535353 100%)`;
}

// ★★★ 通用滑桿監聽 ★★★
function addRangeListener(el, callback) {
    if (!el) return;
    updateRangeVisuals(el);
    el.addEventListener('input', function() {
        updateRangeVisuals(this);
        if (callback) callback(this.value);
    });
}

// --- 3. 播放邏輯 ---
function playMusic(url, title, artist, coverUrl, rowElement, artistId) {
    const p = getPlayerElements();
    p.audio.src = url;
    p.title.innerText = title;
    p.artist.innerText = artist;

    if (p.artist && artistId) {
        const newLink = p.artist.cloneNode(true);
        p.artist.parentNode.replaceChild(newLink, p.artist);
        newLink.href = "#";
        newLink.style.cursor = "pointer";
        newLink.onclick = function(e) {
            e.preventDefault();
            htmx.ajax('GET', `/artist/${artistId}`, {
                target: '#main-content', select: '#main-content', swap: 'outerHTML'
            }).then(() => history.pushState(null, '', `/artist/${artistId}`));
        };
    }
    
    if (p.cover) {
        if (coverUrl && coverUrl !== 'None') {
            p.cover.src = coverUrl;
            p.cover.style.display = 'block';
        } else {
            p.cover.style.display = 'none';
        }
    }

    if (rowElement) {
        buildQueueFromDOM(rowElement);
        document.querySelectorAll('.song-name-highlight').forEach(el => el.style.color = '');
        const titleEl = rowElement.querySelector('.song-name-highlight');
        if (titleEl) titleEl.style.color = '#1ed760';
    }

    const playPromise = p.audio.play();
    if (playPromise !== undefined) {
        playPromise.then(() => updatePlayIcon(true)).catch(err => console.log(err));
    }
    syncVisuals(title);
}

function loadAndPlay(song) {
    const p = getPlayerElements();
    if (!p.audio) return;
    p.audio.src = song.url;
    if (p.title) p.title.innerText = song.title;
    if (p.artist) p.artist.innerText = song.artist;

    if (p.cover) {
        if (song.cover && song.cover !== 'None') {
            p.cover.src = song.cover;
            p.cover.style.display = 'block';
        } else {
            p.cover.style.display = 'none';
        }
    }
    
    if (p.artist && song.artistId) {
        const newLink = p.artist.cloneNode(true);
        p.artist.parentNode.replaceChild(newLink, p.artist);
        newLink.href = "#";
        newLink.style.cursor = "pointer";
        newLink.onclick = function(e) {
            e.preventDefault();
            htmx.ajax('GET', `/artist/${song.artistId}`, {
                target: '#main-content', select: '#main-content', swap: 'outerHTML'
            }).then(() => history.pushState(null, '', `/artist/${song.artistId}`));
        };
    }

    const playPromise = p.audio.play();
    if (playPromise !== undefined) {
        playPromise.then(() => updatePlayIcon(true)).catch(err => console.log(err));
    }
    syncVisuals(song.title);
}

function buildQueueFromDOM(clickedRow) {
    currentQueue = [];
    const rows = document.querySelectorAll('.song-row');
    rows.forEach((row, index) => {
        const onclickText = row.getAttribute('onclick');
        if (!onclickText) return;
        const parts = onclickText.split("'");
        if (parts.length >= 10) {
            currentQueue.push({
                url: parts[1], title: parts[3], artist: parts[5], cover: parts[7], artistId: parts[9]
            });
        }
        if (row === clickedRow) currentSongIndex = index;
    });
}

// --- 4. 播放控制 ---
function playNextSong(autoPlay = false) {
    if (currentQueue.length === 0) return;
    const p = getPlayerElements();
    if ((autoPlay || !autoPlay) && repeatState === 2) {
        p.audio.currentTime = 0;
        p.audio.play();
        return;
    }
    let nextIndex = currentSongIndex + 1;
    if (nextIndex >= currentQueue.length) {
        if (repeatState === 1) {
            nextIndex = 0;
        } else {
            updatePlayIcon(false);
            return;
        }
    }
    currentSongIndex = nextIndex;
    loadAndPlay(currentQueue[nextIndex]);
}// --- 7. 下一首邏輯 (修正版) ---
function playNextSong(autoPlay = false) {
    if (currentQueue.length === 0) return;

    const p = getPlayerElements();

    // 1. 單曲循環
    if ((autoPlay || !autoPlay) && repeatState === 2) {
        p.audio.currentTime = 0;
        p.audio.play();
        return;
    }

    // 計算下一首的位置
    let nextIndex = currentSongIndex + 1;

    // 2. 判斷是否到底了
    if (nextIndex >= currentQueue.length) {
        if (repeatState === 1) {
            // 列表循環：回到第一首
            nextIndex = 0; 
        } else {
            // ★★★ 修正這裡：不循環模式 ★★★
            // 1. 真正的停止音樂
            p.audio.pause(); 
            // 2. (選用) 把進度拉回開頭
            p.audio.currentTime = 0; 
            // 3. 更新圖示為「暫停狀態 (顯示播放鍵)」
            updatePlayIcon(false); 
            return;
        }
    }

    // 3. 正常播放下一首
    currentSongIndex = nextIndex;
    loadAndPlay(currentQueue[nextIndex]);
}

function playPrevSong() {
    if (currentQueue.length === 0) return;
    const p = getPlayerElements();
    if (repeatState === 2 || p.audio.currentTime > 3) {
        p.audio.currentTime = 0;
        p.audio.play();
        return;
    }
    let prevIndex = currentSongIndex - 1;
    if (prevIndex < 0) prevIndex = 0;
    currentSongIndex = prevIndex;
    loadAndPlay(currentQueue[prevIndex]);
}

function playFirstSong() {
    const firstRow = document.querySelector('.song-row');
    if (firstRow) firstRow.click();
}

function togglePlay() {
    const p = getPlayerElements();
    if (p.audio.paused) {
        p.audio.play();
        updatePlayIcon(true);
    } else {
        p.audio.pause();
        updatePlayIcon(false);
    }
}

function updatePlayIcon(isPlaying) {
    const icon = document.getElementById('main-play-icon');
    if (!icon) return;
    if (isPlaying) {
        icon.classList.remove('fa-circle-play');
        icon.classList.add('fa-circle-pause');
    } else {
        icon.classList.remove('fa-circle-pause');
        icon.classList.add('fa-circle-play');
    }
}

function toggleRepeat() {
    const btn = document.getElementById('repeat-btn');
    if (!btn) return;
    repeatState = (repeatState + 1) % 3;
    btn.classList.remove('active');
    btn.classList.remove('repeat-one');
    if (repeatState === 1) {
        btn.classList.add('active');
        btn.title = "列表循環";
    } else if (repeatState === 2) {
        btn.classList.add('active');
        btn.classList.add('repeat-one');
        btn.title = "單曲循環";
    } else {
        btn.title = "不循環";
    }
}

// --- 7. 事件監聽 & 初始化 ---
const defaultVolume = 0.5;
let lastVolume = defaultVolume;

function initPlayerEvents() {
    const p = getPlayerElements();
    if (p.audio) {
        if (p.bar) {
            addRangeListener(p.bar, (val) => {
                const seekTime = (val / 100) * p.audio.duration;
                p.audio.currentTime = seekTime;
            });
        }

        p.audio.onended = function() { playNextSong(true); };
        
        p.audio.ontimeupdate = function() {
            if (p.audio.duration) {
                const progress = (p.audio.currentTime / p.audio.duration) * 100;
                p.bar.value = progress;
                p.currTime.innerText = formatTime(p.audio.currentTime);
                p.totTime.innerText = formatTime(p.audio.duration);
                updateRangeVisuals(p.bar);
            }
        };
    }
}

document.addEventListener('DOMContentLoaded', initPlayerEvents);
document.body.addEventListener('htmx:afterSwap', function() {
    initPlayerEvents();
    syncVisuals();
});

// ★★★ 這就是你剛剛報錯缺少的函式！現在補上了 ★★★
function setVolume() {
    const p = getPlayerElements();
    // 這裡加了防呆，如果抓不到元素就不執行
    if (!p.audio || !p.volBar) return;

    const volume = p.volBar.value;
    p.audio.volume = volume;
    
    updateRangeVisuals(p.volBar);
    updateVolumeIcon(volume);
    
    if (volume > 0) {
        lastVolume = volume;
        p.audio.muted = false;
    }
}

// --- 輔助功能 ---
function toggleMute() {
    const p = getPlayerElements();
    // 如果沒有音量條也沒關係，至少要能靜音
    if (!p.audio) return;

    console.log("Toggle Mute Clicked!"); // ★★★ 除錯用 ★★★

    if (p.audio.muted || p.audio.volume === 0) {
        // 解除靜音
        p.audio.muted = false;
        p.audio.volume = lastVolume || 0.5;
        if (p.volBar) p.volBar.value = p.audio.volume;
    } else {
        // 靜音
        p.audio.muted = true;
        if (p.volBar) p.volBar.value = 0;
    }
    
    // 更新視覺 (包含滑桿和圖示)
    if (p.volBar) updateRangeVisuals(p.volBar);
    updateVolumeIcon(p.audio.volume);
}

function updateVolumeIcon(volume) {
    const volIcon = document.getElementById('volume-icon'); // 改用 ID 抓取更準確
    if (!volIcon) return;
    const aud = document.getElementById('audio-player');
    
    // 先清空所有 class
    volIcon.className = ''; 
    
    // 根據狀態加回去
    if (aud && aud.muted) {
        volIcon.className = 'fa-solid fa-volume-xmark'; // 靜音圖示
    } else if (volume >= 0.5) {
        volIcon.className = 'fa-solid fa-volume-high';
    } else if (volume > 0) {
        volIcon.className = 'fa-solid fa-volume-low';
    } else {
        volIcon.className = 'fa-solid fa-volume-xmark';
    }
    
    // 確保樣式正確
    volIcon.style.cursor = 'pointer';
    volIcon.style.marginRight = '15px';
}

function formatTime(seconds) {
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return min + ":" + (sec < 10 ? "0" + sec : sec);
}

function syncVisuals(playingTitle) {
    document.querySelectorAll('.song-name-highlight').forEach(el => el.style.color = '');
    if (!playingTitle && currentQueue.length > 0 && currentSongIndex !== -1) {
        playingTitle = currentQueue[currentSongIndex].title;
    }
    if (!playingTitle) return;

    const rows = document.querySelectorAll('.song-row');
    rows.forEach(row => {
        const titleEl = row.querySelector('.song-name-highlight');
        if (titleEl && titleEl.innerText.trim() === playingTitle.trim()) {
            titleEl.style.color = '#1ed760';
        }
    });
}

// 彈跳視窗邏輯
let currentSongIdToAdd = null; 
function openAddToPlaylistModal(songId) {
    currentSongIdToAdd = songId;
    const modal = document.getElementById("addToPlaylistModal");
    if (modal) modal.style.display = "flex";
}
function closeAddToPlaylistModal() {
    const modal = document.getElementById("addToPlaylistModal");
    if (modal) modal.style.display = "none";
    currentSongIdToAdd = null;
}
function addToPlaylist(playlistId, element) {
    if (!currentSongIdToAdd) {
        console.error("未選擇歌曲");
        return;
    }

    fetch(`/add_to_playlist/${playlistId}/${currentSongIdToAdd}`, {
        method: 'POST'
    })
    .then(response => response.json()) // ★★★ 改成解析 JSON
    .then(data => {
        // 1. 無論有沒有重複，都更新成「資料庫裡的真實數量」
        if (element) {
            const countDiv = element.querySelector('.song-count-text');
            if (countDiv) {
                countDiv.innerText = data.new_count + " 首歌曲";
            }
        }

        // 2. 根據後端回傳的 added 狀態決定行為
        if (data.added) {
            console.log("加入成功");
            closeAddToPlaylistModal();
        } else {
            // 如果是重複的，雖然數量會更新(保持不變)，但也給個提示
            alert("這首歌已經在播放清單裡囉！");
            // 選擇性：重複的話要不要關視窗？通常可以不關，方便他選別張
            // closeAddToPlaylistModal(); 
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert("發生錯誤，請稍後再試。");
    });
}

function openModal() {
    const modal = document.getElementById("createPlaylistModal");
    if(modal) modal.style.display = "flex";
}
function closeModal() {
    const modal = document.getElementById("createPlaylistModal");
    if(modal) modal.style.display = "none";
}

// 篩選器
function filterLibrary(type, btn) {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const cards = document.querySelectorAll('.cards-container .card');
    cards.forEach(card => {
        if (type === 'all' || card.getAttribute('data-type') === type) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}