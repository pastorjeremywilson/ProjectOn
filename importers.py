import os
import re
from xml.etree import ElementTree

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QDialog, QVBoxLayout, QLabel, QLineEdit, QWidget, QHBoxLayout, \
    QPushButton, QRadioButton, QButtonGroup

from widgets import SimpleSplash


class Importers:
    CHORDPRO = 0
    OPENLYRICS = 1
    import_type = None
    dupe_index = 1

    def __init__(self, gui):
        self.gui = gui

    def do_import(self, import_type):
        self.import_type = import_type

        dialog = QDialog(self.gui.main_window)
        dialog_layout = QVBoxLayout(dialog)
        dialog.setWindowTitle('Import Type')

        label = QLabel('Import a single file or batch import an entire folder?')
        label.setFont(self.gui.standard_font)
        dialog_layout.addWidget(label)

        ok_button = QPushButton('OK')
        ok_button.setEnabled(False)

        radio_button_widget = QWidget(dialog)
        radio_button_layout = QHBoxLayout(radio_button_widget)
        dialog_layout.addWidget(radio_button_widget)

        single_radio_button = QRadioButton('Single File')
        single_radio_button.setFont(self.gui.standard_font)
        radio_button_layout.addWidget(single_radio_button)

        folder_radio_button = QRadioButton('Entire Folder')
        folder_radio_button.setFont(self.gui.standard_font)
        radio_button_layout.addWidget(folder_radio_button)

        self.button_group = QButtonGroup()
        self.button_group.addButton(single_radio_button)
        self.button_group.setId(single_radio_button, 0)
        self.button_group.addButton(folder_radio_button)
        self.button_group.setId(folder_radio_button, 1)
        self.button_group.buttonClicked.connect(lambda: ok_button.setEnabled(True))

        button_widget = QWidget(dialog)
        button_layout = QHBoxLayout(button_widget)
        dialog_layout.addWidget(button_widget)

        ok_button.setFont(self.gui.standard_font)
        ok_button.clicked.connect(lambda: dialog.done(1))
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addSpacing(20)

        cancel_button = QPushButton('Cancel')
        cancel_button.setFont(self.gui.standard_font)
        cancel_button.clicked.connect(lambda: dialog.done(-1))
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()

        result = dialog.exec()

        if result == 1:
            files = self.get_files()

            if import_type == self.CHORDPRO:
                self.import_chordpro(files)
            elif import_type == self.OPENLYRICS:
                self.import_openlyrics(files)

    def get_files(self):
        files = []
        if self.import_type == self.CHORDPRO:
            if self.button_group.checkedId() == 0:
                file_location = QFileDialog.getOpenFileName(
                    self.gui.main_window,
                    'Open ChordPro File',
                    os.path.expanduser('~') + '/Downloads',
                    'ChordPro Files (*.txt *.crd *.chopro *.pro)'
                )

                if not len(file_location[0]) > 0:
                    return
                files = [file_location[0]]
            else:
                folder = QFileDialog.getExistingDirectory(
                    self.gui.main_window,
                    'Open ChordPro Folder',
                    os.path.expanduser('~') + '/Downloads'
                )

                if len(folder) > 0:
                    files = []
                    for file in os.listdir(folder):
                        if file.endswith('.txt') or file.endswith('.crd') or file.endswith('.chopro') or file.endswith(
                                '.pro'):
                            files.append(folder + '/' + file)

                    if len(files) == 0:
                        QMessageBox.information(
                            self.gui.main_window,
                            'No Files Found',
                            'No ChordPro files found in ' + folder,
                            QMessageBox.StandardButton.Ok
                        )
        elif self.import_type == self.OPENLYRICS:
            files = []
            if self.button_group.checkedId() == 0:
                file_location = QFileDialog.getOpenFileName(
                    self.gui.main_window,
                    'Open OpenLyrics File',
                    os.path.expanduser('~') + '/Downloads',
                    'OpenLyrics File (*.xml)'
                )

                if not len(file_location[0]) > 0:
                    return
                files = [file_location[0]]
            else:
                folder = QFileDialog.getExistingDirectory(
                    self.gui.main_window,
                    'Open OpenLyrics Folder',
                    os.path.expanduser('~') + '/Downloads'
                )

                if len(folder) > 0:
                    files = []
                    for file in os.listdir(folder):
                        if file.endswith('.xml'):
                            files.append(folder + '/' + file)

                    if len(files) == 0:
                        QMessageBox.information(
                            self.gui.main_window,
                            'No Files Found',
                            'No ChordPro files found in ' + folder,
                            QMessageBox.StandardButton.Ok
                        )

        return files

    def import_chordpro(self, files):
        for file in files:
            file_contents = ''
            with open(file, 'r', encoding='utf-8') as current_file:
                file_contents = current_file.read()

            if '{' not in file_contents:
                QMessageBox.information(
                    self.gui.main_window,
                    'Invalid File',
                    f'{file} is not a valid ChordPro file.',
                    QMessageBox.StandardButton.Ok
                )
            else:
                content_split = file_contents.split('\n')
                song_title = ''
                author = ''
                ccli_song_number = ''
                copyright = ''
                segments = []
                order = ''
                save_lyrics = False
                lyrics = ''
                tag = ''

                for i in range(len(content_split)):
                    if save_lyrics and '{' in content_split[i]:
                        if len(lyrics.strip()) > 0:
                            order += tag + ' '
                            segments.append('[' + tag + ']\n' + lyrics.strip())
                        tag = ''
                        lyrics = ''
                        save_lyrics = False
                    if not save_lyrics:
                        if 'title:' in content_split[i] and 'subtitle:' not in content_split[i]:
                            song_title = content_split[i].split(':')[1].replace('}', '').strip()
                        if ('artist:' in content_split[i]
                                or 'composer:' in content_split[i]
                                or 'lyricist:' in content_split[i]):
                            if 'artist:' in content_split[i]:
                                if len(author) > 0:
                                    author += ' | ' + content_split[i].split(':')[1].replace('}', '').strip()
                                else:
                                    author = content_split[i].split(':')[1].replace('}', '').strip()
                            if 'composer' in content_split[i]:
                                if len(author) > 0:
                                    author += ' | ' + content_split[i].split(':')[1].replace('}', '').strip()
                                else:
                                    content_split[i].split(':')[1].replace('}', '').strip()
                            if 'lyricist:' in content_split[i]:
                                if len(author) > 0:
                                    author += ' | ' + content_split[i].split(':')[1].replace('}', '').strip()
                                else:
                                    author = content_split[i].split(':')[1].replace('}', '').strip()
                        if 'ccli:' in content_split[i]:
                            ccli_song_number = content_split[i].split(':')[1].replace('}', '').strip()
                        if 'copyright:' in content_split[i]:
                            copyright = content_split[i].split(':')[1].replace('}', '').strip()
                        if 'comment:' in content_split[i]:
                            if '{' not in content_split[i + 1]:
                                whole_tag = content_split[i].split(':')[1].replace('}', '').strip()
                                tag_split = whole_tag.split(' ')
                                for item in tag_split:
                                    tag += item[0].lower()
                                save_lyrics = True
                    else:
                        this_line = re.sub('\[.*?]', '', content_split[i])
                        this_line = re.sub('\s+', ' ', this_line)
                        lyrics += this_line + '\n'

                lyrics = 'n'.join(segments)
                self.save_song(song_title, author, copyright, ccli_song_number, lyrics, order)

    def import_openlyrics(self, files):
        for file in files:
            file_contents = ''
            with open(file, 'r', encoding='utf-8') as current_file:
                file_contents = current_file.read()

            if '<title>' not in file_contents:
                QMessageBox.information(
                    self.gui.main_window,
                    'Invalid File',
                    f'{file} is not a valid OpenLyrics file.',
                    QMessageBox.StandardButton.Ok
                )
            else:
                element_tree = ElementTree.parse(file)
                root = element_tree.getroot()

                root_tag_split = root.tag.split('}')
                if len(root_tag_split) == 1:
                    ns = None
                else:
                    namespace = root_tag_split[0].replace('{', '')
                    ElementTree.register_namespace('', namespace)
                    ns = {'': namespace}

                song_title = None
                author = None

                song_titles = root.findall('.//properties/titles/title', ns)
                for element in song_titles:
                    if song_title:
                        song_title += ' (' + element.text + ')'
                    else:
                        song_title = element.text

                authors = root.findall('.//properties/authors/author', ns)
                for element in authors:
                    if author:
                        author += ' | ' + element.text
                    else:
                        author = element.text

                copyright_element = root.find('.//properties/copyright', ns)
                if copyright_element:
                    copyright = copyright_element
                else:
                    copyright = ''

                ccli_song_number_element = root.find('.//properties/ccliNo', ns)
                if ccli_song_number_element:
                    ccli_song_number = ccli_song_number_element.text
                else:
                    ccli_song_number = ''

                order_element = root.find('.//properties/verseOrder', ns)
                if order_element:
                    order = order_element.text
                else:
                    order = ''

                lyrics_element = root.find('.//lyrics', ns)
                lyrics = ''
                for verse_element in lyrics_element.findall('.//verse', ns):
                    tag = verse_element.attrib['name']
                    if tag:
                        if len(tag) == 1:
                            tag += '1'
                        lyrics += '[' + tag + ']\n'
                    for line_element in verse_element.findall('.//lines', ns):
                        data = ElementTree.tostring(line_element)
                        data = data.decode('utf-8')
                        data_split = re.split('<br.*?>', data)

                        for item in data_split:
                            lyric_block = re.sub('<.*?>', '', item)
                            lyric_block = re.sub('\n+', '\n', lyric_block)
                            lyric_block = re.sub('\s+', ' ', lyric_block)
                            lyrics += lyric_block.strip() + '\n'

                self.save_song(song_title, author, copyright, ccli_song_number, lyrics, order)

    def save_song(self, song_title, author, copyright, ccli_song_number, lyrics, order):
        song_data = [
            song_title.strip(),
            author.strip(),
            copyright.strip(),
            ccli_song_number.strip(),
            lyrics.strip(),
            order.strip(),
            'true',
            'global',
            'global',
            'global_song',
            'global',
            'False',
            0,
            0,
            'False',
            0,
            0,
            'False',
            'False',
            100,
            100
        ]

        if song_data:
            if song_title in self.gui.main.get_song_titles():
                dialog = QDialog(self.gui.main_window)
                dialog.setLayout(QVBoxLayout())
                dialog.setWindowTitle('Song Title Exists')

                label = QLabel('Unable to save song because this title already exists\n'
                               'in the database. Please provide a different title:')
                label.setFont(self.gui.standard_font)
                dialog.layout().addWidget(label)

                line_edit = QLineEdit(song_title + ' (' + str(self.dupe_index) + ')', dialog)
                self.dupe_index += 1
                line_edit.setFont(self.gui.standard_font)
                dialog.layout().addWidget(line_edit)

                button_widget = QWidget()
                button_widget.setLayout(QHBoxLayout())
                dialog.layout().addWidget(button_widget)

                ok_button = QPushButton('OK')
                ok_button.setFont(self.gui.standard_font)
                ok_button.clicked.connect(lambda: dialog.done(1))
                button_widget.layout().addStretch()
                button_widget.layout().addWidget(ok_button)
                button_widget.layout().addStretch()

                cancel_button = QPushButton('Cancel')
                cancel_button.setFont(self.gui.standard_font)
                cancel_button.clicked.connect(lambda: dialog.done(-1))
                button_widget.layout().addWidget(cancel_button)
                button_widget.layout().addStretch()

                result = dialog.exec()

                if result == 1:
                    song_data[0] = line_edit.text()
                else:
                    return

            save_widget = SimpleSplash(self.gui, 'Saving...')

            self.gui.main.save_song(song_data)
            self.gui.media_widget.populate_song_list()

            self.gui.media_widget.song_list.setCurrentItem(
                self.gui.media_widget.song_list.findItems(song_title, Qt.MatchFlag.MatchExactly)[0])

            save_widget.widget.deleteLater()
