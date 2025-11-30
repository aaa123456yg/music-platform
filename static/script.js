/* static/script.js (佇列升級版) */

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
const audioPlayer = document.getElementById('audio-player');
const playIcon = document.getElementById('main-play-icon');
const progressBar = document.getElementById('progress-bar');
const currTimeDisplay = document.getElementById('current-time');
const totTimeDisplay = document.getElementById('total-duration');

const playerCover = document.getElementById('player-cover');
const playerTitle = document.getElementById('player-title');
const playerArtist = document.getElementById('player-artist');
const repeatBtn = document.getElementById('repeat-btn');

// ★★★ 新增：記憶體內的播放佇列 ★★★
let currentQueue = [];      // 存放整張歌單的資訊 [{url, title, artist, cover}, ...]
let currentSongIndex = -1;  // 目前播到第幾首
let repeatState = 0;        // 0:不循環, 1:列表循環, 2:單曲循環

// --- 3. 播放指定歌曲 (接收 artistId) ---
function playMusic(url, title, artist, coverUrl, rowElement, artistId) {
    // 1. 重新抓取 DOM
    const audioPlayer = document.getElementById('audio-player');
    const playerTitle = document.getElementById('player-title');
    const playerArtist = document.getElementById('player-artist'); // 這是 <a> 標籤
    const playerCover = document.getElementById('player-cover');

    // 2. 如果是手動點擊，重建佇列
    if (rowElement) {
        buildQueueFromDOM(rowElement);
    }

    // 3. 設定音訊與文字
    audioPlayer.src = url;
    playerTitle.innerText = title;
    playerArtist.innerText = artist;
    
    // ★★★ 關鍵：設定演出者連結 ★★★
    if (artistId && playerArtist) {
        // 移除舊的事件監聽器 (避免重複)
        const newArtistLink = playerArtist.cloneNode(true);
        playerArtist.parentNode.replaceChild(newArtistLink, playerArtist);
        
        // 綁定新的點擊事件 (使用 HTMX API)
        newArtistLink.onclick = function(e) {
            e.preventDefault(); // 阻止 href="#" 跳轉
            htmx.ajax('GET', `/artist/${artistId}`, {
                target: '#main-content',
                select: '#main-content',
                swap: 'outerHTML'
            }).then(() => {
                // 手動更新網址列
                history.pushState(null, '', `/artist/${artistId}`);
            });
        };
    }

    if (coverUrl && coverUrl !== 'None') {
        playerCover.src = coverUrl;
        playerCover.style.display = 'block';
    } else {
        playerCover.style.display = 'none';
    }

    // 視覺標記
    if (currentPlayingRow) currentPlayingRow.classList.remove('playing');
    if (rowElement) {
        currentPlayingRow = rowElement;
        currentPlayingRow.classList.add('playing');
    }

    audioPlayer.play();
    updatePlayIcon(true);
    syncVisuals();
}

// Update loadAndPlay to handle the link
function loadAndPlay(url, title, artist, coverUrl, artistId) {
    const audioPlayer = document.getElementById('audio-player');
    const playerTitle = document.getElementById('player-title');
    const playerArtist = document.getElementById('player-artist');
    const playerCover = document.getElementById('player-cover');

    audioPlayer.src = url;
    
    if (playerTitle) playerTitle.innerText = title;
    
    if (playerArtist) {
        playerArtist.innerText = artist;
        // ★★★ NEW: Update the link href ★★★
        // Use HTMX logic manually if you want SPA behavior, or just simple href
        // Simple href:
        // playerArtist.href = `/artist/${artistId}`;
        
        // SPA behavior (HTMX-like):
        playerArtist.setAttribute('hx-get', `/artist/${artistId}`);
        playerArtist.setAttribute('hx-target', '#main-content');
        playerArtist.setAttribute('hx-select', '#main-content');
        playerArtist.setAttribute('hx-swap', 'outerHTML');
        playerArtist.setAttribute('hx-push-url', 'true');
        // We need to re-process this element with HTMX because we changed attributes dynamically
        htmx.process(playerArtist);
    }
    
    if (playerCover) {
        if (coverUrl && coverUrl !== 'None') {
            playerCover.src = coverUrl;
            playerCover.style.display = 'block';
        } else {
            playerCover.style.display = 'none';
        }
    }

    audioPlayer.play();
    updatePlayIcon(true);
    syncVisuals();
}

function buildQueueFromDOM(clickedRow) {
    currentQueue = [];
    const rows = document.querySelectorAll('.song-row');
    
    rows.forEach((row, index) => {
        const onclickText = row.getAttribute('onclick');
        const parts = onclickText.split("'"); 
        
        // playMusic('url', 'title', 'artist', 'cover', this, 'artistId')
        // index: 1=url, 3=title, 5=artist, 7=cover, 11=artistId
        
        const songData = {
            url: parts[1],
            title: parts[3],
            artist: parts[5],
            cover: parts[7],
            artistId: parts[11] // ★★★ 抓取第 6 個參數 ★★★
        };
        currentQueue.push(songData);

        if (row === clickedRow) {
            currentSongIndex = index;
        }
    });
}

// 輔助函式：載入並播放
function loadAndPlay(url, title, artist, coverUrl) {
    const audioPlayer = document.getElementById('audio-player'); // 重新抓取確保安全
    const playerTitle = document.getElementById('player-title');
    const playerArtist = document.getElementById('player-artist');
    const playerCover = document.getElementById('player-cover');

    audioPlayer.src = url;
    
    if (playerTitle) playerTitle.innerText = title;
    if (playerArtist) playerArtist.innerText = artist;
    
    if (playerCover) {
        if (coverUrl && coverUrl !== 'None') {
            playerCover.src = coverUrl;
            playerCover.style.display = 'block';
        } else {
            playerCover.style.display = 'none';
        }
    }

    audioPlayer.play();
    updatePlayIcon(true);
    syncVisuals(); // 同步列表綠色字
}

// --- 4. 播放第一首歌 ---
function playFirstSong() {
    const firstRow = document.querySelector('.song-row');
    if (firstRow) firstRow.click();
}

// --- 5. 切換播放/暫停 ---
function togglePlay() {
    if (audioPlayer.paused) {
        audioPlayer.play();
        updatePlayIcon(true);
    } else {
        audioPlayer.pause();
        updatePlayIcon(false);
    }
}

function updatePlayIcon(isPlaying) {
    if (isPlaying) {
        playIcon.classList.remove('fa-circle-play');
        playIcon.classList.add('fa-circle-pause');
    } else {
        playIcon.classList.remove('fa-circle-pause');
        playIcon.classList.add('fa-circle-play');
    }
}

// --- 6. 切換循環模式 ---
function toggleRepeat() {
    repeatState = (repeatState + 1) % 3; 
    
    if(repeatBtn) {
        repeatBtn.classList.remove('active');
        repeatBtn.classList.remove('repeat-one');

        if (repeatState === 1) {
            repeatBtn.classList.add('active');
            repeatBtn.title = "列表循環";
        } else if (repeatState === 2) {
            repeatBtn.classList.add('active');
            repeatBtn.classList.add('repeat-one');
            repeatBtn.title = "單曲循環";
        } else {
            repeatBtn.title = "不循環";
        }
    }
}

// --- 7. ★★★ 下一首邏輯 (改用記憶體佇列) ★★★ ---
function playNextSong(autoPlay = false) {
    if (currentQueue.length === 0) return; // 沒歌單

    // 單曲循環
    if ((autoPlay || !autoPlay) && repeatState === 2) {
        audioPlayer.currentTime = 0;
        audioPlayer.play();
        return;
    }

    // 計算下一首的 Index
    let nextIndex = currentSongIndex + 1;

    // 如果到底了
    if (nextIndex >= currentQueue.length) {
        if (repeatState === 1) {
            nextIndex = 0; // 列表循環：回到第一首
        } else {
            updatePlayIcon(false); // 不循環：停止
            return;
        }
    }

    // 播放下一首
    currentSongIndex = nextIndex;
    const nextSong = currentQueue[nextIndex];
    loadAndPlay(nextSong.url, nextSong.title, nextSong.artist, nextSong.cover, nextSong.artistId);
}

// --- 8. ★★★ 上一首邏輯 (改用記憶體佇列) ★★★ ---
function playPrevSong() {
    if (currentQueue.length === 0) return;

    if (repeatState === 2) { // 單曲循環
        audioPlayer.currentTime = 0;
        audioPlayer.play();
        return;
    }

    let prevIndex = currentSongIndex - 1;
    if (prevIndex < 0) prevIndex = 0; // 已經是第一首就重播第一首

    currentSongIndex = prevIndex;
    const prevSong = currentQueue[prevIndex];
    loadAndPlay(prevSong.url, prevSong.title, prevSong.artist, prevSong.cover, nextSong.artistId);
}

// --- 9. 自動播放結束 ---
audioPlayer.onended = function() {
    playNextSong(true);
};

// --- 10. 進度條與音量 ---
audioPlayer.ontimeupdate = function() {
    if (audioPlayer.duration) {
        const progress = (audioPlayer.currentTime / audioPlayer.duration) * 100;
        progressBar.value = progress;
        currTimeDisplay.innerText = formatTime(audioPlayer.currentTime);
        totTimeDisplay.innerText = formatTime(audioPlayer.duration);
    }
};

function seekAudio() {
    const seekTime = (progressBar.value / 100) * audioPlayer.duration;
    audioPlayer.currentTime = seekTime;
}

function setVolume() {
    audioPlayer.volume = document.getElementById('volume-bar').value;
}

function formatTime(seconds) {
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return min + ":" + (sec < 10 ? "0" + sec : sec);
}

// --- 11. ★★★ 視覺同步 (HTMX 換頁後自動執行) ★★★ ---
// 當你切換頁面回來時，這個函式會幫你把「正在播放」的那首歌名變綠色
function syncVisuals() {
    // 先移除所有綠色標記
    document.querySelectorAll('.song-name-highlight').forEach(el => el.style.color = '');

    // 如果目前沒有播放清單，就不做
    if (currentQueue.length === 0 || currentSongIndex === -1) return;

    // 取得目前正在播的歌資訊
    const currentSong = currentQueue[currentSongIndex];

    // 掃描現在畫面上的列表，看看有沒有這首歌
    const rows = document.querySelectorAll('.song-row');
    rows.forEach(row => {
        // 簡單比對：看歌名是否一樣
        const titleEl = row.querySelector('.song-name-highlight');
        if (titleEl && titleEl.innerText === currentSong.title) {
            titleEl.style.color = '#1ed760'; // 標記綠色
        }
    });
}

// 監聽 HTMX 換頁事件，每次換頁完都同步一次視覺
document.body.addEventListener('htmx:afterSwap', function() {
    syncVisuals();
});

// --- 12. 彈跳視窗邏輯 (加入清單) ---
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

// --- 13. 建立清單 Modal ---
function openModal() {
    const modal = document.getElementById("createPlaylistModal");
    if(modal) modal.style.display = "flex";
}
function closeModal() {
    const modal = document.getElementById("createPlaylistModal");
    if(modal) modal.style.display = "none";
}