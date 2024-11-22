import sys
import os
import subprocess
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsRectItem,
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QGraphicsVideoItem
from PyQt6.QtCore import QUrl, Qt, QRectF, QTimer
from PyQt6.QtGui import QFont, QColor


class VideoPlayer(QMainWindow):
    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path

        # Initialize variables
        self.playlist = []
        self.clip_durations = []
        self.cumulative_durations = []
        self.total_time = 0  # in milliseconds
        self.fps = 25  # Frames per second for timecode calculation

        # Flag to alternate between concatenated videos
        self.current_video_index = 0  # 0 or 1

        # Load the initial playlist and clip durations
        self.load_playlist()

        # Create the graphics scene and view
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setStyleSheet("background: black")  # Set background color

        # Set the central widget
        self.setCentralWidget(self.view)

        # Create the video item
        self.video_item = QGraphicsVideoItem()
        self.scene.addItem(self.video_item)

        # Create text items for timecode and clip number
        self.timecode_item = QGraphicsTextItem()
        self.timecode_item.setDefaultTextColor(QColor("white"))
        self.timecode_item.setFont(QFont("Courier", 24))
        self.timecode_item.setZValue(1)  # Ensure it's above the video
        self.scene.addItem(self.timecode_item)

        self.clip_number_item = QGraphicsTextItem()
        self.clip_number_item.setDefaultTextColor(QColor("white"))
        self.clip_number_item.setFont(QFont("Courier", 14))
        self.clip_number_item.setZValue(1)
        self.scene.addItem(self.clip_number_item)

        # Create background rectangles for text items
        self.timecode_bg = QGraphicsRectItem()
        self.timecode_bg.setBrush(QColor(0, 0, 0, 128))  # Semi-transparent black
        self.timecode_bg.setZValue(0.5)  # Behind the text items
        self.scene.addItem(self.timecode_bg)

        self.clip_number_bg = QGraphicsRectItem()
        self.clip_number_bg.setBrush(QColor(0, 0, 0, 128))
        self.clip_number_bg.setZValue(0.5)
        self.scene.addItem(self.clip_number_bg)

        # Create media player
        self.current_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.current_player.setAudioOutput(self.audio_output)

        # Set the video output to the video item
        self.current_player.setVideoOutput(self.video_item)

        # Connect signals for the current player
        self.current_player.positionChanged.connect(self.update_overlays)
        self.current_player.mediaStatusChanged.connect(self.media_status_changed)

        # Start playing the video
        self.play_video()

    def load_playlist(self):
        # Get list of video files in folder, sorted alphabetically
        files = os.listdir(self.folder_path)
        video_files = [
            f
            for f in files
            if f.lower().endswith((".mp4", ".avi", ".mov", ".mkv", ".wmv"))
            and not f.startswith("concatenated_video_")  # Exclude concatenated videos
        ]
        video_files.sort()
        self.playlist = video_files
        self.clip_durations = []
        for video_file in self.playlist:
            video_path = os.path.join(self.folder_path, video_file)
            duration = self.get_video_duration(video_path)
            self.clip_durations.append(duration)
        # Compute cumulative durations
        self.cumulative_durations = [0]
        for duration in self.clip_durations:
            self.cumulative_durations.append(self.cumulative_durations[-1] + duration)
        self.total_time = self.cumulative_durations[-1]
        # Create the concatenated video
        self.create_concatenated_video()

    def create_concatenated_video(self):
        # Alternate between two video files
        self.current_video_index = 1 - self.current_video_index  # Switch between 0 and 1
        concatenated_video_name = f"concatenated_video_{self.current_video_index}.mp4"
        self.concatenated_video_path = os.path.join(self.folder_path, concatenated_video_name)

        # Create a temporary filelist for ffmpeg
        filelist_path = os.path.join(self.folder_path, f"filelist_{self.current_video_index}.txt")
        with open(filelist_path, "w") as f:
            for video_file in self.playlist:
                video_path = os.path.join(self.folder_path, video_file)
                f.write(f"file '{video_path}'\n")
        # Run ffmpeg to concatenate videos
        command = [
            "ffmpeg",
            "-y",  # overwrite output file if exists
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            filelist_path,
            "-c",
            "copy",
            self.concatenated_video_path,
        ]
        subprocess.run(command)

    def get_video_duration(self, video_file_path):
        # Use ffprobe to get video duration
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_file_path,
        ]
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        duration = float(result.stdout)
        return duration * 1000  # Convert to milliseconds

    def play_video(self):
        # Set the source to the concatenated video
        concatenated_video_name = f"concatenated_video_{self.current_video_index}.mp4"
        self.concatenated_video_path = os.path.join(self.folder_path, concatenated_video_name)
        url = QUrl.fromLocalFile(self.concatenated_video_path)
        self.current_player.setSource(url)
        self.current_player.play()

    def update_overlays(self, position):
        # position is in milliseconds
        total_elapsed_ms = position  # Since we have a single video, total_elapsed_ms is position

        # Convert to timecode format (HH:MM:SS:FF)
        hours, remainder = divmod(total_elapsed_ms // 1000, 3600)
        minutes, seconds = divmod(remainder, 60)
        frames = int((total_elapsed_ms % 1000) * self.fps / 1000)

        total_time = self.total_time  # Total time of the concatenated video

        t_hours, t_remainder = divmod(total_time // 1000, 3600)
        t_minutes, t_seconds = divmod(t_remainder, 60)
        t_frames = int((total_time % 1000) * self.fps / 1000)

        timecode = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}:{int(frames):02d}" + "/" + f"{int(t_hours):02d}:{int(t_minutes):02d}:{int(t_seconds):02d}:{int(t_frames):02d}"
        self.timecode_item.setPlainText(timecode)

        # Determine the current clip index
        clip_index = 0
        while (
            clip_index < len(self.cumulative_durations) - 1
            and total_elapsed_ms >= self.cumulative_durations[clip_index + 1]
        ):
            clip_index += 1

        # Update clip number label
        clip_info = f"{clip_index + 1} / {len(self.playlist)}"
        self.clip_number_item.setPlainText(clip_info)

        # Adjust background rectangles to match text items
        self.timecode_item.update()
        timecode_rect = self.timecode_item.boundingRect()
        self.timecode_bg.setRect(
            self.timecode_item.x(),
            self.timecode_item.y(),
            timecode_rect.width(),
            timecode_rect.height(),
        )

        self.clip_number_item.update()
        clip_number_rect = self.clip_number_item.boundingRect()
        self.clip_number_bg.setRect(
            self.clip_number_item.x(),
            self.clip_number_item.y(),
            clip_number_rect.width(),
            clip_number_rect.height(),
        )

    def media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            # Rescan the folder and rebuild the playlist
            self.load_playlist()
            # Delay playing to allow ffmpeg to finish writing the file
            QTimer.singleShot(1000, self.play_video)  # Wait 1 second before replaying

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        elif event.key() == Qt.Key.Key_F3:
            # Toggle visibility of overlays
            visible = self.timecode_item.isVisible()
            self.timecode_item.setVisible(not visible)
            self.timecode_bg.setVisible(not visible)
            self.clip_number_item.setVisible(not visible)
            self.clip_number_bg.setVisible(not visible)
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.view.viewport().width()
        h = self.view.viewport().height()

        # Resize the scene rect
        self.scene.setSceneRect(0, 0, w, h)

        # Resize the video item to fill the scene
        self.video_item.setSize(QRectF(0, 0, w, h).size())

        # Position the timecode_item at bottom center
        self.timecode_item.update()
        timecode_rect = self.timecode_item.boundingRect()
        self.timecode_item.setPos(
            (w - timecode_rect.width()) / 2, h - timecode_rect.height() - 20
        )
        self.timecode_bg.setRect(
            self.timecode_item.x(),
            self.timecode_item.y(),
            timecode_rect.width(),
            timecode_rect.height(),
        )

        # Position the clip_number_item at top right
        self.clip_number_item.update()
        clip_number_rect = self.clip_number_item.boundingRect()
        self.clip_number_item.setPos(w - clip_number_rect.width() - 100, 20)
        self.clip_number_bg.setRect(
            self.clip_number_item.x(),
            self.clip_number_item.y(),
            clip_number_rect.width(),
            clip_number_rect.height(),
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    folder_path = '/path/to/videos'  # Replace with the path to your folder
    player = VideoPlayer(folder_path)
    player.showFullScreen()
    sys.exit(app.exec())
