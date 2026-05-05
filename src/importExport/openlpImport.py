import json
import os.path
import os.path
import re
import sqlite3
from xml.etree import ElementTree as ET

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QLineEdit, QPushButton, QProgressBar, \
    QFileDialog, QMessageBox, QDialog

from dataHandling.declarations import SLIDE_DATA_DEFAULTS
from dataHandling.parsers import parse_song_data


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
        self.widget = QDialog()
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        self.widget.setWindowTitle('OpenLP Import')

        file_widget = QWidget()
        file_layout = QHBoxLayout()
        file_widget.setLayout(file_layout)
        layout.addWidget(file_widget)

        file_label = QLabel('OpenLP Database:')
        file_label.setFont(self.gui.standard_font)
        file_layout.addWidget(file_label)

        self.file_line_edit = QLineEdit()
        self.file_line_edit.setFont(self.gui.standard_font)
        file_layout.addWidget(self.file_line_edit)

        load_button = QPushButton('Load File')
        load_button.setFont(self.gui.standard_font)
        load_button.clicked.connect(self.load_file)
        file_layout.addWidget(load_button)

        cancel_button = QPushButton('Cancel')
        cancel_button.setFont(self.gui.standard_font)
        cancel_button.clicked.connect(lambda: self.widget.done(0))

        self.song_label = QLabel()
        self.song_label.setFont(self.gui.standard_font)
        layout.addWidget(self.song_label)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.start_button = QPushButton('Start Import')
        self.start_button.setFont(self.gui.standard_font)
        self.start_button.clicked.connect(self.start_import)
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

                # remove 'o' tags and convert to 't' tags
                verse_order = song[4]
                verse_order_split = verse_order.strip().split(' ')
                for i in range(len(verse_order_split)):
                    if verse_order_split[i][0] == 'o':
                        if len(verse_order_split[i]) > 1:
                            verse_order_split[i] = 't' + verse_order_split[i][1]
                        else:
                            verse_order_split[i] = 't1'
                verse_order = ' '.join(verse_order_split)

                data = SLIDE_DATA_DEFAULTS
                data['type'] = 'song'
                data['title'] = title
                data['author'] = author
                data['copyright'] = song[5]
                data['ccli_song_number'] = song[7]
                data['verse_order'] = verse_order
                data['text'] = self.convert_lyrics(song[3])
                data['parsed_text'] = parse_song_data(self.gui, data)

                self.gui.main.save_song(data)

            self.gui.media_widget.populate_song_list()
            self.widget.done(0)

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
            text = re.sub(r'\{.*?\}', '', element.text).strip()
            text = text.replace('[---]\n', '')
            text = text.replace('\n', '<br />')
            type = element.attrib['type'][0].lower()
            if type == 'o':
                type = 't'
            converted_lyrics += '[' + type + element.attrib['label'] + ']<p>' + text + '</p>'

        return converted_lyrics.strip()
