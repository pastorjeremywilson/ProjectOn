import os
import re
from xml.etree import ElementTree

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QHBoxLayout, QPushButton, QLabel, \
    QMessageBox, QFileDialog, QApplication

from simple_splash import SimpleSplash


class OpenlyricsExport(QWidget):
    song_list = None

    def __init__(self, gui):
        super().__init__()
        self.gui = gui

        self.init_components()
        self.show()

    def init_components(self):
        layout = QVBoxLayout(self)
        self.setParent(self.gui.main_window)
        self.setWindowFlag(Qt.WindowType.Window)
        self.setWindowTitle('Export to OpenLyrics')
        self.setMinimumSize(600, 800)
        self.move(100, 50)

        title_label = QLabel('Choose songs to export:')
        title_label.setFont(self.gui.bold_font)
        layout.addWidget(title_label)

        check_button_widget = QWidget()
        check_button_layout = QHBoxLayout(check_button_widget)
        layout.addWidget(check_button_widget)

        self.song_list = QListWidget()
        self.song_list.setFont(self.gui.standard_font)
        for title in self.gui.main.get_song_titles():
            item = QListWidgetItem(title, self.song_list)
            item.setCheckState(Qt.CheckState.Unchecked)

        check_all_button = QPushButton('Check All')
        check_all_button.setFont(self.gui.standard_font)
        check_all_button.setStyleSheet('background: none; border: none; color: darkBlue;')
        check_all_button.pressed.connect(self.check_all)
        check_button_layout.addWidget(check_all_button)
        check_button_layout.addSpacing(20)

        uncheck_all_button = QPushButton('Uncheck All')
        uncheck_all_button.setFont(self.gui.standard_font)
        uncheck_all_button.setStyleSheet('background: none; border: none; color: darkBlue;')
        uncheck_all_button.pressed.connect(self.uncheck_all)
        check_button_layout.addWidget(uncheck_all_button)
        check_button_layout.addStretch()

        layout.addWidget(self.song_list)

        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        layout.addWidget(button_widget)

        export_button = QPushButton('Export Songs')
        export_button.setFont(self.gui.standard_font)
        export_button.pressed.connect(self.do_export)
        button_layout.addWidget(export_button)
        button_layout.addSpacing(20)

        cancel_button = QPushButton('Cancel')
        cancel_button.setFont(self.gui.standard_font)
        cancel_button.pressed.connect(self.deleteLater)
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()

    def check_all(self):
        for i in range(self.song_list.count()):
            self.song_list.item(i).setCheckState(Qt.CheckState.Checked)

    def uncheck_all(self):
        for i in range(self.song_list.count()):
            self.song_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    def do_export(self):
        song_titles = []
        num_songs = 0
        for i in range(self.song_list.count()):
            if self.song_list.item(i).checkState() == Qt.CheckState.Checked:
                song_titles.append(self.song_list.item(i).text())
                num_songs += 1

        if num_songs == 0:
            QMessageBox.information(
                self.gui.main_window,
                'No Songs',
                'So songs selected.',
                QMessageBox.StandardButton.Ok
            )
        else:
            result = QFileDialog.getExistingDirectory(
                self,
                'Choose Export Folder',
                os.path.expanduser('~') + '/Documents')

            saving_splash = SimpleSplash(self.gui, 'Saving Songs...')

            if len(result) > 0:
                counter = 1
                for title in song_titles:
                    saving_splash.label.setText('Saving song ' + str(counter) + ' of ' + str(num_songs))
                    QApplication.processEvents()
                    counter += 1

                    song_data = self.gui.main.get_song_data(title)

                    song = ElementTree.Element('song')
                    song.set('xmlns', 'http://openlyrics.info/namespace/2009/song')
                    song.set('version', '0.9')
                    song.set('createdIn', 'ProjectOn')

                    properties = ElementTree.SubElement(song, 'properties')

                    titles = ElementTree.SubElement(properties, 'titles')

                    title_element = ElementTree.SubElement(titles, 'title')
                    title_element.text = title

                    authors = ElementTree.SubElement(properties, 'authors')
                    author = ElementTree.SubElement(authors, 'author')
                    author.text = song_data[1]

                    copyright = ElementTree.SubElement(properties, 'copyright')
                    copyright.text = song_data[2]

                    verse_order = ElementTree.SubElement(properties, 'verseOrder')
                    verse_order.text = song_data[5]

                    ccli_number = ElementTree.SubElement(properties, 'ccliNo')
                    ccli_number.text = song_data[3]

                    lyrics = ElementTree.SubElement(song, 'lyrics')

                    if '[' in song_data[4]:
                        lyric_split = song_data[4].split('[')
                        for segment in lyric_split:
                            if len(segment) > 0:
                                tag_split = segment.split(']')
                                tag = tag_split[0]

                                segment_split = re.split('<br.*?>', tag_split[1])
                                for i in range(len(segment_split)):
                                    segment_split[i] = re.sub('<.*?>', '', segment_split[i])
                                lyrics_text = '<br />'.join(segment_split)

                                verse_element = ElementTree.SubElement(lyrics, 'verse')
                                verse_element.set('name', tag)

                                lines = ElementTree.SubElement(verse_element, 'lines')
                                lines.text = lyrics_text

                    ElementTree.indent(song, '   ', 0)
                    file_contents = ElementTree.tostring(song, encoding='unicode')
                    file_contents = file_contents.replace('&lt;', '<')
                    file_contents = file_contents.replace('&gt;', '>')
                    file_contents = file_contents.replace(chr(8216), '\'')
                    file_contents = file_contents.replace(chr(8217), '\'')
                    file_contents = file_contents.replace(chr(8220), '"')
                    file_contents = file_contents.replace(chr(8221), '"')
                    file_contents = ('<?xml version="1.0" encoding="utf-8"?>\n'
                                     '<?xml-stylesheet href="../stylesheets/openlyrics.css" type="text/css"?>\n'
                                     + file_contents)

                    invalid = '<>:"/\|?*'
                    for char in invalid:
                        title = title.replace(char, '')

                    with open(result + '/' + title + '.xml', 'w', encoding='utf-8') as file:
                        file.write(file_contents)

                self.deleteLater()
