import sys
import os
import json
import shutil
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QAbstractItemView,
    QCheckBox, QSlider, QStyle
)
from PyQt6.QtCore import Qt, QUrl, QEvent
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QKeyEvent
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

class VideoRanker(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Video Ranker")
        self.resize(800, 600)

        self.processed_videos = {}
        self.json_file = 'processed_videos.json'
        self.load_json()

        self.video_list = []
        self.current_index = -1
        self.awaiting_media_load = False  # New flag to track media loading

        self.create_ui()

        self.setAcceptDrops(True)

        self.populate_video_list_from_processed_videos()

    def create_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Left side: video list
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.itemDoubleClicked.connect(self.play_selected_video)
        self.list_widget.itemSelectionChanged.connect(self.on_item_selection_changed)  # Connect selection change
        self.list_widget.installEventFilter(self)  # Install event filter
        main_layout.addWidget(self.list_widget)

        # Right side: media player
        media_player_widget = QWidget()
        media_layout = QVBoxLayout()
        media_player_widget.setLayout(media_layout)
        main_layout.addWidget(media_player_widget)

        self.video_widget = QVideoWidget()
        media_layout.addWidget(self.video_widget)

        self.player = QMediaPlayer()
        self.player.setVideoOutput(self.video_widget)
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        # Slider for timeline
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.set_position)
        media_layout.addWidget(self.position_slider)

        # Playback controls
        controls_layout = QHBoxLayout()
        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_button.clicked.connect(self.play_video)
        self.pause_button = QPushButton()
        self.pause_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        self.pause_button.clicked.connect(self.pause_video)
        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_button.clicked.connect(self.stop_video)
        self.next_button = QPushButton()
        self.next_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))
        self.next_button.clicked.connect(self.play_next_video)
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.pause_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.next_button)

        self.autoplay_checkbox = QCheckBox("Autoplay")
        controls_layout.addWidget(self.autoplay_checkbox)

        media_layout.addLayout(controls_layout)

        # Connect signals
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.mediaStatusChanged.connect(self.media_status_changed)
        self.player.errorOccurred.connect(self.handle_error)
        self.player.playbackStateChanged.connect(self.playback_state_changed)

    def populate_video_list_from_processed_videos(self):
        for video_path, rating in self.processed_videos.items():
            if os.path.exists(video_path):
                self.video_list.append(video_path)
                item = QListWidgetItem(os.path.basename(video_path) + ' ' + '★' * rating)
                self.list_widget.addItem(item)
            else:
                print(f"Warning: {video_path} does not exist")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        for url in urls:
            path = url.toLocalFile()
            if os.path.isdir(path):
                self.add_videos_from_folder(path)
            else:
                if self.is_video_file(path):
                    self.add_video_file(path)

    def add_videos_from_folder(self, folder_path):
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if self.is_video_file(file):
                    full_path = os.path.join(root, file)
                    self.add_video_file(full_path)

    def add_video_file(self, file_path):
        if file_path not in self.video_list:
            self.video_list.append(file_path)
            if file_path in self.processed_videos:
                rating = self.processed_videos[file_path]
                item = QListWidgetItem(os.path.basename(file_path) + ' ' + '★' * rating)
            else:
                item = QListWidgetItem(os.path.basename(file_path))
            self.list_widget.addItem(item)

    def is_video_file(self, filename):
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
        ext = os.path.splitext(filename)[1].lower()
        return ext in video_extensions

    def play_selected_video(self, item):
        index = self.list_widget.row(item)
        self.current_index = index
        self.play_video_at_index(index)

    def play_video_at_index(self, index):
        if 0 <= index < len(self.video_list):
            video_path = self.video_list[index]
            self.player.setSource(QUrl.fromLocalFile(video_path))
            self.player.play()

    def play_video(self):
        if self.current_index == -1 and self.video_list:
            self.current_index = 0
            self.play_video_at_index(self.current_index)
        else:
            self.player.play()

    def pause_video(self):
        self.player.pause()

    def stop_video(self):
        self.player.stop()

    def play_next_video(self):
        self.current_index += 1
        if self.current_index < len(self.video_list):
            self.play_video_at_index(self.current_index)
        else:
            self.current_index = -1  # Reset index

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if Qt.Key.Key_1.value <= key <= Qt.Key.Key_5.value:
            rating = key - Qt.Key.Key_0.value
            self.rate_current_video(rating)
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            # Play selected clip from the list
            selected_items = self.list_widget.selectedItems()
            if selected_items:
                item = selected_items[0]
                self.play_selected_video(item)
        elif key == Qt.Key.Key_Space:
            # Pause or resume the video
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
            else:
                self.player.play()

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.KeyPress and source is self.list_widget:
            key = event.key()
            if Qt.Key.Key_1.value <= key <= Qt.Key.Key_5.value:
                rating = key - Qt.Key.Key_0.value
                self.rate_current_video(rating)
                return True
            elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                # Play selected clip from the list
                selected_items = self.list_widget.selectedItems()
                if selected_items:
                    item = selected_items[0]
                    self.play_selected_video(item)
                return True
            elif key == Qt.Key.Key_Space:
                # Pause or resume the video
                if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                    self.player.pause()
                else:
                    self.player.play()
                return True
        return super().eventFilter(source, event)

    def rate_current_video(self, rating):
        if 0 <= self.current_index < len(self.video_list):
            video_path = self.video_list[self.current_index]
            output_folder = os.path.join(os.getcwd(), str(rating))
            os.makedirs(output_folder, exist_ok=True)
            dest_path = os.path.join(output_folder, os.path.basename(video_path))
            if not os.path.exists(dest_path):
                try:
                    self.player.stop()  # Stop the player before moving the file
                    shutil.move(video_path, dest_path)
                except Exception as e:
                    print(f"Error moving file: {e}")
                    return
                # Update the path in video_list
                self.video_list[self.current_index] = dest_path
                # Update the processed_videos dict
                if video_path in self.processed_videos:
                    del self.processed_videos[video_path]
                self.processed_videos[dest_path] = rating
                self.save_json()
                # Update the item text
                item = self.list_widget.item(self.current_index)
                item.setText(os.path.basename(dest_path) + ' ' + '★' * rating)
                # Update the player's source to the new file path
                self.player.setSource(QUrl.fromLocalFile(dest_path))
            # if self.autoplay_checkbox.isChecked():
            #     self.play_next_video()

    def load_json(self):
        if os.path.exists(self.json_file):
            with open(self.json_file, 'r') as f:
                self.processed_videos = json.load(f)

    def save_json(self):
        with open(self.json_file, 'w') as f:
            json.dump(self.processed_videos, f)

    def position_changed(self, position):
        self.position_slider.setValue(position)

    def duration_changed(self, duration):
        self.position_slider.setRange(0, duration)

    def set_position(self, position):
        self.player.setPosition(position)

    def media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.autoplay_checkbox.isChecked():
                self.play_next_video()
        elif status == QMediaPlayer.MediaStatus.LoadedMedia and self.awaiting_media_load:
            # Media is loaded, set position to 0 and pause
            self.player.setPosition(0)
            self.player.pause()
            self.awaiting_media_load = False  # Reset the flag

    def handle_error(self):
        print("Error:", self.player.errorString())

    def playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.stop_button.setEnabled(True)
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.play_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_button.setEnabled(True)
        else:
            self.play_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_button.setEnabled(False)

    # New method to handle item selection changes
    def on_item_selection_changed(self):
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            item = selected_items[0]
            index = self.list_widget.row(item)
            self.current_index = index
            self.load_video_at_index(index)

    # New method to load video without playing
    def load_video_at_index(self, index):
        if 0 <= index < len(self.video_list):
            video_path = self.video_list[index]
            self.player.setSource(QUrl.fromLocalFile(video_path))
            self.awaiting_media_load = True  # Set the flag to wait for media load

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VideoRanker()
    window.show()
    sys.exit(app.exec())
