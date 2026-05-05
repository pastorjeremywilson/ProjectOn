import json
import os
import re
from xml.etree import ElementTree

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QDialog, QVBoxLayout, QLabel, QLineEdit, QWidget, QHBoxLayout, \
    QPushButton, QRadioButton, QButtonGroup

from dataHandling.declarations import SLIDE_DATA_DEFAULTS
from dataHandling.parsers import parse_song_data
from gui.widgets.widgets import SimpleSplash


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

                data = SLIDE_DATA_DEFAULTS
                data['type'] = 'song'
                
                content_tags = re.findall(r'\{.*?}', file_contents)
                content_data = re.split(r'\{.*?}', file_contents)[1:]

                # the block of text below the final tag should contain the CCLI song number and/or the copyright info
                final_block = content_data[-1]
                final_block_split = final_block.split('\n')

                ccli_song_number = ''
                copyright = ''
                for i in range(len(final_block_split)):
                    if 'ccli' in final_block_split[i].lower() and not 'license' in final_block_split[i].lower():
                        for character in final_block_split[i]:
                            if character.isdigit():
                                ccli_song_number += character
                    if '©' in final_block_split[i] or 'copyright' in final_block_split[i].lower():
                        copyright = ' | '.join(final_block_split[i:]).strip()

                data['ccli_song_number'] = ccli_song_number
                data['copyright'] = copyright

                # separate the ccli/copyright info from the text of the final lyrics block
                final_block = ''
                for item in final_block_split:
                    if 'ccli' in item.lower() or '©' in item or 'copyright' in item:
                        break
                    else:
                        final_block += item + '\n'
                content_data[-1] = final_block.strip()

                title = ''
                subtitle = ''
                author = ''
                lyrics = ''
                order = ''
                for i in range(len(content_tags)):
                    if '{' in content_tags[i] and not 'comment:' in content_tags[i].lower():
                        if 'title' in content_tags[i].lower() and not 'subtitle' in content_tags[i].lower():
                            title = content_tags[i].split(':')[1].replace('}', '').strip()
                        elif 'subtitle:' in content_tags[i]:
                            subtitle = content_tags[i].split(':')[1].replace('}', '').strip()
                        elif ('artist' in content_tags[i]
                              or 'composer' in content_tags[i]
                              or 'lyricist' in content_tags[i]):
                            author += content_tags[i].split(':')[1].replace('}', '').strip() + ' | '
                        elif 'ccli:' in content_tags[i]:
                            data['ccli_song_number'] = content_tags[i].split(':')[1].replace('}', '').strip()
                        elif 'copyright' in content_tags[i]:
                            data['copyright'] = content_tags[i].split(':')[1].replace('}', '').strip()
                    else:
                        tag = content_tags[i].split(':')[1].replace('}', '').strip()
                        if not any(x.isdigit() for x in tag):
                            tag += ' 1'
                        tag_split = tag.split(' ')
                        short_tag = tag_split[0][0].lower() + tag_split[1]
                        cleaned_lyrics = re.sub(r'\[.*?]', '', content_data[i])
                        lyrics_split = cleaned_lyrics.split('\n')
                        cleaned_lyrics = ''
                        for lyric in lyrics_split:
                            cleaned_lyrics += re.sub(r'\s+', ' ', lyric.strip()) + '\n'
                        lyrics += f'[{tag}]\n{cleaned_lyrics.strip()}\n'
                        order += short_tag + ' '

                if len(subtitle.strip()) > 0:
                    data['title'] = title + ' ' + subtitle
                else:
                    data['title'] = title.strip()
                if author.endswith(' | '):
                    author = author[:-3]
                data['author'] = author.strip()
                data['verse_order'] = order.strip()
                data['text'] = lyrics.strip()
                data['parsed_text'] = parse_song_data(self.gui, data)

                self.save_song(data)

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

                data = SLIDE_DATA_DEFAULTS

                song_title = ''
                song_titles = root.findall('.//properties/titles/title', ns)
                for element in song_titles:
                    if song_title:
                        song_title += ' (' + element.text + ')'
                    else:
                        song_title = element.text
                data['title'] = song_title

                author = ''
                authors = root.findall('.//properties/authors/author', ns)
                for element in authors:
                    if author:
                        author += ' | ' + element.text
                    else:
                        author = element.text
                data['author'] = author

                data['copyright'] = ''
                data['copyright'] += root.find('.//properties/copyright', ns).text

                data['ccli_song_number'] = ''
                data['ccli_song_number'] += root.find('.//properties/ccliNo', ns).text

                data['verse_order'] = ''
                data['verse_order'] += root.find('.//properties/verseOrder', ns).text

                lyrics_element = root.find('.//lyrics', ns)
                lyrics = ''
                for verse_element in lyrics_element.findall('.//verse', ns):
                    tag = verse_element.attrib['name']
                    if tag:
                        if len(tag) == 1:
                            tag += '1'
                        lyrics += '[' + tag + ']\n'
                    for line_element in verse_element.findall('.//lines', ns):
                        lyric_data = ElementTree.tostring(line_element)
                        lyric_data = lyric_data.decode('utf-8')
                        data_split = re.split('<br.*?>', lyric_data)

                        for item in data_split:
                            lyric_block = re.sub('<.*?>', '', item)
                            lyric_block = re.sub('\n+', '\n', lyric_block)
                            lyric_block = re.sub(r'\s+', ' ', lyric_block)
                            lyrics += lyric_block.strip() + '\n'
                data['text'] = lyrics
                data['parsed_text'] = parse_song_data(self.gui, data)

                self.save_song(data)

    def save_song(self, song_data):
        if song_data['title'] in self.gui.main.get_song_titles():
            dialog = QDialog(self.gui.main_window)
            dialog.setLayout(QVBoxLayout())
            dialog.setWindowTitle('Song Title Exists')

            label = QLabel('Unable to save song because this title already exists\n'
                           'in the database. Please provide a different title:')
            label.setFont(self.gui.standard_font)
            dialog.layout().addWidget(label)

            line_edit = QLineEdit(song_data['title'] + ' (' + str(self.dupe_index) + ')', dialog)
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
                song_data['title'] = line_edit.text()
            else:
                return

        save_widget = SimpleSplash(self.gui, 'Saving...')

        self.gui.main.save_song(song_data)
        self.gui.media_widget.populate_song_list()

        self.gui.media_widget.song_list.setCurrentItem(
            self.gui.media_widget.song_list.findItems(song_data['title'], Qt.MatchFlag.MatchExactly)[0])

        save_widget.widget.deleteLater()
