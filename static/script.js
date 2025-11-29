/* static/script.js */

// --- 1. 下拉選單控制 ---
function toggleDropdown() { 
    document.getElementById("userDropdown").classList.toggle("show"); 
}

// 點擊視窗其他地方關閉選單
window.onclick = function(event) {
    if (!event.target.closest('.user-btn')) {
        var dropdowns = document.getElementsByClassName("dropdown-content");
        for (var i = 0; i < dropdowns.length; i++) {
            if (dropdowns[i].classList.contains('show')) {
                dropdowns[i].classList.remove('show');
            }
        }
    }
}

// --- 2. 播放器全域變數 ---
// 注意：這些變數會在頁面載入後抓取 DOM
const audioPlayer = document.getElementById('audio-player');
const playIcon = document.getElementById('main-play-icon');
const progressBar = document.getElementById('progress-bar');
const currTimeDisplay = document.getElementById('current-time');
const totTimeDisplay = document.getElementById('total-duration');

const playerCover = document.getElementById('player-cover');
const playerTitle = document.getElementById('player-title');
const playerArtist = document.getElementById('player-artist');
const repeatBtn = document.getElementById('repeat-btn');

// 循環狀態：0:不循環, 1:列表循環, 2:單曲循環
let repeatState = 0; 
let currentPlayingRow = null; 

// --- 3. 播放指定歌曲 ---
function playMusic(url, title, artist, coverUrl, rowElement) {
    audioPlayer.src = url;
    playerTitle.innerText = title;
    playerArtist.innerText = artist;
    
    if (coverUrl && coverUrl !== 'None') {
        playerCover.src = coverUrl;
        playerCover.style.display = 'block';
    } else {
        playerCover.style.display = 'none';
    }

    // 視覺標記目前播放的行
    if (currentPlayingRow) currentPlayingRow.classList.remove('playing');
    if (rowElement) {
        currentPlayingRow = rowElement;
        // rowElement.classList.add('playing'); // 如果 CSS 有寫 .playing 效果
    }

    audioPlayer.play();
    updatePlayIcon(true);
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
    repeatState = (repeatState + 1) % 3; // 0->1->2->0

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

// --- 7. 下一首邏輯 ---
function playNextSong(autoPlay = false) {
    // 自動播放且單曲循環 -> 重播
    if (autoPlay && repeatState === 2) {
        audioPlayer.currentTime = 0;
        audioPlayer.play();
        return;
    }

    // 手動點擊且是單曲/不循環 -> 重播
    if (!autoPlay) {
        if (repeatState === 2 || repeatState === 0) {
            audioPlayer.currentTime = 0;
            audioPlayer.play();
            return;
        }
    }

    // 列表循環：找下一首
    if (!currentPlayingRow) return;
    let nextRow = currentPlayingRow.nextElementSibling;
    if (nextRow && nextRow.classList.contains('song-row')) {
        nextRow.click();
    } else if (repeatState === 1) {
        playFirstSong(); // 循環回第一首
    }
}

// --- 8. 上一首邏輯 ---
function playPrevSong() {
    if (repeatState === 2 || repeatState === 0) {
        audioPlayer.currentTime = 0;
        audioPlayer.play();
        return;
    }

    if (!currentPlayingRow) return;
    let prevRow = currentPlayingRow.previousElementSibling;
    if (prevRow && prevRow.classList.contains('song-row')) {
        prevRow.click();
    }
}

// --- 9. 自動播放結束監聽 ---
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