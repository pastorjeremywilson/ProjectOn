import json
import os
import shutil
import sqlite3
import sys
import time
from datetime import datetime
from os.path import exists

import requests
from PIL.ImageQt import QPixmap
from PyQt5.QtCore import QRunnable, Qt, QByteArray, QBuffer, QIODevice, QTimer
from PyQt5.QtWidgets import QMessageBox, QFileDialog


class CheckFiles(QRunnable):
    """
    Provides a threadable class to check that the files needed by the program exist. Creates them if not.
    :param ProjectOn main: The current instance of the ProjectOn class
    """
    def __init__(self, main):
        """
        :param ProjectOn main: The current instance of the ProjectOn class
        """
        super().__init__()
        self.main = main

    def run(self):
        if not exists(os.path.expanduser('~/AppData/Roaming/ProjectOn')):
            os.mkdir(os.path.expanduser('~/AppData/Roaming/ProjectOn'))
        self.main.device_specific_config_file = os.path.expanduser('~/AppData/Roaming/ProjectOn/localConfig.json')

        if not exists(self.main.device_specific_config_file):
            device_specific_settings = {
                'used_services': '',
                'last_save_dir': '',
                'last_status_count': 100,
                'data_dir': '',
                'selected_screen_name': ''
            }
            with open(self.main.device_specific_config_file, 'w') as file:
                file.write(json.dumps(device_specific_settings))
        else:
            with open(self.main.device_specific_config_file, 'r') as file:
                device_specific_settings = json.loads(file.read())

        data_dir = False
        if 'data_dir' in device_specific_settings.keys():
            if '~' in device_specific_settings['data_dir']:
                self.main.data_dir = os.path.expanduser(device_specific_settings['data_dir'])
            else:
                self.main.data_dir = device_specific_settings['data_dir']

            if exists(self.main.data_dir):
                data_dir = True

        if not data_dir:
            QMessageBox.question(
                None,
                'Locate Data Directory',
                'Please locate the ProjectOn Data Directory that contains "projecton.db"',
                QMessageBox.StandardButton.Ok
            )
            self.main.app.processEvents()

            result = QFileDialog.getExistingDirectory(
                None,
                'Data Directory',
                os.path.expanduser('~/Documents')
            )
            if len(result) == 0:
                sys.exit(-1)
            self.main.data_dir = result

        self.main.config_file = self.main.data_dir + '/settings.json'
        self.main.database = self.main.data_dir + '/projecton.db'
        self.main.background_dir = self.main.data_dir + '/backgrounds'
        self.main.image_dir = self.main.data_dir + '/images'
        self.main.bible_dir = self.main.data_dir + '/bibles'
        self.main.video_dir = self.main.data_dir + '/videos'

        # provide default settings should the settings file not exist
        default_settings = {
            'selected_screen_name': '',
            'font_face': 'Helvetica',
            'font_size': 60,
            'font_color': 'white',
            'global_song_background': '',
            'global_bible_background': '',
            'logo_image': '',
            'last_save_dir': './saved services',
            'last_status_count': 0,
            'stage_font_size': 60
        }

        if exists(self.main.data_dir + '/settings.json'):
            with open(self.main.data_dir + '/settings.json', 'r') as file:
                try:
                    self.main.settings = json.loads(file.read())
                except json.decoder.JSONDecodeError:
                    self.main.settings = {}
        else:
            self.main.settings = default_settings

        for key in default_settings:
            if key not in self.main.settings.keys():
                self.main.settings[key] = default_settings[key]

        self.main.settings['used_services'] = device_specific_settings['used_services']
        self.main.settings['last_save_dir'] = device_specific_settings['last_save_dir']
        if 'selected_screen_name' in device_specific_settings.keys():
            self.main.settings['selected_screen_name'] = device_specific_settings['selected_screen_name']
        else:
            self.main.settings['selected_screen_name'] = ''
        if 'last_status_count' in device_specific_settings.keys():
            self.main.settings['last_status_count'] = device_specific_settings['last_status_count']
        self.main.settings['data_dir'] = self.main.data_dir

        if not exists(self.main.config_file):
            if exists(self.main.data_dir + '/settings.json'):
                shutil.copy(self.main.data_dir + '/settings.json', self.main.config_file)


class IndexImages(QRunnable):
    """
    Walks through the 'backgrounds' and 'images' folders of the program's data folder and creates or deletes entries
    and thumbnails in the appropriate tables of the program's database based on the files it finds.
    :param ProjectOn main: The current instance of ProjectOn
    :param str type: Directory to index - 'backgrounds' or 'images'
    :param bool force: Optional, force a reindexing whether needed or not
    """
    def __init__(self, main, type, force=False):
        """
        :param ProjectOn main: The current instance of ProjectOn
        :param str type: Directory to index - 'backgrounds' or 'images'
        :param bool force: Optional, force a reindexing whether needed or not
        """
        super().__init__()
        self.main = main
        self.force = force
        if type == 'backgrounds':
            self.table = 'backgroundThumbnails'
            self.directory = self.main.background_dir
        elif type == 'images':
            self.table = 'imageThumbnails'
            self.directory = self.main.image_dir

    def run(self):
        connection = sqlite3.connect(self.main.database)
        cursor = connection.cursor()

        thumbnails = cursor.execute('SELECT fileName FROM ' + self.table).fetchall()
        database_list = []
        for record in thumbnails:
            database_list.append(record[0])

        file_list = os.listdir(self.directory)
        file_types = ['jpg', 'png', 'svg', 'bmp']
        filtered_files = []
        for file in file_list:
            file_type = file.split('.')[1]
            if file_type in file_types:
                filtered_files.append(file)

        reindex = False
        for file in database_list:
            if self.main.initial_startup:
                self.main.update_status_signal.emit(f'Checking Database for {file}', 'info')
            if file not in filtered_files:
                reindex = True
                break

        for file in filtered_files:
            if self.main.initial_startup:
                self.main.update_status_signal.emit(f'Checking Folder for {file}', 'info')
            if file not in database_list:
                reindex = True
                break

        if not reindex and not self.force:
            return

        cursor.execute('DELETE FROM ' + self.table)
        connection.commit()
        for file in file_list:
            file_type = file.split('.')[1]
            if file_type in file_types:
                if self.main.initial_startup:
                    self.main.update_status_signal.emit(f'Indexing {file}', 'info')
                pixmap = QPixmap(self.directory + '/' + file)
                scaled_pixmap = pixmap.scaled(96, 54, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

                thumbnail_array = QByteArray()
                thumbnail_buffer = QBuffer(thumbnail_array)
                thumbnail_buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                scaled_pixmap.save(thumbnail_buffer, 'JPG')
                thumbnail_blob = bytes(thumbnail_array.data())
                thumbnail_buffer.close()

                cursor.execute(f'INSERT INTO {self.table} (fileName, image) '
                               f'VALUES("{file}", ?)', (thumbnail_blob,))

        connection.commit()
        connection.close()

    def add_image_index(self, file, type):
        """
        Does the work of adding the file name and image blob to the proper table in the program's database.
        :param str file: The file location
        :param str type: 'background' or 'image' file
        """
        table = ''
        if type == 'background':
            table = 'backgroundThumbnails'
        elif type == 'image':
            table = 'imageThumbnails'
        file_split = file.split('/')
        file_name = file_split[len(file_split) - 1]

        pixmap = QPixmap(file)
        pixmap = pixmap.scaled(96, 54, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

        array = QByteArray()
        buffer = QBuffer(array)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        pixmap.save(buffer, 'JPG')
        blob = bytes(array.data())

        connection = sqlite3.connect(self.main.database)
        cursor = connection.cursor()
        cursor.execute('INSERT INTO ' + table + ' (fileName, image) VALUES("' + file_name + '", ?)', (blob,))
        connection.commit()
        connection.close()


class ServerCheckTimer(QTimer):
    """
    Implements QTimer to periodically check that the three servers are up and running. Emits the GUI's
    server_alert_signal if the check fails.
    Args:
        remote_server (RemoteServer): The current instance of RemoteServer
        gui (GUI): The current instance of GUI
    """
    def __init__(self, remote_server, gui):
        super().__init__()
        self.remote_server = remote_server
        self.gui = gui
        self.setInterval(5000)
        self.timeout.connect(self.check_server)

    def check_server(self):
        if self.remote_server.socketio:
            remote_response = requests.get('http://' + self.remote_server.gui.main.ip + ':15171/remote')
            mremote_response = requests.get('http://' + self.remote_server.gui.main.ip + ':15171/mremote')
            stage_response = requests.get('http://' + self.remote_server.gui.main.ip + ':15171/stage')

            if remote_response and mremote_response and stage_response:
                if not (remote_response.status_code == 200
                        and mremote_response.status_code == 200
                        and stage_response.status_code == 200):
                    self.keep_checking = False
                    error_text = (str(time.time()) + ' - '
                                  + 'server error: remote-' + str(remote_response.status_code)
                                  + ', mremote-' + str(mremote_response.status_code)
                                  + ', stage-' + str(stage_response.status_code))
                    with open('./error.log', 'a') as file:
                        file.write(error_text)
                    self.gui.server_alert_signal.emit()
            else:
                self.keep_checking = False
                with open('./error.log', 'a') as file:
                    file.write('unknown server error')
                self.gui.server_alert_signal.emit()


class SaveSettings(QRunnable):
    def __init__(self, main):
        super().__init__()
        self.main = main

    def run(self):
        """
        Saves all of the settings currently stored in the ProjectOn.settings variable to the settings.json file in the
        program's data directory.
        """
        try:
            with open(self.main.data_dir + '/settings.json', 'w') as file:
                file.write(json.dumps(self.main.settings, indent=4))

            device_specific_settings = {}
            device_specific_settings['used_services'] = self.main.settings['used_services']
            device_specific_settings['last_save_dir'] = self.main.settings['last_save_dir']
            device_specific_settings['last_status_count'] = self.main.settings['last_status_count']
            device_specific_settings['selected_screen_name'] = self.main.settings['selected_screen_name']
            device_specific_settings['data_dir'] = self.main.data_dir
            with open(self.main.device_specific_config_file, 'w') as file:
                file.write(json.dumps(device_specific_settings, indent=4))

        except Exception:
            self.main.error_log()


class TimedPreviewUpdate(QRunnable):
    """
    Used to update the preview image in the live widget when a video is playing.
    """
    gui = None
    def __init__(self, gui):
        """
        Used to update the preview image in the live widget when a video is playing.
        :param gui.GUI gui: The current instance of GUI
        """
        super().__init__()
        self.gui = gui
        self.keep_running = True

    def run(self):
        while self.keep_running:
            self.gui.grab_display_signal.emit()
            time.sleep(0.1)


class SlideAutoPlay(QRunnable):
    def __init__(self, gui, text, interval):
        """
        Cycles through the text in a list of strings, changing the display widget's lyrics based on a given interval
        :param gui: the current instance of GUI
        :param text: list of strings to be displayed
        :param interval: number of seconds between each lyric change
        """
        super().__init__()
        self.gui = gui
        self.interval = interval
        self.text = text
        self.keep_running = True

    def run(self):
        while self.keep_running:
            time.sleep(float(self.interval))
            # don't emit the signal if keep_running was changed during sleep
            if self.keep_running:
                self.gui.change_current_live_item_signal.emit()


class CountdownTimer(QTimer):
    """
    Implements QTimer to check every second whether the service countdown widget should be displayed, and to change
    the text of the widget's label.
    Args:
        countdown_widget (CountdownWidget): The countdown widget to be manipulated.
        start_time (datetime.time): The start time of the service.
        display_time (datetime.time): The time to start showing the countdown widget.
    """
    def __init__(self, countdown_widget, start_time, display_time):
        super().__init__()
        self.countdown_widget = countdown_widget
        self.start_time = start_time
        self.display_time = display_time

        self.setInterval(1000)
        self.timeout.connect(self.operate_countdown)

    def operate_countdown(self):
        if datetime.now() > self.start_time:
            self.stop()
            self.countdown_widget.hide_self_signal.emit()
        elif datetime.now() >= self.display_time:
            if self.countdown_widget.isHidden():
                self.countdown_widget.show_self_signal.emit()
                self.countdown_widget.raise_()
            time_remaining = self.start_time - datetime.now()
            minutes = str(time_remaining.seconds / 60).split('.')[0]
            seconds = str(time_remaining.seconds % 60)
            if len(seconds) == 1:
                seconds = '0' + seconds
            self.countdown_widget.update_label_signal.emit(f'Service starts in {minutes}:{seconds}')