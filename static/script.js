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

// --- 2. 播放器變數與狀態 ---
function getPlayerElements() {
    return {
        audio: document.getElementById('audio-player'),
        icon: document.getElementById('main-play-icon'),
        bar: document.getElementById('progress-bar'),
        currTime: document.getElementById('current-time'),
        totTime: document.getElementById('total-duration'),
        cover: document.getElementById('player-cover'),
        title: document.getElementById('player-title'),
        artist: document.getElementById('player-artist'), // <a> 標籤
        repeatBtn: document.getElementById('repeat-btn')
    };
}

let currentQueue = [];
let currentSongIndex = -1;
let repeatState = 0; // 0:不循環, 1:列表循環, 2:單曲循環

// --- 3. 播放指定歌曲 (手動點擊入口) ---
function playMusic(url, title, artist, coverUrl, rowElement, artistId) {
    // 1. 如果是手動點擊，重建播放佇列
    if (rowElement) {
        buildQueueFromDOM(rowElement);
    }

    // 2. 建構歌曲物件
    const song = {
        url: url,
        title: title,
        artist: artist,
        cover: coverUrl,
        artistId: artistId
    };

    // 3. 統一呼叫播放函式
    loadAndPlay(song);
}

// --- 核心：載入並播放 (所有播放動作都走這裡) ---
function loadAndPlay(song) {
    const p = getPlayerElements();
    if (!p.audio) return;

    // 1. 設定音訊
    p.audio.src = song.url;

    // 2. 更新文字與封面
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

    // 3. ★★★ 關鍵：更新演出者連結 (上一首/下一首也能更新連結了) ★★★
    if (p.artist && song.artistId) {
        // 複製節點以移除舊事件
        const newLink = p.artist.cloneNode(true);
        p.artist.parentNode.replaceChild(newLink, p.artist);
        
        // 設定新連結
        newLink.href = "#"; // 防止跳轉
        newLink.style.cursor = "pointer";
        
        // 綁定 HTMX 行為
        newLink.onclick = function(e) {
            e.preventDefault();
            htmx.ajax('GET', `/artist/${song.artistId}`, {
                target: '#main-content',
                select: '#main-content',
                swap: 'outerHTML'
            }).then(() => {
                history.pushState(null, '', `/artist/${song.artistId}`);
            });
        };
    }

    // 4. 播放
    // 使用 Promise 避免報錯
    const playPromise = p.audio.play();
    if (playPromise !== undefined) {
        playPromise
            .then(() => updatePlayIcon(true))
            .catch(err => console.log("播放被瀏覽器阻擋:", err));
    }

    // 5. 同步視覺 (變綠色)
    syncVisuals(song.title);
}

// --- 輔助：從 DOM 建立佇列 ---
function buildQueueFromDOM(clickedRow) {
    currentQueue = [];
    const rows = document.querySelectorAll('.song-row');
    
    rows.forEach((row, index) => {
        // 解析 onclick 屬性
        const onclickText = row.getAttribute('onclick');
        if (!onclickText) return;

        const parts = onclickText.split("'");
        // 格式: playMusic('url', 'title', 'artist', 'cover', this, 'id')
        // index: 1=url, 3=title, 5=artist, 7=cover, 9=artistId
        if (parts.length >= 10) {
            currentQueue.push({
                url: parts[1],
                title: parts[3],
                artist: parts[5],
                cover: parts[7],
                artistId: parts[9]
            });
        }

        if (row === clickedRow) {
            currentSongIndex = index;
        }
    });
    console.log(`佇列已建立: ${currentQueue.length} 首`);
}

// --- 4. 上/下一首邏輯 ---
function playNextSong(autoPlay = false) {
    if (currentQueue.length === 0) return;

    const p = getPlayerElements();

    // 單曲循環
    if ((autoPlay || !autoPlay) && repeatState === 2) {
        p.audio.currentTime = 0;
        p.audio.play();
        return;
    }

    let nextIndex = currentSongIndex + 1;
    if (nextIndex >= currentQueue.length) {
        if (repeatState === 1) {
            nextIndex = 0; // 列表循環回到頭
        } else {
            updatePlayIcon(false); // 停止
            return;
        }
    }

    currentSongIndex = nextIndex;
    loadAndPlay(currentQueue[nextIndex]);
}

function playPrevSong() {
    if (currentQueue.length === 0) return;

    const p = getPlayerElements();

    // 單曲循環 -> 重播
    if (repeatState === 2) {
        p.audio.currentTime = 0;
        p.audio.play();
        return;
    }

    // 如果播放超過 3 秒，按上一首通常是「重頭播」
    if (p.audio.currentTime > 3) {
        p.audio.currentTime = 0;
        p.audio.play();
        return;
    }

    // 真的切換到上一首
    let prevIndex = currentSongIndex - 1;
    if (prevIndex < 0) prevIndex = 0; // 已經是第一首就重播第一首

    currentSongIndex = prevIndex;
    loadAndPlay(currentQueue[prevIndex]);
}

// --- 5. 視覺同步 (變綠色) ---
function syncVisuals(playingTitle) {
    // 如果沒傳參數，嘗試從佇列抓
    if (!playingTitle && currentQueue.length > 0 && currentSongIndex !== -1) {
        playingTitle = currentQueue[currentSongIndex].title;
    }
    if (!playingTitle) return;

    // 移除所有綠色
    document.querySelectorAll('.song-name-highlight').forEach(el => el.style.color = '');
    
    // 加上綠色 (使用 trim 去除空白，增加準確度)
    const rows = document.querySelectorAll('.song-row');
    rows.forEach(row => {
        const titleEl = row.querySelector('.song-name-highlight');
        if (titleEl && titleEl.innerText.trim() === playingTitle.trim()) {
            titleEl.style.color = '#1ed760';
        }
    });
}

// --- 6. 其他播放控制 ---
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

// --- 7. 事件監聽 ---
// 頁面載入後綁定
document.addEventListener('DOMContentLoaded', () => {
    const p = getPlayerElements();
    if (p.audio) {
        p.audio.onended = function() { playNextSong(true); };
        p.audio.ontimeupdate = handleTimeUpdate;
    }
});

// HTMX 換頁後重新綁定 (並同步綠色文字)
document.body.addEventListener('htmx:afterSwap', function() {
    const p = getPlayerElements();
    if (p.audio) {
        p.audio.onended = function() { playNextSong(true); };
        p.audio.ontimeupdate = handleTimeUpdate;
        syncVisuals(); // 換頁後立刻檢查有沒有正在播的歌
    }
});

function handleTimeUpdate() {
    const p = getPlayerElements();
    if (p.audio && p.audio.duration) {
        const progress = (p.audio.currentTime / p.audio.duration) * 100;
        p.bar.value = progress;
        p.currTime.innerText = formatTime(p.audio.currentTime);
        p.totTime.innerText = formatTime(p.audio.duration);
    }
}

function seekAudio() {
    const p = getPlayerElements();
    const seekTime = (p.bar.value / 100) * p.audio.duration;
    p.audio.currentTime = seekTime;
}

function setVolume() {
    const p = getPlayerElements();
    const vol = document.getElementById('volume-bar');
    p.audio.volume = vol.value;
}

function formatTime(seconds) {
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return min + ":" + (sec < 10 ? "0" + sec : sec);
}

// --- 8. 彈跳視窗邏輯 ---
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
function submitAddToPlaylist(playlistId) {
    if (!currentSongIdToAdd) {
        alert("錯誤：找不到歌曲 ID");
        closeAddToPlaylistModal();
        return;
    }
    fetch(`/add_to_playlist/${playlistId}/${currentSongIdToAdd}`, { method: 'POST' })
    .then(response => {
        if (response.ok) {
            closeAddToPlaylistModal();
            location.reload(); 
        } else {
            alert("加入失敗");
            closeAddToPlaylistModal();
        }
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