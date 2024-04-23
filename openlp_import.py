import os.path
import os.path
import re
import sqlite3
from xml.etree import ElementTree as ET

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QLineEdit, QPushButton, QProgressBar, \
    QFileDialog, QMessageBox


class OpenLPImport:
    """
    Provides the ability to import and parse songs from an OpenLP sqlite database.
    """
    def __init__(self, gui):
        """
        Provides the ability to import and parse songs from an OpenLP sqlite database.
        :param gui.GUI gui: the current instance of GUI
        """
        self.gui = gui
        self.init_components()

    def init_components(self):
        """
        Creates and lays out the widget prompting the user to import their database and shows a progress bar when
        importing.
        """
        self.widget = QWidget()
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        self.widget.setWindowTitle('OpenLP Import')

        file_widget = QWidget()
        file_layout = QHBoxLayout()
        file_widget.setLayout(file_layout)
        layout.addWidget(file_widget)

        file_label = QLabel('OpenLP Database:')
        file_layout.addWidget(file_label)

        self.file_line_edit = QLineEdit()
        file_layout.addWidget(self.file_line_edit)

        load_button = QPushButton('load file')
        load_button.pressed.connect(self.load_file)
        file_layout.addWidget(load_button)

        self.song_label = QLabel()
        layout.addWidget(self.song_label)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.start_button = QPushButton('Start Import')
        self.start_button.pressed.connect(self.start_import)
        layout.addWidget(self.start_button)
        self.start_button.setEnabled(False)

        self.widget.show()

    def load_file(self):
        """
        Creates a QFileDialog for the user to locate their OpenLP Database
        """
        file_dialog = QFileDialog()
        file = file_dialog.getOpenFileName(self.widget, 'Choose File', os.path.expanduser('~'),
                                                 'OpenLP Database (*.sqlite)')

        if len(file[0]) > 0:
            self.openlp_database_file = file[0]
            self.file_line_edit.setText(self.openlp_database_file)
            self.start_button.setEnabled(True)

    def start_import(self):
        """
        Method to perform the task of retrieving the song data from the OpenLP database.
        """
        connection = None
        try:
            connection = sqlite3.connect(self.openlp_database_file)
            cursor = connection.cursor()

            result = cursor.execute('SELECT * FROM songs').fetchall()
            num_songs = len(result)
            self.progress_bar.setRange(0, num_songs)
            self.progress_bar.setValue(0)

            for song in result:
                self.song_label.setText(song[1])
                title = song[1]
                auth_num = cursor.execute('SELECT song_id FROM authors_songs WHERE song_id = ' + str(song[0])).fetchone()
                author = cursor.execute('SELECT display_name FROM authors WHERE id = ' + str(auth_num[0])).fetchone()
                if author:
                    author = author[0]
                else:
                    author = ''
                copyright = song[5]
                ccli_song_num = song[7]
                song_order = song[4]
                lyrics = song[3]
                footer = 'true'

                # rearrange the song's data to conform to the order used in this program's database
                converted_lyrics = self.convert_lyrics(lyrics)
                self.gui.main.save_song(
                    [
                        title,
                        author,
                        copyright,
                        ccli_song_num,
                        converted_lyrics,
                        song_order,
                        footer,
                        'global',
                        'global',
                        'global'
                    ]
                )
                self.progress_bar.setValue(self.progress_bar.value() + 1)
            self.gui.media_widget.populate_song_list()
            self.widget.deleteLater()

        except Exception as ex:
            self.gui.main.error_log()
            if connection:
                connection.close()
            QMessageBox.information(
                self.widget,
                'Import Error',
                'File is not a valid OpenLP Database' + str(ex),
                QMessageBox.StandardButton.Ok)

    def convert_lyrics(self, lyrics):
        """
        Method to change OpenLp's segment tags to this program's segment tags.
        :param str lyrics: The song's lyrics
        :return str converted_lyrics: The reformatted lyrics
        """
        root = ET.fromstring(lyrics)
        lyrics = root.find('lyrics')
        converted_lyrics = ''
        for element in lyrics:
            text = re.sub('\{.*?\}', '', element.text).rstrip()
            text = text.replace('[---]\n', '')
            text = text.replace('\n', '<br />')
            type = element.attrib['type'][0].lower()
            converted_lyrics += '[' + type + element.attrib['label'] + ']<p>' + text + '</p>'

        return converted_lyrics.strip()
