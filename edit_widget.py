import re

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase, QColor, QPixmap, QPainter, QBrush
from PyQt6.QtWidgets import QDialog, QGridLayout, QLabel, QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QLineEdit, \
    QMessageBox, QCheckBox, QComboBox, QRadioButton, QButtonGroup, QColorDialog, QFileDialog, QScrollArea

from formattable_text_edit import FormattableTextEdit
from simple_splash import SimpleSplash


class EditWidget(QDialog):
    """
    Provides a QDialog containing the necessary widgets.py to edit a song or custom slide.
    """
    def __init__(self, gui, type, data=None, item_text=None):
        """
        Provides a QDialog containing the necessary widgets.py to edit a song or custom slide.
        :param gui.GUI gui: The current instance of GUI
        :param str type: The type of slide being edited: 'song' or 'custom'
        :param list of str data: Optional: The data contained in QListWidget.data()
        :param item_text: Optional: Default text (not used)
        """
        super().__init__()
        self.gui = gui
        self.type = type
        self.lyrics_edit = None
        self.item_text = item_text
        self.setModal(True)
        self.old_title = None
        self.new_song = False
        if not data:
            self.new_song = True

        self.init_components()
        if data and type == 'song':
            self.populate_song_data(data)
        elif data and type == 'custom':
            self.populate_custom_data(data)

        preferred_height = int(self.gui.primary_screen.size().height() * 4 / 5)
        widget_height = self.main_widget.height() + self.scroll_area.horizontalScrollBar().height()
        if preferred_height < widget_height:
            self.height = preferred_height
        else:
            self.height = widget_height
        self.setGeometry(50, 50, self.scroll_area.width(), self.height)
        self.setMaximumHeight(self.gui.primary_screen.size().height() - 20)
        self.title_line_edit.setFocus()
        self.exec()

    def init_components(self):
        """
        Create and add the necessary widgets.py to this dialog
        """
        self.setParent(self.gui.main_window)
        self.setWindowFlag(Qt.WindowType.Window)
        if self.type == 'song':
            self.setWindowTitle('Edit Song')
        else:
            self.setWindowTitle('Edit Custom Slide')
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        self.main_widget.setLayout(main_layout)

        title_widget = QWidget()
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 5)
        title_widget.setLayout(title_layout)
        main_layout.addWidget(title_widget)

        title_label = QLabel('Title:')
        title_label.setFont(self.gui.list_font)
        title_layout.addWidget(title_label)

        self.title_line_edit = QLineEdit()
        self.title_line_edit.setFont(self.gui.list_font)
        title_layout.addWidget(self.title_line_edit)

        if self.type == 'song':
            author_widget = QWidget()
            author_layout = QHBoxLayout()
            author_layout.setContentsMargins(0, 0, 0, 5)
            author_widget.setLayout(author_layout)
            main_layout.addWidget(author_widget)

            author_label = QLabel('Author:')
            author_label.setFont(self.gui.list_font)
            author_layout.addWidget(author_label)

            self.author_line_edit = QLineEdit()
            self.author_line_edit.setFont(self.gui.list_font)
            author_layout.addWidget(self.author_line_edit)

            copyright_widget = QWidget()
            copyright_layout = QHBoxLayout()
            copyright_layout.setContentsMargins(0, 0, 0, 5)
            copyright_widget.setLayout(copyright_layout)
            main_layout.addWidget(copyright_widget)

            copyright_label = QLabel('Copyright:')
            copyright_label.setFont(self.gui.list_font)
            copyright_layout.addWidget(copyright_label)

            self.copyright_line_edit = QLineEdit()
            self.copyright_line_edit.setFont(self.gui.list_font)
            copyright_layout.addWidget(self.copyright_line_edit)

            ccli_widget = QWidget()
            ccli_layout = QHBoxLayout()
            ccli_layout.setContentsMargins(0, 0, 0, 0)
            ccli_widget.setLayout(ccli_layout)
            main_layout.addWidget(ccli_widget)

            ccli_label = QLabel('CCLI Song Number:')
            ccli_label.setFont(self.gui.list_font)
            ccli_layout.addWidget(ccli_label)

            self.ccli_num_line_edit = QLineEdit()
            self.ccli_num_line_edit.setFont(self.gui.list_font)
            ccli_layout.addWidget(self.ccli_num_line_edit)

        main_layout.addSpacing(20)

        lyrics_label = QLabel('Lyrics')
        lyrics_label.setFont(self.gui.list_title_font)
        main_layout.addWidget(lyrics_label)

        if self.type == 'song':
            tool_bar = QWidget()
            toolbar_layout = QHBoxLayout()
            tool_bar.setLayout(toolbar_layout)
            main_layout.addWidget(tool_bar)

            verse_button = QPushButton('Verse')
            verse_button.setFont(self.gui.list_font)
            verse_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            verse_button.pressed.connect(lambda: self.add_tag('v'))
            toolbar_layout.addWidget(verse_button)

            chorus_button = QPushButton('Chorus')
            chorus_button.setFont(self.gui.list_font)
            chorus_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            chorus_button.pressed.connect(lambda: self.add_tag('c'))
            toolbar_layout.addWidget(chorus_button)

            pre_chorus_button = QPushButton('Pre-Chorus')
            pre_chorus_button.setFont(self.gui.list_font)
            pre_chorus_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            pre_chorus_button.pressed.connect(lambda: self.add_tag('p'))
            toolbar_layout.addWidget(pre_chorus_button)

            bridge_button = QPushButton('Bridge')
            bridge_button.setFont(self.gui.list_font)
            bridge_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            bridge_button.pressed.connect(lambda: self.add_tag('b'))
            toolbar_layout.addWidget(bridge_button)

            tag_button = QPushButton('Tag')
            tag_button.setFont(self.gui.list_font)
            tag_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            tag_button.pressed.connect(lambda: self.add_tag('t'))
            toolbar_layout.addWidget(tag_button)

            ending_button = QPushButton('Ending')
            ending_button.setFont(self.gui.list_font)
            ending_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            ending_button.pressed.connect(lambda: self.add_tag('e'))
            toolbar_layout.addWidget(ending_button)

        self.lyrics_edit = FormattableTextEdit(self.gui)
        self.lyrics_edit.setFont(self.gui.list_font)
        main_layout.addWidget(self.lyrics_edit)

        if self.type == 'song':
            song_order_widget = QWidget()
            song_order_layout = QHBoxLayout()
            song_order_widget.setLayout(song_order_layout)
            main_layout.addWidget(song_order_widget)

            song_order_label = QLabel('Song Order:')
            song_order_label.setFont(self.gui.list_font)
            song_order_layout.addWidget(song_order_label)

            self.song_order_line_edit = QLineEdit()
            self.song_order_line_edit.setFont(self.gui.list_font)
            song_order_layout.addWidget(self.song_order_line_edit)

            advanced_options_widget = QWidget()
            advanced_options_layout = QHBoxLayout()
            advanced_options_widget.setLayout(advanced_options_layout)
            main_layout.addWidget(advanced_options_widget)

            advanced_options_label = QLabel('Show Advanced Options')
            advanced_options_label.setFont(self.gui.list_title_font)
            advanced_options_layout.addWidget(advanced_options_label)

            self.advanced_options_button = QPushButton('+')
            self.advanced_options_button.setFont(self.gui.list_title_font)
            self.advanced_options_button.setMaximumWidth(15)
            self.advanced_options_button.pressed.connect(self.show_hide_advanced_options)
            advanced_options_layout.addWidget(self.advanced_options_button)
            advanced_options_layout.addStretch()

            self.footer_checkbox = QCheckBox('Use Footer for this song')
            self.footer_checkbox.setFont(self.gui.list_font)
            self.footer_checkbox.setChecked(True)
            main_layout.addWidget(self.footer_checkbox)
            self.footer_checkbox.hide()

        self.format_widget = QWidget()
        format_layout = QHBoxLayout()
        self.format_widget.setLayout(format_layout)
        main_layout.addWidget(self.format_widget)
        if self.type == 'song':
            self.format_widget.hide()

        font_widget = QWidget()
        font_layout = QGridLayout()
        font_widget.setLayout(font_layout)
        format_layout.addWidget(font_widget)

        font_label = QLabel('Font Options')
        font_label.setFont(self.gui.list_title_font)
        font_layout.addWidget(font_label, 0, 0)

        font_family_label = QLabel('Font Family:')
        font_family_label.setFont(self.gui.list_font)
        font_layout.addWidget(font_family_label, 1, 0)

        self.font_combo_box = QComboBox()
        self.font_combo_box.setFont(self.gui.list_font)
        self.font_combo_box.addItem('Use Global Font')
        font_list = QFontDatabase.families()
        self.font_combo_box.addItems(font_list)
        font_layout.addWidget(self.font_combo_box, 1, 1, 1, 2)

        font_color_label = QLabel('Font Color')
        font_color_label.setFont(self.gui.list_font)
        font_layout.addWidget(font_color_label, 2, 0)

        default_radio_button = QRadioButton('Use Global Font Color')
        default_radio_button.setFont(self.gui.list_font)
        default_radio_button.pressed.connect(lambda: self.font_color_line_edit.setText('Use Global Font Color'))

        white_radio_button = QRadioButton('White')
        white_radio_button.setFont(self.gui.list_font)
        white_radio_button.pressed.connect(lambda: self.font_color_line_edit.setText('#FFFFFF'))

        black_radio_button = QRadioButton('Black')
        black_radio_button.setFont(self.gui.list_font)
        black_radio_button.pressed.connect(lambda: self.font_color_line_edit.setText('#000000'))

        custom_font_color_radio_button = QRadioButton('Custom')
        custom_font_color_radio_button.setFont(self.gui.list_font)
        custom_font_color_radio_button.setObjectName('custom_font_color_radio_button')
        custom_font_color_radio_button.pressed.connect(self.color_chooser)

        self.font_color_button_group = QButtonGroup()
        self.font_color_button_group.setObjectName('font_color_button_group')
        self.font_color_button_group.addButton(default_radio_button, 0)
        self.font_color_button_group.addButton(white_radio_button, 1)
        self.font_color_button_group.addButton(black_radio_button, 2)
        self.font_color_button_group.addButton(custom_font_color_radio_button, 3)
        default_radio_button.setChecked(True)

        font_layout.addWidget(default_radio_button, 2, 1)
        font_layout.addWidget(white_radio_button, 2, 2)
        font_layout.addWidget(black_radio_button, 2, 3)
        font_layout.addWidget(custom_font_color_radio_button, 2, 4)

        font_color_label = QLabel('Chosen Font Color:')
        font_layout.addWidget(font_color_label, 3, 0)

        self.font_color_line_edit = QLineEdit()
        self.font_color_line_edit.setText('Use Global Font Color')
        font_layout.addWidget(self.font_color_line_edit, 3, 1, 1, 2)

        self.font_size_combo_box = QComboBox()
        self.font_size_combo_box.setFont(self.gui.list_font)
        self.font_size_combo_box.addItem('Use Global Font Size')
        for i in range(10, 250, 2):
            self.font_size_combo_box.addItem(str(i))
        font_layout.addWidget(self.font_size_combo_box, 4, 1)

        background_widget = QWidget()
        background_layout = QVBoxLayout()
        background_widget.setLayout(background_layout)
        format_layout.addWidget(background_widget)

        background_label = QLabel('Background')
        background_label.setFont(self.gui.list_title_font)
        background_layout.addWidget(background_label)

        background_default_radio_button = QRadioButton('Use Global Song Background')
        background_default_radio_button.setFont(self.gui.list_font)
        background_default_radio_button.pressed.connect(
            lambda: self.background_line_edit.setText('Use Global Song Background'))

        background_bible_default_radio_button = QRadioButton('Use Global Bible Background')
        background_bible_default_radio_button.setFont(self.gui.list_font)
        background_bible_default_radio_button.pressed.connect(
            lambda: self.background_line_edit.setText('Use Global Bible Background'))

        background_color_radio_button = QRadioButton('Solid Color')
        background_color_radio_button.setFont(self.gui.list_font)
        background_color_radio_button.pressed.connect(self.color_chooser)

        from widgets import ImageCombobox
        background_combobox = ImageCombobox(self.gui, 'edit')
        background_combobox.currentIndexChanged.connect(
            lambda: self.background_line_edit.setText(background_combobox.currentData(Qt.ItemDataRole.UserRole)))

        self.background_image_radio_button = QRadioButton('Image')
        self.background_image_radio_button.setFont(self.gui.list_font)
        self.background_image_radio_button.pressed.connect(background_combobox.show)

        self.background_button_group = QButtonGroup()
        self.background_button_group.setObjectName('background_button_group')
        if self.type == 'custom':
            self.background_button_group.addButton(background_default_radio_button, 0)
            self.background_button_group.addButton(background_bible_default_radio_button, 1)
            self.background_button_group.addButton(background_color_radio_button, 2)
            self.background_button_group.addButton(self.background_image_radio_button, 3)
        else:
            self.background_button_group.addButton(background_default_radio_button, 0)
            self.background_button_group.addButton(background_color_radio_button, 1)
            self.background_button_group.addButton(self.background_image_radio_button, 2)
        background_default_radio_button.setChecked(True)

        background_layout.addWidget(background_default_radio_button)
        if self.type == 'custom':
            background_layout.addWidget(background_bible_default_radio_button)
        background_layout.addWidget(background_color_radio_button)
        background_layout.addWidget(self.background_image_radio_button)
        background_layout.addWidget(background_combobox)
        if self.type == 'song':
            background_combobox.hide()

        chosen_widget = QWidget()
        chosen_layout = QHBoxLayout()
        chosen_widget.setLayout(chosen_layout)
        background_layout.addWidget(chosen_widget)

        chosen_background_label = QLabel('Chosen Background:')
        chosen_layout.addWidget(chosen_background_label)

        self.background_line_edit = QLineEdit()
        self.background_line_edit.setText('Use Global Background')
        chosen_layout.addWidget(self.background_line_edit)

        button_widget = QWidget()
        button_layout = QHBoxLayout()
        button_widget.setLayout(button_layout)
        main_layout.addWidget(button_widget)

        save_button = QPushButton('Save')
        save_button.setFont(self.gui.list_font)
        if self.type == 'song':
            save_button.pressed.connect(self.save_song)
        elif self.type == 'custom':
            save_button.pressed.connect(self.save_custom)
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addSpacing(20)

        cancel_button = QPushButton('Cancel')
        cancel_button.setFont(self.gui.list_font)
        cancel_button.pressed.connect(lambda: self.done(1))
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()

        if self.type == 'custom':
            background_default_radio_button.setText('Use Global Song Background')

        self.main_widget.adjustSize()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.main_widget)
        self.scroll_area.setMinimumWidth(self.main_widget.width() + self.scroll_area.verticalScrollBar().width())
        layout.addWidget(self.scroll_area)

    def populate_song_data(self, song_data):
        """
        Use the provided data to set the proper widgets.py to match the saved data
        :param list of str song_data: The song's QListWidgetItem data
        """
        self.old_title = song_data[0]
        self.title_line_edit.setText(song_data[0])
        self.author_line_edit.setText(song_data[1])
        self.copyright_line_edit.setText(song_data[2])
        self.ccli_num_line_edit.setText(song_data[3])

        lyrics = re.sub('<p.*?>', '<p>', song_data[4])
        lyrics = re.sub('\n', '<br />', lyrics)
        self.lyrics_edit.text_edit.setHtml(lyrics)

        self.song_order_line_edit.setText(song_data[5])

        if song_data[6] == 'true':
            self.footer_checkbox.setChecked(True)
        else:
            self.footer_checkbox.setChecked(False)

        if song_data[7] == 'global':
            self.font_combo_box.setCurrentIndex(0)
        else:
            self.font_combo_box.setCurrentText(song_data[7])

        if song_data[8] == 'global':
            self.font_color_button_group.button(0).setChecked(True)
        elif song_data[8] == '#FFFFFF':
            self.font_color_button_group.button(1).setChecked(True)
            self.font_color_line_edit.setText(song_data[8])
        elif song_data[8] == '#000000':
            self.font_color_button_group.button(2).setChecked(True)
            self.font_color_line_edit.setText(song_data[8])
        else:
            self.font_color_button_group.button(3).setChecked(True)
            self.font_color_line_edit.setText(song_data[8])

        if song_data[9] == 'global_song':
            self.background_button_group.button(0).setChecked(True)
            self.background_line_edit.setText('Use Global Song Background')
        elif 'rgb(' in song_data[9]:
            self.background_button_group.button(1).setChecked(True)
            self.background_line_edit.setText(song_data[9])
        else:
            self.background_button_group.button(2).setChecked(True)
            self.background_line_edit.setText(song_data[9])

        if song_data[10] == 'global':
            self.font_size_combo_box.setCurrentText('Use Global Font Size')
        else:
            self.font_size_combo_box.setCurrentText(song_data[10])

    def populate_custom_data(self, custom_data):
        """
        Use the provided data to set the proper widgets.py to match the saved data
        :param list of str custom_data: The custom slide's QListWidgetItem data
        """
        self.old_title = custom_data[0]
        self.title_line_edit.setText(custom_data[0])
        self.lyrics_edit.text_edit.setHtml(custom_data[1])

        if custom_data[2] == 'global':
            self.font_combo_box.setCurrentIndex(0)
        else:
            self.font_combo_box.setCurrentText(custom_data[2])

        if custom_data[3] == 'global':
            self.font_color_button_group.button(0).setChecked(True)
        elif custom_data[3] == '#FFFFFF':
            self.font_color_button_group.button(1).setChecked(True)
            self.font_color_line_edit.setText(custom_data[3])
        elif custom_data[3] == '#000000':
            self.font_color_button_group.button(2).setChecked(True)
            self.font_color_line_edit.setText(custom_data[3])
        else:
            self.font_color_button_group.button(3).setChecked(True)
            self.font_color_line_edit.setText(custom_data[3])

        if custom_data[4] == 'global_song':
            self.background_button_group.button(0).setChecked(True)
            self.background_line_edit.setText('Use Global Song Background')
        elif custom_data[4] == 'global_bible':
            self.background_button_group.button(1).setChecked(True)
            self.background_line_edit.setText('Use Global Bible Background')
        elif 'rgb(' in custom_data[4]:
            self.background_button_group.button(2).setChecked(True)
            self.background_line_edit.setText(custom_data[4])
        else:
            self.background_button_group.button(3).setChecked(True)
            self.background_line_edit.setText(custom_data[4])

        if custom_data[5] == 'global':
            self.font_size_combo_box.setCurrentText('Use Global Font Size')
        else:
            self.font_size_combo_box.setCurrentText(custom_data[5])

    def show_hide_advanced_options(self):
        """
        Method to show or hide advanced options the user may or may not want to change. Advanced options are contained
        in the format_widget QWidget.
        """
        pos = self.gui.main_window.mapToGlobal(self.pos())
        if self.format_widget.isHidden():
            self.format_widget.show()
            self.footer_checkbox.show()
            self.main_widget.adjustSize()
            self.scroll_area.setMinimumWidth(self.main_widget.width() + self.scroll_area.verticalScrollBar().width())
            self.setGeometry(pos.x(), pos.y(), self.scroll_area.width(), self.height)
            self.advanced_options_button.setText('-')
        else:
            self.format_widget.hide()
            self.footer_checkbox.hide()
            self.main_widget.adjustSize()
            self.scroll_area.setMinimumWidth(self.main_widget.width() + self.scroll_area.verticalScrollBar().width())
            self.setGeometry(pos.x(), pos.y(), self.scroll_area.width(), self.height)
            self.advanced_options_button.setText('+')

    def disambiguate_background_click(self, background_button_group):
        """
        Method to call the proper function when user selects a color from a QButtonGroup.
        :param QButtonGroup background_button_group: The QButtonGroup that was changed
        """
        if 'Color' in background_button_group.checkedButton().text():
            self.color_chooser()
        else:
            self.image_chooser()

    def color_chooser(self):
        """
        Method to provide a QColorDialog when setting a custom color.
        """
        sender = self.sender()
        color = QColorDialog.getColor(QColor(Qt.GlobalColor.black), self)
        rgb = color.getRgb()
        color_string = 'rgb(' + str(rgb[0]) + ', ' + str(rgb[1]) + ', ' + str(rgb[2]) + ')'
        if 'font' in sender.objectName():
            self.font_color_line_edit.setText(color_string)
            sender.setChecked(True)
        else:
            self.background_line_edit.setText(color_string)
            sender.setChecked(True)

    def image_chooser(self):
        """
        Method to provide a file dialog for the user to import a new image.
        """
        file = QFileDialog.getOpenFileName(self, 'Choose Image File', self.gui.main.background_dir)
        if len(file[0]) > 0:
            file_split = file[0].split('/')
            file_name = file_split[len(file_split) - 1]
            self.background_line_edit.setText(file_name)
            self.gui.main.copy_image(file[0])
        self.background_image_radio_button.setChecked(True)

    def add_tag(self, type):
        """
        Method to add tags to the song lyrics based on button push.
        :param str type: The tag type to be inserted
        :return:
        """
        if type == 'os':
            self.lyrics_edit.text_edit.insertPlainText('\n#optional split#')

        else:
            # search first for previous instances of this tag; append numbers to the tag for multiple instances
            lyrics_text = self.lyrics_edit.text_edit.toHtml()
            occurrences = re.findall('\[' + type + '.*?\]', lyrics_text)

            if len(occurrences) == 0:
                self.lyrics_edit.text_edit.insertPlainText('\n[' + type + '1]\n')
            else:
                self.lyrics_edit.text_edit.insertPlainText('\n[' + type + type + ']\n')
                lyrics_text = self.lyrics_edit.text_edit.toHtml()
                occurrences = re.findall('\[' + type + '.*?\]', lyrics_text)

                count = 1
                for item in occurrences:
                    lyrics_text = lyrics_text.replace(item, '\n[' + type + str(count) + '\n]', 1)
                    count += 1

                self.lyrics_edit.text_edit.setHtml(lyrics_text)
                self.lyrics_edit.text_edit.setFocus()

    def save_song(self):
        """
        Method to save user's changes for the song type editor.
        """
        # title is essential for the database, prompt user for title if not inputted
        if len(self.title_line_edit.text()) == 0:
            QMessageBox.information(
                self,
                'No Title',
                'Title field is empty. Please enter a title before saving.',
                QMessageBox.StandardButton.Ok
            )
        else:
            if self.footer_checkbox.isChecked():
                footer = 'true'
            else:
                footer = 'false'

            if 'Global' in self.font_combo_box.currentText():
                font = 'global'
            else:
                font = self.font_combo_box.currentText()

            if 'Global' in self.font_color_line_edit.text():
                font_color = 'global'
            else:
                font_color = self.font_color_line_edit.text()

            if 'Global' in self.font_size_combo_box.currentText():
                font_size = 'global'
            else:
                font_size = self.font_size_combo_box.currentText()

            if self.type == 'song':
                if 'Global' in self.background_line_edit.text():
                    if 'Song' in self.background_line_edit.text():
                        background = 'global_song'
                    else:
                        background = 'global_bible'
                else:
                    background = self.background_line_edit.text()
            elif self.type == 'custom':
                if 'Global' in self.background_line_edit.text():
                    if 'Song' in self.background_line_edit.text():
                        background = 'global_song'
                    else:
                        background = 'global_bible'
                else:
                    background = self.background_line_edit.text()

            lyrics = self.lyrics_edit.text_edit.toHtml()
            lyrics_split = re.split('<body.*?>', lyrics)
            lyrics = lyrics_split[1].replace('</body></html>', '')
            lyrics = re.sub(
                '<span style=" text-decoration: underline.*?>',
                '<span style="text-decoration: underline; text-underline-width: 5px;">',
                lyrics
            )
            lyrics = re.sub('<p.*?>', '', lyrics)
            lyrics = re.sub('</p>', '', lyrics)
            if lyrics.startswith('<br />'):
                lyrics = lyrics[6:len(lyrics)]
            elif lyrics.startswith('\n'):
                lyrics = lyrics[1:len(lyrics)]

            lyrics = lyrics.replace('<br />', '\n')

            song_data = [
                self.title_line_edit.text(),
                self.author_line_edit.text(),
                self.copyright_line_edit.text(),
                self.ccli_num_line_edit.text(),
                lyrics,
                self.song_order_line_edit.text(),
                footer,
                font,
                font_color,
                background,
                font_size
            ]

            if self.new_song:
                if self.title_line_edit.text() in self.gui.main.get_song_titles():
                    dialog = QDialog(self.gui.main_window)
                    dialog.setLayout(QVBoxLayout())
                    dialog.setWindowTitle('Song Title Exists')

                    label = QLabel('Unable to save song because this title already exists\n'
                                   'in the database. Please provide a different title:')
                    label.setFont(self.gui.standard_font)
                    dialog.layout().addWidget(label)

                    line_edit = QLineEdit(self.title_line_edit.text() + '(1)', dialog)
                    line_edit.setFont(self.gui.standard_font)
                    dialog.layout().addWidget(line_edit)

                    button_widget = QWidget()
                    button_widget.setLayout(QHBoxLayout())
                    dialog.layout().addWidget(button_widget)

                    ok_button = QPushButton('OK')
                    ok_button.setFont(self.gui.standard_font)
                    ok_button.pressed.connect(lambda: dialog.done(1))
                    button_widget.layout().addStretch()
                    button_widget.layout().addWidget(ok_button)
                    button_widget.layout().addStretch()

                    cancel_button = QPushButton('Cancel')
                    cancel_button.setFont(self.gui.standard_font)
                    cancel_button.pressed.connect(lambda: dialog.done(-1))
                    button_widget.layout().addWidget(cancel_button)
                    button_widget.layout().addStretch()

                    result = dialog.exec()

                    if result == 1:
                        song_data[0] = line_edit.text()
                    else:
                        return

            save_widget = SimpleSplash(self.gui, 'Saving...')

            self.gui.main.save_song(song_data, self.old_title)
            self.gui.media_widget.populate_song_list()

            if self.old_title:
                for i in range(self.gui.oos_widget.oos_list_widget.count()):
                    if self.gui.oos_widget.oos_list_widget.item(i).data(20) == self.old_title:
                        new_item = self.gui.media_widget.song_list.findItems(song_data[0], Qt.MatchFlag.MatchExactly)[0].clone()
                        self.gui.oos_widget.oos_list_widget.takeItem(i)
                        self.gui.media_widget.add_song_to_service(new_item, i)
                        break

            self.done(0)
            save_widget.widget.deleteLater()
            if self.gui.oos_widget.oos_list_widget.currentItem():
                self.gui.send_to_preview(self.gui.oos_widget.oos_list_widget.currentItem())

    def save_custom(self):
        """
        Method to save user's changes for the custom slide type editor.
        """
        if 'Global' in self.font_combo_box.currentText():
            font = 'global'
        else:
            font = self.font_combo_box.currentText()

        if 'Global' in self.font_color_line_edit.text():
            font_color = 'global'
        else:
            font_color = self.font_color_line_edit.text()

        if 'Global' in self.font_size_combo_box.currentText():
            font_size = 'global'
        else:
            font_size = self.font_size_combo_box.currentText()

        if 'Global' in self.background_line_edit.text():
            if 'Song' in self.background_line_edit.text():
                background = 'global_song'
            else:
                background = 'global_bible'
        elif 'rgb(' in self.background_line_edit.text():
            background = self.background_line_edit.text()
        else:
            background = self.background_line_edit.text()

        text = self.lyrics_edit.text_edit.toHtml()
        text_split = re.split('<body.*?>', text)
        text = text_split[1].replace('</body></html>', '')
        text = text.replace('"', '""').strip()

        custom_data = [
            self.title_line_edit.text(),
            text,
            font,
            font_color,
            background,
            font_size
        ]

        if self.new_song:
            if self.title_line_edit.text() in self.gui.main.get_custom_titles():
                dialog = QDialog(self.gui.main_window)
                dialog.setLayout(QVBoxLayout())
                dialog.setWindowTitle('Song Title Exists')

                label = QLabel('Unable to save song because this title already exists\n'
                               'in the database. Please provide a different title:')
                label.setFont(self.gui.standard_font)
                dialog.layout().addWidget(label)

                line_edit = QLineEdit(self.title_line_edit.text() + '(1)', dialog)
                line_edit.setFont(self.gui.standard_font)
                dialog.layout().addWidget(line_edit)

                button_widget = QWidget()
                button_widget.setLayout(QHBoxLayout())
                dialog.layout().addWidget(button_widget)

                ok_button = QPushButton('OK')
                ok_button.setFont(self.gui.standard_font)
                ok_button.pressed.connect(lambda: dialog.done(1))
                button_widget.layout().addStretch()
                button_widget.layout().addWidget(ok_button)
                button_widget.layout().addStretch()

                cancel_button = QPushButton('Cancel')
                cancel_button.setFont(self.gui.standard_font)
                cancel_button.pressed.connect(lambda: dialog.done(-1))
                button_widget.layout().addWidget(cancel_button)
                button_widget.layout().addStretch()

                result = dialog.exec()

                if result == 1:
                    custom_data[0] = line_edit.text()
                else:
                    return

        save_widget = SimpleSplash(self.gui, 'Saving...')

        self.gui.main.save_custom(custom_data, self.old_title)
        self.gui.media_widget.populate_custom_list()
        self.gui.main.app.processEvents()

        if self.old_title:
            for i in range(self.gui.oos_widget.oos_list_widget.count()):
                if self.gui.oos_widget.oos_list_widget.item(i).data(20) == self.old_title:
                    new_item = self.gui.media_widget.custom_list.findItems(custom_data[0], Qt.MatchFlag.MatchExactly)[0]
                    for j in range(20, 33):
                        self.gui.oos_widget.oos_list_widget.item(i).setData(j, new_item.data(j))
                    self.change_thumbnail(self.gui.oos_widget.oos_list_widget.item(i))

        self.done(0)
        save_widget.widget.deleteLater()
        if self.gui.oos_widget.oos_list_widget.currentItem():
            self.gui.send_to_preview(self.gui.oos_widget.oos_list_widget.currentItem())

    def change_thumbnail(self, item):
        """
        Change the thumbnail image of this song/custom slide's QListWidget ItemWidget to what has just been saved.
        :param QListWidgetItem item: The edited song/custom slide's QListWidgetItem
        :return:
        """
        if item.data(29) == 'global_song':
            pixmap = self.gui.global_song_background_pixmap
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        elif item.data(29) == 'global_bible':
            pixmap = self.gui.global_bible_background_pixmap
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        elif 'rgb(' in item.data(29):
            pixmap = QPixmap(50, 27)
            painter = QPainter(pixmap)
            rgb = item.data(29).replace('rgb(', '')
            rgb = rgb.replace(')', '')
            rgb_split = rgb.split(',')
            brush = QBrush(QColor.fromRgb(
                int(rgb_split[0].strip()), int(rgb_split[1].strip()), int(rgb_split[2].strip())))
            painter.setBrush(brush)
            painter.fillRect(pixmap.rect(), brush)
            painter.end()
        else:
            pixmap = QPixmap(self.gui.main.background_dir + '/' + item.data(29))
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

        item_widget = QWidget()
        item_layout = QHBoxLayout()
        item_widget.setLayout(item_layout)

        picture_label = QLabel()
        picture_label.setPixmap(pixmap)
        item_layout.addWidget(picture_label)

        title_label = QLabel(item.data(20))
        title_label.setFont(self.gui.list_font)
        item_layout.addWidget(title_label)
        item_layout.addStretch()

        item.setSizeHint(item_widget.sizeHint())
        self.gui.oos_widget.oos_list_widget.setItemWidget(item, item_widget)
