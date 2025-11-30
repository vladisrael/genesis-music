import os, sys, threading, locale, configparser, glob
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressDialog,
    QComboBox, QLineEdit, QListWidget, QPushButton, QSlider, QScrollBar, QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QFont, QKeyEvent, QIcon

from yt_dlp.dependencies import yt_dlp_ejs
from ytmusicapi import YTMusic
import yt_dlp, json, shutil, subprocess
from typing import Optional, TypedDict, Union, Any


version : str = '2025.11.30'

file_dir : str = os.path.dirname(os.path.realpath(__file__))
frozen_dir = os.path.dirname(sys.executable)
executable_dir : str = file_dir
if getattr(sys, 'frozen', False):
    executable_dir = frozen_dir

os.chdir(executable_dir)

instance_path : str = os.path.join(executable_dir, 'instance')
download_path : str = os.path.join(instance_path, 'downloaded')
os.makedirs(download_path, exist_ok=True)


class Track(TypedDict):
    title:str
    url:str

from PySide6.QtWidgets import QDialog, QFormLayout, QDialogButtonBox

class AddPlaylistDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Add Playlist')
        self.setFixedSize(300, 150)

        layout : QFormLayout = QFormLayout(self)

        self.entry_name : QLineEdit = QLineEdit()
        self.entry_name.setPlaceholderText('(Playlist name)')
        layout.addRow(self.entry_name)

        self.entry_url : QLineEdit = QLineEdit()
        self.entry_url.setPlaceholderText('(YouTube playlist URL) or (local folder path)')
        layout.addRow(self.entry_url)

        self.buttons : QDialogButtonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def get_data(self) -> tuple[str, str]:
        return self.entry_name.text().strip(), self.entry_url.text().strip()


class MusicPlayer(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.yt_playlist_path : str = os.path.join(instance_path, 'playlists_yt.json')
        self.local_playlist_path : str = os.path.join(instance_path, 'playlists_local.json')
        if not os.path.exists(self.yt_playlist_path):
            with open(self.yt_playlist_path, 'w') as file:
                json.dump({}, file)
        if not os.path.exists(self.local_playlist_path):
            with open(self.local_playlist_path, 'w') as file:
                json.dump({}, file)


        self.config: configparser.ConfigParser = configparser.ConfigParser()
        self.config.read(os.path.join(executable_dir, 'app.ini'))
        self.use_cookies : bool = self.config.getboolean('user', 'use_cookies', fallback=False)
        self.browser : str = self.config.get('user', 'browser', fallback='firefox')

        self.recents_path : str = os.path.join(instance_path, 'playlist_recents.json')

        self.setWindowTitle('Genesis Music Player')
        self.setFixedSize(500, 600)
        theme_user : str = self.config.get('user', 'theme', fallback='default')
        theme_file : str = self.config.get('themes', theme_user, fallback='none.qss')
        with open(os.path.join(os.path.join(executable_dir, 'themes'), theme_file), 'r') as file:
            self.setStyleSheet(file.read())

        self.yt_music_api : YTMusic = YTMusic()
        self.player : Optional[subprocess.Popen] = None

        self.track_url : Optional[str] = None
        self.track_text : str = '(NA)'

        self.playlist : dict[str, str] = {}
        self.playlist_titles : list[str] = []
        self.selected_playlist : str = ''
        self.tracks : list[Track] = []

        self.load_playlists()
        self.init_ui()

    def load_playlists(self) -> None:
        self.playlist_titles = []
        with open(self.yt_playlist_path, 'r') as file:
            self.playlist.update({f'YT - {k}': v for k, v in json.load(file).items()})
        with open(self.local_playlist_path, 'r') as file:
            self.playlist.update({f'LOCAL - {k}': v for k, v in json.load(file).items()})

        for file in glob.glob(os.path.join(instance_path, 'cache_*.json')):
            name : str = os.path.splitext(os.path.basename(file))[0].replace('cache_', '')
            self.playlist[f'CACHE - {name}'] = file

        for file in glob.glob(os.path.join(instance_path, 'download_*.json')):
            name : str = os.path.splitext(os.path.basename(file))[0].replace('download_', '')
            self.playlist[f'DOWNLOAD - {name}'] = file

        self.playlist['RECENTS'] = 'RECENTS'
        self.playlist['SEARCH YT'] = 'SEARCH'
        self.playlist['SEARCH PLAYLIST'] = 'SEARCH_PLAYLIST'
        self.playlist_titles = list(self.playlist.keys())

    def download_playlist(self, playlist_url: str, playlist_name:str) -> None:
        progress : QProgressDialog = QProgressDialog(f'Downloading playlist {playlist_name}', 'Cancel', 0, 0)
        progress.setWindowTitle('Downloading')
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()

        QApplication.processEvents()

        ydl_opts : yt_dlp._Params = {
            'format': 'bestaudio/best',
            'outtmpl': f'{download_path}/%(id)s.%(ext)s',
            'ignoreerrors': True,
            'download_archive': os.path.join(instance_path, 'downloaded.txt'),
            'restrictfilenames': True,
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '0',
                },
                {
                    'key': 'EmbedThumbnail',
                },
                {
                    'key': 'FFmpegMetadata',
                },
            ],
            'writethumbnail': True,
        }

        tracks: list[Track] = []
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist_info : dict = ydl.extract_info(playlist_url, download=False)
            progress.setMaximum(len(playlist_info['entries']))
            QApplication.processEvents()
            for i, entry in enumerate(playlist_info['entries']):
                if entry is None:
                    continue

                video_id : str = entry['id']
                title : str = entry['title']
                info : yt_dlp.extractor.common._InfoDict = ydl.extract_info(video_id, download=True)
                tracks.append({
                    'title': title,
                    'url': f'{download_path}/{video_id}.mp3'
                })
                progress.setValue(i)
                QApplication.processEvents()

        with open(os.path.join(instance_path, f'download_{playlist_name}.json'), 'w') as file:
            json.dump(tracks, file, indent=4, ensure_ascii=False)
        progress.close()

    def init_ui(self) -> None:
        layout : QVBoxLayout = QVBoxLayout()

        self.combo_playlist : QComboBox = QComboBox()
        self.combo_playlist.addItems(self.playlist_titles)
        self.combo_playlist.currentIndexChanged.connect(self.load_selected_playlist)
        layout.addWidget(self.combo_playlist)

        self.entry_filter : QLineEdit = QLineEdit()
        self.entry_filter.setPlaceholderText('Search or filter tracks...')
        self.entry_filter.textChanged.connect(self.filter_tracks)
        self.entry_filter.returnPressed.connect(self.entry_enter)
        layout.addWidget(self.entry_filter)

        self.list_tracks : QListWidget = QListWidget()
        self.list_tracks.itemActivated.connect(self.select_track)
        layout.addWidget(self.list_tracks)

        self.label_track : QLabel = QLabel('(NA)')
        self.label_track.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label_track)

        self.setLayout(layout)
        self.combo_playlist.setCurrentIndex(self.playlist_titles.index('RECENTS'))

    @Slot()
    def load_selected_playlist(self) -> None:
        index : int = self.combo_playlist.currentIndex()
        self.selected_playlist = self.playlist_titles[index]
        playlist_url : str = self.playlist[self.selected_playlist]
        self.load_playlist(playlist_url)

    def load_playlist(self, playlist_url:str) -> None:
        if not playlist_url:
            return

        if playlist_url == 'SEARCH':
            self.tracks = []
            self.update_track_list()
        elif playlist_url == 'SEARCH_PLAYLIST':
            self.tracks = []
            self.update_track_list()
        elif playlist_url == 'RECENTS':
            self.load_recents()
        elif playlist_url.endswith('.json'):
            with open(playlist_url, 'r', encoding='utf-8') as f:
                self.tracks = json.load(f)
            self.update_track_list()
        elif os.path.isdir(playlist_url):
            self.tracks = [{'title': entry, 'url': os.path.join(playlist_url, entry)} for entry in sorted(os.listdir(playlist_url))]
            self.update_track_list()
        else:
            ydl_opts : yt_dlp._Params = {
                'extract_flat': True,
                'skip_download': True
            }
            if self.use_cookies:
                ydl_opts['cookiesfrombrowser'] = (self.browser,)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info : dict = ydl.extract_info(playlist_url, download=False)
                self.tracks = [{'title': entry['title'], 'url': entry['url']} for entry in info['entries']]
                self.update_track_list()

    def update_track_list(self) -> None:
        self.list_tracks.clear()
        for idx, track in enumerate(self.tracks):
            self.list_tracks.addItem(f'{idx + 1}. {track['title']}')

    def filter_tracks(self) -> None:
        if self.selected_playlist == 'SEARCH YT':
            return
        keyword : str = self.entry_filter.text().lower()
        filtered_tracks : list[Track] = [{'title': str(idx + 1) + '. ' + track['title'], 'url': track['url']} for idx, track in enumerate(self.tracks) if keyword in track['title'].lower()]
        self.list_tracks.clear()
        for track in filtered_tracks:
            self.list_tracks.addItem(track['title'])

    def reload_playlists(self) -> None:
        self.load_playlists()
        self.combo_playlist.clear()
        self.combo_playlist.addItems(self.playlist_titles)
        self.entry_filter.clear()
        self.combo_playlist.setCurrentIndex(self.playlist_titles.index('RECENTS'))

    def entry_enter(self) -> None:
        match self.entry_filter.text():
            case '/CACHE':
                with open(os.path.join(instance_path, f'cache_{self.selected_playlist}.json'), 'w', encoding='utf-8') as file:
                    json.dump(self.tracks, file, indent=4, ensure_ascii=False)
                self.reload_playlists()
                self.entry_filter.clear()
                return
            case '/RELOAD':
                self.reload_playlists()
                self.entry_filter.clear()
                return
            case '/ADD':
                dialog : AddPlaylistDialog = AddPlaylistDialog(self)
                if dialog.exec() == QDialog.Accepted:
                    name, url = dialog.get_data()
                    if (not name) or (not url):
                        return

                    json_path : str = os.path.join(instance_path, 'playlists_local.json')
                    if url.startswith('http'):
                        json_path = os.path.join(instance_path, 'playlists_yt.json')

                    playlists : dict[str, str] = {}
                    if os.path.exists(json_path):
                        with open(json_path, 'r', encoding='utf-8') as file:
                            try:
                                playlists = json.load(file)
                            except json.JSONDecodeError:
                                playlists = {}

                    playlists[name] = url
                    with open(json_path, 'w', encoding='utf-8') as file:
                        json.dump(playlists, file, indent=4, ensure_ascii=False)
                    self.reload_playlists()
                else:
                    self.entry_filter.clear()
                return
            case '/COOKIES':
                self.use_cookies = not self.use_cookies
                self.entry_filter.clear()
                return

            case '/DOWNLOAD':
                if self.selected_playlist.startswith('YT - '):
                    playlist_url : str = self.playlist[self.selected_playlist]
                    self.download_playlist(playlist_url, self.selected_playlist.lstrip('YT - '))
                    self.reload_playlists()
                    return

        match self.selected_playlist:
            case 'SEARCH YT':
                term : str = self.entry_filter.text().lower()
                results : list[dict] = self.yt_music_api.search(term, filter='songs')
                self.tracks = [{'title': item['title'], 'url': f'https://music.youtube.com/watch?v={item['videoId']}'} for item in results]
                self.update_track_list()
            case 'SEARCH PLAYLIST':
                term : str = self.entry_filter.text().lower()
                results : list[dict] = self.yt_music_api.search(term, filter='playlists')
                self.tracks = [{'title': item['title'], 'url': f'https://music.youtube.com/playlist?list={item['browseId'].removeprefix('VL')}'} for item in results]
                self.update_track_list()

    def select_track(self) -> None:
        current_item : Optional[QListWidgetItem] = self.list_tracks.currentItem()
        if not current_item:
            return
        index : int = int(current_item.text().split('.')[0]) - 1
        if self.selected_playlist == 'SEARCH PLAYLIST':
            if self.tracks[index]['url'].startswith('https://music.youtube.com/playlist?list='):
                playlist_url : str = self.tracks[index]['url']
                self.load_playlist(playlist_url)
                return
        self.track_url = self.tracks[index]['url']
        self.track_text = self.tracks[index]['title']
        self.play_track()

    def load_recents(self) -> None:
        if not os.path.exists(self.recents_path):
            self.tracks = []
            self.update_track_list()
            return

        with open(self.recents_path, 'r', encoding='utf-8') as f:
            data : list[Track] = json.load(f)
        data = data[-self.config.getint('user', 'recents'):]
        data.reverse()
        self.tracks = data
        self.update_track_list()

    def play_track(self) -> None:
        if self.player:
            self.player.terminate()
        self.label_track.setText(self.track_text)

        if self.track_url:

            self.add_to_recents({
                'title': self.track_text,
                'url': self.track_url
            })

            mpv_path : Optional[str] = shutil.which('mpv')
            if not mpv_path:
                raise RuntimeError('MPV not found in PATH.')
            command : list[str] = [
                mpv_path,
                '--ytdl=yes',
                '--osc=yes',
                '--force-window=yes',
                '--loop=inf',
                self.track_url
            ]
            if self.use_cookies:
                command.append('--ytdl-raw-options=cookies-from-browser=firefox')

            self.player = subprocess.Popen(command)

    def add_to_recents(self, track: Track) -> None:
        recents: list[Track] = []
        if os.path.exists(self.recents_path):
            try:
                with open(self.recents_path, 'r', encoding='utf-8') as file:
                    recents = json.load(file)
            except Exception:
                recents = []

        recents = [t for t in recents if t['url'] != track['url']]
        recents.append(track)
        recents = recents[-self.config.getint('user', 'recents'):]

        with open(self.recents_path, 'w', encoding='utf-8') as file:
            json.dump(recents, file, indent=4, ensure_ascii=False)

    def closeEvent(self, event):
        if self.player:
            self.player.terminate()
        return super().closeEvent(event)

if __name__ == '__main__':
    icon_path : str = os.path.join(executable_dir, 'icon.svg')
    icon : QIcon = QIcon(icon_path)

    app : QApplication = QApplication(sys.argv)
    app.setWindowIcon(icon)
    player : MusicPlayer = MusicPlayer()
    player.show()
    sys.exit(app.exec())
