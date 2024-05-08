"""
This file and all files contained within this distribution are parts of the ProjectOn worship projection software.

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
import threading
import time
import traceback
from os.path import exists
from xml.etree import ElementTree

import requests
from PyQt6.QtCore import Qt, QByteArray, QBuffer, QIODevice, QRunnable, QThreadPool, pyqtSignal, QObject, QPoint
from PyQt6.QtGui import QPixmap, QFont, QPainter, QBrush, QColor, QPen, QAction
from PyQt6.QtWidgets import QApplication, QLabel, QListWidgetItem, QWidget, QVBoxLayout, QFileDialog, QMessageBox, \
    QProgressBar

from gui import GUI
from simple_splash import SimpleSplash
from web_remote import RemoteServer


class ProjectOn(QObject):
    """
    Main entry point of the program. Loads necessary configuration information, starts the GUI and its QApplication,
    starts the web server.
    """
    app = None
    data_dir = None
    database = None
    bible_dir = None
    commit_done_event = threading.Event()
    get_scripture = None
    settings = None
    remote_server = None
    splash_widget = None
    status_label = None
    update_status_signal = pyqtSignal(str, str)
    info_label = None
    initial_startup = True
    portable = True

    status_update_count = 0

    def __init__(self):
        super().__init__()

        #not currently implimented, but sets different directory locations for a portable or standard installment
        if self.portable:
            os.chdir(os.path.dirname(__file__))
            self.data_dir = os.path.dirname(os.path.abspath(__file__)).replace('\\\\', '/') + '/data'
            self.config_file = self.data_dir + '/settings.json'
            self.device_specific_config_file = os.path.expanduser('~/AppData/Roaming/ProjectOn/localConfig.json')
            self.database = self.data_dir + '/projecton.db'
            self.background_dir = self.data_dir + '/backgrounds'
            self.image_dir = self.data_dir + '/images'
            self.bible_dir = self.data_dir + '/bibles'
            self.video_dir = self.data_dir + '/videos'
        else:
            self.data_dir = os.path.expanduser('~/AppData/Roaming/ProjectOn')
            self.config_file = self.data_dir + '/settings.json'
            self.device_specific_config_file = self.data_dir + '/localConfig.json'
            self.database = self.data_dir + '/projecton.db'
            self.background_dir = self.data_dir + '/backgrounds'
            self.image_dir = self.data_dir + '/images'
            self.bible_dir = self.data_dir + '/bibles'
            self.video_dir = self.data_dir + '/videos'

        if not exists(os.path.expanduser('~/AppData/Roaming/ProjectOn')):
            os.mkdir(os.path.expanduser('~/AppData/Roaming/ProjectOn'))
        if not exists(self.config_file):
            if exists(self.data_dir + '/settings.json'):
                shutil.copy(self.data_dir + '/settings.json', self.config_file)
        if not exists(self.device_specific_config_file):
            device_specific_settings = {'used_services': '', 'last_save_dir': ''}

        # ensure all needed files exist; thread it and wait until done before moving on
        self.thread_pool = QThreadPool()
        cf = CheckFiles(self)
        self.thread_pool.start(cf)
        self.thread_pool.waitForDone()

        os.environ['QT_MULTIMEDIA_PREFERRED_PLUGINS'] = 'windowsmediafoundation'

        self.server_thread_pool = QThreadPool()
        self.update_status_signal.connect(self.update_status_label)

        # create a web socket to be used for sending data to/from the remote and stage view servers
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('192.255.255.255', 1))
        self.ip = s.getsockname()[0]

        self.app = QApplication(sys.argv)

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

        if exists(self.data_dir + '/settings.json'):
            with open(self.data_dir + '/settings.json', 'r') as file:
                try:
                    self.settings = json.loads(file.read())
                except json.decoder.JSONDecodeError:
                    self.settings = {}
        else:
            self.settings = default_settings

        if exists(self.device_specific_config_file):
            with open(self.device_specific_config_file, 'r') as file:
                device_specific_settings = json.loads(file.read())

            self.settings['used_services'] = device_specific_settings['used_services']
            self.settings['last_save_dir'] = device_specific_settings['last_save_dir']

        for key in default_settings:
            if not key in self.settings.keys():
                self.settings[key] = default_settings[key]
        self.get_song_titles()

        self.make_splash_screen()

        self.update_status_signal.emit('Checking Files', 'status')
        self.app.processEvents()

        self.status_label.setText('Indexing Images')
        self.app.processEvents()

        ii = IndexImages(self, 'backgrounds')
        self.thread_pool.start(ii)
        self.thread_pool.waitForDone()

        ii = IndexImages(self, 'images')
        self.thread_pool.start(ii)
        self.thread_pool.waitForDone()

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

        if len(self.settings) > 0:
            self.gui.apply_settings()

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

    def make_splash_screen(self):
        """
        Create the splash screen that will show progress as the program is loading
        """
        self.splash_widget = QWidget()
        self.splash_widget.setObjectName('splash_widget')
        self.splash_widget.setMinimumWidth(450)
        self.splash_widget.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.splash_widget.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, True)
        self.splash_widget.setStyleSheet(
            '#splash_widget { background: #5555aa; }')
        splash_layout = QVBoxLayout(self.splash_widget)
        splash_layout.setContentsMargins(20, 20, 20, 20)

        container = QWidget()
        container.setObjectName('container')
        container.setStyleSheet('#container { background: #5555aa; border: 2px solid white; }')
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
        if self.settings['last_status_count']:
            self.progress_bar.setRange(0, self.settings['last_status_count'])
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            'QProgressBar { border: 1px solid white; background: white; } '
            'QProgressBar::chunk { background-color: #5555aa; }'
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
            result = cursor.execute('SELECT * FROM songs ORDER BY title').fetchall()
            connection.close()
            return result
        except Exception:
            self.error_log()
            if connection:
                connection.close()
            return -1

    def get_all_custom_slides(self):
        """
        Retrieves all custom slide data from the ProjectOn database's 'customSlides' table
        :return: list of str result
        """
        connection = None
        try:
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()
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
                    song_data[i] = song_data[i].replace('"', '""')
                else:
                    song_data[i] = ''
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()

            if old_title:
                sql = ('UPDATE songs SET '
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
                       'font_size="' + song_data[10] + '" WHERE title="' + old_title + '"')
            else:
                sql = ('INSERT INTO songs (title, author, copyright, ccliNum, lyrics, vorder, footer, font, fontColor, '
                       'background) VALUES ("' + song_data[0] + '","' + song_data[1] + '","' + song_data[2] + '","'
                       + song_data[3] + '","' + song_data[4] + '","' + song_data[5] + '","' + song_data[6]
                       + '","' + song_data[7] + '","' + song_data[8] + '","' + song_data[9] + '")')

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
            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()

            if old_title:
                sql = ('UPDATE customSlides SET '
                       'title="' + custom_data[0] + '", '
                       'text="' + custom_data[1] + '", ' 
                       'font="' + custom_data[2] + '", ' 
                       'fontColor="' + custom_data[3] + '", ' 
                       'background="' + custom_data[4] + '", '
                       'font_size="' + custom_data[5] + '" WHERE title="' + old_title + '"')
            else:
                sql = ('INSERT INTO customSlides (title, text, font, fontColor, background) VALUES '
                       '("' + custom_data[0] + '","' + custom_data[1] + '","' + custom_data[2] + '","'
                       + custom_data[3] + '","' + custom_data[4] + '")')

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
            if item.data(30) == 'song':
                table = 'songs'
                description = 'Song'
            elif item.data(30) == 'custom':
                table = 'customSlides'
                description = 'Custom Slide'
            elif item.data(30) == 'video':
                os.remove(self.video_dir + '/' + item.data(20))
                filename_split = item.data(20).split('.')
                thumbnail_filename = '.'.join(filename_split[:len(filename_split) - 1]) + '.jpg'
                os.remove(self.video_dir + '/' + thumbnail_filename)
                return
            elif item.data(30) == 'web':
                table = 'web'
                description = 'Web Page'
            else:
                return

            connection = sqlite3.connect(self.database)
            cursor = connection.cursor()
            cursor.execute('DELETE FROM ' + table + ' WHERE title="' + item.data(20) + '"')
            connection.commit()
            connection.close()

            QMessageBox.information(
                self.gui.main_window,
                description + 'Removed',
                item.data(20) + ' has been removed.',
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
            if not self.gui.tool_bar.font_widget.font_list_widget.currentText():
                self.gui.tool_bar.font_widget.font_list_widget.setCurrentText('Arial')

            service_items = {
                'global_song_background': self.settings['global_song_background'],
                'global_bible_background': self.settings['global_bible_background'],
                'font_face': self.settings['font_face'],
                'font_size': self.settings['font_size'],
                'font_color': self.settings['font_color'],
                'use_shadow': self.settings['use_shadow'],
                'shadow_color': self.settings['shadow_color'],
                'shadow_offset': self.settings['shadow_offset'],
                'use_outline': self.settings['use_outline'],
                'outline_color': self.settings['outline_color'],
                'outline_width': self.settings['outline_width'],
            }

            for i in range(self.gui.oos_widget.oos_list_widget.count()):
                service_items[i] = {
                    'title': self.gui.oos_widget.oos_list_widget.item(i).data(20),
                    'type': self.gui.oos_widget.oos_list_widget.item(i).data(30)
                }
            """for i in range(self.gui.oos_widget.oos_list_widget.count()):
                service_items[i] = {}
                for j in range(20, 33):
                    if j == 21 and self.gui.oos_widget.oos_list_widget.item(i).data(30) == 'bible':
                        service_items[i][j] = self.gui.oos_widget.oos_list_widget.item(i).data(j)
                    elif j == 31:
                        service_items[i][j] = self.gui.oos_widget.oos_list_widget.item(i).data(j)
                        if self.gui.oos_widget.oos_list_widget.item(i).data(30) == 'image':
                            service_items[i][j][2] = ''
                    else:
                        if type(self.gui.oos_widget.oos_list_widget.item(i).data(j)) == bytes:
                            service_items[i][j] = ''
                        else:
                            service_items[i][j] = str(self.gui.oos_widget.oos_list_widget.item(i).data(j))"""

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
                        filename = self.gui.current_file
                    else:
                        filename = result[0]

                    with open(filename, 'w') as file:
                        json.dump(service_items, file, indent=4)

                    directory = os.path.dirname(filename)
                    filename = filename.replace(directory, '').replace('/', '')
                    self.settings['last_save_dir'] = directory
                    self.save_settings()

                    QMessageBox.information(
                        self.gui.main_window,
                        'File Saved',
                        'Service saved as\n' + filename.replace('/', '\\'),
                        QMessageBox.StandardButton.Ok
                    )

                    # add this file to the recently used services menu
                    self.add_to_recently_used(directory, filename)

                    self.gui.current_file = filename
                    self.gui.changes = False
                    return 1
                except Exception as ex:
                    QMessageBox.information(
                        self.gui.main_window,
                        'Save Error',
                        'There was a problem saving the service:\n\n' + str(ex),
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
            if 'font_face' in service_dict.keys():
                self.settings['font_face'] = service_dict['font_face']
            if 'font_size' in service_dict.keys():
                self.settings['font_size'] = service_dict['font_size']
            if 'font_color' in service_dict.keys():
                self.settings['font_color'] = service_dict['font_color']
            if 'use_shadow' in service_dict.keys():
                self.settings['use_shadow'] = service_dict['use_shadow']
            if 'shadow_color' in service_dict.keys():
                self.settings['shadow_color'] = service_dict['shadow_color']
            if 'shadow_offset' in service_dict.keys():
                self.settings['shadow_offset'] = service_dict['shadow_offset']
            if 'use_outline' in service_dict.keys():
                self.settings['use_outline'] = service_dict['use_outline']
            if 'outline_color' in service_dict.keys():
                self.settings['outline_color'] = service_dict['outline_color']
            if 'outline_width' in service_dict.keys():
                self.settings['outline_width'] = service_dict['outline_width']

            self.gui.apply_settings()

            # walk through the items saved in the file and load their QListWidgetItems into the order of service widget
            self.gui.oos_widget.oos_list_widget.clear()
            from media_widget import OOSItemWidget
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
                        if not self.gui.main.get_scripture:
                            from get_scripture import GetScripture
                            self.gui.main.get_scripture = GetScripture(self.gui.main)
                        passages = self.gui.main.get_scripture.get_passage(service_dict[key]['title'])
                        if passages[0] == -1:
                            QMessageBox.information(
                                self.gui.main_window,
                                'Error Loading Scripture',
                                'Unable to load scripture passage "' + service_dict[key]['title'] + '". "' + passages[1] + '"',
                                QMessageBox.StandardButton.Ok
                            )
                        else:
                            scripture = ''
                            for passage in passages[1]:
                                scripture += passage + ' '

                            reference = service_dict[key]['title']
                            text = scripture
                            version = self.gui.media_widget.bible_selector_combobox.currentText()
                            self.gui.add_scripture_item(reference, scripture, version)

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
                            for i in range(20, 33):
                                widget_item.setData(i, custom_item.data(i))

                            if widget_item.data(29) == 'global_song':
                                pixmap = self.gui.global_song_background_pixmap
                                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                            elif widget_item.data(29) == 'global_bible':
                                pixmap = self.gui.global_bible_background_pixmap
                                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                            elif 'rgb(' in widget_item.data(29):
                                pixmap = QPixmap(50, 27)
                                painter = QPainter(pixmap)
                                brush = QBrush(QColor(widget_item.data(29)))
                                painter.fillRect(pixmap.rect(), brush)
                                painter.end()
                            else:
                                pixmap = QPixmap(self.gui.main.background_dir + '/' + widget_item.data(29))
                                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

                            widget = OOSItemWidget(self.gui, pixmap, widget_item.data(20), 'Custom')

                            widget_item.setSizeHint(widget.sizeHint())
                            self.gui.oos_widget.oos_list_widget.addItem(widget_item)
                            self.gui.oos_widget.oos_list_widget.setItemWidget(widget_item, widget)

                    elif service_dict[key]['type'] == 'image':
                        image_item = None
                        for i in range(self.gui.media_widget.image_list.count()):
                            if self.gui.media_widget.image_list.item(i).data(20) == service_dict[key]['title']:
                                image_item = self.gui.media_widget.image_list.item(i).clone()

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
                            pixmap = QPixmap()
                            pixmap.loadFromData(image_item.data(21), 'JPG')
                            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation)

                            widget = OOSItemWidget(self.gui, pixmap, image_item.data(20), 'Image')

                            image_item.setSizeHint(widget.sizeHint())
                            self.gui.oos_widget.oos_list_widget.addItem(image_item)
                            self.gui.oos_widget.oos_list_widget.setItemWidget(image_item, widget)

                    elif service_dict[key]['type'] == 'video':
                        video_item = None
                        for i in range(self.gui.media_widget.video_list.count()):
                            if self.gui.media_widget.video_list.item(i).data(20) == service_dict[key]['title']:
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
                                self.gui.main.video_dir + '/' + video_item.data(20).split('.')[
                                    0] + '.jpg')
                            pixmap = pixmap.scaled(96, 54, Qt.AspectRatioMode.IgnoreAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation)

                            widget = OOSItemWidget(self.gui, pixmap, video_item.data(20), 'Image')

                            video_item.setSizeHint(widget.sizeHint())
                            self.gui.oos_widget.oos_list_widget.addItem(video_item)
                            self.gui.oos_widget.oos_list_widget.setItemWidget(video_item, widget)

                    elif service_dict[key]['type'] == 'web':
                        web_item = None
                        for i in range(self.gui.media_widget.web_list.count()):
                            if self.gui.media_widget.web_list.item(i).data(20) == service_dict[key]['title']:
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
                            item.setData(20, web_item.data(20))
                            item.setData(21, web_item.data(21))
                            item.setData(30, 'web')
                            item.setData(31, ['', web_item.data(20),
                                              web_item.data(21)])

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

                            widget = OOSItemWidget(self.gui,pixmap, web_item.data(21), 'Web')

                            item.setSizeHint(widget.sizeHint())
                            self.gui.oos_widget.oos_list_widget.addItem(item)
                            self.gui.oos_widget.oos_list_widget.setItemWidget(item, widget)

            self.gui.current_file = result[0]

            self.gui.preview_widget.slide_list.clear()
            self.gui.live_widget.slide_list.clear()

            # set the last used directory in settings
            file_dir = os.path.dirname(result[0])
            file_name = result[0].replace(file_dir, '').replace('/', '')
            self.settings['last_save_dir'] = file_dir

            # add this file to the recently used services menu
            self.add_to_recently_used(file_dir, file_name)

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

        if len(file[0]) > 0:
            result = QMessageBox.question(
                self.gui.main_window,
                'Make Default',
                'Make this your default bible?',
                QMessageBox.StandardButton.Yes,
                QMessageBox.StandardButton.No
            )

            file_name_split = file[0].split('/')
            file_name = file_name_split[len(file_name_split) - 1]
            shutil.copy(file[0], self.bible_dir + '/' + file_name)

            if result == QMessageBox.StandardButton.Yes:
                self.settings['default_bible'] = self.bible_dir + '/' + file_name

            tree = ElementTree.parse(self.gui.main.data_dir + '/bibles/' + file)
            root = tree.getroot()
            name = root.attrib['biblename']

            self.gui.media_widget.bible_selector_combobox.addItem(name)
            self.gui.media_widget.bible_selector_combobox.setItemData(
                self.gui.media_widget.bible_selector_combobox.count() - 1,
                self.bible_dir + '/' + file_name, Qt.ItemDataRole.UserRole
            )

    def error_log(self):
        """
        Method to write a traceback to the program's error log file as well as show the user the error.
        """
        tb = traceback.walk_tb(sys.exc_info()[2])
        for frame, line_no in tb:
            clss = str(frame.f_locals['self']).split('<')[1].split(' ')[0].split('.')[1]
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
            date_time = time.time()
            log_text = (f'\n{date_time}:\n'
                        f'    {sys.exc_info()[1]} on line {line_num} of {file_name} in {clss}.{method}')

        with open('./error.log', 'a') as file:
            file.write(log_text)
        QMessageBox.critical(None, 'An Error Occurred', message_box_text, QMessageBox.StandardButton.Ok)
        self.app.processEvents()


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
        defaults_dir = os.path.dirname(os.path.abspath(__file__)).replace('\\\\', '/') + '/resources/defaults'
        try:
            if not exists(self.main.data_dir):
                os.mkdir(self.main.data_dir)

            if not exists(self.main.config_file):
                config = {
                    'selected_screen_name': '',
                    'font_face': 'Helvetica',
                    'font_size': 60,
                    'font_color': 'white',
                    'global_song_background': '',
                    'global_bible_background': '',
                    'logo_image': '',
                    'last_save_dir': '',
                    'last_status_count': 1000,
                    'stage_font_size': 60,
                    'use_shadow': False,
                    'shadow_color': 190,
                    'use_outline': True,
                    'outline_color': 0,
                    'outline_width': 3,
                    'ccli_num': '',
                    'used_services': [],
                    'default_bible': ''
                }
                with open(self.main.config_file, 'w') as file:
                    file.write(json.dumps(config, indent=4))

            if not exists(self.main.database):
                shutil.copy(defaults_dir + '/default_database.db', self.main.database)

            if not exists(self.main.background_dir):
                os.mkdir(self.main.background_dir)
                default_background_dir = defaults_dir + '/backgrounds'
                image_files = os.listdir(default_background_dir)
                for file in image_files:
                    shutil.copy(default_background_dir + '/' + file, self.main.background_dir + '/' + file)

            if not exists(self.main.image_dir):
                os.mkdir(self.main.image_dir)
                default_image_dir = defaults_dir + '/images'
                image_files = os.listdir(default_image_dir)
                for file in image_files:
                    shutil.copy(default_image_dir + '/' + file, self.main.image_dir + '/' + file)

            if not exists(self.main.bible_dir):
                os.mkdir(self.main.bible_dir)
                default_bible_dir = defaults_dir + '/bibles'
                bible_files = os.listdir(default_bible_dir)
                for file in bible_files:
                    shutil.copy(default_bible_dir + '/' + file, self.main.bible_dir + '/' + file)

            if not exists(self.main.video_dir):
                os.mkdir(self.main.video_dir)
                default_video_dir = defaults_dir + '/videos'
                video_files = os.listdir(default_video_dir)
                for file in video_files:
                    shutil.copy(default_video_dir + '/' + file, self.main.video_dir + '/' + file)
        except Exception:
            self.main.error_log()


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
        file_list = os.listdir(self.directory)

        filtered_files = []
        for file in file_list:
            file_type = file.split('.')[1]
            if file_type == 'jpg' or file_type == 'png' or file_type == 'svg':
                filtered_files.append(file)

        reindex = False
        for record in thumbnails:
            if not record[0] in file_list:
                reindex = True
                break

        for file in filtered_files:
            file_found = False
            for record in thumbnails:
                if record[0] == file:
                    file_found = True
            if not file_found:
                reindex = True
                break

        if not reindex and not self.force:
            return

        cursor.execute('DELETE FROM ' + self.table)
        connection.commit()
        for file in file_list:
            file_type = file.split('.')[1]
            if file_type == 'jpg' or file_type == 'png' or file_type == 'svg':
                pixmap = QPixmap(self.directory + '/' + file)
                pixmap = pixmap.scaled(96, 54, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

                array = QByteArray()
                buffer = QBuffer(array)
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                pixmap.save(buffer, 'JPG')
                blob = bytes(array.data())
                cursor.execute('INSERT INTO ' + self.table + ' (fileName, image) VALUES("' + file + '", ?)', (blob,))

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

    date_time = time.time()
    log_text = (f'\n{date_time}:\n'
                f'    UNHANDLED EXCEPTION\n'
                f'    {exc_type}\n'
                f'    {exc_value}\n'
                f'    {full_traceback}')
    with open('./error.log', 'a') as file:
        file.write(log_text)

    QMessageBox.critical(
        None,
        'Unhandled Exception',
        'An unhandled exception occurred:\n\n'
        f'{exc_type}\n'
        f'{exc_value}\n'
        f'{full_traceback}',
        QMessageBox.StandardButton.Close
    )

if __name__ == '__main__':
    sys.excepthook = log_unhandled_exception
    ProjectOn()
