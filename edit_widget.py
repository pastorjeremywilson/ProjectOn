import os.path
import re

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QPixmap, QPainter, QBrush, QIcon, QTextCursor
from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QLineEdit, \
    QMessageBox, QCheckBox, QRadioButton, QButtonGroup, QColorDialog, QFileDialog, QScrollArea, QListWidget, \
    QSpinBox, QTextEdit, QComboBox

import parsers
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
        self.item_index = None
        if self.type == 'song':
            self.item_index = self.gui.media_widget.song_list.currentIndex()
        else:
            self.item_index = self.gui.media_widget.custom_list.currentIndex()

        self.setObjectName('edit_widget')
        self.setWindowFlag(Qt.WindowType.Window)
        self.init_components()

        self.main_widget.adjustSize()
        preferred_height = int(self.gui.primary_screen.size().height() * 4 / 5)
        self.setGeometry(50, 50, self.scroll_area.width(), preferred_height)
        self.title_line_edit.setFocus()
        if data and type == 'song':
            self.populate_song_data(data)
            self.font_widget.change_font_sample()
        elif data and type == 'custom':
            self.populate_custom_data(data)
            self.font_widget.change_font_sample()
        elif not data:
            if type == 'song':
                self.new_song = True
                self.set_defaults()
            else:
                self.new_custom = True
                self.set_defaults()

        # ensure the advanced options widgets are hidden or shown accordingly
        self.override_global_changed()

        self.font_widget.change_font()
        self.show()

    def init_components(self):
        """
        Create and add the necessary widgets.py to this dialog
        """
        button_size = QSize(36, 36)
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
        self.lyrics_edit.setMinimumHeight(400)
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

        if self.type == 'custom':
            audio_widget = QWidget()
            audio_layout = QHBoxLayout(audio_widget)
            main_layout.addWidget(audio_widget)

            self.add_audio_button = QPushButton()
            self.add_audio_button.setObjectName('add_audio_button')
            self.add_audio_button.setCheckable(True)
            self.add_audio_button.setToolTip('Add an audio file that will play when this slide is shown')
            self.add_audio_button.setIcon(QIcon('resources/gui_icons/audio.svg'))
            self.add_audio_button.setIconSize(button_size)
            self.add_audio_button.setChecked(False)
            self.add_audio_button.released.connect(self.add_audio_changed)
            audio_layout.addWidget(self.add_audio_button)

            add_audio_label = QLabel('Add Audio')
            add_audio_label.setFont(self.gui.bold_font)
            audio_layout.addWidget(add_audio_label)
            audio_layout.addSpacing(20)

            self.audio_line_edit = QLineEdit()
            self.audio_line_edit.setObjectName('audio_line_edit')
            self.audio_line_edit.setFont(self.gui.standard_font)
            audio_layout.addWidget(self.audio_line_edit)
            audio_layout.addSpacing(20)

            self.choose_file_button = QPushButton()
            self.choose_file_button.setObjectName('choose_file_button')
            self.choose_file_button.setIcon(QIcon('resources/gui_icons/open.svg'))
            self.choose_file_button.setIconSize(QSize(24, 24))
            self.choose_file_button.setFont(self.gui.standard_font)
            self.choose_file_button.setToolTip('Choose an audio file')
            self.choose_file_button.pressed.connect(self.get_audio_file)
            audio_layout.addWidget(self.choose_file_button)

            self.loop_audio_button = QPushButton()
            self.loop_audio_button.setObjectName('loop_audio_button')
            self.loop_audio_button.setCheckable(True)
            self.loop_audio_button.setIcon(QIcon('resources/gui_icons/repeat.svg'))
            self.loop_audio_button.setIconSize(QSize(24, 24))
            self.loop_audio_button.setFont(self.gui.standard_font)
            self.loop_audio_button.setToolTip('Play this audio on a continual loop so long as this slide is showing')
            audio_layout.addWidget(self.loop_audio_button)
            audio_layout.addStretch()

            self.loop_audio_button.hide()
            self.audio_line_edit.hide()
            self.choose_file_button.hide()

            auto_play_widget = QWidget()
            auto_play_layout = QHBoxLayout(auto_play_widget)
            main_layout.addWidget(auto_play_widget)

            self.auto_play_spinbox = QSpinBox()

            self.split_slides_button = QPushButton()
            self.split_slides_button.setObjectName('split_slides_button')
            self.split_slides_button.setCheckable(True)
            self.split_slides_button.setToolTip(
                'Split the above text into individual slides wherever there is a blank line')
            self.split_slides_button.setFont(self.gui.bold_font)
            self.split_slides_button.setIcon(QIcon('resources/gui_icons/split.svg'))
            self.split_slides_button.setIconSize(button_size)
            self.split_slides_button.setChecked(False)
            self.split_slides_button.released.connect(self.split_slides_changed)
            auto_play_layout.addWidget(self.split_slides_button)

            split_slides_label = QLabel('Split Slides')
            split_slides_label.setFont(self.gui.bold_font)
            auto_play_layout.addWidget(split_slides_label)
            auto_play_layout.addSpacing(20)

            self.auto_play_checkbox = QCheckBox('Auto-Play Slide Text')
            self.auto_play_checkbox.setObjectName('auto_play_checkbox')
            self.auto_play_checkbox.setToolTip(
                'Use blank lines to create separate slides that will be scrolled through automatically')
            self.auto_play_checkbox.setFont(self.gui.bold_font)
            self.auto_play_checkbox.setChecked(False)
            auto_play_layout.addWidget(self.auto_play_checkbox)
            auto_play_layout.addSpacing(20)

            self.auto_play_spinbox_label = QLabel('Secs. Between Slides:')
            self.auto_play_spinbox_label.setFont(self.gui.standard_font)
            auto_play_layout.addWidget(self.auto_play_spinbox_label)

            self.auto_play_spinbox.setFont(self.gui.standard_font)
            self.auto_play_spinbox.setMinimumSize(60, 30)
            self.auto_play_spinbox.setRange(1, 60)
            self.auto_play_spinbox.setValue(6)
            auto_play_layout.addWidget(self.auto_play_spinbox)
            auto_play_layout.addStretch()

            self.auto_play_checkbox.hide()
            self.auto_play_spinbox_label.hide()
            self.auto_play_spinbox.hide()

        override_button_widget = QWidget()
        override_button_layout = QHBoxLayout(override_button_widget)
        main_layout.addWidget(override_button_widget)

        self.override_global_button = QPushButton()
        self.override_global_button.setObjectName('override_global_button')
        self.override_global_button.setCheckable(True)
        self.override_global_button.setToolTip(
            'Checking this box will apply all of the below settings to this song/custom slide')
        self.override_global_button.setFont(self.gui.bold_font)
        self.override_global_button.setIcon(QIcon('resources/gui_icons/override_global.svg'))
        self.override_global_button.setIconSize(button_size)
        self.override_global_button.setChecked(False)
        self.override_global_button.released.connect(self.override_global_changed)
        override_button_layout.addWidget(self.override_global_button)

        override_global_label = QLabel('Custom Slide Settings')
        override_global_label.setFont(self.gui.bold_font)
        override_button_layout.addWidget(override_global_label)
        override_button_layout.addStretch()

        self.advanced_options_widget = QWidget()
        advanced_options_layout = QVBoxLayout(self.advanced_options_widget)
        main_layout.addWidget(self.advanced_options_widget)

        if self.type == 'song':
            footer_widget = QWidget()
            footer_layout = QVBoxLayout(footer_widget)
            footer_layout.setContentsMargins(60, 0, 0, 0)
            advanced_options_layout.addWidget(footer_widget)

            self.footer_checkbox = QCheckBox('Use Footer for this song')
            self.footer_checkbox.setToolTip(
                'Unchecking this box will prevent the slide footer from being displayed')
            self.footer_checkbox.setFont(self.gui.bold_font)
            self.footer_checkbox.setChecked(True)
            footer_layout.addWidget(self.footer_checkbox)

        slide_settings_container = QWidget()
        slide_settings_layout = QHBoxLayout(slide_settings_container)
        advanced_options_layout.addWidget(slide_settings_container)

        self.font_widget = FontWidget(self.gui, self.type, draw_border=False, applies_to_global=False)
        slide_settings_layout.addWidget(self.font_widget)

        background_widget = QWidget()
        background_layout = QVBoxLayout()
        background_widget.setLayout(background_layout)
        background_layout.setContentsMargins(60, 0, 0, 0)
        advanced_options_layout.addWidget(background_widget)

        background_label = QLabel('Background')
        background_label.setFont(self.gui.bold_font)
        background_layout.addWidget(background_label)

        background_song_radio_button = QRadioButton('Use Global Song Background')
        background_song_radio_button.setFont(self.gui.standard_font)
        background_song_radio_button.clicked.connect(
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
        self.background_combobox.currentIndexChanged.connect(self.background_combobox_change)

        self.background_image_radio_button = QRadioButton('Image')
        self.background_image_radio_button.setFont(self.gui.standard_font)

        self.background_button_group = QButtonGroup()
        self.background_button_group.setObjectName('background_button_group')
        self.background_button_group.addButton(background_song_radio_button, 0)
        self.background_button_group.addButton(background_bible_default_radio_button, 1)
        self.background_button_group.addButton(background_color_radio_button, 2)
        self.background_button_group.addButton(self.background_image_radio_button, 3)
        background_song_radio_button.setChecked(True)

        background_layout.addWidget(background_song_radio_button)
        background_layout.addWidget(background_bible_default_radio_button)
        background_layout.addWidget(background_color_radio_button)
        background_layout.addWidget(self.background_image_radio_button)
        background_layout.addWidget(self.background_combobox)

        chosen_widget = QWidget()
        chosen_layout = QHBoxLayout()
        chosen_widget.setLayout(chosen_layout)
        background_layout.addWidget(chosen_widget)

        chosen_background_label = QLabel('Chosen Background:')
        chosen_layout.addWidget(chosen_background_label)

        self.background_line_edit = QLineEdit()
        self.background_line_edit.setObjectName('background_line_edit')
        self.background_line_edit.setText('Use Global Song Background')
        self.background_line_edit.textChanged.connect(self.font_widget.font_sample.repaint)
        chosen_layout.addWidget(self.background_line_edit)
        background_layout.addStretch()

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
            background_song_radio_button.setText('Use Global Song Background')

        self.main_widget.adjustSize()
        self.adjustSize()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.main_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumWidth(self.main_widget.width() + self.scroll_area.verticalScrollBar().width())
        layout.addWidget(self.scroll_area)

    def set_defaults(self):
        if self.type == 'song':
            slide_type = 'song'
        else:
            slide_type = 'bible'

        for i in range(self.font_widget.font_face_combobox.count()):
            if self.font_widget.font_face_combobox.itemText(i)  == self.gui.main.settings[slide_type + '_font_face']:
                self.font_widget.font_face_combobox.setCurrentIndex(i)
                break

        if self.gui.main.settings[slide_type + '_font_color'] == 'black':
            self.font_widget.black_radio_button.setChecked(True)
        elif self.gui.main.settings[slide_type + '_font_color'] == 'white':
            self.font_widget.white_radio_button.setChecked(True)
        else:
            self.font_widget.custom_font_color_radio_button.setChecked(True)
            self.font_widget.custom_font_color_radio_button.setObjectName(self.gui.main.settings[slide_type + '_font_color'])

        if slide_type == 'song':
            self.background_button_group.button(0).setChecked(True)
            self.background_line_edit.setText('Use Global Song Background')
        else:
            self.background_button_group.button(1).setChecked(True)
            self.background_line_edit.setText('Use Global Bible Background')

        self.font_widget.font_size_spinbox.setValue(self.gui.main.settings[slide_type + '_font_size'])

        self.font_widget.shadow_checkbox.setChecked(self.gui.main.settings[slide_type + '_use_shadow'])
        self.font_widget.shadow_color_slider.color_slider.setValue(self.gui.main.settings[slide_type + '_shadow_color'])
        self.font_widget.shadow_offset_slider.offset_slider.setValue(self.gui.main.settings[slide_type + '_shadow_offset'])

        self.font_widget.outline_checkbox.setChecked(self.gui.main.settings[slide_type + '_use_outline'])
        self.font_widget.outline_color_slider.color_slider.setValue(self.gui.main.settings[slide_type + '_outline_color'])
        self.font_widget.outline_width_slider.offset_slider.setValue(self.gui.main.settings[slide_type + '_outline_width'])

        self.font_widget.shade_behind_text_checkbox.setChecked(self.gui.main.settings[slide_type + '_use_shade'])
        self.font_widget.shade_color_slider.color_slider.setValue(self.gui.main.settings[slide_type + '_shade_color'])
        self.font_widget.shade_opacity_slider.color_slider.setValue(self.gui.main.settings[slide_type + '_shade_opacity'])

    def background_combobox_change(self):
        self.background_line_edit.setText(self.background_combobox.currentData(Qt.ItemDataRole.UserRole))
        self.font_widget.font_sample.paint_font()

    def add_audio_changed(self):
        self.audio_line_edit.setVisible(self.add_audio_button.isChecked())
        self.choose_file_button.setVisible(self.add_audio_button.isChecked())
        self.loop_audio_button.setVisible(self.add_audio_button.isChecked())
        if self.add_audio_button.isChecked():
            self.add_audio_button.setIcon(QIcon('resources/gui_icons/audio_selected.svg'))
        else:
            self.add_audio_button.setIcon(QIcon('resources/gui_icons/audio.svg'))
            self.audio_line_edit.clear()

    def split_slides_changed(self):
        if self.split_slides_button.isChecked():
            self.split_slides_button.setIcon(QIcon('resources/gui_icons/split_selected.svg'))
        else:
            self.split_slides_button.setIcon(QIcon('resources/gui_icons/split.svg'))
        self.auto_play_checkbox.setVisible(self.split_slides_button.isChecked())
        self.auto_play_spinbox_label.setVisible(self.split_slides_button.isChecked())
        self.auto_play_spinbox.setVisible(self.split_slides_button.isChecked())

    def get_audio_file(self):
        file_dialog = QFileDialog()
        result = file_dialog.getOpenFileName(
            self,
            'Choose Audio File',
            os.path.expanduser('~'),
            'Audio Files (*.mp3 *.wav *.wma *.flac)'
        )
        if len(result[0]) > 0:
            self.audio_line_edit.setText(result[0])

    def override_global_changed(self):
        if self.override_global_button.isChecked():
            self.override_global_button.setIcon(QIcon('resources/gui_icons/override_global_selected.svg'))
        else:
            self.override_global_button.setIcon(QIcon('resources/gui_icons/override_global.svg'))
        for widget in self.advanced_options_widget.findChildren(QWidget):
            if not widget.objectName() == 'override_global_button':
                set_enabled = getattr(widget, 'setEnabled', None)
                hide = getattr(widget, 'hide', None)
                if callable(hide):
                    widget.setHidden(not self.override_global_button.isChecked())

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

        lyrics = self.get_simplified_text(song_data[4])

        # reformat old tags, add coloring to tags
        tag_list = re.findall('\[.*?]', lyrics, flags=re.S)
        if self.gui.main.settings['theme'] == 'light':
            color_tag_start = '<span style="color: #007600;">'
        else:
            color_tag_start = '<span style="color: #00ff00;">'
        color_tag_end = '</span>'
        for i in range(len(tag_list)):
            if len(tag_list[i]) < 6:
                if 'v' in tag_list[i]:
                    tag_num = tag_list[i].replace('[', '').replace(']', '').replace('v', '').strip()
                    new_tag = f'{color_tag_start}[Verse {tag_num}]{color_tag_end}'
                    lyrics = lyrics.replace(tag_list[i], new_tag)
                elif 'p' in tag_list[i]:
                    tag_num = tag_list[i].replace('[', '').replace(']', '').replace('p', '').strip()
                    new_tag = f'{color_tag_start}[Pre-Chorus {tag_num}]{color_tag_end}'
                    lyrics = lyrics.replace(tag_list[i], new_tag)
                elif 'c' in tag_list[i]:
                    tag_num = tag_list[i].replace('[', '').replace(']', '').replace('c', '').strip()
                    new_tag = f'{color_tag_start}[Chorus {tag_num}]{color_tag_end}'
                    lyrics = lyrics.replace(tag_list[i], new_tag)
                elif 'b' in tag_list[i]:
                    tag_num = tag_list[i].replace('[', '').replace(']', '').replace('b', '').strip()
                    new_tag = f'{color_tag_start}[Bridge {tag_num}]{color_tag_end}'
                    lyrics = lyrics.replace(tag_list[i], new_tag)
                elif 't' in tag_list[i]:
                    tag_num = tag_list[i].replace('[', '').replace(']', '').replace('t', '').strip()
                    new_tag = f'{color_tag_start}[Tag {tag_num}]{color_tag_end}'
                    lyrics = lyrics.replace(tag_list[i], new_tag)
                elif 'e' in tag_list[i]:
                    tag_num = tag_list[i].replace('[', '').replace(']', '').replace('e', '').strip()
                    new_tag = f'{color_tag_start}[Ending {tag_num}]{color_tag_end}'
                    lyrics = lyrics.replace(tag_list[i], new_tag)
                else:
                    new_tag = f'{color_tag_start}{tag_list[i]}{color_tag_end}'
                    lyrics = lyrics.replace(tag_list[i], new_tag)
            else:
                new_tag = f'{color_tag_start}{tag_list[i]}{color_tag_end}'
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

        self.font_widget.blockSignals(True)

        # set the override global checkbox
        if song_data[17] == 'True':
            self.override_global_button.setChecked(True)
        else:
            self.override_global_button.setChecked(False)

        # set the footer checkbox
        if song_data[6] == 'true':
            self.footer_checkbox.setChecked(True)
        else:
            self.footer_checkbox.setChecked(False)

        # set the font face list widget
        if not song_data[7] or 'global' in song_data[7]:
            font_face = self.gui.main.settings['song_font_face']
        else:
            font_face = song_data[7]
        for i in range(self.font_widget.font_face_combobox.count()):
            if self.font_widget.font_face_combobox.itemText(i) == font_face:
                self.font_widget.font_face_combobox.setCurrentIndex(i)
                break

        # check the proper font color radio button
        if not song_data[8] or 'global' in song_data[8]:
            if self.gui.main.settings['song_font_color'] == 'black':
                self.font_widget.black_radio_button.setChecked(True)
            elif self.gui.main.settings['song_font_color'] == 'white':
                self.font_widget.white_radio_button.setChecked(True)
            else:
                self.font_widget.custom_font_color_radio_button.setChecked(True)
                self.font_widget.custom_font_color_radio_button.setObjectName(self.gui.main.settings['song_font_color'])
        elif song_data[8] == '#FFFFFF':
            self.font_widget.white_radio_button.setChecked(True)
        elif song_data[8] == '#000000':
            self.font_widget.black_radio_button.setChecked(True)
        else:
            self.font_widget.custom_font_color_radio_button.setChecked(True)
            self.font_widget.custom_font_color_radio_button.setObjectName(song_data[8])

        # check the proper background radio button
        if not song_data[9] or song_data[9] == 'global_song':
            self.background_button_group.button(0).setChecked(True)
            self.background_line_edit.setText('Use Global Song Background')
        elif song_data[9] == 'global_bible':
            self.background_button_group.button(1).setChecked(True)
            self.background_line_edit.setText('Use Global Bible Background')
        elif 'rgb(' in song_data[9]:
            self.background_button_group.button(2).setChecked(True)
            self.background_line_edit.setText(song_data[9])
        else:
            for i in range(self.background_combobox.count()):
                if self.background_combobox.itemData(i, Qt.ItemDataRole.UserRole) == song_data[9]:
                    self.background_combobox.setCurrentIndex(i)
                    break
            self.background_button_group.button(3).setChecked(True)
            self.background_combobox.setEnabled(True)
            self.background_line_edit.setText(song_data[9])

        # set the font size spinbox's value
        if not song_data[10] or 'global' in song_data[10]:
            self.font_widget.font_size_spinbox.setValue(self.gui.main.settings['song_font_size'])
        else:
            self.font_widget.font_size_spinbox.setValue(int(song_data[10]))

        # set the shadow checkbox
        if not song_data[11] or 'global' in song_data[11]:
            self.font_widget.shadow_checkbox.setChecked(self.gui.main.settings['song_use_shadow'])
        elif song_data[11] == 'True':
            self.font_widget.shadow_checkbox.setChecked(True)
        else:
            self.font_widget.shadow_checkbox.setChecked(False)

        # set the shadow color slider's value
        if not song_data[12] or 'global' in song_data[12]:
            self.font_widget.shadow_color_slider.color_slider.setValue(self.gui.main.settings['song_shadow_color'])
        else:
            self.font_widget.shadow_color_slider.color_slider.setValue(int(song_data[12]))

        # set the shadow offset slider's value
        if not song_data[13] or 'global' in song_data[13]:
            self.font_widget.shadow_offset_slider.offset_slider.setValue(self.gui.main.settings['song_shadow_offset'])
        else:
            self.font_widget.shadow_offset_slider.offset_slider.setValue(int(song_data[13]))
        self.font_widget.shadow_offset_slider.current_label.setText(
            str(self.font_widget.shadow_offset_slider.offset_slider.value()) + 'px')

        # set the outline checkbox
        if not song_data[14] or 'global' in song_data[14]:
            self.font_widget.outline_checkbox.setChecked(self.gui.main.settings['song_use_outline'])
        elif song_data[14] == 'True':
            self.font_widget.outline_checkbox.setChecked(True)
        else:
            self.font_widget.outline_checkbox.setChecked(False)

        # set the outline color slider's value
        if not song_data[15] or 'global' in song_data[15]:
            self.font_widget.outline_color_slider.color_slider.setValue(self.gui.main.settings['song_outline_color'])
        else:
            self.font_widget.outline_color_slider.color_slider.setValue(int(song_data[15]))

        # set the outline width slider's value
        if not song_data[16] or 'global' in song_data[16]:
            self.font_widget.outline_width_slider.offset_slider.setValue(self.gui.main.settings['song_outline_width'])
        else:
            self.font_widget.outline_width_slider.offset_slider.setValue(int(song_data[16]))
        self.font_widget.outline_width_slider.current_label.setText(
            str(self.font_widget.outline_width_slider.offset_slider.value()) + 'px')

        # set the shade behind text checkbox
        if not song_data[18] or 'global' in song_data[18]:
            self.font_widget.shade_behind_text_checkbox.setChecked(self.gui.main.settings['song_use_shade'])
        elif song_data[18] == 'True':
            self.font_widget.shade_behind_text_checkbox.setChecked(True)
        else:
            self.font_widget.shade_behind_text_checkbox.setChecked(False)

        # set the shade color slider's value
        if not song_data[19] or 'global' in song_data[19]:
            self.font_widget.shade_color_slider.color_slider.setValue(self.gui.main.settings['song_shade_color'])
        else:
            self.font_widget.shade_color_slider.color_slider.setValue(int(song_data[19]))

        # set the shade opacity slider's value
        if not song_data[20] or 'global' in song_data[20]:
            self.font_widget.shade_opacity_slider.color_slider.setValue(self.gui.main.settings['song_shade_opacity'])
        else:
            self.font_widget.shade_opacity_slider.color_slider.setValue(int(song_data[20]))

        self.font_widget.blockSignals(False)
        self.populate_tag_list()

    def populate_custom_data(self, custom_data):
        """
        Use the provided data to set the proper widgets.py to match the saved data
        :param list of str custom_data: The custom slide's QListWidgetItem data
        """
        self.old_title = custom_data[0]
        self.title_line_edit.setText(custom_data[0])
        self.lyrics_edit.text_edit.setHtml(self.get_simplified_text(custom_data[1]))
        self.font_widget.blockSignals(True)

        # set the override global checkbox
        if custom_data[12] == 'True':
            self.override_global_button.setChecked(True)
        else:
            self.override_global_button.setChecked(False)
        self.override_global_changed()

        # set the font face list widget
        if not custom_data[2] or 'global' in custom_data[2]:
            font_face = self.gui.main.settings['bible_font_face']
        else:
            font_face = custom_data[2]
        for i in range(self.font_widget.font_face_combobox.count()):
            if self.font_widget.font_face_combobox.itemText(i) == font_face:
                self.font_widget.font_face_combobox.setCurrentIndex(i)
                break

        # check the proper font color radio button
        if not custom_data[3] or 'global' in custom_data[3]:
            if self.gui.main.settings['bible_font_color'] == 'black':
                self.font_widget.black_radio_button.setChecked(True)
            elif self.gui.main.settings['bible_font_color'] == 'white':
                self.font_widget.white_radio_button.setChecked(True)
            else:
                self.font_widget.custom_font_color_radio_button.setChecked(True)
                self.font_widget.custom_font_color_radio_button.setObjectName(
                    self.gui.main.settings['bible_font_color'])
        elif custom_data[3] == '#FFFFFF':
            self.font_widget.white_radio_button.setChecked(True)
        elif custom_data[3] == '#000000':
            self.font_widget.black_radio_button.setChecked(True)
        else:
            self.font_widget.custom_font_color_radio_button.setChecked(True)
            self.font_widget.custom_font_color_radio_button.setObjectName(custom_data[3])

        # check the proper background radio button
        if not custom_data[4]:
            self.background_button_group.button(1).setChecked(True)
            self.background_line_edit.setText('Use Global Bible Background')
        elif custom_data[4] == 'global_song':
            self.background_button_group.button(0).setChecked(True)
            self.background_line_edit.setText('Use Global Song Background')
        elif custom_data[4] == 'global_bible':
            self.background_button_group.button(1).setChecked(True)
            self.background_line_edit.setText('Use Global Bible Background')
        elif 'rgb(' in custom_data[4]:
            self.background_button_group.button(2).setChecked(True)
            self.background_line_edit.setText(custom_data[4])
        else:
            for i in range(self.background_combobox.count()):
                if self.background_combobox.itemData(i, Qt.ItemDataRole.UserRole) == custom_data[4]:
                    self.background_combobox.setCurrentIndex(i)
                    break
            self.background_button_group.button(3).setChecked(True)
            self.background_combobox.setEnabled(True)
            self.background_line_edit.setText(custom_data[4])

        # set the font size spinbox's value
        if not custom_data[5] or 'global' in custom_data[5]:
            self.font_widget.font_size_spinbox.setValue(self.gui.main.settings['bible_font_size'])
        else:
            self.font_widget.font_size_spinbox.setValue(int(custom_data[5]))

        # set the use shadow checkbox
        if not custom_data[6] or 'global' in custom_data[6]:
            self.font_widget.shadow_checkbox.setChecked(self.gui.main.settings['bible_use_shadow'])
        elif custom_data[6] == 'True':
            self.font_widget.shadow_checkbox.setChecked(True)
        else:
            self.font_widget.shadow_checkbox.setChecked(False)

        # set the shadow color slider's value
        if not custom_data[7] or 'global' in custom_data[7]:
            self.font_widget.shadow_color_slider.color_slider.setValue(self.gui.main.settings['bible_shadow_color'])
        else:
            self.font_widget.shadow_color_slider.color_slider.setValue(int(custom_data[7]))

        # set the shadow offset slider's value
        if not custom_data[8] or 'global' in custom_data[8]:
            self.font_widget.shadow_offset_slider.offset_slider.setValue(self.gui.main.settings['bible_shadow_offset'])
        else:
            self.font_widget.shadow_offset_slider.offset_slider.setValue(int(custom_data[8]))
        self.font_widget.shadow_offset_slider.current_label.setText(
            str(self.font_widget.shadow_offset_slider.offset_slider.value()) + 'px')

        # set the outline checkbox
        if not custom_data[9] or 'global' in custom_data[9]:
            self.font_widget.outline_checkbox.setChecked(self.gui.main.settings['bible_use_outline'])
        elif custom_data[9] == 'True':
            self.font_widget.outline_checkbox.setChecked(True)
        else:
            self.font_widget.outline_checkbox.setChecked(False)

        # set the outline color slider value
        if not custom_data[10] or 'global' in custom_data[10]:
            self.font_widget.outline_color_slider.color_slider.setValue(self.gui.main.settings['bible_outline_color'])
        else:
            self.font_widget.outline_color_slider.color_slider.setValue(int(custom_data[10]))

        # set the outline width slider's value
        if not custom_data[11] or 'global' in custom_data[11]:
            self.font_widget.outline_width_slider.offset_slider.setValue(self.gui.main.settings['bible_outline_width'])
        else:
            self.font_widget.outline_width_slider.offset_slider.setValue(int(custom_data[11]))
        self.font_widget.outline_width_slider.current_label.setText(
            str(self.font_widget.outline_width_slider.offset_slider.value()) + 'px')

        # set the shade behind text checkbox
        if not custom_data[13] or 'global' in custom_data[13]:
            self.font_widget.shade_behind_text_checkbox.setChecked(self.gui.main.settings['bible_use_shade'])
        elif custom_data[13] == 'True':
            self.font_widget.shade_behind_text_checkbox.setChecked(True)
        else:
            self.font_widget.shade_behind_text_checkbox.setChecked(False)

        # set the shade color slider's value
        if not custom_data[14] or 'global' in custom_data[14]:
            self.font_widget.shade_color_slider.color_slider.setValue(self.gui.main.settings['bible_shade_color'])
        else:
            self.font_widget.shade_color_slider.color_slider.setValue(int(custom_data[14]))

        # set the shade opacity slider's value
        if not custom_data[15] or 'global' in custom_data[15]:
            self.font_widget.shade_opacity_slider.color_slider.setValue(self.gui.main.settings['bible_shade_opacity'])
        else:
            self.font_widget.shade_opacity_slider.color_slider.setValue(int(custom_data[15]))

        # set the audio file
        if custom_data[16] and len(custom_data[6]) > 0:
            self.add_audio_button.setChecked(True)
            self.audio_line_edit.setText(custom_data[16])
        self.add_audio_changed()
        if custom_data[17] == 'True':
            self.loop_audio_button.setChecked(True)
        else:
            self.loop_audio_button.setChecked(False)

        # set auto-play
        if custom_data[18] == 'True':
            self.auto_play_checkbox.setChecked(True)
        else:
            self.auto_play_checkbox.setChecked(False)
        if custom_data[19]:
            self.auto_play_spinbox.setValue(int(custom_data[19]))

        if custom_data[20] == 'True':
            self.split_slides_button.setChecked(True)
        else:
            self.split_slides_button.setChecked(False)
        self.split_slides_changed()

        self.font_widget.blockSignals(False)

    def show_hide_advanced_options(self):
        """
        Method to show or hide advanced options the user may or may not want to change. Advanced options are contained
        in the format_widget QWidget.
        """
        if self.advanced_options_widget.isHidden():
            self.advanced_options_widget.show()
            self.advanced_options_widget.adjustSize()
            width = self.advanced_options_widget.width() + 60
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

        if self.sender().text() == 'os':
            self.lyrics_edit.text_edit.insertPlainText('\n#optional split#')

        else:
            # search first for previous instances of this tag; append numbers to the tag for multiple instances
            tag_name = self.sender().text()
            lyrics_text = self.lyrics_edit.text_edit.toHtml()
            occurrences = re.findall('\[' + tag_name + '.*?\]', lyrics_text)

            # determine if breaks are needed before or after the tag
            tag_start = '<br />'
            tag_end = '<br />'
            cursor = self.lyrics_edit.text_edit.textCursor()
            cursor_pos = cursor.position()
            cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter, QTextCursor.MoveMode.KeepAnchor)
            if cursor.selection().toPlainText() == '\n' or cursor.position() == 0:
                tag_start = ''
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.MoveAnchor)
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
            if cursor.selection().toPlainText() == '\n':
                tag_end = ''

            if len(occurrences) == 0:
                self.lyrics_edit.text_edit.insertHtml(
                    f'{tag_start}<span style="color:#00ff00;">[{tag_name} 1]</span>{tag_end}')
            else:
                self.lyrics_edit.text_edit.insertHtml(
                    f'{tag_start}<span style="color:#00ff00;">[{tag_name + tag_name}]</span>{tag_end}')

                self.lyrics_edit.text_edit.setHtml(self.renumber_tags(tag_name, self.lyrics_edit.text_edit.toHtml()))
                self.lyrics_edit.text_edit.setFocus()

                cursor.setPosition(cursor_pos)
                while True:
                    cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
                    if cursor.selectedText() == ']':
                        break
                    cursor.clearSelection()

                cursor.clearSelection()
                cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.MoveAnchor)
                self.lyrics_edit.text_edit.setTextCursor(cursor)

        self.populate_tag_list()
        self.lyrics_edit.text_edit.verticalScrollBar().setSliderPosition(slider_pos)
        self.lyrics_edit.text_edit.setFocus()

    def renumber_tags(self, tag_name, html):
        """
        Searches the html of a QTextEdit for a given song tag and renumbers all similar tags
        :param str tag_name: Verse, Chorus, Pre-Chorus, Bridge, Tag, Ending, or all
        :param str html: The html from QTextEdit.toHtml()
        :return str: The modified html
        """
        if tag_name == 'all':
            tag_names = [
                'Verse',
                'Chorus',
                'Pre-Chorus',
                'Bridge',
                'Tag',
                'Ending'
            ]

            for tag_name in tag_names:
                occurrences = re.findall('\[' + tag_name + '.*?\]', html)
                if len(occurrences) > 1:
                    for i in range(len(occurrences)):
                        html = html.replace(occurrences[i], f'<<{tag_name} {i + 1}>>', 1)
                    html = html.replace('<<', '[').replace('>>', ']')

            return html
        else:
            occurrences = re.findall('\[' + tag_name + '.*?\]', html)

            for i in range(len(occurrences)):
                html = html.replace(occurrences[i], f'<<{tag_name} {i + 1}>>', 1)
            html = html.replace('<<', '[').replace('>>', ']')

            return html

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

        if self.override_global_button.isChecked():
            override_global = 'True'
        else:
            override_global = 'False'

        if self.footer_checkbox.isChecked():
            footer = 'true'
        else:
            footer = 'false'

        if self.font_widget.font_face_combobox.currentText():
            font = self.font_widget.font_face_combobox.currentText()
        else:
            font = self.font_widget.font_face_combobox.itemText(0)

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

        use_shade = str(self.font_widget.shade_behind_text_checkbox.isChecked())
        shade_color = str(self.font_widget.shade_color_slider.color_slider.value())
        shade_opacity = str(self.font_widget.shade_opacity_slider.color_slider.value())

        if 'Global' in self.background_line_edit.text():
            if 'Song' in self.background_line_edit.text():
                background = 'global_song'
            else:
                background = 'global_bible'
        else:
            background = self.background_line_edit.text()

        lyrics = self.get_simplified_text(self.lyrics_edit.text_edit.toHtml())

        song_order = ''
        for i in range(self.song_order_list_widget.count()):
            tag = self.song_order_list_widget.item(i).text()
            tag_split = tag.split(' ')
            tag_split[0] = tag_split[0][0].lower()
            tag = ''.join(tag_split)
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
            override_global,
            use_shade,
            shade_color,
            shade_opacity
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
                if self.gui.oos_widget.oos_list_widget.item(i).data(Qt.ItemDataRole.UserRole)['title'] == self.old_title:
                    new_item = self.gui.media_widget.song_list.findItems(song_data[0], Qt.MatchFlag.MatchExactly)[
                        0].clone()
                    new_data = new_item.data(Qt.ItemDataRole.UserRole).copy()
                    new_data['parsed_text'] = parsers.parse_song_data(self.gui, new_data)
                    new_item.setData(Qt.ItemDataRole.UserRole, new_data)
                    self.gui.oos_widget.oos_list_widget.takeItem(i)
                    self.gui.media_widget.add_song_to_service(new_item, i)
                    self.gui.oos_widget.oos_list_widget.setCurrentRow(i)
                    break

        self.deleteLater()
        save_widget.widget.deleteLater()
        if self.gui.oos_widget.oos_list_widget.currentItem():
            self.gui.send_to_preview(self.gui.oos_widget.oos_list_widget.currentItem())
        if self.item_index:
            self.gui.media_widget.song_list.setCurrentIndex(self.item_index)
            self.gui.media_widget.song_list.scrollTo(self.item_index)

    def get_simplified_text(self, lyrics):
        break_tag = '<br />'

        # 'flatten' the html if this is directly from the QTextEdit's toHtml function
        if lyrics.startswith('<!'):
            lyrics.replace('\n', '')
            lyrics_split = re.split('<body.*?>', lyrics)
            lyrics = lyrics_split[1].replace('</body></html>', '').strip()

            # convert paragraphs to lines followed by break
            paragraphs = re.findall('<p.*?>.*?</p>', lyrics)
            lyrics = ''
            for i in range(len(paragraphs)):
                line = re.sub('<p.*?>', '', paragraphs[i])
                line = line.replace('</p>', '').strip()
                if i < len(paragraphs) - 1:
                    if line != '<br />':
                        lyrics += line + break_tag
                    else:
                        lyrics += line
                elif line != '<br />':
                    lyrics += line

        # make paragraph tags if none exist
        else:
            lyrics = re.sub('\n', break_tag, lyrics)
        lyrics = re.sub('<br.*?/>', break_tag, lyrics) # format old br tags

        # simplify the formatting tags for bold, italic, and underline
        style_substrings = re.findall('<span.*?</span>', lyrics)
        for substring in style_substrings:
            prefix = ''
            suffix = ''
            if 'font-weight' in substring:
                prefix += '<b>'
                suffix += '</b>'
            if 'font-style' in substring:
                prefix += '<i>'
                suffix += '</i>'
            if 'text-decoration' in substring:
                prefix += '<u>'
                suffix += '</u>'

            new_substring = prefix + re.sub('<.*?>', '', substring) + suffix
            lyrics = lyrics.replace(substring, new_substring)

        return lyrics

    def save_custom(self):
        """
        Method to save user's changes for the custom slide type editor.
        """

        if self.override_global_button.isChecked():
            override_global = 'True'
        else:
            override_global = 'False'

        if self.font_widget.font_face_combobox.currentText():
            font = self.font_widget.font_face_combobox.currentText()
        else:
            font = self.font_widget.font_face_combobox.itemText(0)

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

        use_shade = str(self.font_widget.shade_behind_text_checkbox.isChecked())
        shade_color = str(self.font_widget.shade_color_slider.color_slider.value())
        shade_opacity = str(self.font_widget.shade_opacity_slider.color_slider.value())

        if 'Global' in self.background_line_edit.text():
            if 'Song' in self.background_line_edit.text():
                background = 'global_song'
            else:
                background = 'global_bible'
        elif 'rgb(' in self.background_line_edit.text():
            background = self.background_line_edit.text()
        else:
            background = self.background_line_edit.text()

        text = self.get_simplified_text(self.lyrics_edit.text_edit.toHtml())

        audio_file = ''
        if len(self.audio_line_edit.text()) > 0:
            audio_file = self.audio_line_edit.text()
        if self.loop_audio_button.isChecked():
            loop_audio = 'True'
        else:
            loop_audio = 'False'

        if self.auto_play_checkbox.isChecked():
            auto_play = 'True'
        else:
            auto_play = 'False'
        slide_delay = str(self.auto_play_spinbox.value())

        if self.split_slides_button.isChecked():
            split_slides = 'True'
        else:
            split_slides = 'False'

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
            override_global,
            use_shade,
            shade_color,
            shade_opacity,
            audio_file,
            loop_audio,
            auto_play,
            slide_delay,
            split_slides
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
                item_data = self.gui.oos_widget.oos_list_widget.item(i).data(Qt.ItemDataRole.UserRole)
                if item_data['title'] == self.old_title:
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
        if self.item_index:
            self.gui.media_widget.custom_list.setCurrentIndex(self.item_index)
            self.gui.media_widget.custom_list.scrollTo(self.item_index)

    def change_thumbnail(self, item):
        """
        Change the thumbnail image of this song/custom slide's QListWidget ItemWidget to what has just been saved.
        :param QListWidgetItem item: The edited song/custom slide's QListWidgetItem
        :return:
        """
        if item.data(Qt.ItemDataRole.UserRole)['background'] == 'global_song':
            pixmap = self.gui.global_song_background_pixmap
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
        elif item.data(Qt.ItemDataRole.UserRole)['background'] == 'global_bible':
            pixmap = self.gui.global_bible_background_pixmap
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
        elif 'rgb(' in item.data(Qt.ItemDataRole.UserRole)['background']:
            pixmap = QPixmap(50, 27)
            painter = QPainter(pixmap)
            rgb = item.data(Qt.ItemDataRole.UserRole)['background'].replace('rgb(', '')
            rgb = rgb.replace(')', '')
            rgb_split = rgb.split(',')
            brush = QBrush(QColor.fromRgb(
                int(rgb_split[0].strip()), int(rgb_split[1].strip()), int(rgb_split[2].strip())))
            painter.setBrush(brush)
            painter.fillRect(pixmap.rect(), brush)
            painter.end()
        else:
            pixmap = QPixmap(self.gui.main.background_dir + '/' + item.data(Qt.ItemDataRole.UserRole)['background'])
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)

        item_widget = StandardItemWidget(self.gui, item.data(Qt.ItemDataRole.UserRole)['text'], '', pixmap)
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
