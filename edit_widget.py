import re

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QPixmap, QPainter, QBrush
from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QLineEdit, \
    QMessageBox, QCheckBox, QRadioButton, QButtonGroup, QColorDialog, QFileDialog, QScrollArea, QListWidget

from formattable_text_edit import FormattableTextEdit
from simple_splash import SimpleSplash
from widgets import StandardItemWidget, FontWidget


class EditWidget(QDialog):
    """
    Provides a QDialog containing the necessary widgets to edit a song or custom slide.
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
        self.old_title = None
        self.new_song = False
        self.new_custom = False

        self.setObjectName('edit_widget')
        self.setWindowFlag(Qt.WindowType.Window)
        self.init_components()

        self.main_widget.adjustSize()
        preferred_height = int(self.gui.primary_screen.size().height() * 4 / 5)
        self.setGeometry(50, 50, self.scroll_area.width(), preferred_height)
        self.title_line_edit.setFocus()
        if data and type == 'song':
            self.populate_song_data(data)
        elif data and type == 'custom':
            self.populate_custom_data(data)
        elif not data:
            if type == 'song':
                self.new_song = True
                self.set_defaults()
            else:
                self.new_custom = True
                self.set_defaults()

        self.show()

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
        self.main_widget.setObjectName('edit_main_widget')
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        self.main_widget.setLayout(main_layout)

        title_widget = QWidget()
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 5)
        title_widget.setLayout(title_layout)
        main_layout.addWidget(title_widget)

        title_label = QLabel('Title:')
        title_label.setFont(self.gui.bold_font)
        title_layout.addWidget(title_label)

        self.title_line_edit = QLineEdit()
        self.title_line_edit.setFont(self.gui.standard_font)
        title_layout.addWidget(self.title_line_edit)

        if self.type == 'song':
            author_widget = QWidget()
            author_layout = QHBoxLayout()
            author_layout.setContentsMargins(0, 0, 0, 5)
            author_widget.setLayout(author_layout)
            main_layout.addWidget(author_widget)

            author_label = QLabel('Author:')
            author_label.setFont(self.gui.bold_font)
            author_layout.addWidget(author_label)

            self.author_line_edit = QLineEdit()
            self.author_line_edit.setFont(self.gui.standard_font)
            author_layout.addWidget(self.author_line_edit)

            copyright_widget = QWidget()
            copyright_layout = QHBoxLayout()
            copyright_layout.setContentsMargins(0, 0, 0, 5)
            copyright_widget.setLayout(copyright_layout)
            main_layout.addWidget(copyright_widget)

            copyright_label = QLabel('Copyright:')
            copyright_label.setFont(self.gui.bold_font)
            copyright_layout.addWidget(copyright_label)

            self.copyright_line_edit = QLineEdit()
            self.copyright_line_edit.setFont(self.gui.standard_font)
            copyright_layout.addWidget(self.copyright_line_edit)

            ccli_widget = QWidget()
            ccli_layout = QHBoxLayout()
            ccli_layout.setContentsMargins(0, 0, 0, 0)
            ccli_widget.setLayout(ccli_layout)
            main_layout.addWidget(ccli_widget)

            ccli_label = QLabel('CCLI Song Number:')
            ccli_label.setFont(self.gui.bold_font)
            ccli_layout.addWidget(ccli_label)

            self.ccli_num_line_edit = QLineEdit()
            self.ccli_num_line_edit.setFont(self.gui.standard_font)
            ccli_layout.addWidget(self.ccli_num_line_edit)

        main_layout.addSpacing(20)

        lyrics_label = QLabel('Lyrics')
        lyrics_label.setFont(self.gui.bold_font)
        main_layout.addWidget(lyrics_label)

        if self.type == 'song':
            lyrics_widget = QWidget()
            lyrics_widget.setObjectName('lyrics_widget')
            lyrics_layout = QGridLayout(lyrics_widget)
            lyrics_layout.setRowStretch(0, 1)
            lyrics_layout.setRowStretch(1, 20)
            lyrics_layout.setColumnStretch(0, 10)
            lyrics_layout.setColumnStretch(1, 1)
            lyrics_layout.setColumnStretch(2, 1)
            main_layout.addWidget(lyrics_widget)

        self.lyrics_edit = FormattableTextEdit(self.gui)
        self.lyrics_edit.setFont(self.gui.standard_font)
        if self.type == 'song':
            lyrics_layout.addWidget(self.lyrics_edit, 0, 0, 3, 1)
        else:
            main_layout.addWidget(self.lyrics_edit)

        if self.type == 'song':
            segment_label = QLabel('Segments')
            segment_label.setFont(self.gui.standard_font)
            lyrics_layout.addWidget(segment_label, 0, 1)

            song_order_label = QLabel('Song Order')
            song_order_label.setFont(self.gui.standard_font)
            lyrics_layout.addWidget(song_order_label, 0, 2)

            self.song_section_list_widget = QListWidget()
            self.song_section_list_widget.setAcceptDrops(False)
            self.song_section_list_widget.setDragEnabled(True)
            self.song_section_list_widget.setDragDropMode(QListWidget.DragDropMode.DragOnly)
            self.song_section_list_widget.setMinimumWidth(120)
            self.song_section_list_widget.setToolTip('Drag and drop the song segments into the song order box to '
                                                     'set the oder in which verses, choruses, etc. are displayed')
            self.song_section_list_widget.setFont(self.gui.standard_font)
            lyrics_layout.addWidget(self.song_section_list_widget, 1, 1)

            self.song_order_list_widget = CustomListWidget()
            self.song_order_list_widget.setAcceptDrops(True)
            self.song_order_list_widget.setDragEnabled(True)
            self.song_order_list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
            self.song_order_list_widget.setMinimumWidth(120)
            self.song_order_list_widget.setToolTip('Press "Delete" to remove an item from the song order list')
            self.song_order_list_widget.setFont(self.gui.standard_font)
            lyrics_layout.addWidget(self.song_order_list_widget, 1, 2)

        if self.type == 'song':
            tool_bar = QWidget()
            toolbar_layout = QHBoxLayout()
            tool_bar.setLayout(toolbar_layout)
            main_layout.addWidget(tool_bar)
            button_size = QSize(100, 30)

            tag_label = QLabel('Insert a Tag:')
            tag_label.setFont(self.gui.standard_font)
            toolbar_layout.addWidget(tag_label)

            verse_button = QPushButton('Verse')
            verse_button.setFixedSize(button_size)
            verse_button.setFont(self.gui.standard_font)
            verse_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            verse_button.clicked.connect(self.add_tag)
            toolbar_layout.addWidget(verse_button)

            chorus_button = QPushButton('Chorus')
            chorus_button.setFixedSize(button_size)
            chorus_button.setFont(self.gui.standard_font)
            chorus_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            chorus_button.clicked.connect(self.add_tag)
            toolbar_layout.addWidget(chorus_button)

            pre_chorus_button = QPushButton('Pre-Chorus')
            pre_chorus_button.setFixedSize(button_size)
            pre_chorus_button.setFont(self.gui.standard_font)
            pre_chorus_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            pre_chorus_button.clicked.connect(self.add_tag)
            toolbar_layout.addWidget(pre_chorus_button)

            bridge_button = QPushButton('Bridge')
            bridge_button.setFixedSize(button_size)
            bridge_button.setFont(self.gui.standard_font)
            bridge_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            bridge_button.clicked.connect(self.add_tag)
            toolbar_layout.addWidget(bridge_button)

            tag_button = QPushButton('Tag')
            tag_button.setFixedSize(button_size)
            tag_button.setFont(self.gui.standard_font)
            tag_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            tag_button.clicked.connect(self.add_tag)
            toolbar_layout.addWidget(tag_button)

            ending_button = QPushButton('Ending')
            ending_button.setFixedSize(button_size)
            ending_button.setFont(self.gui.standard_font)
            ending_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            ending_button.clicked.connect(self.add_tag)
            toolbar_layout.addWidget(ending_button)
            toolbar_layout.addStretch()

        show_hide_advanced_widget = QWidget()
        show_hide_advanced_layout = QHBoxLayout(show_hide_advanced_widget)
        main_layout.addWidget(show_hide_advanced_widget)

        self.show_hide_advanced_button = QPushButton('+')
        self.show_hide_advanced_button.setFont(self.gui.bold_font)
        self.show_hide_advanced_button.setFixedSize(40, 40)
        self.show_hide_advanced_button.pressed.connect(self.show_hide_advanced_options)
        show_hide_advanced_layout.addWidget(self.show_hide_advanced_button)

        show_hide_advanced_label = QLabel('Advanced Options')
        show_hide_advanced_label.setFont(self.gui.standard_font)
        show_hide_advanced_layout.addWidget(show_hide_advanced_label)
        show_hide_advanced_layout.addStretch()

        self.advanced_options_widget = QWidget()
        advanced_options_layout = QVBoxLayout(self.advanced_options_widget)
        main_layout.addWidget(self.advanced_options_widget)
        self.advanced_options_widget.hide()

        self.override_global_checkbox = QCheckBox('Override Global Settings')
        self.override_global_checkbox.setObjectName('override_global_checkbox')
        self.override_global_checkbox.setToolTip(
            'Checking this box will apply all of the below settings to this song/custom slide')
        self.override_global_checkbox.setFont(self.gui.bold_font)
        self.override_global_checkbox.setChecked(False)
        advanced_options_layout.addWidget(self.override_global_checkbox)

        if self.type == 'song':
            self.footer_checkbox = QCheckBox('Use Footer for this song')
            self.footer_checkbox.setToolTip(
                'Unchecking this box will prevent the slide footer from being displayed')
            self.footer_checkbox.setFont(self.gui.bold_font)
            self.footer_checkbox.setChecked(True)
            advanced_options_layout.addWidget(self.footer_checkbox)

        slide_settings_container = QWidget()
        slide_settings_layout = QHBoxLayout(slide_settings_container)
        advanced_options_layout.addWidget(slide_settings_container)

        self.font_widget = FontWidget(self.gui, draw_border=False, auto_update=False)
        slide_settings_layout.addWidget(self.font_widget)

        background_widget = QWidget()
        background_layout = QVBoxLayout()
        background_widget.setLayout(background_layout)
        slide_settings_layout.addWidget(background_widget)

        background_label = QLabel('Background')
        background_label.setFont(self.gui.bold_font)
        background_layout.addWidget(background_label)

        background_default_radio_button = QRadioButton('Use Global Song Background')
        background_default_radio_button.setFont(self.gui.standard_font)
        background_default_radio_button.clicked.connect(
            lambda: self.background_line_edit.setText('Use Global Song Background'))

        background_bible_default_radio_button = QRadioButton('Use Global Bible Background')
        background_bible_default_radio_button.setFont(self.gui.standard_font)
        background_bible_default_radio_button.clicked.connect(
            lambda: self.background_line_edit.setText('Use Global Bible Background'))

        background_color_radio_button = QRadioButton('Solid Color')
        background_color_radio_button.setFont(self.gui.standard_font)
        background_color_radio_button.clicked.connect(self.color_chooser)

        from widgets import ImageCombobox
        self.background_combobox = ImageCombobox(self.gui, 'edit')
        self.background_combobox.currentIndexChanged.connect(
            lambda: self.background_line_edit.setText(self.background_combobox.currentData(Qt.ItemDataRole.UserRole)))

        self.background_image_radio_button = QRadioButton('Image')
        self.background_image_radio_button.setFont(self.gui.standard_font)
        self.background_image_radio_button.clicked.connect(self.background_combobox.show)

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
        background_layout.addWidget(self.background_combobox)
        if self.type == 'song':
            self.background_combobox.hide()

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
        save_button.setFont(self.gui.standard_font)
        if self.type == 'song':
            save_button.clicked.connect(self.save_song)
        elif self.type == 'custom':
            save_button.clicked.connect(self.save_custom)
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addSpacing(20)

        cancel_button = QPushButton('Cancel')
        cancel_button.setFont(self.gui.standard_font)
        cancel_button.clicked.connect(self.deleteLater)
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()

        if self.type == 'custom':
            background_default_radio_button.setText('Use Global Song Background')

        self.main_widget.adjustSize()
        self.adjustSize()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.main_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumWidth(self.main_widget.width() + self.scroll_area.verticalScrollBar().width())
        layout.addWidget(self.scroll_area)

    def set_defaults(self):
        for i in range(self.font_widget.font_list_widget.count()):
            if self.font_widget.font_list_widget.item(i).data(20) == self.gui.main.settings['font_face']:
                self.font_widget.font_list_widget.setCurrentRow(i)
                break

        if self.gui.main.settings['font_color'] == 'black':
            self.font_widget.black_radio_button.setChecked(True)
        elif self.gui.main.settings['font_color'] == 'white':
            self.font_widget.white_radio_button.setChecked(True)
        else:
            self.font_widget.custom_font_color_radio_button.setChecked(True)
            self.font_widget.custom_font_color_radio_button.setObjectName(self.gui.main.settings['font_color'])

        self.background_button_group.button(0).setChecked(True)
        self.background_line_edit.setText('Use Global Song Background')

        self.font_widget.font_size_spinbox.setValue(self.gui.main.settings['font_size'])

        self.font_widget.shadow_checkbox.setChecked(self.gui.main.settings['use_shadow'])
        self.font_widget.shadow_color_slider.color_slider.setValue(self.gui.main.settings['shadow_color'])
        self.font_widget.shadow_offset_slider.offset_slider.setValue(self.gui.main.settings['shadow_offset'])

        self.font_widget.outline_checkbox.setChecked(self.gui.main.settings['use_outline'])
        self.font_widget.outline_color_slider.color_slider.setValue(self.gui.main.settings['outline_color'])
        self.font_widget.outline_width_slider.offset_slider.setValue(self.gui.main.settings['outline_width'])

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
        tag_list = re.findall('\[.*?\]', lyrics)
        for i in range(len(tag_list)):
            if len(tag_list[i]) < 6:
                if 'v' in tag_list[i]:
                    new_tag = '[Verse ' + tag_list[i].replace('[', '').replace(']', '').replace('v', '') + ']'
                    lyrics = lyrics.replace(tag_list[i], new_tag)
                elif 'p' in tag_list[i]:
                    new_tag = '[Pre-Chorus ' + tag_list[i].replace('[', '').replace(']', '').replace('p', '') + ']'
                    lyrics = lyrics.replace(tag_list[i], new_tag)
                elif 'c' in tag_list[i]:
                    new_tag = '[Chorus ' + tag_list[i].replace('[', '').replace(']', '').replace('c', '') + ']'
                    lyrics = lyrics.replace(tag_list[i], new_tag)
                elif 'b' in tag_list[i]:
                    new_tag = '[Bridge ' + tag_list[i].replace('[', '').replace(']', '').replace('b', '') + ']'
                    lyrics = lyrics.replace(tag_list[i], new_tag)
                elif 't' in tag_list[i]:
                    new_tag = '[Tag ' + tag_list[i].replace('[', '').replace(']', '').replace('t', '') + ']'
                    lyrics = lyrics.replace(tag_list[i], new_tag)
                elif 'e' in tag_list[i]:
                    new_tag = '[Ending ' + tag_list[i].replace('[', '').replace(']', '').replace('e', '') + ']'
                    lyrics = lyrics.replace(tag_list[i], new_tag)
                else:
                    new_tag = '[' + tag_list[i][:1] + ' ' + tag_list[i][1:] + ']'
                    lyrics = lyrics.replace(tag_list[i], new_tag)
        self.lyrics_edit.text_edit.setHtml(lyrics)

        order_items = song_data[5].split(' ')
        for i in range(len(order_items)):
            if 'v' in order_items[i]:
                order_items[i] = 'Verse ' + order_items[i].replace('[', '').replace(']', '').replace('v', '')
            elif 'p' in order_items[i]:
                order_items[i] = 'Pre-Chorus ' + order_items[i].replace('[', '').replace(']', '').replace('p', '')
            elif 'c' in order_items[i]:
                order_items[i] = 'Chorus ' + order_items[i].replace('[', '').replace(']', '').replace('c', '')
            elif 'b' in order_items[i]:
                order_items[i] = 'Bridge ' + order_items[i].replace('[', '').replace(']', '').replace('b', '')
            elif 't' in order_items[i]:
                order_items[i] = 'Tag ' + order_items[i].replace('[', '').replace(']', '').replace('t', '')
            elif 'e' in order_items[i]:
                order_items[i] = 'Ending ' + order_items[i].replace('[', '').replace(']', '').replace('e', '')

        for i in range(len(order_items)):
            if len(order_items[i].strip()) > 0:
                self.song_order_list_widget.addItem(order_items[i])

        if song_data[6] == 'true':
            self.footer_checkbox.setChecked(True)
        else:
            self.footer_checkbox.setChecked(False)

        self.font_widget.blockSignals(True)

        if song_data[17] == 'True':
            self.override_global_checkbox.setChecked(True)
        else:
            self.override_global_checkbox.setChecked(False)

        if song_data[7] == 'global':
            for i in range(self.font_widget.font_list_widget.count()):
                if self.font_widget.font_list_widget.item(i).data(20) == self.gui.main.settings['font_face']:
                    self.font_widget.font_list_widget.setCurrentRow(i)
                    break
        else:
            for i in range(self.font_widget.font_list_widget.count()):
                if self.font_widget.font_list_widget.item(i).data(20) == song_data[7]:
                    self.font_widget.font_list_widget.setCurrentRow(i)
                    break

        if song_data[8] == 'global':
            if self.gui.main.settings['font_color'] == 'black':
                self.font_widget.black_radio_button.setChecked(True)
            elif self.gui.main.settings['font_color'] == 'white':
                self.font_widget.white_radio_button.setChecked(True)
            else:
                self.font_widget.custom_font_color_radio_button.setChecked(True)
                self.font_widget.custom_font_color_radio_button.setObjectName(self.gui.main.settings['font_color'])
        elif song_data[8] == '#FFFFFF':
            self.font_widget.white_radio_button.setChecked(True)
        elif song_data[8] == '#000000':
            self.font_widget.black_radio_button.setChecked(True)
        else:
            self.font_widget.custom_font_color_radio_button.setChecked(True)
            self.font_widget.custom_font_color_radio_button.setObjectName(song_data[8])

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
            self.font_widget.font_size_spinbox.setValue(self.gui.main.settings['font_size'])
        else:
            try:
                self.font_widget.font_size_spinbox.setValue(int(song_data[10]))
            except TypeError:
                self.font_widget.font_size_spinbox.setValue(self.gui.main.settings['font_size'])

        if song_data[10] and 'global' not in song_data[10]:
            self.font_widget.font_size_spinbox.setValue(int(song_data[10]))
        else:
            self.font_widget.font_size_spinbox.setValue(int(self.gui.main.settings['font_size']))

        if song_data[11]:
            if song_data[11] == 'True':
                self.font_widget.shadow_checkbox.setChecked(True)
            else:
                self.font_widget.shadow_checkbox.setChecked(False)
        else:
            self.font_widget.shadow_checkbox.setChecked(self.gui.main.settings['use_shadow'])

        if song_data[12] and not song_data[12] == 'global':
            self.font_widget.shadow_color_slider.color_slider.setValue(int(song_data[12]))
        else:
            self.font_widget.shadow_color_slider.color_slider.setValue(self.gui.main.settings['shadow_color'])

        if song_data[13] and not song_data[13] == 'global':
            self.font_widget.shadow_offset_slider.offset_slider.setValue(int(song_data[13]))
        else:
            self.font_widget.shadow_offset_slider.offset_slider.setValue(self.gui.main.settings['shadow_offset'])

        if song_data[14]:
            if song_data[14] == 'True':
                self.font_widget.outline_checkbox.setChecked(True)
            else:
                self.font_widget.outline_checkbox.setChecked(False)
        else:
            self.font_widget.outline_checkbox.setChecked(self.gui.main.settings['use_outline'])

        if song_data[15] and not song_data[15] == 'global':
            self.font_widget.outline_color_slider.color_slider.setValue(int(song_data[15]))
        else:
            self.font_widget.outline_color_slider.color_slider.setValue(self.gui.main.settings['outline_color'])

        if song_data[16] and not song_data[16] == 'global':
            self.font_widget.outline_width_slider.offset_slider.setValue(int(song_data[16]))
        else:
            self.font_widget.outline_width_slider.offset_slider.setValue(self.gui.main.settings['outline_width'])

        self.font_widget.blockSignals(False)

        self.populate_tag_list()

    def populate_custom_data(self, custom_data):
        """
        Use the provided data to set the proper widgets.py to match the saved data
        :param list of str custom_data: The custom slide's QListWidgetItem data
        """
        self.old_title = custom_data[0]
        self.title_line_edit.setText(custom_data[0])
        self.lyrics_edit.text_edit.setHtml(custom_data[1])
        self.font_widget.blockSignals(True)

        if custom_data[2]:
            if 'global' in custom_data[2]:
                for i in range(self.font_widget.font_list_widget.count()):
                    if self.font_widget.font_list_widget.item(i).data(20) == self.gui.main.settings['font_face']:
                        self.font_widget.font_list_widget.setCurrentRow(i)
                        break
            else:
                for i in range(self.font_widget.font_list_widget.count()):
                    if self.font_widget.font_list_widget.item(i).data(20) == custom_data[2]:
                        self.font_widget.font_list_widget.setCurrentRow(i)
                        break
        else:
            for i in range(self.font_widget.font_list_widget.count()):
                if self.font_widget.font_list_widget.item(i).data(20) == self.gui.main.settings['font_face']:
                    self.font_widget.font_list_widget.setCurrentRow(i)
                    break

        if 'global' in custom_data[3]:
            if self.gui.main.settings['font_color'] == 'black':
                self.font_widget.black_radio_button.setChecked(True)
            elif self.gui.main.settings['font_color'] == 'white':
                self.font_widget.white_radio_button.setChecked(True)
            else:
                self.font_widget.custom_font_color_radio_button.setChecked(True)
                self.font_widget.custom_font_color_radio_button.setObjectName(self.gui.main.settings['font_color'])
        elif custom_data[3] == '#FFFFFF':
            self.font_widget.white_radio_button.setChecked(True)
        elif custom_data[3] == '#000000':
            self.font_widget.black_radio_button.setChecked(True)
        else:
            self.font_widget.custom_font_color_radio_button.setChecked(True)
            self.font_widget.custom_font_color_radio_button.setObjectName(custom_data[3])

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
            for i in range(self.background_combobox.count()):
                if self.background_combobox.itemText(i) == custom_data[4].split('.')[0]:
                    self.background_combobox.setCurrentIndex(i)
                    break
            self.background_line_edit.setText(custom_data[4])

        if 'global' in custom_data[5]:
            self.font_widget.font_size_spinbox.setValue(self.gui.main.settings['font_size'])
        else:
            self.font_widget.font_size_spinbox.setValue(int(custom_data[5]))

        if 'global' in custom_data[6]:
            self.font_widget.shadow_checkbox.setChecked(self.gui.main.settings['use_shadow'])
        else:
            if custom_data[6] == 'True':
                self.font_widget.shadow_checkbox.setChecked(True)
            else:
                self.font_widget.shadow_checkbox.setChecked(False)

        if 'global' in custom_data[7]:
            self.font_widget.shadow_color_slider.color_slider.setValue(self.gui.main.settings['shadow_color'])
        else:
            self.font_widget.shadow_color_slider.color_slider.setValue(int(custom_data[7]))

        if 'global' in custom_data[8]:
            self.font_widget.shadow_offset_slider.offset_slider.setValue(self.gui.main.settings['shadow_offset'])
        else:
            self.font_widget.shadow_offset_slider.offset_slider.setValue(int(custom_data[8]))

        if 'global' in custom_data[9]:
            self.font_widget.outline_checkbox.setChecked(self.gui.main.settings['use_outline'])
        else:
            if custom_data[9] == 'True':
                self.font_widget.outline_checkbox.setChecked(True)
            else:
                self.font_widget.outline_checkbox.setChecked(False)

        if 'global' in custom_data[10]:
            self.font_widget.outline_color_slider.color_slider.setValue(self.gui.main.settings['outline_color'])
        else:
            self.font_widget.outline_color_slider.color_slider.setValue(int(custom_data[10]))

        if 'global' in custom_data[11]:
            self.font_widget.outline_width_slider.offset_slider.setValue(self.gui.main.settings['outline_width'])
        else:
            self.font_widget.outline_width_slider.offset_slider.setValue(int(custom_data[11]))

        if custom_data[12] == 'True':
            self.override_global_checkbox.setChecked(True)
        else:
            self.override_global_checkbox.setChecked(False)

        self.font_widget.blockSignals(False)

    def show_hide_advanced_options(self):
        """
        Method to show or hide advanced options the user may or may not want to change. Advanced options are contained
        in the format_widget QWidget.
        """
        if self.advanced_options_widget.isHidden():
            self.advanced_options_widget.show()
            self.advanced_options_widget.adjustSize()
            width = self.advanced_options_widget.width()
            if width > self.gui.main_window.width():
                width = self.gui.main_window.width()
            self.setMinimumWidth(width)
            self.show_hide_advanced_button.setText('-')
        else:
            self.advanced_options_widget.hide()
            self.show_hide_advanced_button.setText('+')

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

    def add_tag(self):
        """
        Method to add tags to the song lyrics based on button push.
        :param str type: The tag type to be inserted
        :return:
        """

        slider_pos = self.lyrics_edit.text_edit.verticalScrollBar().sliderPosition()

        if type == 'os':
            self.lyrics_edit.text_edit.insertPlainText('\n#optional split#')

        else:
            # search first for previous instances of this tag; append numbers to the tag for multiple instances
            tag_name = self.sender().text()
            lyrics_text = self.lyrics_edit.text_edit.toHtml()
            occurrences = re.findall('\[' + tag_name + '.*?\]', lyrics_text)

            if len(occurrences) == 0:
                self.lyrics_edit.text_edit.insertPlainText('\n[' + tag_name + ' 1]\n')
            else:
                self.lyrics_edit.text_edit.insertPlainText('\n[' + tag_name + tag_name + ']\n')
                lyrics_text = self.lyrics_edit.text_edit.toHtml()
                occurrences = re.findall('\[' + tag_name + '.*?\]', lyrics_text)

                count = 1
                for item in occurrences:
                    lyrics_text = lyrics_text.replace(item, '\n[' + tag_name + ' ' + str(count) + ']\n', 1)
                    count += 1

                self.lyrics_edit.text_edit.setHtml(lyrics_text)
                self.lyrics_edit.text_edit.setFocus()

        self.populate_tag_list()
        self.lyrics_edit.text_edit.verticalScrollBar().setSliderPosition(slider_pos)
        self.lyrics_edit.text_edit.setFocus()

    def populate_tag_list(self):
        """
        Method to find tags in the song's lyrics and add those tags to the "segements" QListWidget
        """
        self.song_section_list_widget.clear()
        lyrics_text = self.lyrics_edit.text_edit.toPlainText()
        tag_list = re.findall('\[.*?\]', lyrics_text)
        for tag in tag_list:
            self.song_section_list_widget.addItem(tag.replace('[', '').replace(']', ''))

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
            return

        if self.override_global_checkbox.isChecked():
            override_global = 'True'
        else:
            override_global = 'False'

        if self.footer_checkbox.isChecked():
            footer = 'true'
        else:
            footer = 'false'

        if self.override_global_checkbox.isChecked():
            if self.font_widget.font_list_widget.currentItem():
                font = self.font_widget.font_list_widget.currentItem().data(20)
            else:
                font = self.font_widget.font_list_widget.item(0).data(20)

            if self.font_widget.font_color_button_group.checkedButton():
                font_color = self.font_widget.font_color_button_group.checkedButton().objectName()
            else:
                font_color = 'white'

            font_size = str(self.font_widget.font_size_spinbox.value())

            use_shadow = str(self.font_widget.shadow_checkbox.isChecked())
            shadow_color = str(self.font_widget.shadow_color_slider.color_slider.value())
            shadow_offset = str(self.font_widget.shadow_offset_slider.offset_slider.value())

            use_outline = str(self.font_widget.outline_checkbox.isChecked())
            outline_color = str(self.font_widget.outline_color_slider.color_slider.value())
            outline_width = str(self.font_widget.outline_width_slider.offset_slider.value())

            if 'Global' in self.background_line_edit.text():
                if 'Song' in self.background_line_edit.text():
                    background = 'global_song'
                else:
                    background = 'global_bible'
            else:
                background = self.background_line_edit.text()

        else:
            font = 'global'
            font_color = 'global'
            font_size = 'global'
            use_shadow = 'global'
            shadow_color = 'global'
            shadow_offset = 'global'
            use_outline = 'global'
            outline_color = 'global'
            outline_width = 'global'
            if self.type == 'song':
                background = 'global_song'
            else:
                background = 'global_bible'

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

        lyrics = lyrics.replace('\n', '<br />')

        song_order = ''
        for i in range(self.song_order_list_widget.count()):
            tag = self.song_order_list_widget.item(i).text()
            tag = tag.split(' ')[0][:1].lower() + tag.split(' ')[1]
            song_order += tag + ' '
        song_order = song_order.strip()

        song_data = [
            self.title_line_edit.text(),
            self.author_line_edit.text(),
            self.copyright_line_edit.text(),
            self.ccli_num_line_edit.text(),
            lyrics,
            song_order,
            footer,
            font,
            font_color,
            background,
            font_size,
            use_shadow,
            shadow_color,
            shadow_offset,
            use_outline,
            outline_color,
            outline_width,
            override_global
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

        self.gui.main.save_song(song_data, self.old_title)
        self.gui.media_widget.populate_song_list()

        if self.old_title:
            for i in range(self.gui.oos_widget.oos_list_widget.count()):
                if self.gui.oos_widget.oos_list_widget.item(i).data(20) == self.old_title:
                    new_item = self.gui.media_widget.song_list.findItems(song_data[0], Qt.MatchFlag.MatchExactly)[
                        0].clone()
                    new_item.setData(24, self.gui.media_widget.parse_song_data(new_item))
                    self.gui.oos_widget.oos_list_widget.takeItem(i)
                    self.gui.media_widget.add_song_to_service(new_item, i)
                    self.gui.oos_widget.oos_list_widget.setCurrentRow(i)
                    break

        self.deleteLater()
        save_widget.widget.deleteLater()
        if self.gui.oos_widget.oos_list_widget.currentItem():
            self.gui.send_to_preview(self.gui.oos_widget.oos_list_widget.currentItem())

    def save_custom(self):
        """
        Method to save user's changes for the custom slide type editor.
        """

        if self.override_global_checkbox.isChecked():
            override_global = 'True'
        else:
            override_global = 'False'

        if self.override_global_checkbox.isChecked():
            if self.font_widget.font_list_widget.currentItem():
                font = self.font_widget.font_list_widget.currentItem().data(20)
            else:
                font = self.font_widget.font_list_widget.item(0).data(20)

            if self.font_widget.font_color_button_group.checkedButton():
                font_color = self.font_widget.font_color_button_group.checkedButton().objectName()
            else:
                font_color = 'white'

            font_size = str(self.font_widget.font_size_spinbox.value())

            use_shadow = str(self.font_widget.shadow_checkbox.isChecked())
            shadow_color = str(self.font_widget.shadow_color_slider.color_slider.value())
            shadow_offset = str(self.font_widget.shadow_offset_slider.offset_slider.value())

            use_outline = str(self.font_widget.outline_checkbox.isChecked())
            outline_color = str(self.font_widget.outline_color_slider.color_slider.value())
            outline_width = str(self.font_widget.outline_width_slider.offset_slider.value())

            if 'Global' in self.background_line_edit.text():
                if 'Song' in self.background_line_edit.text():
                    background = 'global_song'
                else:
                    background = 'global_bible'
            elif 'rgb(' in self.background_line_edit.text():
                background = self.background_line_edit.text()
            else:
                background = self.background_line_edit.text()

        else:
            font = 'global'
            font_color = 'global'
            font_size = 'global'
            use_shadow = 'global'
            shadow_color = 'global'
            shadow_offset = 'global'
            use_outline = 'global'
            outline_color = 'global'
            outline_width = 'global'
            if self.type == 'song':
                background = 'global_song'
            else:
                background = 'global_bible'

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
            font_size,
            use_shadow,
            shadow_color,
            shadow_offset,
            use_outline,
            outline_color,
            outline_width,
            override_global
        ]

        if self.new_custom:
            if self.title_line_edit.text() in self.gui.main.get_custom_titles():
                dialog = QDialog(self.gui.main_window)
                dialog.setLayout(QVBoxLayout())
                dialog.setWindowTitle('Custom Slide Title Exists')

                label = QLabel('Unable to save Custom Slide because this title already exists\n'
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
                    custom_data[0] = line_edit.text()
                else:
                    return

        save_widget = SimpleSplash(self.gui, 'Saving...')

        self.gui.main.save_custom(custom_data, self.old_title)
        self.gui.media_widget.populate_custom_list()

        if self.old_title:
            for i in range(self.gui.oos_widget.oos_list_widget.count()):
                if self.gui.oos_widget.oos_list_widget.item(i).data(20) == self.old_title:
                    self.change_thumbnail(self.gui.oos_widget.oos_list_widget.item(i))
                    new_item = self.gui.media_widget.custom_list.findItems(custom_data[0], Qt.MatchFlag.MatchExactly)[
                        0].clone()
                    self.gui.oos_widget.oos_list_widget.takeItem(i)
                    self.gui.media_widget.add_custom_to_service(new_item, i)
                    self.gui.oos_widget.oos_list_widget.setCurrentRow(i)
                    break

        self.deleteLater()
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
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
        elif item.data(29) == 'global_bible':
            pixmap = self.gui.global_bible_background_pixmap
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
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
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)

        item_widget = StandardItemWidget(self.gui, item.data(20), '', pixmap)
        item.setSizeHint(item_widget.sizeHint())
        self.gui.oos_widget.oos_list_widget.setItemWidget(item, item_widget)


class CustomListWidget(QListWidget):
    """
    Implements QListWidget to provide the ability to press "Delete" in order to remove an item from the list
    """

    def __init__(self):
        super().__init__()

    def keyPressEvent(self, evt):
        """
        Overrides keyPressEvent to listen for a delete key press. Uses takeItem to remove the currently selected row
        """
        if evt.key() == Qt.Key.Key_Delete:
            if self.currentRow() or self.currentRow() == 0:
                self.takeItem(self.currentRow())
            else:
                super().keyPressEvent(evt)
