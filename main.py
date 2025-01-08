"""
This file and all files contained within this distribution are parts of the ProjectOn worship projection software.

ProjectOn v.1.5.3
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

import requests
from PyQt5.QtCore import Qt, QByteArray, QBuffer, QIODevice, QRunnable, QThreadPool, pyqtSignal, QObject, QPoint
from PyQt5.QtGui import QPixmap, QFont, QPainter, QBrush, QColor, QPen, QIcon
from PyQt5.QtWidgets import QApplication, QLabel, QListWidgetItem, QWidget, QVBoxLayout, QFileDialog, QMessageBox, \
    QProgressBar, QHBoxLayout, QDialog, QLineEdit, QPushButton, QAction
from gevent import monkey

import declarations
from gui import GUI
from simple_splash import SimpleSplash
from web_remote import RemoteServer
from widgets import StandardItemWidget


class ProjectOn(QObject):
    """
    Main entry point of the program. Loads necessary configuration information, starts the GUI and its QApplication,
    starts the web server.
    """
    app = None
    data_dir = None
    user_dir = None
    database = None
    bible_dir = None
    get_scripture = None
    settings = None
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

    def __init__(self):
        super().__init__()

        os.chdir(os.path.dirname(__file__))
        os.environ['QTWEBENGINE_DISABLE_SANDBOX'] = '1'
        os.environ['QT_MULTIMEDIA_PREFERRED_PLUGINS'] = 'windowsmediafoundation'

        self.app = QApplication(sys.argv)
        #self.app.setAttribute(Qt.ApplicationAttribute.AA_DisableWindowContextHelpButton, True)

        self.thread_pool = QThreadPool()
        self.server_thread_pool = QThreadPool()
        self.update_status_signal.connect(self.update_status_label)

        last_status_count = 100
        if exists(os.path.expanduser('~/AppData/Roaming/ProjectOn/localConfig.json')):
            with open(os.path.expanduser('~/AppData/Roaming/ProjectOn/localConfig.json'), 'r') as file:
                contents = json.loads(file.read())
            if 'last_status_count' in contents.keys():
                last_status_count = contents['last_status_count']
        self.make_splash_screen(last_status_count)

        self.update_status_signal.emit('Creating Socket', 'status')
        self.app.processEvents()

        # create a web socket to be used for sending data to/from the remote and stage view servers
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('192.255.255.255', 1))
        self.ip = s.getsockname()[0]

        self.update_status_signal.emit('Creating GUI', 'status')
        self.app.processEvents()

        self.gui = GUI(self)

        self.update_status_signal.emit('Starting Remote Server', 'status')
        self.app.processEvents()

        self.remote_server = RemoteServer(self.gui)
        self.server_thread_pool.start(self.remote_server)
        self.server_check = ServerCheck(self.remote_server, self.gui)
        self.server_thread_pool.start(self.server_check)

        self.splash_widget.deleteLater()
        self.settings['last_status_count'] = self.status_update_count
        self.initial_startup = False

        # load a service file if given at runtime
        for arg in sys.argv:
            if '.pro' in arg:
                self.load_service(arg)

        self.app.processEvents()

        self.app.exec()

    def update_status_label(self, text, type):
        """
        Updates the splash widget with the given text.
        :param str text: The text to be displayed
        :param str type: Use 'status' if this will be an update to the status text under the main text
        """
        if self.splash_widget:
            if type == 'status':
                self.status_label.setText(text)
            else:
                self.info_label.setText(text)

            self.progress_bar.setValue(self.progress_bar.value() + 1)
            self.app.processEvents()
            self.status_update_count += 1
            self.splash_widget.setFocus()

    def make_splash_screen(self, last_status_count):
        """
        Create the splash screen that will show progress as the program is loading
        """
        self.splash_widget = QWidget()
        self.splash_widget.setObjectName('splash_widget')
        self.splash_widget.setMinimumWidth(610)
        self.splash_widget.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.splash_widget.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, True)
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

        version_label = QLabel('v.1.5.3')
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

    def get_all_songs(self):
        """
        Retrieves all song data from the ProjectOn database's 'songs' table
        :return: list of str result
        """
        connection = None
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()

            # check that the database has the newest columns
            result = cursor.execute('PRAGMA table_info(songs)').fetchall()
            updated_table = False
            for record in result:
                if record[1] == 'shade_opacity':
                    updated_table = True
            if not updated_table:
                self.update_table(connection, cursor, 'songs')

            result = cursor.execute('SELECT * FROM songs ORDER BY title').fetchall()
            connection.close()
            return result
        except Exception:
            self.error_log()
            if connection:
                connection.close()
            return -1

    def update_table(self, connection, cursor, table):
        column_names = [
            ['use_shade', 'False'],
            ['shade_color', '0'],
            ['shade_opacity', '75']
        ]
        for name in column_names:
            cursor.execute(f'ALTER TABLE {table} ADD {name[0]} TEXT;')
            cursor.execute(f'UPDATE {table} SET {name[0]}={str(name[1])}')
        connection.commit()

    def get_all_custom_slides(self):
        """
        Retrieves all custom slide data from the ProjectOn database's 'customSlides' table
        :return: list of str result
        """
        connection = None
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()

            # check that the database has the newest columns
            result = cursor.execute('PRAGMA table_info(customSlides)').fetchall()
            updated_table = False
            for record in result:
                if record[1] == 'shade_opacity':
                    updated_table = True
            if not updated_table:
                self.update_table(connection, cursor, 'customSlides')

            result = cursor.execute('SELECT * FROM customSlides ORDER BY title').fetchall()
            connection.close()
            return result
        except Exception:
            self.error_log()
            if connection:
                connection.close()
            return -1

    def get_song_data(self, title):
        """
        Gets the song data for a particular song where the 'title' column matches 'title'
        :param str title: the song title
        :return: list of str result
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

    def get_custom_data(self, title):
        """
        Gets the song data for a particular custom slide where the 'title' column matches 'title'
        :param str title: the title (name) of the custom slide
        :return: list of str result
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

    def copy_image(self, file):
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

    def save_song(self, song_data, old_title=None):
        """
        Takes song data as a string list, ordered by the column order of the 'songs' table of the program's database,
        and inserts or updates that data in the database.
        :param list of str song_data: The song's data in columnar order
        :param str old_title: Optional, the song's original title so that it can be updated instead of inserted
        """
        connection = None
        try:
            for i in range(len(song_data)):
                if song_data[i]:
                    song_data[i] = (str(song_data[i])).replace('"', '""')
                else:
                    song_data[i] = ''
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()

            if old_title:
                sql = (
                    'UPDATE songs SET '
                    'title="' + song_data[0] + '", '
                    'author="' + song_data[1] + '", '
                    'copyright="' + song_data[2] + '", '
                    'ccliNum="' + song_data[3] + '", '
                    'lyrics="' + song_data[4] + '", '
                    'vorder="' + song_data[5] + '", '
                    'footer="' + song_data[6] + '", ' 
                    'font="' + song_data[7] + '", ' 
                    'fontColor="' + song_data[8] + '", ' 
                    'background="' + song_data[9] + '", '
                    'font_size="' + song_data[10] + '", '
                    'use_shadow="' + song_data[11] + '", '
                    'shadow_color="' + song_data[12] + '", '
                    'shadow_offset="' + song_data[13] + '", '
                    'use_outline="' + song_data[14] + '", '
                    'outline_color="' + song_data[15] + '", '
                    'outline_width="' + song_data[16] + '", '
                    'override_global="' + song_data[17] + '", '
                    'use_shade="' + song_data[18] + '", '
                    'shade_color="' + song_data[19] + '", '
                    'shade_opacity="' + song_data[20] + '" '
                    'WHERE title="' + old_title + '"'
                )
            else:
                sql = ('INSERT INTO songs (title, author, copyright, ccliNum, lyrics, vorder, footer, font, fontColor, '
                       'background, font_size, use_shadow, shadow_color, shadow_offset, use_outline, outline_color, '
                       'outline_width, override_global, use_shade, shade_color, shade_opacity) VALUES ("'
                       + song_data[0] + '","' + song_data[1] + '","' + song_data[2] + '","'
                       + song_data[3] + '","' + song_data[4] + '","' + song_data[5] + '","' + song_data[6]
                       + '","' + song_data[7] + '","' + song_data[8] + '","' + song_data[9] + '","' + song_data[10]
                       + '","' + song_data[11] + '","' + song_data[12] + '","' + song_data[13] + '","' + song_data[14]
                       + '","' + song_data[15] + '","' + song_data[16] + '","' + song_data[17] + '","' + song_data[18]
                       + '","' + song_data[19] + '","' + song_data[20] + '")')

            cursor.execute(sql)
            connection.commit()
            connection.close()
        except Exception:
            self.error_log()
            if connection:
                connection.close()

    def get_song_titles(self):
        """
        Retrieves just the titles of all songs in the database.
        :return list of str song_titles: Song titles
        """
        connection = sqlite3.connect(self.database)
        cursor = connection.cursor()
        data = cursor.execute('SELECT title FROM songs ORDER BY title').fetchall()
        song_titles = []
        for item in data:
            song_titles.append(item[0])

        return song_titles

    def get_custom_titles(self):
        """
        Retrieves just the titles of all custom slides in the database.
        :return list of str custom_titles: Custom slide titles
        """
        connection = sqlite3.connect(self.database)
        cursor = connection.cursor()
        data = cursor.execute('SELECT title FROM customSlides').fetchall()
        custom_titles = []
        for item in data:
            custom_titles.append(item[0])

        return custom_titles

    def save_custom(self, custom_data, old_title):
        """
        Takes custom slide data as a string list, ordered by the column order of the 'customSlides' table of the
        program's database, and inserts or updates that data in the database.
        :param list of str custom_data: The custom slide's data in columnar order
        :param str old_title: Optional, the custom slide's original title so that it can be updated instead of inserted
        """
        connection = None
        try:
            if old_title:
                sql = ('UPDATE customSlides SET '
                       'title="' + custom_data[0] + '", '
                       'text="' + custom_data[1] + '", ' 
                       'font="' + custom_data[2] + '", ' 
                       'fontColor="' + custom_data[3] + '", ' 
                       'background="' + custom_data[4] + '", '
                       'font_size="' + custom_data[5] + '", '
                       'use_shadow="' + custom_data[6] + '", '
                       'shadow_color="' + custom_data[7] + '", '
                       'shadow_offset="' + custom_data[8] + '", '
                       'use_outline="' + custom_data[9] + '", '
                       'outline_color="' + custom_data[10] + '", '
                       'outline_width="' + custom_data[11] + '", '
                       'override_global="' + custom_data[12] + '", '
                       'use_shade="' + custom_data[13] + '", '
                       'shade_color="' + custom_data[14] + '", '
                       'shade_opacity="' + custom_data[15] + '" ,'
                       'audio_file="' + custom_data[16] + '", '
                       'loop_audio="' + custom_data[17] + '", '
                       'auto_play="' + custom_data[18] + '", '
                       'slide_delay="' + custom_data[19] + '", '
                       'split_slides="' + custom_data[20] + '" '
                       'WHERE title="' + old_title + '";')
            else:
                sql = ('INSERT INTO customSlides (title, text, font, fontColor, background, font_size, use_shadow, '
                       'shadow_color, shadow_offset, use_outline, outline_color, outline_width, override_global, '
                       'use_shade, shade_color, shade_opacity, audio_file, loop_audio, auto_play, slide_delay, '
                       'split_slides) VALUES ("' + custom_data[0] + '","' + custom_data[1] + '","' + custom_data[2]
                       + '","' + custom_data[3] + '","' + custom_data[4] + '","' + custom_data[5]
                       + '","' + custom_data[6] + '","' + custom_data[7] + '","' + custom_data[8]
                       + '","' + custom_data[9] + '","' + custom_data[10] + '","' + custom_data[11]
                       + '","' + custom_data[12] + '","' + custom_data[13] + '","' + custom_data[14]
                       + '","' + custom_data[15] + '","' + custom_data[16] + '","' + custom_data[17]
                       + '","' + custom_data[18] + '","' + custom_data[19] + '","' + custom_data[20] + '");')

            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()
            cursor.execute(sql)
            connection.commit()
            connection.close()
        except Exception:
            self.error_log()
            if connection:
                connection.close()

    def save_web_item(self, title, url):
        """
        Stores the title and url of a web slide to the program's database. Checks the database first to see if the
        given title already exists.
        :param str title: The title of the web slide
        :param url: The url the web slide is to fetch
        """
        connection = None
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()
            result = cursor.execute('SELECT * FROM web WHERE title="' + title + '"').fetchone()

            if result:
                sql = ('UPDATE web SET url="' + url + '" WHERE title="' + title + '"')
                cursor.execute(sql)
                connection.commit()
                connection.close()
            else:
                sql = ('INSERT INTO web (title, url) VALUES ("' + title + '", "' + url + '")')
                cursor.execute(sql)
                connection.commit()
                connection.close()
        except Exception:
            self.error_log()
            if connection:
                connection.close()

    def delete_item(self, item):
        """
        Provides a method of deleting a given item from the program's database.
        :param QListWidgetItem item: The item to be removed
        """
        connection = None
        try:
            if item.data(Qt.ItemDataRole.UserRole)['type'] == 'song':
                table = 'songs'
                description = 'Song'
            elif item.data(Qt.ItemDataRole.UserRole)['type'] == 'custom':
                table = 'customSlides'
                description = 'Custom Slide'
            elif item.data(Qt.ItemDataRole.UserRole)['type'] == 'video':
                file_name = item.data(Qt.ItemDataRole.UserRole)['file_name']
                os.remove(self.video_dir + '/' + file_name)
                filename_split = file_name.split('.')
                thumbnail_filename = '.'.join(filename_split[:len(filename_split) - 1]) + '.jpg'
                os.remove(self.video_dir + '/' + thumbnail_filename)
                return
            elif item.data(Qt.ItemDataRole.UserRole)['type'] == 'web':
                table = 'web'
                description = 'Web Page'
            else:
                return

            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()
            cursor.execute('DELETE FROM ' + table + ' WHERE title="' + item.data(Qt.ItemDataRole.UserRole)['title'] + '"')
            connection.commit()
            connection.close()

            QMessageBox.information(
                self.gui.main_window,
                description + 'Removed',
                item.data(Qt.ItemDataRole.UserRole)['title'] + ' has been removed.',
                QMessageBox.StandardButton.Ok
            )
        except Exception:
            self.error_log()
            if connection:
                connection.close()

    def delete_all_songs(self):
        """
        Provides a method for removing all of the songs from the database's 'songs' table. Checks and double-checks
        with the user that they really want to do this.
        """
        result = QMessageBox.question(
            self.gui.main_window,
            'Really Delete?',
            'This will remove ALL SONGS from your database. This cannot be undone. Really DELETE ALL SONGS?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if result == QMessageBox.StandardButton.Yes:
            result = QMessageBox.question(
                self.gui.main_window,
                'Really Delete?',
                'Just making sure: Do you really want to DELETE ALL SONGS?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
        else:
            return

        connection = None
        try:
            if result == QMessageBox.StandardButton.Yes:
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
        Saves all of the settings currently stored in the self.settings variable to the settings.json file in the
        program's data directory.
        """
        try:
            with open(self.data_dir + '/settings.json', 'w') as file:
                file.write(json.dumps(self.settings, indent=4))

            device_specific_settings = {}
            device_specific_settings['used_services'] = self.settings['used_services']
            device_specific_settings['last_save_dir'] = self.settings['last_save_dir']
            device_specific_settings['last_status_count'] = self.settings['last_status_count']
            device_specific_settings['selected_screen_name'] = self.settings['selected_screen_name']
            device_specific_settings['data_dir'] = self.data_dir
            with open(self.device_specific_config_file, 'w') as file:
                file.write(json.dumps(device_specific_settings, indent=4))

        except Exception:
            self.error_log()

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
            return

        try:
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
                if self.gui.oos_widget.oos_list_widget.item(i).data(Qt.ItemDataRole.UserRole)['type'] == 'custom_scripture':
                    service_items[i]['text'] = item_data['parsed_text']
                elif self.gui.oos_widget.oos_list_widget.item(i).data(Qt.ItemDataRole.UserRole)['type'] == 'custom':
                    service_items[i]['text'] = item_data['parsed_text']

            dialog_needed = True
            if self.gui.current_file:
                dialog_needed = False
            elif len(self.settings['last_save_dir']) > 0:
                save_dir = self.settings['last_save_dir']
            else:
                save_dir = os.path.expanduser('~' + '/Documents')

            result = 'saved'
            if dialog_needed:
                result = QFileDialog.getSaveFileName(
                    self.gui.main_window,
                    'Save Service File',
                    save_dir,
                    'ProjectOn Service File (*.pro)')

            if len(result[0]) > 0:
                try:
                    if result == 'saved':
                        file_loc = self.gui.current_file
                    else:
                        file_loc = result[0]

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
                    return 1
                except Exception as ex:
                    QMessageBox.information(
                        self.gui.main_window,
                        'Save Error',
                        'There was a problem saving the service: '
                        + file_loc.replace('/', '\\') + '\n\n' + str(ex),
                        QMessageBox.StandardButton.Ok
                    )
                    return -1
            else:
                return -1
        except Exception:
            self.error_log()
            return -1

    def load_service(self, filename=None):
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

        # open a file dialog if flename was not provided
        if not filename:
            if len(self.settings['last_save_dir']) > 0:
                open_dir = self.settings['last_save_dir']
            else:
                open_dir = os.path.expanduser('~' + '/Documents')

            result = QFileDialog.getOpenFileName(
                self.gui.main_window,
                'Load Service File',
                open_dir,
                'ProjectOn Service Files (*.pro)'
            )
        else:
            result = [filename]

        # because songs and bible verses are parsed as the order of service is being loaded, and this can take a bit,
        # provide a splash
        if len(result[0]) > 0:
            wait_widget = SimpleSplash(self.gui, 'Loading service...')
            service_dict = None

            try:
                with open(result[0], 'r') as file:
                    service_dict = json.load(file)

                json.dumps(service_dict, indent=4)
            except Exception:
                logging.exception('')

            if not service_dict:
                QMessageBox.information(
                    self.gui.main_window,
                    'Error Loading Service',
                    'Unable to load service. Please check that the file has not moved.',
                    QMessageBox.StandardButton.Ok
                )
                return

            if 'global_song_background' in service_dict.keys():
                self.settings['global_song_background'] = service_dict['global_song_background']
            if 'global_bible_background' in service_dict.keys():
                self.settings['global_bible_background'] = service_dict['global_bible_background']

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

            self.gui.apply_settings()

            # walk through the items saved in the file and load their QListWidgetItems into the order of service widget
            self.gui.oos_widget.oos_list_widget.clear()
            for key in service_dict:
                if key.isnumeric():
                    if service_dict[key]['type'] == 'song':
                        try:
                            song_item = self.gui.media_widget.song_list.findItems(
                                service_dict[key]['title'], Qt.MatchFlag.MatchExactly)[0].clone()
                        except IndexError:
                            song_item = None

                        if not song_item:
                            title = service_dict[key]['title']
                            QMessageBox.information(
                                None,
                                'Song Missing',
                                f'Saved song "{title}" not found in current database. '
                                f'Inserting placeholder.',
                                QMessageBox.StandardButton.Ok
                            )
                            item = QListWidgetItem('Missing song: ' + service_dict[key]['title'])
                            self.gui.oos_widget.oos_list_widget.addItem(item)
                        else:
                            self.gui.media_widget.add_song_to_service(song_item, from_load_service=True)

                    elif service_dict[key]['type'] == 'bible':
                        if service_dict[key]['title'] == 'custom_scripture':
                            self.gui.add_scripture_item(None, service_dict[key]['text'], None)
                        else:
                            if not self.gui.main.get_scripture:
                                from get_scripture import GetScripture
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
                                self.gui.add_scripture_item(reference, passages[1], version)

                    elif service_dict[key]['type'] == 'custom':
                        try:
                            custom_item = self.gui.media_widget.custom_list.findItems(
                                service_dict[key]['title'], Qt.MatchFlag.MatchExactly)[0]
                        except IndexError:
                            custom_item = None

                        if not custom_item:
                            title = service_dict[key]['title']
                            QMessageBox.information(
                                None,
                                'Custom Slide Missing',
                                f'Saved custom slide "{title}" not found in current database. '
                                f'Inserting placeholder.',
                                QMessageBox.StandardButton.Ok
                            )
                            item = QListWidgetItem('Missing custom slide: ' + service_dict[key]['title'])
                            self.gui.oos_widget.oos_list_widget.addItem(item)
                        else:
                            widget_item = QListWidgetItem()
                            item_data = custom_item.data(Qt.ItemDataRole.UserRole).copy()
                            widget_item.setData(Qt.ItemDataRole.UserRole, item_data)

                            if item_data['override_global'] == 'False' or not item_data['background']:
                                pixmap = self.gui.global_bible_background_pixmap
                                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                                       Qt.TransformationMode.SmoothTransformation)
                            elif item_data['background'] == 'global_song':
                                pixmap = self.gui.global_song_background_pixmap
                                pixmap = pixmap.scaled(
                                    50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                            elif item_data['background'] == 'global_bible':
                                pixmap = self.gui.global_bible_background_pixmap
                                pixmap = pixmap.scaled(
                                    50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                            elif 'rgb(' in item_data['background']:
                                pixmap = QPixmap(50, 27)
                                painter = QPainter(pixmap)
                                brush = QBrush(QColor(item_data['background']))
                                painter.fillRect(pixmap.rect(), brush)
                                painter.end()
                            else:
                                pixmap = QPixmap(
                                    self.gui.main.background_dir + '/' + item_data['background'])
                                pixmap = pixmap.scaled(
                                    50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

                            widget = StandardItemWidget(
                                self.gui, item_data['title'], 'Custom', pixmap)

                            widget_item.setSizeHint(widget.sizeHint())
                            self.gui.oos_widget.oos_list_widget.addItem(widget_item)
                            self.gui.oos_widget.oos_list_widget.setItemWidget(widget_item, widget)

                    elif service_dict[key]['type'] == 'image':
                        image_item = None
                        for i in range(self.gui.media_widget.image_list.count()):
                            if (self.gui.media_widget.image_list.item(i).data(Qt.ItemDataRole.UserRole)['title']
                                    == service_dict[key]['title']):
                                image_item = self.gui.media_widget.image_list.item(i).clone()
                                break

                        if not image_item:
                            title = service_dict[key]['title']
                            QMessageBox.information(
                                self.gui.main_window,
                                'Custom Slide Missing',
                                f'Saved image slide "{title}" not found in current database. '
                                f'Inserting placeholder.',
                                QMessageBox.StandardButton.Ok
                            )
                            item = QListWidgetItem('Missing image slide: ' + service_dict[key]['title'])
                            self.gui.oos_widget.oos_list_widget.addItem(item)
                        else:
                            pixmap = QPixmap(image_item.data(Qt.ItemDataRole.UserRole)['thumbnail'])
                            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation)

                            widget = StandardItemWidget(
                                self.gui, image_item.data(Qt.ItemDataRole.UserRole)['title'], 'Image', pixmap)

                            image_item.setSizeHint(widget.sizeHint())
                            self.gui.oos_widget.oos_list_widget.addItem(image_item)
                            self.gui.oos_widget.oos_list_widget.setItemWidget(image_item, widget)

                    elif service_dict[key]['type'] == 'video':
                        video_item = None
                        for i in range(self.gui.media_widget.video_list.count()):
                            if (self.gui.media_widget.video_list.item(i).data(Qt.ItemDataRole.UserRole)['title']
                                    == service_dict[key]['title']):
                                video_item = self.gui.media_widget.video_list.item(i).clone()

                        if not video_item:
                            title = service_dict[key]['title']
                            QMessageBox.information(
                                self.gui.main_window,
                                'Custom Slide Missing',
                                f'Saved video "{title}" not found in current database. '
                                f'Inserting placeholder.',
                                QMessageBox.StandardButton.Ok
                            )
                            item = QListWidgetItem('Missing video: ' + service_dict[key]['title'])
                            self.gui.oos_widget.oos_list_widget.addItem(item)
                        else:
                            pixmap = QPixmap(
                                self.gui.main.video_dir + '/' + video_item.data(Qt.ItemDataRole.UserRole)['file_name'].split('.')[
                                    0] + '.jpg')
                            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation)

                            widget = StandardItemWidget(
                                self.gui, video_item.data(Qt.ItemDataRole.UserRole)['title'], 'Video', pixmap)

                            video_item.setSizeHint(widget.sizeHint())
                            self.gui.oos_widget.oos_list_widget.addItem(video_item)
                            self.gui.oos_widget.oos_list_widget.setItemWidget(video_item, widget)

                    elif service_dict[key]['type'] == 'web':
                        web_item = None
                        for i in range(self.gui.media_widget.web_list.count()):
                            if (self.gui.media_widget.web_list.item(i).data(Qt.ItemDataRole.UserRole)['title']
                                    == service_dict[key]['title']):
                                web_item = self.gui.media_widget.web_list.item(i)

                        if not web_item:
                            title = service_dict[key]['title']
                            QMessageBox.information(
                                self.gui.main_window,
                                'Web Slide Missing',
                                f'Saved web slide "{title}" not found in current database. '
                                f'Inserting placeholder.',
                                QMessageBox.StandardButton.Ok
                            )
                            item = QListWidgetItem('Missing web slide: ' + service_dict[key]['title'])
                            self.gui.oos_widget.oos_list_widget.addItem(item)
                        else:
                            item = QListWidgetItem()
                            item.setData(Qt.ItemDataRole.UserRole, web_item.data(Qt.ItemDataRole.UserRole).copy())

                            pixmap = QPixmap(50, 27)
                            painter = QPainter(pixmap)
                            brush = QBrush(Qt.GlobalColor.black)
                            pen = QPen(Qt.GlobalColor.white)
                            painter.setPen(pen)
                            painter.setBrush(brush)
                            painter.begin(pixmap)
                            painter.fillRect(pixmap.rect(), brush)
                            painter.setFont(self.gui.bold_font)
                            painter.drawText(QPoint(2, 20), 'WWW')
                            painter.end()

                            widget = StandardItemWidget(
                                self.gui, web_item.data(Qt.ItemDataRole.UserRole)['title'], 'Web', pixmap)

                            item.setSizeHint(widget.sizeHint())
                            self.gui.oos_widget.oos_list_widget.addItem(item)
                            self.gui.oos_widget.oos_list_widget.setItemWidget(item, widget)

            self.gui.current_file = result[0]

            self.gui.preview_widget.slide_list.clear()
            self.gui.live_widget.slide_list.clear()

            # set the last used directory in settings
            file_dir = os.path.dirname(result[0])
            file_name = result[0].replace(file_dir, '').replace('/', '').replace('\\', '')
            self.settings['last_save_dir'] = file_dir

            # add this file to the recently used services menu
            self.add_to_recently_used(file_dir, file_name)

            # apply any settings changes
            self.gui.apply_settings()

            self.gui.changes = False
            wait_widget.widget.deleteLater()

    def add_to_recently_used(self, directory, file_name):
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

    def error_log(self):
        """
        Method to write a traceback to the program's error log file as well as show the user the error.
        """
        tb = traceback.walk_tb(sys.exc_info()[2])
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

        if not exists(os.path.expanduser('~/AppData/Roaming/ProjectOn/error.log')):
            with open(os.path.expanduser('~/AppData/Roaming/ProjectOn/error.log'), 'w') as file:
                pass

        with open(os.path.expanduser('~/AppData/Roaming/ProjectOn/error.log'), 'a') as file:
            file.write(log_text)

        message_box = QMessageBox()
        message_box.setIconPixmap(QPixmap('resources/gui_icons/face-palm.png'))
        message_box.setWindowTitle('An Error Occurred')
        message_box.setText('<strong>Well, that wasn\'t supposed to happen!</strong><br><br>' + message_box_text)
        message_box.setStandardButtons(QMessageBox.StandardButton.Close)
        message_box.exec()

    def check_db(self, db_file):
        db_structure = declarations.DB_STRUCTURE.copy()
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
            with open(os.path.expanduser('~/AppData/Roaming/ProjectOn/error.log'), 'a') as file:
                file.write(log_text)
        connection.close()


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
            if file not in filtered_files:
                reindex = True
                break

        for file in filtered_files:
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


class ServerCheck(QRunnable):
    """
    Creates a QRunnable that will periodically check that the three servers are up and running. Emits the GUI's
    server_alert_signal if the check fails.
    """
    def __init__(self, remote_server, gui):
        """
        :param RemoteServer remote_server: The current instance of RemoteServer
        :param gui.GUI gui: The current instance of GUI
        """
        super().__init__()
        self.remote_server = remote_server
        self.gui = gui
        self.keep_checking = True

    def run(self):
        while self.keep_checking:
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

                time.sleep(5)


def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    """
    Provides a method for handling exceptions that arent' handled elsewhere in the program.
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
    with open('./error.log', 'a') as file:
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
    message_box.exec()

if __name__ == '__main__':
    os.environ['QT_DEBUG_PLUGINS'] = '1'
    sys.excepthook = log_unhandled_exception
    monkey.patch_all(ssl=False)
    ProjectOn()
