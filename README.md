<p align="center">
  <img width="240" src="./icon.svg" alt="Genesis Music Player Icon">
</p>

<h1 align="center">Genesis Music Player</h1>

**Version 2025.11.12**

<p align="center">
  <strong>A lightweight Qt6 YouTube Music playlist manager & MPV player</strong>
</p>

---

## ✨ Features

- **YouTube Music Search** – Find songs, albums, and artists directly
- **YouTube Playlists** – Load any public or unlisted playlist
- **Local Playlists** – Play from folders
- **Offline Caching** – Save playlists as JSON to avoid repeated API calls
- **MPV-Powered Playback** – Full video playback with MPV’s superior rendering
- **Firefox Cookie Support** – Bypass age/login restrictions using your browser session
- **Clean, Native Qt6 UI** – Fast, responsive, and minimal

> **Note**: This is a **playlist loader & player helper**, not a full music library manager.

---

## 📦 Installation

### Prerequisites
- Python 3.9+
- [MPV](https://mpv.io/installation/) (installed and in `PATH`)
- Firefox (optional, for `/COOKIES` cookie support)

### Install via pip

```bash
pip install PySide6 ytmusicapi yt-dlp
```

### Clone & Run

```bash
git clone https://github.com/vladisrael/genesis-music.git
cd genesis-music
python app.py
```

---

## 🎮 Usage

Launch the app
Use the search bar to find YouTube Music content
Use /ADD to import a YouTube playlist or local folder
Select a playlist from the dropdown
Click tracks to play via MPV


Playback opens in an external MPV window


## ⌨️ Commands
Type these in the command input field:

| Command | Description |
|---------|-------------|
| /ADD    | Add a YouTube playlist URL or local folder |
| /CACHE  | Save current YouTube playlist as local JSON (fast reload) |
| /RELOAD | Refresh the playlist dropdown |
| /COOKIES| Toggle Firefox cookies in MPV (for restricted videos) |
