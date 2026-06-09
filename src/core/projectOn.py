"""
This file and all files contained within this distribution are parts of the ProjectOn worship projection software.

ProjectOn v.1.10.0.011
Written by Jeremy G Wilson

ProjectOn is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License (GNU GPL)
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import base64
import threading
import json
import logging
import os.path
import shutil
import socket
import sqlite3
import sys
import time
import traceback
import zipfile
from datetime import datetime
from os.path import exists
from xml.etree import ElementTree

from PyQt5.QtCore import Qt, QThreadPool, pyqtSignal, QObject, QPoint, QCoreApplication, QtMsgType, \
    QByteArray, QBuffer, QIODevice, qInstallMessageHandler
from PyQt5.QtGui import QPixmap, QFont, QPainter, QBrush, QColor, QPen, QIcon
from PyQt5.QtMultimedia import QMediaPlayer
from PyQt5.QtWidgets import QApplication, QLabel, QListWidgetItem, QWidget, QVBoxLayout, QFileDialog, QMessageBox, \
    QProgressBar, QHBoxLayout, QDialog, QLineEdit, QPushButton, QAction, QTreeWidgetItem

from dataHandling.declarations import SLIDE_DATA_DEFAULTS, SQL_COLUMN_TO_DICTIONARY_SONG, \
    SLIDE_DICTIONARY_TO_CUSTOM_SQL_COLUMN, SLIDE_DICTIONARY_TO_SONG_SQL_COLUMN, DB_STRUCTURE, SLIDE_DATA_DATA_TYPES, \
    SQL_COLUMN_TO_DICTIONARY_CUSTOM
from guiElements.gui import GUI
from core.runnables import SaveSettings, ServerCheckTimer
from guiElements.widgets.widgets import SimpleSplash, StandardItemWidget
from core.webRemote import RemoteServer


class ProjectOn(QObject):
    """
    Main entry point of the program. Loads necessary configuration information, starts the GUI and its QApplication,
    starts the web server.
    """
    app = None
    data_dir = None
    user_dir = None
    config_file = None
    database = None
    background_dir = None
    image_dir = None
    bible_dir = None
    video_dir = None
    get_scripture = None
    settings = {}
    remote_server = None
    splash_widget = None
    status_label = None
    update_status_signal = pyqtSignal(str, str)
    info_label = None
    initial_startup = True
    image_items = None
    logo_items = None
    thread_pool = None
    status_update_count = 0
    updating_label = False
    server_check_timer = None

    def __init__(self):
        super().__init__()
        sys.excepthook = log_unhandled_exception

        ########## For Debugging, not necessary in production ##########
        def qt_message_handler(mode, context, message):
            # Only intercept warnings (QtWarningMsg is 1)
            if mode == QtMsgType.QtWarningMsg:
                print(f"\n--- Qt Warning Intercepted ---")
                print(f"Message: {message}")
                print("Locating source...")
                traceback.print_stack()
                print("-----------------------------\n")

        # Install the handler at the very start of your script
        #qInstallMessageHandler(qt_message_handler)
        ################################################################

        # ensure we are working from the source root of the program
        self.file_dir = os.path.dirname(os.path.dirname(__file__))
        os.chdir(self.file_dir)

        if sys.platform == 'win32':
            os.environ['QT_MULTIMEDIA_PREFERRED_PLUGINS'] = 'windowsmediafoundation'

        os.environ['QTWEBENGINE_DISABLE_SANDBOX'] = '1'
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
            "--ignore-gpu-blacklist "
            "--enable-native-gpu-memory-buffers "
            "--disable-gpu-sandbox "  # can help on some setups
            "--enable-accelerated-video-decode "
            "--enable-features=ExperimentalJavaScript"
        )
        
        self.app = QApplication(sys.argv)

        self.thread_pool = QThreadPool()
        self.update_status_signal.connect(self.update_status_label)

        self.update_status_signal.emit('Creating Socket', 'status')
        self.app.processEvents()

        # create a web socket to be used for sending data to/from the remote and stage view servers
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('192.255.255.255', 1))
        self.ip = s.getsockname()[0]
        self.port = 15171

        self.update_status_signal.emit('Creating GUI', 'status')
        self.app.processEvents()

        self.gui = GUI(self)

        self.update_status_signal.emit('Starting Remote Server', 'status')
        self.app.processEvents()

        self.remote_server = RemoteServer(self.gui)
        self.server_thread = threading.Thread(target=self.remote_server.start_server, daemon=True)
        self.server_thread.start()

        self.splash_widget.deleteLater()
        self.settings['last_status_count'] = self.status_update_count
        self.initial_startup = False

        # load a service file if given at runtime
        for arg in sys.argv:
            if '.pro' in arg:
                self.load_service(arg)

        #self.app.processEvents()

        self.server_check_timer = ServerCheckTimer(self.remote_server, self.gui)
        self.server_check_timer.start()

        self.app.exec()

    def update_status_label(self, text: str, update_type: str):
        """
        Updates the splash widget with the given text.
        :param str text: The text to be displayed
        :param str update_type: Use 'status' if this will be an update to the status text under the main text
        """
        # just in case
        if not self.initial_startup:
            return

        if self.splash_widget and not self.updating_label: # prevent access violation by ensuring processEvents has finished
            self.updating_label = True
            if update_type == 'status':
                self.status_label.setText(text)
            else:
                self.info_label.setText(text)

            self.progress_bar.setValue(self.progress_bar.value() + 1)
            self.app.processEvents()
            self.updating_label = False
            self.status_update_count += 1

    def make_splash_screen(self, last_status_count: int):
        """
        Create the splash screen that will show progress as the program is loading
        :param int last_status_count: The total number of update calls last time the program was run; used for setting
        the upper range of the QProgressBar
        """
        self.splash_widget = QWidget()
        self.splash_widget.setObjectName('splash_widget')
        self.splash_widget.setMinimumWidth(610)
        self.splash_widget.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.splash_widget.setStyleSheet(
            '#splash_widget { background: #6060c0; }')
        splash_layout = QHBoxLayout(self.splash_widget)
        splash_layout.setContentsMargins(20, 20, 20, 20)

        icon_widget = QWidget()
        icon_layout = QVBoxLayout(icon_widget)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        splash_layout.addWidget(icon_widget)

        icon_label = QLabel()
        icon_label.setStyleSheet('background: #6060c0')
        icon_label.setPixmap(
            QPixmap('resources/branding/logo.svg').scaled(
                160, 160, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))
        icon_layout.addWidget(icon_label)

        version_label = QLabel('v.1.10.0.011')
        version_label.setStyleSheet('color: white')
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(version_label, Qt.AlignmentFlag.AlignCenter)

        container = QWidget()
        container.setObjectName('container')
        container.setStyleSheet('background: #6060c0')
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(20, 20, 20, 20)
        splash_layout.addWidget(container)

        self.title_label = QLabel('Starting ProjectOn...')
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet('color: white')
        self.title_label.setFont(QFont('Helvetica', 16, QFont.Weight.Bold))
        container_layout.addWidget(self.title_label, Qt.AlignmentFlag.AlignCenter)
        container_layout.addSpacing(20)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet('color: white')
        self.status_label.setFont(QFont('Helvetica', 12))
        container_layout.addWidget(self.status_label, Qt.AlignmentFlag.AlignCenter)
        container_layout.addSpacing(20)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(364)
        self.progress_bar.setRange(0, last_status_count)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            'QProgressBar { border: 1px solid white; background: white; } '
            'QProgressBar::chunk { background-color: #6060c0; }'
        )
        container_layout.addWidget(self.progress_bar)

        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet('color: white')
        self.info_label.setFont(QFont('Helvetica', 10))
        container_layout.addWidget(self.info_label)

        self.splash_widget.show()
        self.splash_widget.raise_()
        self.splash_widget.setFocus()

    def check_database_update(self) -> bool:
        """
        Method to check the current database version, updating the database if it's not current
        :return: True if up to date or update successful
        """
        connection = sqlite3.connect(self.database)
        cursor = connection.cursor()
        db_version = cursor.execute('PRAGMA user_version').fetchone()[0]

        if db_version == 2:
            # this is the most recent version
            connection.close()
            return True
        elif db_version > 2:
            QMessageBox.critical(
                None,
                'Database Mismatch',
                'Your database was created/updated by a newer verison of ProjectOn. Please install the newest '
                'version of ProjectOn and try again.'
            )
            sys.exit(-2)

        date = datetime.now().strftime('%Y-%m-%d_%H.%M.%S')
        db_backup_loc = f'{self.data_dir}/backups/projecton.{date}.db'
        QMessageBox.information(
            None,
            'Updating Database',
            f'Your database will be upgraded to the newest version. A backup of your old database will be created'
            f'at {db_backup_loc}'
        )

        if not exists(f'{self.data_dir}/backups'):
            os.mkdir(f'{self.data_dir}/backups')
        shutil.copy(self.database, db_backup_loc)

        # first, check for the second-most-recently added columns in the songs table
        result = cursor.execute('PRAGMA table_info(songs)').fetchall()
        columns = []
        for record in result:
            columns.append(record[1])

        if not 'shade_opacity' in columns:
            column_names = [
                ['use_shade', 'False'],
                ['shade_color', '0'],
                ['shade_opacity', '75']
            ]
            for name in column_names:
                cursor.execute(f'ALTER TABLE songs ADD {name[0]} TEXT;')
                cursor.execute(f'UPDATE songs SET {name[0]}={str(name[1])}')
            connection.commit()

        # check for the 'folder' column in the songs table
        if not 'folder' in columns:
            cursor.execute('ALTER TABLE songs ADD folder TEXT default "";')
            connection.commit()

        # check for the 'folder' column in the customSlides table
        result = cursor.execute('PRAGMA table_info(customSlides)').fetchall()
        columns = []
        for record in result:
            columns.append(record[1])

        if not 'folder' in columns:
            cursor.execute('ALTER TABLE customSlides ADD folder TEXT default "";')
            cursor.execute('UPDATE customSlides SET folder="";')
            connection.commit()

        # check for the 'folder' column in the imageThumbnails table
        result = cursor.execute('PRAGMA table_info(imageThumbnails)').fetchall()
        columns = []
        for record in result:
            columns.append(record[1])

        if not 'folder' in columns:
            cursor.execute('ALTER TABLE imageThumbnails ADD folder TEXT default "";')
            connection.commit()

        # check that the videos table exists
        result = cursor.execute(f'SELECT name FROM sqlite_schema WHERE type="table" AND name="videos";').fetchall()
        if len(result) == 0:
            cursor.execute('CREATE TABLE videos (filename TEXT DEFAULT "", thumbnail BLOB, folder TEXT DEFAULT "");')

        files = os.listdir(self.video_dir)
        for file in files:
            video_file = None
            if file.endswith('.jpg'):
                name_only = file.split('.')[0]
                for other_file in files:
                    if other_file.startswith(name_only) and not other_file.endswith('.jpg'):
                        video_file = other_file

                if video_file:
                    pixmap = QPixmap(self.video_dir + '/' + file)
                    pixmap = pixmap.scaled(96, 54, Qt.AspectRatioMode.IgnoreAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation)

                    array = QByteArray()
                    buffer = QBuffer(array)
                    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                    pixmap.save(buffer, 'JPG')
                    blob = bytes(array.data())

                    sql = 'INSERT INTO videos (filename, thumbnail, folder) VALUES (?, ?, ?)'
                    cursor.execute(sql, (video_file, blob, ''))
                    connection.commit()

        # check for the 'folder' column in the web table
        result = cursor.execute('PRAGMA table_info(web)').fetchall()
        columns = []
        for record in result:
            columns.append(record[1])

        if not 'folder' in columns:
            cursor.execute('ALTER TABLE web ADD folder TEXT default "";')
            connection.commit()

        cursor.execute('PRAGMA user_version = 2')
        connection.commit()
        connection.close()

        return True

    def get_all_songs(self) -> list[str]:
        """
        Retrieves all song data from the ProjectOn database's 'songs' table
        :return: list[str]: all songs and their data
        """
        connection = None
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()

            result = cursor.execute('SELECT * FROM songs ORDER BY title').fetchall()

            # there's been enough variation in how data is stored across versions that we're going to
            # convert the stored sql data to the standardized slide data, including making sure the
            # data types are standardized in each dictionary
            all_songs = []
            for song in result:
                data = SLIDE_DATA_DEFAULTS.copy()
                data['type'] = 'song'
                for i in range(len(song)):
                    if 'global' in str(song[i]):
                        data[SQL_COLUMN_TO_DICTIONARY_SONG[i]] = song[i]
                    elif song[i] is not None and type(song[i]) is not int and song[i].lower() == 'true':
                        data[SQL_COLUMN_TO_DICTIONARY_SONG[i]] = True
                    elif song[i] is not None and type(song[i]) is not int and song[i].lower() == 'false':
                        data[SQL_COLUMN_TO_DICTIONARY_SONG[i]] = False
                    elif song[i] is not None:
                        data[SQL_COLUMN_TO_DICTIONARY_SONG[i]] = SLIDE_DATA_DATA_TYPES[SQL_COLUMN_TO_DICTIONARY_SONG[i]](song[i])
                all_songs.append(data)

            return all_songs
        except Exception:
            self.error_log()
            if connection:
                connection.close()
            return -1

    def get_all_custom_slides(self) -> list[str]:
        """
        Retrieves all custom slide data from the ProjectOn database's 'customSlides' table
        :return: list[str] all custom slides and their data
        """
        connection = None
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()

            result = cursor.execute('SELECT * FROM customSlides ORDER BY title').fetchall()

            # there's been enough variation in how data is stored across versions that we're going to
            # convert the stored sql data to the standardized slide data, including making sure the
            # data types are standardized in each dictionary
            all_custom = []
            for custom in result:
                data = SLIDE_DATA_DEFAULTS.copy()
                data['type'] = 'custom'
                for i in range(len(custom)):
                    if 'global' in str(custom[i]):
                        data[SQL_COLUMN_TO_DICTIONARY_CUSTOM[i]] = custom[i]
                    elif custom[i] is not None and type(custom[i]) is not int and custom[i].lower() == 'true':
                        data[SQL_COLUMN_TO_DICTIONARY_CUSTOM[i]] = True
                    elif custom[i] is not None and type(custom[i]) is not int and custom[i].lower() == 'false':
                        data[SQL_COLUMN_TO_DICTIONARY_CUSTOM[i]] = False
                    elif custom[i] is not None:
                        data[SQL_COLUMN_TO_DICTIONARY_CUSTOM[i]] = SLIDE_DATA_DATA_TYPES[SQL_COLUMN_TO_DICTIONARY_CUSTOM[i]](custom[i])
                all_custom.append(data)
            connection.close()
            return all_custom
        except Exception:
            self.error_log()
            if connection:
                connection.close()
            return -1

    def get_all_images(self) -> list | int:
        """
        Retrieves all image data from the ProjectOn database's 'images' table
        :return: list: all images and their data or -1 on exception
        """
        connection = None
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()
            result = cursor.execute('SELECT * FROM imageThumbnails ORDER BY fileName COLLATE NOCASE ASC').fetchall()

            all_images = []
            for image in result:
                data = SLIDE_DATA_DEFAULTS.copy()
                data['type'] = 'image'
                data['title'] = image[0]
                pixmap = QPixmap()
                pixmap.loadFromData(image[1], 'jpg')
                data['background'] = pixmap
                data['folder'] = image[2]
                all_images.append(data)
            connection.close()
            return all_images
        except Exception:
            self.error_log()
            if connection:
                connection.close()
            return -1

    def get_all_videos(self) -> list | int:
        """
        Retrieves all video data from the ProjectOn database's 'videos' table
        :return: list of all videos and their data or -1 on exception
        """
        connection = None
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()
            result = cursor.execute('SELECT * FROM videos').fetchall()
            all_videos = []
            for video in result:
                data = SLIDE_DATA_DEFAULTS.copy()
                data['type'] = 'video'
                data['title'] = video[0]
                data['file_name'] = video[0]
                data['folder'] = video[2]
                data['use_footer'] = False

                pixmap = QPixmap()
                pixmap.loadFromData(video[1], 'jpg')
                data['background'] = pixmap

                all_videos.append(data)
            return all_videos
        except Exception:
            self.error_log()
            if connection:
                connection.close()
            return -1

    def get_all_web(self) -> list | int:
        """
        Retrieves all web page data from the ProjectOn database's 'web' table
        :return: list of all web pages and their data or -1 on exception
        """
        connection = None
        all_web = []
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()
            results = cursor.execute('SELECT * FROM web').fetchall()
            connection.close()

            for record in results:
                data = SLIDE_DATA_DEFAULTS.copy()
                data['type'] = 'web'
                data['title'] = record[0]
                data['url'] = record[1]
                data['folder'] = record[2]
                data['use_footer'] = False
                all_web.append(data)

            return all_web
        except Exception:
            self.error_log()
            if connection:
                connection.close()
            return -1

    def get_song_data(self, title: str) -> list[str] | int:
        """
        Gets the song data for a particular song where the 'title' column matches 'title'
        :param str title: the song title
        :return: list[str]: all columns for this song
        """
        connection = None
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()
            result = cursor.execute('SELECT * FROM songs WHERE title="' + title + '"').fetchone()
            connection.close()
            return result
        except Exception:
            self.error_log()
            if connection:
                connection.close()
            return -1

    def get_custom_data(self, title: str) -> list[str] | int:
        """
        Gets the song data for a particular custom slide where the 'title' column matches 'title'
        :param str title: the title (name) of the custom slide
        :return: list[str]: all columns for this custom slide
        """
        connection = None
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()
            result = cursor.execute('SELECT * FROM customSlides WHERE title="' + title + '"').fetchone()
            connection.close()
            return result
        except Exception:
            self.error_log()
            if connection:
                connection.close()
            return -1

    def get_folders(self, slide_type: str) -> list[str] | int:
        """
        Retrieves all the folders associated with items for this slide type
        :param slide_type: The type of slide
        :return: list[str] of all folders or -1 on exception, 0 if wrong slide_type
        """
        connection = None
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()
            if slide_type == 'song':
                result = cursor.execute('SELECT folder FROM songs').fetchall()
            elif slide_type == 'custom':
                result = cursor.execute('SELECT folder FROM customSlides').fetchall()
            elif slide_type == 'images':
                result = cursor.execute('SELECT folder FROM imageThumbnails').fetchall()
            elif slide_type == 'videos':
                result = cursor.execute('SELECT folder FROM videos').fetchall()
            elif slide_type == 'web':
                result = cursor.execute('SELECT folder FROM web').fetchall()
            else:
                connection.close()
                return 0
            connection.close()
        except Exception:
            if connection:
                connection.close()
            self.error_log()

        folders = set()
        for item in result:
            folder_name = item[0].strip()
            if len(folder_name) > 0:
                folders.add(folder_name)

        return list(folders)

    def get_audio_clip_names(self) -> list[str] | int:
        """
        Retrievers all info from the "name" column of the audio table
        :return: list[str]: all audio clip names or 0 on exception
        """
        connection = None
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()
            result = cursor.execute('SELECT "name" FROM "audio";').fetchall()
            connection.close()
            return result
        except Exception:
            self.error_log()
            if connection:
                connection.close()
            return -1

    def get_audio_data(self, name: str) -> list[str] | int:
        """
        Retrieves all the audio data for the given audio clip
        :param name: The name of the qudio clip
        :return: list[str]: all audio data or -1 on exception
        """
        connection = None
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()
            result = cursor.execute(f'SELECT data, format FROM audio WHERE name="{name}";').fetchone()
            if len(result) == 0:
                return -2
            connection.close()
            return result
        except Exception:
            self.error_log()
            if connection:
                connection.close()
            return -1

    def save_audio(self, name: str, audio_format: str, audio_data: bytes) -> int:
        """
        Saves an audio clip to the database
        :param str name: The name of the qudio clip
        :param str audio_format: The format the audio clip is rendered as
        :param bytes audio_data: The audio clip's data
        :return: int: 0 on success, -2 on failed execute, -1 on exception
        """
        connection = None
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()
            result = cursor.execute(f'SELECT "name" FROM "audio" WHERE "name"="{name}";').fetchall()
            if len(result) > 0:
                return -2
            cursor.execute(
                f'INSERT INTO audio (name, format, data) VALUES ("{name}", "{audio_format}", ?);', (audio_data,))
            connection.commit()
            connection.close()
            return 0
        except Exception:
            self.error_log()
            if connection:
                connection.close()
            return -1

    def copy_image(self, file: str):
        """
        Creates a copy of an image file chosen by the user and stores it in this program's data folder
        :param str file: the image's file name
        """
        try:
            file_split = file.split('/')
            file_name = file_split[len(file_split) - 1]

            if not exists(self.image_dir + '/' + file_name):
                shutil.copy(file, self.image_dir + '/' + file_name)
        except Exception:
            self.error_log()

    def save_song(self, data: dict, old_title: str=None):
        """
        Takes song data as a dictionary, converts the dictionary keys to the database's columns,
        and inserts or updates that data in the database.
        :param dict data: The song's data
        :param str old_title: Optional, the song's original title so that it can be updated instead of inserted
        """
        connection = None
        try:
            for key in data.keys():
                if type(data[key]) == str:
                    data[key] = data[key].replace('"', '""')

            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()

            # if old_title has been provided, this song already exists in the database and we need to use UPDATE
            if old_title:
                sql = 'UPDATE songs SET '
                for key in data.keys():
                    if key in SLIDE_DICTIONARY_TO_SONG_SQL_COLUMN.keys():
                        sql += f'{SLIDE_DICTIONARY_TO_SONG_SQL_COLUMN[key]}="{data[key]}",'
                sql = sql[:-1] + f' WHERE title="{old_title}";'
            else: # use INSERT INTO instead
                sql = 'INSERT INTO songs ('
                for key in data.keys():
                    if key in SLIDE_DICTIONARY_TO_SONG_SQL_COLUMN.keys():
                        sql += SLIDE_DICTIONARY_TO_SONG_SQL_COLUMN[key] + ','
                sql = sql[:-1] + ') VALUES ("'
                for key in data.keys():
                    if key in SLIDE_DICTIONARY_TO_SONG_SQL_COLUMN.keys():
                        sql += f'{data[key]}","'
                sql = sql[:-2] + ');'

            cursor.execute(sql)
            connection.commit()
            connection.close()
        except Exception:
            self.error_log()
            if connection:
                connection.close()

    def get_song_titles(self) -> list[str]:
        """
        Retrieves just the titles of all songs in the database.
        :return list[str]: list of song titles
        """
        connection = sqlite3.connect(self.database)
        cursor = connection.cursor()
        data = cursor.execute('SELECT title FROM songs ORDER BY title').fetchall()
        song_titles = []
        for item in data:
            song_titles.append(item[0])

        return song_titles

    def get_custom_titles(self) -> list[str]:
        """
        Retrieves just the titles of all custom slides in the database.
        :return list[str]: Custom slide titles
        """
        connection = sqlite3.connect(self.database)
        cursor = connection.cursor()
        data = cursor.execute('SELECT title FROM customSlides').fetchall()
        custom_titles = []
        for item in data:
            custom_titles.append(item[0])

        return custom_titles

    def save_custom(self, data: dict, old_title: str | None = None):
        """
        Takes custom slide data as a dict, converts the dictionary keys to the database's columns,
        and inserts or updates that data in the database.
        :param dict data: The custom slide's data in columnar order
        :param str old_title: Optional, the custom slide's original title so that it can be updated instead of inserted
        """
        connection = None

        try:
            for key in data.keys():
                if type(data[key]) == str:
                    data[key] = data[key].replace('"', '""')
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()

            # if old_title has been provided, this song already exists in the database and we need to use UPDATE
            if old_title:
                sql = 'UPDATE customSlides SET '
                for key in data.keys():
                    if key in SLIDE_DICTIONARY_TO_CUSTOM_SQL_COLUMN.keys():
                        sql += f'{SLIDE_DICTIONARY_TO_CUSTOM_SQL_COLUMN[key]}="{data[key]}",'
                sql = sql[:-1] + f' WHERE title="{old_title}";'
            else: # use INSERT INTO instead
                sql = 'INSERT INTO customSlides ('
                for key in data.keys():
                    if key in SLIDE_DICTIONARY_TO_CUSTOM_SQL_COLUMN.keys():
                        sql += SLIDE_DICTIONARY_TO_CUSTOM_SQL_COLUMN[key] + ','
                sql = sql[:-1] + ') VALUES ("'
                for key in data.keys():
                    if key in SLIDE_DICTIONARY_TO_CUSTOM_SQL_COLUMN.keys():
                        sql += f'{data[key]}","'
                sql = sql[:-2] + ');'

            cursor.execute(sql)
            connection.commit()
            connection.close()
        except Exception:
            self.error_log()
            if connection:
                connection.close()

    def save_image(self, data: dict, old_title: str | None = None):
        """
        Saves an image to the database by first scaling the image to a standardized thumbnail, then inserts or updates
        the database with the info in its dictionary
        :param dict data: The dictionary associated with the image
        :param old_title: optional: The title of an image already existant in the database
        :return: None
        """
        connection = None
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()
            for key in data.keys():
                if type(data[key]) == str:
                    data[key] = data[key].replace('"', '""')

            pixmap = data['background'].scaled(
                96,
                54,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            array = QByteArray()
            buffer = QBuffer(array)
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            pixmap.save(buffer, 'JPG')
            blob = bytes(array.data())

            # if old_title has been provided, this image already exists in the database and we need to use UPDATE
            if old_title:
                sql = (f'UPDATE imageThumbnails SET '
                       f'filename="{data["title"]}",'
                       f'image=?,'
                       f'folder="{data["folder"]}" '
                       f'WHERE filename="{old_title}";')

                cursor.execute(sql, (blob,))
                connection.commit()
                connection.close()
            else:  # use INSERT INTO instead

                sql = (f'INSERT INTO imageThumbnails (filename, image, folder) VALUES ('
                       f'"{data["title"]}",'
                       f'?,'
                       f'"{data["folder"]}");')
                cursor.execute(sql, (blob,))
                connection.commit()
                connection.close()

        except Exception:
            self.error_log()
            if connection:
                connection.close()

    def save_video(self, data: dict, old_title: str | None = None) -> int:
        """
        Saves a video to the database by first scaling the video to a standardized thumbnail, then inserts or updates
        the database with the info in its dictionary
        :param dict data: Dictionary associated with the video
        :param old_title: optional: The title of a video already existant in the database
        :return: int: 0 on success, -1 on exception
        """
        connection = None
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()

            array = QByteArray()
            buffer = QBuffer(array)
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            data['background'].save(buffer, 'JPG')
            blob = bytes(array.data())

            # if old_title has been provided, this video already exists in the database so we need to use UPDATE
            if old_title:
                sql = (f'UPDATE videos SET '
                       f'filename="{data["title"]}",'
                       f'thumbnail=?,'
                       f'folder="{data["folder"]}" '
                       f'WHERE filename="{old_title}";')

                cursor.execute(sql, (blob,))
                connection.commit()
                connection.close()
                return 0
            else:  # use INSERT INTO instead
                pixmap = data['background']
                array = QByteArray()
                buffer = QBuffer(array)
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                pixmap.save(buffer, 'JPG')
                blob = bytes(array.data())

                sql = (f'INSERT INTO videos (filename, thumbnail, folder) VALUES ('
                       f'"{data["title"]}",'
                       f'?,'
                       f'"{data["folder"]}");')
                cursor.execute(sql, (blob,))
                connection.commit()
                buffer.close()
                connection.close()
            return 0
        except Exception:
            self.error_log()
            return -1

    def save_web_item(self, data: dict, old_title: str | None = None) -> int:
        """
        Stores the title and url of a web slide to the program's database. Checks the database first to see if the
        given title already exists.
        :param dict data: The title of the web slide
        :param str old_title: The url the web slide is to fetch
        :param int: 0 on success, -1 on exception
        """
        connection = None
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()

            # if old_title has been provided, this web item already exists in the database and we need to use UPDATE
            if old_title:
                sql = (f'UPDATE web SET '
                       f'title="{data["title"]}",'
                       f'url="{data["url"]}",'
                       f'folder="{data["folder"]}" '
                       f'WHERE title="{old_title}";')

                cursor.execute(sql)
                connection.commit()
                connection.close()
            else:  # use INSERT INTO instead
                sql = (f'INSERT INTO web (title, url, folder) VALUES ('
                       f'"{data["title"]}",'
                       f'"{data["url"]}",'
                       f'"{data["folder"]}");')
                cursor.execute(sql)
                connection.commit()
                connection.close()
            return 0

        except Exception:
            self.error_log()
            if connection:
                connection.close()
            return -1

    def delete_items_from_db(self, items: set) -> int:
        """
        Provides a method of deleting a given item from the program's database.
        :param set items: Set of two-value tuples(type, title) to be removed
        :return: int: 0 on success, -1 on exception
        """
        connection = None
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()
            for item in items:
                no_command = False
                type, title = item
                table, column = '', ''
                if type == 'song':
                    table = 'songs'
                    column = 'title'
                elif type == 'custom':
                    table = 'customSlides'
                    column = 'title'
                elif type == 'image':
                    table = 'imageThumbnails'
                    column = 'filename'
                    os.remove(self.image_dir + '/' + title)
                elif type == 'video':
                    # first, check to see if this video is currently queued up; get rid of the media player if so
                    if (self.gui.live_widget.slide_list.item(0)
                            and self.gui.live_widget.slide_list.item(0).data(Qt.ItemDataRole.UserRole)['title'] == title):
                        # handle stopping the media player carefully to avoid an Access Violation
                        if self.gui.media_player:
                            if self.gui.media_player.state() == QMediaPlayer.PlayingState:
                                self.gui.media_player.stop()
                                if self.gui.timed_update:
                                    self.gui.timed_update.stop = True
                            self.gui.media_player.deleteLater()
                            self.gui.media_player = None
                            if self.gui.video_widget:
                                self.gui.video_widget.deleteLater()
                                self.gui.graphics_view.deleteLater()
                                self.gui.video_widget = None
                                self.gui.graphics_view = None
                        self.gui.live_widget.slide_list.clear()
                        self.gui.live_widget.preview_label.clear()
                        self.gui.live_widget.player_controls.hide()

                    # remove the video from the video directory as well as its snapshot image, if it exists
                    file_name = title
                    os.remove(self.video_dir + '/' + file_name)
                    filename_split = file_name.split('.')
                    thumbnail_filename = '.'.join(filename_split[:len(filename_split) - 1]) + '.jpg'
                    if exists(self.video_dir + '/' + thumbnail_filename):
                        os.remove(self.video_dir + '/' + thumbnail_filename)

                    table = 'videos'
                    column = 'filename'
                elif type == 'web':
                    table = 'web'
                    column = 'title'
                else:
                    no_command = True

                if not no_command:
                    cursor.execute(f'DELETE FROM {table} WHERE {column}="{title}"')
            connection.commit()
            connection.close()

            return 0
        except Exception:
            self.error_log()
            if connection:
                connection.close()

            return -1

    def delete_all_songs(self):
        """
        Provides a method for removing all of the songs from the database's 'songs' table. Checks and double-checks
        with the user that they really want to do this. Not currently accessible by the user.
        """
        result = QMessageBox.question(
            self.gui.main_window,
            'Really Delete?',
            'This will remove ALL SONGS from your database. This cannot be undone. Really DELETE ALL SONGS?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if result == QMessageBox.StandardButton.Yes:
            second_result = QMessageBox.question(
                self.gui.main_window,
                'Really Delete?',
                'Just making sure: Do you really want to DELETE ALL SONGS?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if not second_result == QMessageBox.StandardButton.Yes:
                return
        else:
            return

        connection = None
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()
            cursor.execute('DELETE FROM songs')
            connection.commit()
            connection.close()

            QMessageBox.information(
                self.gui.main_window,
                'Songs Deleted',
                'All songs have been removed.',
                QMessageBox.StandardButton.Ok
            )
            self.gui.media_widget.song_list.clear()
        except Exception:
            self.error_log()
            if connection:
                connection.close()

    def save_settings(self):
        """
        Saves all the settings currently stored in the self.settings dict to the settings.json file in the
        program's data directory by threading the SaveSettings class.
        """
        save_settings = SaveSettings(self)
        self.thread_pool.start(save_settings)

    def save_service(self):
        """
        Saves the user's current order of service to a file chosen by the user.
        """
        if self.gui.oos_widget.oos_list_widget.count() == 0:
            QMessageBox.information(
                self.gui.main_window,
                'Nothing to do',
                'There are no Order of Service items to save.',
                QMessageBox.StandardButton.Ok
            )
            return 0

        service_items = {
            'global_song_background': self.settings['global_song_background'],
            'global_bible_background': self.settings['global_bible_background'],
            'song_font_face': self.settings['song_font_face'],
            'song_font_size': self.settings['song_font_size'],
            'song_font_color': self.settings['song_font_color'],
            'song_use_shadow': self.settings['song_use_shadow'],
            'song_shadow_color': self.settings['song_shadow_color'],
            'song_shadow_offset': self.settings['song_shadow_offset'],
            'song_use_outline': self.settings['song_use_outline'],
            'song_outline_color': self.settings['song_outline_color'],
            'song_outline_width': self.settings['song_outline_width'],
            'song_use_shade': self.settings['song_use_shade'],
            'song_shade_color': self.settings['song_shade_color'],
            'song_shade_opacity': self.settings['song_shade_opacity'],
            'bible_font_face': self.settings['bible_font_face'],
            'bible_font_size': self.settings['bible_font_size'],
            'bible_font_color': self.settings['bible_font_color'],
            'bible_use_shadow': self.settings['bible_use_shadow'],
            'bible_shadow_color': self.settings['bible_shadow_color'],
            'bible_shadow_offset': self.settings['bible_shadow_offset'],
            'bible_use_outline': self.settings['bible_use_outline'],
            'bible_outline_color': self.settings['bible_outline_color'],
            'bible_outline_width': self.settings['bible_outline_width'],
            'bible_use_shade': self.settings['bible_use_shade'],
            'bible_shade_color': self.settings['bible_shade_color'],
            'bible_shade_opacity': self.settings['bible_shade_opacity']
        }

        for i in range(self.gui.oos_widget.oos_list_widget.count()):
            item_data = self.gui.oos_widget.oos_list_widget.item(i).data(Qt.ItemDataRole.UserRole)
            service_items[i] = {
                'title': item_data['title'],
                'type': item_data['type']
            }
            if self.gui.oos_widget.oos_list_widget.item(i).data(Qt.ItemDataRole.UserRole)['type'] == 'custom_bible':
                service_items[i]['text'] = item_data['parsed_text']
            elif self.gui.oos_widget.oos_list_widget.item(i).data(Qt.ItemDataRole.UserRole)['type'] == 'custom':
                service_items[i]['text'] = item_data['parsed_text']

        result = self.complete_save(service_items, 'pro')
        return result

    def save_frozen_service(self):
        """
        Saves the user's current order of service as well as each item's full dataset so that it preserves the slides
        exactly as they are, ignoring any changes made in the program apart from the service.
        """

        if self.gui.oos_widget.oos_list_widget.count() == 0:
            QMessageBox.information(
                self.gui.main_window,
                'Nothing to do',
                'There are no Order of Service items to save.',
                QMessageBox.StandardButton.Ok
            )
            return 0

        service_items = {
            'global_song_background': self.settings['global_song_background'],
            'global_bible_background': self.settings['global_bible_background'],
            'song_font_face': self.settings['song_font_face'],
            'song_font_size': self.settings['song_font_size'],
            'song_font_color': self.settings['song_font_color'],
            'song_use_shadow': self.settings['song_use_shadow'],
            'song_shadow_color': self.settings['song_shadow_color'],
            'song_shadow_offset': self.settings['song_shadow_offset'],
            'song_use_outline': self.settings['song_use_outline'],
            'song_outline_color': self.settings['song_outline_color'],
            'song_outline_width': self.settings['song_outline_width'],
            'song_use_shade': self.settings['song_use_shade'],
            'song_shade_color': self.settings['song_shade_color'],
            'song_shade_opacity': self.settings['song_shade_opacity'],
            'bible_font_face': self.settings['bible_font_face'],
            'bible_font_size': self.settings['bible_font_size'],
            'bible_font_color': self.settings['bible_font_color'],
            'bible_use_shadow': self.settings['bible_use_shadow'],
            'bible_shadow_color': self.settings['bible_shadow_color'],
            'bible_shadow_offset': self.settings['bible_shadow_offset'],
            'bible_use_outline': self.settings['bible_use_outline'],
            'bible_outline_color': self.settings['bible_outline_color'],
            'bible_outline_width': self.settings['bible_outline_width'],
            'bible_use_shade': self.settings['bible_use_shade'],
            'bible_shade_color': self.settings['bible_shade_color'],
            'bible_shade_opacity': self.settings['bible_shade_opacity']
        }

        for i in range(self.gui.oos_widget.oos_list_widget.count()):
            service_items[i] = self.gui.oos_widget.oos_list_widget.item(i).data(Qt.ItemDataRole.UserRole)
            for key in service_items[i].keys():
                if type(service_items[i][key]) == QPixmap:
                    byte_array = QByteArray()
                    buffer = QBuffer(byte_array)
                    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                    service_items[i][key].save(buffer, "PNG")
                    raw_bytes = byte_array.data()
                    base64_bytes = base64.b64encode(raw_bytes)
                    base64_string = base64_bytes.decode('utf-8')
                    service_items[i][key] = base64_string

        result = self.complete_save(service_items, 'proj')
        return result

    def complete_save(self, service_items, file_type):
        if len(self.settings['last_save_dir']) > 0:
            save_dir = os.path.expanduser(self.settings['last_save_dir'])
        else:
            save_dir = os.path.expanduser('~' + '/Documents')

        if self.gui.current_file and self.gui.current_file.endswith(file_type):
            file_loc = self.gui.current_file
        else:
            if file_type == 'proj':
                QMessageBox.information(
                    self.gui.main_window,
                    'Save Fixed Service',
                    'This will lock the current slide content directly into the file. '
                    'Any future changes you make to these items in your library will not affect this specific service. '
                    'Fixed services are saved with a ".proj" extension.',
                    QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
                )
            type_text = 'Service'
            if file_type == 'proj':
                type_text = 'Fixed Service'
            result = QFileDialog.getSaveFileName(
                self.gui.main_window,
                'Save Service File',
                save_dir,
                f'ProjectOn {type_text} File (*.{file_type})')
            if len(result[0]) == 0:
                return -1
            file_loc = result[0]
            if not file_loc.endswith(file_type):
                file_loc += f'.{file_type}'

        try:
            with open(file_loc, 'w') as file:
                json.dump(service_items, file, indent=4)

            directory = os.path.dirname(file_loc)
            filename = file_loc.replace(directory, '').replace('/', '')
            self.settings['last_save_dir'] = directory
            self.save_settings()

            QMessageBox.information(
                self.gui.main_window,
                'File Saved',
                'Service saved as\n' + file_loc.replace('/', '\\'),
                QMessageBox.StandardButton.Ok
            )

            # add this file to the recently used services menu
            self.add_to_recently_used(directory, filename)

            self.gui.current_file = file_loc
            self.gui.changes = False
            self.gui.main_window.setWindowTitle(f'ProjectOn - {filename}')
            return 0
        except Exception as ex:
            QMessageBox.information(
                self.gui.main_window,
                'Save Error',
                'There was a problem saving the service: '
                + file_loc.replace('/', '\\') + '\n\n' + str(ex),
                QMessageBox.StandardButton.Ok
            )
            return -1

    def load_service(self, filename: str | None = None):
        """
        Provides a method for loading an order of service from a service file. Will open a file dialog to the user's
        last-accessed directory (if available) if a filename is not supplied.
        :param str filename: Optional, the file location to be opened
        """
        # first, check for any changes to the current order of service
        response = -1
        if self.gui.changes:
            response = QMessageBox.question(
                self.gui.main_window,
                'Save Changes',
                'Changes have been made. Save changes?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )

        save_result = 1
        if response == QMessageBox.StandardButton.Cancel:
            return
        elif response == QMessageBox.StandardButton.Yes:
            save_result = self.save_service()

        if save_result == -1:
            return

        # open a file dialog if filename was not provided
        if not filename:
            if len(self.settings['last_save_dir']) > 0:
                open_dir = self.settings['last_save_dir']
            else:
                open_dir = os.path.expanduser('~' + '/Documents')

            result = QFileDialog.getOpenFileName(
                self.gui.main_window,
                'Load Service File',
                open_dir,
                'ProjectOn Service Files (*.pro *.proj)'
            )
        else:
            result = [filename]

        if len(result[0]) > 0:
            self.finish_load(result[0])

    def finish_load(self, filename):
        self.gui.oos_widget.oos_list_widget.clear()

        # because songs and bible verses are parsed as the order of service is being loaded, and this can take a bit,
        # provide a splash
        wait_widget = SimpleSplash(self.gui, 'Loading service...')
        service_dict = None
        try:
            with open(filename, 'r') as file:
                service_dict = json.load(file)
            if not service_dict:
                QMessageBox.information(
                    self.gui.main_window,
                    'Error Loading Service',
                    'Unable to load service. Please check that the file has not moved.',
                    QMessageBox.StandardButton.Ok
                )
                return
        except Exception:
            self.error_log()
            return

        # change the background and font options in the current settings
        if 'global_song_background' in service_dict.keys():
            self.settings['global_song_background'] = service_dict['global_song_background']
            self.gui.global_song_background_pixmap = QPixmap(
                self.background_dir + '/' + self.settings['global_song_background'])
        if 'global_bible_background' in service_dict.keys():
            self.settings['global_bible_background'] = service_dict['global_bible_background']
            self.gui.global_bible_background_pixmap = QPixmap(
                self.background_dir + '/' + self.settings['global_bible_background'])

        slide_types = ['song', 'bible']
        for slide_type in slide_types:
            if f'{slide_type}_font_face' in service_dict.keys():
                self.settings[f'{slide_type}_font_face'] = service_dict[f'{slide_type}_font_face']
            if f'{slide_type}_font_size' in service_dict.keys():
                self.settings[f'{slide_type}_font_size'] = service_dict[f'{slide_type}_font_size']
            if f'{slide_type}_font_color' in service_dict.keys():
                self.settings[f'{slide_type}_font_color'] = service_dict[f'{slide_type}_font_color']
            if f'{slide_type}_use_shadow' in service_dict.keys():
                self.settings[f'{slide_type}_use_shadow'] = service_dict[f'{slide_type}_use_shadow']
            if f'{slide_type}_shadow_color' in service_dict.keys():
                self.settings[f'{slide_type}_shadow_color'] = service_dict[f'{slide_type}_shadow_color']
            if f'{slide_type}_shadow_offset' in service_dict.keys():
                self.settings[f'{slide_type}_shadow_offset'] = service_dict[f'{slide_type}_shadow_offset']
            if f'{slide_type}_use_outline' in service_dict.keys():
                self.settings[f'{slide_type}_use_outline'] = service_dict[f'{slide_type}_use_outline']
            if f'{slide_type}_outline_color' in service_dict.keys():
                self.settings[f'{slide_type}_outline_color'] = service_dict[f'{slide_type}_outline_color']
            if f'{slide_type}_outline_width' in service_dict.keys():
                self.settings[f'{slide_type}_outline_width'] = service_dict[f'{slide_type}_outline_width']
            if f'{slide_type}_use_shade' in service_dict.keys():
                self.settings[f'{slide_type}_use_shade'] = service_dict[f'{slide_type}_use_shade']
            if f'{slide_type}_shade_color' in service_dict.keys():
                self.settings[f'{slide_type}_shade_color'] = service_dict[f'{slide_type}_shade_color']
            if f'{slide_type}_shade_opacity' in service_dict.keys():
                self.settings[f'{slide_type}_shade_opacity'] = service_dict[f'{slide_type}_shade_opacity']

        # handle the loading differently depending on whether this is a standard service file or a frozen service file
        if filename.endswith('.pro'):
            def make_missing_item(slide_type: str, title: str):
                # Creates a placeholder list widget item when a saved item is not found
                QMessageBox.information(
                    None,
                    'Song Missing',
                    f'Saved {slide_type} "{title}" not found in current database. '
                    f'Inserting placeholder.',
                    QMessageBox.StandardButton.Ok
                )

                pixmap = QPixmap(50, 27)
                pixmap.fill(QColor(255, 255, 255, 50))
                icon = QPixmap('resources/gui_icons/x_icon.svg')
                icon = icon.scaledToHeight(20, Qt.TransformationMode.SmoothTransformation)
                painter = QPainter(pixmap)
                icon_loc = QPoint(
                    int(pixmap.width() / 2 - icon.width() / 2),
                    int(pixmap.height() / 2 - icon.height() / 2)
                )
                painter.drawPixmap(icon_loc, icon)
                painter.end()

                placeholder_item = QListWidgetItem()
                placeholder_widget = StandardItemWidget(
                    self.gui,
                    'Missing custom slide: ' + service_dict[key]['title'],
                    icon=pixmap
                )
                placeholder_item.setSizeHint(placeholder_widget.sizeHint())
                self.gui.oos_widget.oos_list_widget.addItem(placeholder_item)
                self.gui.oos_widget.oos_list_widget.setItemWidget(placeholder_item, placeholder_widget)

            # walk through the items saved in the file and load their QListWidgetItems into the order of service widget
            for key in service_dict:
                if key.isnumeric():
                    if service_dict[key]['type'] == 'song':
                        song_items = self.gui.media_widget.song_list.findItems(
                            service_dict[key]['title'],
                            Qt.MatchFlag.MatchFixedString | Qt.MatchFlag.MatchRecursive,
                            0
                        )

                        if len(song_items) == 0:
                            make_missing_item('song', service_dict[key]['title'])
                        else:
                            self.gui.media_widget.add_song_to_service(song_items[0].clone())

                    elif service_dict[key]['type'] == 'bible':
                        if not self.gui.main.get_scripture:
                            from dataHandling.getScripture import GetScripture
                            self.get_scripture = GetScripture(self)
                        passages = self.get_scripture.get_passage(service_dict[key]['title'])

                        if passages[0] == -1:
                            QMessageBox.information(
                                self.gui.main_window,
                                'Error Loading Scripture',
                                'Unable to load scripture passage "' + service_dict[key]['title'] + '". "' + passages[1] + '"',
                                QMessageBox.StandardButton.Ok
                            )
                        else:
                            reference = service_dict[key]['title']
                            version = self.gui.media_widget.bible_selector_combobox.currentText()
                            self.gui.add_scripture_item(reference, passages[1], version, scripture_edited=False)

                    elif service_dict[key]['type'] == 'custom_bible':
                        try:
                            reference = service_dict[key]['title']
                            text = service_dict[key]['text']
                            passages = []
                            for item in text:
                                passage_split = item.split()
                                passages.append([passage_split[0], ' '.join(passage_split[1:])])
                            version = self.gui.media_widget.bible_selector_combobox.currentText()
                            self.gui.add_scripture_item(reference, passages, version, scripture_edited=True)
                        except KeyError:
                            pass

                    elif service_dict[key]['type'] == 'custom':
                        custom_items = self.gui.media_widget.custom_list.findItems(
                            service_dict[key]['title'],
                            Qt.MatchFlag.MatchFixedString | Qt.MatchFlag.MatchRecursive,
                            0
                        )

                        if len(custom_items) == 0:
                            make_missing_item('custom slide', service_dict[key]['title'])
                        else:
                            self.gui.media_widget.add_custom_to_service(custom_items[0].clone())

                    elif service_dict[key]['type'] == 'image':
                        image_items = self.gui.media_widget.image_list.findItems(
                            service_dict[key]['title'],
                            Qt.MatchFlag.MatchFixedString | Qt.MatchFlag.MatchRecursive,
                            0
                        )

                        if len(image_items) == 0:
                            make_missing_item('image', service_dict[key]['title'])
                        else:
                            self.gui.media_widget.add_image_to_service(image_items[0].clone())

                    elif service_dict[key]['type'] == 'video':
                        video_items = self.gui.media_widget.video_list.findItems(
                            service_dict[key]['title'],
                            Qt.MatchFlag.MatchFixedString | Qt.MatchFlag.MatchRecursive,
                            0
                        )

                        if len(video_items) == 0:
                            make_missing_item('video', service_dict[key]['title'])
                        else:
                            self.gui.media_widget.add_video_to_service(video_items[0].clone())

                    elif service_dict[key]['type'] == 'web':
                        web_items = self.gui.media_widget.web_list.findItems(
                            service_dict[key]['title'],
                            Qt.MatchFlag.MatchFixedString | Qt.MatchFlag.MatchRecursive,
                            0
                        )

                        if len(web_items) == 0:
                            make_missing_item('web', service_dict[key]['title'])
                        else:
                            self.gui.media_widget.add_web_to_service(web_items[0].clone())
        elif filename.endswith('.proj'):
            # walk through the items saved in the file and load their QListWidgetItems into the order of service widget
            self.gui.oos_widget.oos_list_widget.clear()
            for key in service_dict:
                if key.isnumeric():
                    # first, look for values that might be PNG bytes
                    data = service_dict[key]
                    for data_key in data:
                        # test to see if this key's value contains the bytes for a PNG image
                        # convert to a pixmap if so
                        if type(data[data_key]) is str and len(data[data_key]) > 90:
                            try:
                                decoded_bytes = base64.b64decode(
                                    service_dict[key][data_key].encode('utf-8'), validate=True)
                                if decoded_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
                                    # these are the bytes of a PNG image
                                    pixmap = QPixmap()
                                    pixmap.loadFromData(decoded_bytes)
                                    service_dict[key][data_key] = pixmap
                            except Exception:
                                pass

                    # create a QListWidgetItem and its itemWidget for each service item based on the stored data
                    item = QListWidgetItem()
                    item.setData(Qt.ItemDataRole.UserRole, service_dict[key])

                    # create the proper icon for this slide type
                    if data['type'] == 'song':
                        if not data['override_global'] or data['background'] == 'global_song':
                            print('setting icon to global song pixmap')
                            pixmap = self.gui.global_song_background_pixmap
                            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation)
                        elif data['background'] == 'global_bible':
                            pixmap = self.gui.global_bible_background_pixmap
                            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation)
                        elif 'rgb(' in data['background']:
                            pixmap = QPixmap(50, 27)
                            painter = QPainter(pixmap)
                            rgb = data['background'].replace('rgb(', '')
                            rgb = rgb.replace(')', '')
                            rgb_split = rgb.split(',')
                            brush = QBrush(QColor.fromRgb(
                                int(rgb_split[0].strip()), int(rgb_split[1].strip()), int(rgb_split[2].strip())))
                            painter.setBrush(brush)
                            painter.fillRect(pixmap.rect(), brush)
                            painter.end()
                        else:
                            pixmap = QPixmap(self.gui.main.background_dir + '/' + data['background'])
                            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation)
                    elif data['type'] == 'bible' or data['type'] == 'custom_bible':
                        pixmap = self.gui.global_bible_background_pixmap.scaled(
                            50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    elif data['type'] == 'custom':
                        if not data['override_global'] or data['background'] == 'global_bible':
                            pixmap = self.gui.global_bible_background_pixmap
                            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation)
                        elif data['background'] == 'global_song':
                            pixmap = self.gui.global_song_background_pixmap
                            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation)
                        elif 'rgb(' in data['background']:
                            pixmap = QPixmap(50, 27)
                            painter = QPainter(pixmap)
                            brush = QBrush(QColor(data['background']))
                            painter.fillRect(pixmap.rect(), brush)
                            painter.end()
                        else:
                            pixmap = QPixmap(self.gui.main.background_dir + '/' + data['background'])
                            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation)
                    elif service_dict[key]['type'] == 'image':
                        pixmap = data['background']
                        pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                               Qt.TransformationMode.SmoothTransformation)
                    elif service_dict[key]['type'] == 'video':
                        pixmap = QPixmap(
                            self.gui.main.video_dir + '/' + data['file_name'].split('.')[0] + '.jpg')
                        pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                               Qt.TransformationMode.SmoothTransformation)
                    elif service_dict[key]['type'] == 'web':
                        pixmap = QPixmap(50, 27)
                        pixmap.fill(QColor(255, 255, 255, 50))
                        icon = QPixmap('resources/gui_icons/web_icon.svg')
                        icon = icon.scaledToHeight(20, Qt.TransformationMode.SmoothTransformation)
                        painter = QPainter(pixmap)
                        icon_loc = QPoint(
                            int(pixmap.width() / 2 - icon.width() / 2),
                            int(pixmap.height() / 2 - icon.height() / 2)
                        )
                        painter.drawPixmap(icon_loc, icon)
                        painter.end()
                    else:
                        pixmap = QPixmap()

                    widget = StandardItemWidget(self.gui, data['title'], icon=pixmap)
                    item.setSizeHint(widget.sizeHint())
                    self.gui.oos_widget.oos_list_widget.addItem(item)
                    self.gui.oos_widget.oos_list_widget.setItemWidget(item, widget)

        # update the gui to reflect the changes loaded from the service file
        self.gui.current_file = filename[0]

        self.gui.preview_widget.slide_list.clear()
        self.gui.preview_widget.preview_label.clear()
        self.gui.live_widget.slide_list.clear()
        self.gui.live_widget.preview_label.clear()

        # set the last used directory in settings
        file_dir = os.path.dirname(filename[0])
        file_name = filename[0].replace(file_dir, '').replace('/', '').replace('\\', '')
        self.settings['last_save_dir'] = file_dir

        # add this file to the recently used services menu
        self.add_to_recently_used(file_dir, file_name)

        # apply any settings changes
        self.gui.apply_settings()

        self.gui.changes = False
        wait_widget.widget.deleteLater()

        self.gui.main_window.setWindowTitle(f'ProjectOn - {file_name}')

    def add_to_recently_used(self, directory: str, file_name: str):
        """
        Provides a method to add a file to the user's recently used file menu if this file doesn't already exist
        there.
        :param str directory: directory file is located in
        :param str file_name: the name of the file
        """
        if 'used_services' in self.settings.keys():
            used_services = self.settings['used_services']
            if len(used_services) == 0:
                used_services = []
        else:
            used_services = []

        add_file = True
        for item in used_services:
            if file_name == item[1]:
                add_file = False

        if add_file:
            # remove a recently used file if 5 already exist
            if len(used_services) == 5:
                name = used_services[0][1]
                used_services.pop(0)
                self.gui.open_recent_menu.removeAction(self.gui.open_recent_menu.findChild(QAction, name))

            # add this file to the recently used services menu
            action = self.gui.open_recent_menu.addAction(file_name)
            action.setData(directory + '/' + file_name)
            action.triggered.connect(lambda: self.load_service(action.data()))

            used_services.append([directory, file_name])
            self.settings['used_services'] = used_services
            self.save_settings()

    def import_xml_bible(self):
        file = QFileDialog.getOpenFileName(
            self.gui.main_window,
            'Choose XML Bible',
            os.path.expanduser('~') +
            '/Downloads',
            'XML Files (*.xml)'
        )

        if len(file[0]) == 0:
            return

        file_name_split = file[0].split('/')
        file_name = file_name_split[len(file_name_split) - 1]
        new_location = self.bible_dir + '/' + file_name
        shutil.copy(file[0], new_location)

        result = QMessageBox.question(
            self.gui.main_window,
            'Make Default',
            'Make this your default bible?',
            QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.No
        )
        if result == QMessageBox.StandardButton.Yes:
            self.settings['default_bible'] = new_location
            self.save_settings()

        new_tree = ElementTree.parse(new_location)
        new_root = new_tree.getroot()
        name = new_root.attrib['biblename']

        dialog = QDialog(self.gui.main_window)
        dialog.setWindowIcon(QIcon('resources/branding/logo.svg'))
        dialog.setWindowTitle('Set Bible Name')
        layout = QVBoxLayout(dialog)
        label = QLabel('What would you like to name this bible?')
        layout.addWidget(label)
        edit = QLineEdit(name)
        layout.addWidget(edit)
        button_widget = QWidget()
        layout.addWidget(button_widget)
        button_layout = QHBoxLayout(button_widget)
        ok_button = QPushButton('OK')
        ok_button.released.connect(lambda: dialog.done(0))
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addStretch()

        dialog.exec()
        bible_name = edit.text()
        if len(bible_name) == 0:
            bible_name = name
        new_root.attrib['biblename'] = bible_name

        new_tree.write(new_location)

        # refresh the bible combobox in the media widget
        self.gui.media_widget.bible_selector_combobox.blockSignals(True)
        self.gui.media_widget.bible_selector_combobox.clear()
        bibles = self.gui.media_widget.get_bibles()

        if len(bibles[0]) > 0:
            for bible in bibles:
                self.gui.media_widget.bible_selector_combobox.addItem(bible[1])
                self.gui.media_widget.bible_selector_combobox.setItemData(
                    self.gui.media_widget.bible_selector_combobox.count() - 1, bible[0], Qt.ItemDataRole.UserRole)

            default_bible_exists = False
            if 'default_bible' in self.settings.keys():
                if exists(self.settings['default_bible']):
                    tree = ElementTree.parse(self.settings['default_bible'])
                    root = tree.getroot()
                    name = root.attrib['biblename']
                    self.gui.media_widget.bible_selector_combobox.setCurrentText(name)
                    default_bible_exists = True

            if not default_bible_exists:
                self.settings['default_bible'] = bibles[0][0]
                self.gui.media_widget.bible_selector_combobox.setCurrentIndex(0)
                self.gui.main.save_settings()
                tree = ElementTree.parse(self.settings['default_bible'])
                root = tree.getroot()
                name = root.attrib['biblename']

        self.gui.media_widget.bible_selector_combobox.blockSignals(False)

    def do_backup(self):
        response = QMessageBox.question(
            self.gui.main_window,
            'Backup Your Data',
            'This will perform a complete backup of your data and may take a few minutes. Continue?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if not response == QMessageBox.StandardButton.Yes:
            return

        now = str(datetime.now())
        now = now.replace(' ', '_')
        now = now.replace('-', '.')
        now = now.replace(':', '.')

        result = QFileDialog.getSaveFileName(
            self.gui.main_window,
            'Backup File',
            os.path.expanduser('~/Documents') + '/po_backup_' + now + '.zip',
            'ZIP Files (*.zip)'
        )

        if not len(result[0]) > 0:
            return
        backup_file_name = result[0]
        wait_widget = SimpleSplash(self.gui, 'Backing Up Data...', subtitle=True)

        zf = zipfile.ZipFile(
            backup_file_name,
            'w', compression=zipfile.ZIP_DEFLATED,
            compresslevel=9
        )
        for file in os.listdir(self.data_dir):
            file_path = self.data_dir + '/' + file
            zf.write(file_path, arcname=file_path.replace(self.data_dir, 'data'))
        for root, directories, files in os.walk(self.data_dir):
            for directory in directories:
                for file in os.listdir(str(os.path.join(root, directory))):
                    file_path = root + '/' + directory + '/' + file
                    if not file.endswith('.zip'):
                        wait_widget.subtitle_label.setText('Compressing ' + str(file))
                        zf.write(file_path, arcname=file_path.replace(root, 'data'))
                        self.app.processEvents()
        zf.close()
        wait_widget.widget.deleteLater()

    def restore_from_backup(self):
        result = QMessageBox.information(
            self.gui.main_window,
            'Restore from Backup',
            'This will restore all of your data from a backup zip file. Continue?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if not result == QMessageBox.StandardButton.Yes:
            return

        result = QFileDialog.getOpenFileName(
            self.gui.main_window,
            'Choose Backup File',
            os.path.expanduser('~/Documents'),
            'ZIP Files (*.zip)'
        )

        if len(result[0]) == 0 or not zipfile.is_zipfile(result[0]):
            return

        zf = zipfile.ZipFile(
            result[0],
            'r',
        )

        destination = '/'.join(self.data_dir.split('/')[:-1])
        ss = SimpleSplash(self.gui, 'Restoring', subtitle=True)
        for file in zf.infolist():
            ss.subtitle_label.setText(file.filename)
            self.app.processEvents()
            try:
                zf.extract(file, destination)
            except Exception as ex:
                self.error_log()

        QMessageBox.information(
            self.gui.main_window,
            'Finished',
            'Restore from backup complete',
            QMessageBox.StandardButton.Ok
        )

    def error_log(self, log_text: str | None = None):
        """
        Method to write a traceback to the program's error log file as well as show the user the error.
        """
        if not log_text: # if text was provided, we're only logging information
            tb = traceback.walk_tb(sys.exc_info()[2])
            message_box_text = ''
            for frame, line_no in tb:
                clss = ''
                if 'self' in frame.f_locals.keys():
                    try:
                        clss = str(frame.f_locals['self']).split('<')[1].split(' ')[0].split('.')[1]
                    except IndexError:
                        clss = str(frame.f_locals['self'])
                file_name = frame.f_code.co_filename
                method = frame.f_code.co_name
                line_num = line_no
                message_box_text = (
                    f'An error:\n'
                    f'    {sys.exc_info()[1]},\n'
                    f'occurred on line\n'
                    f'    {line_num}\n'
                    f'of\n'
                    f'    {file_name}\n'
                    f'in\n'
                    f'    {clss}.{method}'
                )
                date_time = time.ctime(time.time())
                log_text = (f'\n{date_time}:\n'
                            f'    {sys.exc_info()[1]} on line {line_num} of {file_name} in {clss}.{method}')
            print(f'ProjectOn.error_log log text: {log_text}')

            message_box = QMessageBox()
            message_box.setIconPixmap(QPixmap('resources/gui_icons/face-palm.png'))
            message_box.setWindowTitle('An Error Occurred')
            message_box.setText('<strong>Well, that wasn\'t supposed to happen!</strong><br><br>' + message_box_text)
            message_box.setStandardButtons(QMessageBox.StandardButton.Close)
            message_box.exec()
        else:
            date_time = time.ctime(time.time())
            log_text = (f'\n{date_time}:\n' + log_text)

        if 'linux' in sys.platform:
            log_location = os.path.expanduser('~/.config/ProjectOn/error.log')
        else:
            log_location = os.path.expanduser('~/AppData/Roaming/ProjectOn/error.log')

        if not exists(log_location):
            with open(log_location, 'w') as file:
                pass

        with open(log_location, 'a') as file:
            file.write(log_text)

    def check_db(self, db_file: str):
        db_structure = DB_STRUCTURE.copy()
        connection = sqlite3.connect(db_file)
        cursor = connection.cursor()
        changes_made = False
        log_text = ''
        for table_name in db_structure.keys():
            result = cursor.execute(
                f'SELECT name FROM sqlite_master WHERE type = "table" AND name = "{table_name}";').fetchall()
            if len(result) == 0: # this means the table doesn't exist and must be created
                date_time = time.ctime(time.time())
                log_text += f'\n{date_time}:\n    database missing table {table_name}; creating table'

                sql = f'CREATE TABLE {table_name} ('
                for column in db_structure[table_name]:
                    sql += f'{column} {db_structure[table_name][column]}, '
                sql = sql[:-2]
                sql += ');'

                cursor.execute(sql)
                changes_made = True
            else: # this means the table exists and now will be checked that all columns exist
                result = connection.execute(f'PRAGMA table_info({table_name});').fetchall()
                existing_columns = []
                for column in result:
                    existing_columns.append(column[1])

                for column in db_structure[table_name]:
                    if column not in existing_columns:
                        date_time = time.ctime(time.time())
                        log_text += f'\n{date_time}:\n    table {table_name} missing column {column}; creating column'

                        cursor.execute(
                            f'ALTER TABLE {table_name} ADD COLUMN {column} {db_structure[table_name][column]};')
                        changes_made = True
                        
        if changes_made:
            connection.commit()
            self.error_log(log_text)

        connection.close()

    def move_data_folder(self):
        response = QMessageBox.information(
            self.gui.main_window,
            'Move Data Folder',
            'Would you like to move the ProjectOn data folder to a new location?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )
        if not response == QMessageBox.StandardButton.Yes:
            return

        result = QFileDialog.getExistingDirectory(
            self.gui.main_window,
            'Choose Data Folder Location',
            os.path.expanduser('~')
        )
        if len(result) == 0:
            return

        old_path = self.data_dir
        new_path = result + '/data'
        if 'win' in sys.platform:
            old_path = old_path.replace('/', '\\')
            new_path = new_path.replace('/', '\\')

        splash = SimpleSplash(
            self.gui, 'Moving data folder. This may take a while...', subtitle=True, parent=self.gui.main_window)
        splash.widget.raise_()
        self.app.processEvents()

        def copy_update(src, dst, *, follow_symlinks=True):
            splash.subtitle_label.setText('Copying ' + src)
            if splash.subtitle_label.width() > splash.widget.width() - 40:
                splash.widget.adjustSize()
            self.app.processEvents()
            result = shutil.copy2(src, dst, follow_symlinks=follow_symlinks)

        try:
            shutil.copytree(old_path, new_path, copy_function=copy_update)
        except Exception as ex:
            QMessageBox.critical(
                self.gui.main_window,
                'Error Moving Data Folder',
                f'There was an error moving the Data folder (see below). Your folder has not been moved.<br><br>{ex}',
                QMessageBox.StandardButton.Ok
            )
            return

        splash.widget.deleteLater()
        self.app.processEvents()

        ending = '.'
        result = QMessageBox.question(
            self.gui.main_window,
            'Delete Old Data Folder?',
            'Would you like to delete the old ProjectOn Data Folder?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if result == QMessageBox.StandardButton.Yes:
            splash = SimpleSplash(self.gui, 'Deleting old data folder...', parent=self.gui.main_window)
            splash.widget.raise_()
            self.app.processEvents()

            shutil.rmtree(old_path)
            ending = f' and the old data folder at\n{old_path}\nhas been deleted.'
            splash.widget.deleteLater()

        QMessageBox.information(
            self.gui.main_window,
            'Move Complete',
            f'Your new data folder has been moved to\n{new_path}{ending}',
            QMessageBox.StandardButton.Ok
        )

        new_path = new_path.replace('\\', '/')
        self.data_dir = new_path
        self.settings['data_dir'] = new_path
        save_settings = SaveSettings(self)
        thread = threading.Thread(target=save_settings.run())
        thread.start()
        thread.join()

        self.gui.check_files()

    def select_data_folder(self):
        response = QMessageBox.question(
            self.gui.main_window,
            'Select Data Folder',
            'Would you like to choose a different ProjectOn Data Folder?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )
        if not response == QMessageBox.StandardButton.Yes:
            return

        result = QFileDialog.getExistingDirectory(
            self.gui.main_window,
            'Choose Data Folder Location',
            os.path.expanduser('~')
        )
        if len(result) == 0:
            return
        target_directory = result

        if not exists(result + '/projecton.db'):
            QMessageBox.critical(
                self.gui.main_window,
                'Invalid Data Folder',
                'The selected folder does not contain a ProjectOn database. Please try again.',
                QMessageBox.StandardButton.Ok
            )
            return

        common_folders = [
            'videos',
            'images',
            'backgrounds',
            'bibles'
        ]
        list_dir = os.listdir(target_directory)
        missing_folders = []
        for folder in common_folders:
            folder_found = False
            for file in list_dir:
                full_path = os.path.join(target_directory, file)
                if os.path.isdir(full_path) and file == folder:
                    folder_found = True
            if not folder_found:
                missing_folders.append(folder)

        recreate_folders = False
        if len(missing_folders) > 0:
            result = QMessageBox.question(
                self.gui.main_window,
                'Data folder(s) missing',
                f'The data folder(s), {", ".join(missing_folders)}, are missing from this folder. '
                f'Would you like to recreate them?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if not result == QMessageBox.StandardButton.Yes:
                return
            if result == QMessageBox.StandardButton.Yes:
                recreate_folders = True

        if recreate_folders:
            for folder in missing_folders:
                shutil.copytree(f'resources/defaults/data/{folder}', f'{target_directory}/{folder}')

        self.data_dir = target_directory
        self.settings['data_dir'] = target_directory
        save_settings = SaveSettings(self)
        thread = threading.Thread(target=save_settings.run())
        thread.start()
        thread.join()

        self.gui.check_files()
        self.gui.apply_settings()
        self.gui.media_widget.populate_song_list()
        self.gui.media_widget.populate_custom_list()
        self.gui.media_widget.populate_image_list()
        self.gui.media_widget.populate_video_list()
        self.gui.media_widget.populate_web_list()

        if 'win' in sys.platform:
            target_directory = target_directory.replace('/', '\\')

        QMessageBox.information(
            self.gui.main_window,
            'New Data Folder Selected',
            f'You are now working with the data folder located at\n{target_directory}.',
            QMessageBox.StandardButton.Ok
        )

    def copy_file_with_progress(self, src, dst, callback=None, chunk_size=1024 * 1024):
        """
        Copies a file from src to dst and reports progress via a callback function.
        chunk_size defaults to 1MB.
        :param str src: source file
        :param str dst: destination file
        :param callable callback: callback function to report progress
        :param int chunk_size: chunk size in bytes
        """
        total_size = os.path.getsize(src)
        bytes_copied = 0

        with open(src, 'rb') as fsrc:
            with open(dst, 'wb') as fdst:
                while True:
                    chunk = fsrc.read(chunk_size)
                    if not chunk:
                        break
                    fdst.write(chunk)
                    bytes_copied += len(chunk)

                    # Calculate percentage and send it to the callback
                    if callback:
                        percentage = int((bytes_copied / total_size) * 100)
                        callback(percentage)


def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    """
    Provides a method for handling exceptions that aren't handled elsewhere in the program.
    :param exc_type:
    :param exc_value:
    :param exc_traceback:
    :return:
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # Will call default excepthook
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    exc_type = str(exc_type).replace('<class ', '')
    exc_type = exc_type.replace('>', '')
    full_traceback = str(traceback.StackSummary.extract(traceback.walk_tb(exc_traceback)))
    full_traceback = full_traceback.replace('[', '').replace(']', '')
    full_traceback = full_traceback.replace('<FrameSummary ', '')
    full_traceback = full_traceback.replace('>', '')
    full_traceback_split = full_traceback.split(',')
    formatted_traceback = ''
    for i in range(len(full_traceback_split)):
        if i == 0:
            formatted_traceback += full_traceback_split[i] + '\n'
        else:
            formatted_traceback += '    ' + full_traceback_split[i] + '\n'

    date_time = time.ctime(time.time())
    log_text = (f'\n{date_time}:\n'
                f'    UNHANDLED EXCEPTION\n'
                f'    {exc_type}\n'
                f'    {exc_value}\n'
                f'    {full_traceback}')
    print(f'log_unhandled_exception log text: {log_text}')

    if 'linux' in sys.platform:
        user_dir = os.path.expanduser('~/.config/ProjectOn')
    else:
        user_dir = os.getenv('APPDATA') + '/ProjectOn'
    with open(user_dir + '/error.log', 'a') as file:
        file.write(log_text)

    message_box = QMessageBox()
    message_box.setIconPixmap(QPixmap('resources/gui_icons/face-palm.png'))
    message_box.setWindowTitle('Unhandled Exception')
    message_box.setText(
        '<strong>Well, that wasn\'t supposed to happen!</strong><br><br>An unhandled exception occurred:<br>'
        f'{exc_type}<br>'
        f'{exc_value}<br>'
        f'{full_traceback}')
    message_box.setStandardButtons(QMessageBox.StandardButton.Close)
    message_box.adjustSize()
    message_box.exec()
