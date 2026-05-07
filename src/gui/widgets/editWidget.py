import json
import os.path
import re
from os.path import exists

from PyQt5.QtCore import Qt, QSize, QPoint
from PyQt5.QtGui import QColor, QPixmap, QPainter, QBrush, QIcon, QTextCursor, QFont, QTextDocument, QDrag, \
    QStandardItemModel, QStandardItem, QFontMetrics
from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QLineEdit, \
    QMessageBox, QCheckBox, QRadioButton, QButtonGroup, QColorDialog, QFileDialog, QScrollArea, QListWidget, \
    QSpinBox, QComboBox, QListWidgetItem, QTextEdit, QGroupBox, QAbstractItemView, QStyledItemDelegate, QListView, \
    QMenu, QAction

from dataHandling import parsers
from gui.widgets.formattableTextEdit import FormattableTextEdit
from gui.widgets.widgets import StandardItemWidget, PrintDialog, SimpleSplash, NewFontWidget


class EditWidget(QDialog):
    """
    Provides a QDialog containing the necessary widgets to edit a song or custom slide.
    """

    def __init__(self, gui, data: dict=None, type: str=None, from_oos: bool=False):
        """
        Provides a QDialog containing the necessary widgets.py to edit a song or custom slide.
        :param gui.GUI gui: The current instance of GUI
        :param dict data: The dictionary of data for this song/custom
        :param str type: The type of slide being edited: 'song' or 'custom'
        :param bool from_oos: Whether the slide is being edited from OOS
        """
        if not data:
            return

        super().__init__()

        self.gui = gui
        self.lyrics_edit = None
        self.old_title = None
        self.new_custom = False
        self.from_oos = from_oos
        self.new_song = False
        self.data = data
        self.type = data['type']

        self.setObjectName('edit_widget')
        self.setWindowFlag(Qt.WindowType.Window)

        if self.data['title'] == '':
            self.new_song = True
        else:
            self.old_title = self.data['title']

        self.init_components()

        self.main_widget.adjustSize()
        preferred_height = int(self.gui.primary_screen.size().height() * 4 / 5)
        self.setGeometry(50, 50, 1200, preferred_height)
        self.title_line_edit.setFocus()
        if type == 'song':
            self.populate_song_data()
        elif type == 'custom':
            self.populate_custom_data()

        self.font_widget.change_font_sample()

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

        upper_widget = QWidget()
        main_layout.addWidget(upper_widget)
        upper_layout = QHBoxLayout(upper_widget)
        upper_layout.setContentsMargins(0, 0, 0, 0)

        details_widget = QWidget()
        upper_layout.addWidget(details_widget)
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)

        title_widget = QWidget()
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 5)
        title_widget.setLayout(title_layout)
        details_layout.addWidget(title_widget)

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
            details_layout.addWidget(author_widget)

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
            details_layout.addWidget(copyright_widget)

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
            details_layout.addWidget(ccli_widget)

            ccli_label = QLabel('CCLI Song Number:')
            ccli_label.setFont(self.gui.bold_font)
            ccli_layout.addWidget(ccli_label)

            self.ccli_num_line_edit = QLineEdit()
            self.ccli_num_line_edit.setFont(self.gui.standard_font)
            ccli_layout.addWidget(self.ccli_num_line_edit)

            print_button = QPushButton('Print Lyrics')
            print_button.setFont(self.gui.standard_font)
            print_button.pressed.connect(self.print_lyrics)
            upper_layout.addWidget(print_button)

        main_layout.addSpacing(20)

        lyrics_widget = QGroupBox('Lyrics')
        lyrics_widget.setFont(self.gui.bold_font)
        if self.type == 'custom':
            lyrics_widget.setTitle('Text')
        lyrics_widget.setObjectName('lyrics_widget')
        lyrics_layout = QGridLayout(lyrics_widget)
        lyrics_layout.setSpacing(20)
        main_layout.addWidget(lyrics_widget)

        if self.type == 'song':
            lyrics_header_widget = QWidget()
            lyrics_layout.addWidget(lyrics_header_widget, 0, 0)
            lyrics_header_layout = QGridLayout(lyrics_header_widget)
            lyrics_header_layout.setContentsMargins(0, 0, 0, 0)

            lyrics_label = QLabel('Edit all lyrics')
            lyrics_label.setFont(self.gui.standard_font)
            lyrics_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            lyrics_header_layout.addWidget(lyrics_label, 0, 0, Qt.AlignmentFlag.AlignLeft)

            lyrics_toggle = QPushButton()
            lyrics_toggle.setObjectName('lyrics_toggle')
            lyrics_toggle.setCheckable(True)
            lyrics_toggle.setFont(self.gui.standard_font)
            lyrics_toggle.released.connect(self.toggle_lyrics)
            lyrics_header_layout.addWidget(lyrics_toggle, 1, 0, Qt.AlignmentFlag.AlignLeft)

            add_lyrics_label = QLabel('Add lyrics')
            add_lyrics_label.setFont(self.gui.standard_font)
            add_lyrics_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            lyrics_header_layout.addWidget(add_lyrics_label, 0, 1, Qt.AlignmentFlag.AlignRight)

            add_lyrics_button = QPushButton()
            add_lyrics_button.setIcon(QIcon('resources/gui_icons/add_icon.svg'))
            add_lyrics_button.setToolTip('Add a block of lyrics')
            add_lyrics_button.clicked.connect(self.add_lyrics_block)
            lyrics_header_layout.addWidget(add_lyrics_button, 1, 1, Qt.AlignmentFlag.AlignRight)

            help_label = QLabel('Hint: Double click a lyric block to edit it')
            help_label.setObjectName('help_label')
            help_label.setFont(self.gui.standard_font)
            lyrics_header_layout.addWidget(help_label, 2, 0)

        if self.type == 'song':
            lyrics_layout.setRowStretch(0, 1)
            lyrics_layout.setRowStretch(1, 20)
            lyrics_layout.setColumnStretch(0, 10)
            lyrics_layout.setColumnStretch(1, 1)
            lyrics_layout.setColumnStretch(2, 1)
            lyrics_layout.setColumnStretch(3, 5)
        else:
            lyrics_layout.setColumnStretch(0, 10)
            lyrics_layout.setColumnStretch(1, 5)

        self.lyrics_list_widget = LyricListWidget(self.gui)
        self.lyrics_list_widget.setObjectName('lyrics_list_widget')
        self.lyrics_list_widget.setFont(self.gui.standard_font)
        self.lyrics_list_widget.setMinimumSize(220, 400)
        self.lyrics_list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.lyrics_list_widget.verticalScrollBar().setSingleStep(15)
        self.lyrics_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lyrics_list_widget.setSpacing(5)
        model = QStandardItemModel()
        self.lyrics_list_widget.setModel(model)
        self.lyrics_list_widget.selectionModel().currentChanged.connect(self.update_preview_widget)
        self.lyrics_list_widget.setItemDelegate(LyricDelegate(self.lyrics_list_widget, self.gui))
        self.lyrics_list_widget.setDragEnabled(True)
        self.lyrics_list_widget.setAcceptDrops(True)
        self.lyrics_list_widget.setDragDropOverwriteMode(False)

        self.lyrics_text_edit = FormattableTextEdit(self.gui)
        self.lyrics_text_edit.setObjectName('lyrics_text_edit')
        self.lyrics_text_edit.setFont(self.gui.standard_font)
        self.lyrics_text_edit.hide()

        if self.type == 'song':
            lyrics_layout.addWidget(self.lyrics_list_widget, 1, 0, 4, 1)
            lyrics_layout.addWidget(self.lyrics_text_edit, 1, 0, 4, 1)
        else:
            help_label = QLabel('Hint: Add a blank line between paragraphs when choosing "Split Slides"')
            help_label.setObjectName('help_label')
            help_label.setFont(self.gui.standard_font)
            lyrics_layout.addWidget(help_label, 0, 0)
            lyrics_layout.addWidget(self.lyrics_text_edit, 1, 0)
            self.lyrics_list_widget.hide()
            self.lyrics_text_edit.show()

        if self.type == 'song':
            self.song_order_header_widget = QWidget()
            lyrics_layout.addWidget(self.song_order_header_widget, 0, 1)
            song_order_header_layout = QVBoxLayout(self.song_order_header_widget)
            song_order_header_layout.setContentsMargins(0, 0, 0, 0)

            song_order_label = QLabel('Song Order')
            song_order_label.setFont(self.gui.standard_font)
            song_order_header_layout.addWidget(song_order_label)

            help_label = QLabel('Hint: Drag lyrics here to set the song order.\nPress "Delete" to remove an item.')
            help_label.setObjectName('help_label')
            help_label.setFont(self.gui.standard_font)
            song_order_header_layout.addWidget(help_label)

            self.song_order_list_widget = SongOrderListWidget()
            self.song_order_list_widget.setObjectName('song_order_list_widget')
            self.song_order_list_widget.setDragEnabled(True)
            self.song_order_list_widget.setAcceptDrops(True)
            self.song_order_list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
            self.song_order_list_widget.setMinimumWidth(120)
            self.song_order_list_widget.setToolTip('Press "Delete" to remove an item from the song order list')
            self.song_order_list_widget.setFont(self.gui.standard_font)
            lyrics_layout.addWidget(self.song_order_list_widget, 1, 1, 2, 1)

            self.song_order_help_label = QLabel('Toggle "Edit all lyrics"\nto edit the song order')
            self.song_order_help_label.setObjectName('help_label')
            self.song_order_help_label.setFont(self.gui.standard_font)
            self.song_order_help_label.hide()
            lyrics_layout.addWidget(self.song_order_help_label, 1, 1)

            self.tool_bar = QWidget()
            self.tool_bar.hide()
            toolbar_layout = QHBoxLayout()
            self.tool_bar.setLayout(toolbar_layout)
            main_layout.addWidget(self.tool_bar)
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

        self.preview_label_one = QLabel()
        self.preview_label_two = QLabel()
        if self.type == 'song':
            lyrics_layout.addWidget(self.preview_label_one, 0, 3, 2, 1)
            lyrics_layout.addWidget(self.preview_label_two, 2, 3, 1, 1)
        else:
            lyrics_layout.addWidget(self.preview_label_one, 0, 1)
            lyrics_layout.addWidget(self.preview_label_two, 1, 1)

        if self.type == 'custom':
            audio_widget = QWidget()
            audio_layout = QHBoxLayout(audio_widget)
            main_layout.addWidget(audio_widget)

            self.add_audio_button = QPushButton()
            self.add_audio_button.setObjectName('add_audio_button')
            self.add_audio_button.setCheckable(True)
            self.add_audio_button.setToolTip('Add audio that will play when this slide is shown')
            self.add_audio_button.setIcon(QIcon('resources/gui_icons/audio.svg'))
            self.add_audio_button.setIconSize(button_size)
            self.add_audio_button.setChecked(False)
            self.add_audio_button.released.connect(self.add_audio_changed)
            audio_layout.addWidget(self.add_audio_button)

            add_audio_label = QLabel('Add Audio')
            add_audio_label.setFont(self.gui.bold_font)
            audio_layout.addWidget(add_audio_label)
            audio_layout.addSpacing(20)

            self.audio_combobox = QComboBox()
            self.audio_combobox.setFont(self.gui.standard_font)
            audio_layout.addWidget(self.audio_combobox)
            audio_layout.addSpacing(20)
            results = self.gui.main.get_audio_clip_names()
            self.audio_combobox.addItem('Choose an Audio File')
            for result in results:
                self.audio_combobox.addItem(result[0])

            self.choose_file_button = QPushButton()
            self.choose_file_button.setObjectName('choose_file_button')
            self.choose_file_button.setIcon(QIcon('resources/gui_icons/open.svg'))
            self.choose_file_button.setIconSize(QSize(24, 24))
            self.choose_file_button.setFont(self.gui.standard_font)
            self.choose_file_button.setToolTip('Import an audio file')
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
            #self.audio_line_edit.hide()
            self.audio_combobox.hide()
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

        self.font_widget = NewFontWidget(self.gui, self.type, draw_border=False, applies_to_global=False, edit_widget=self)
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

        background_bible_default_radio_button = QRadioButton('Use Global Bible Background')
        background_bible_default_radio_button.setFont(self.gui.standard_font)

        background_color_radio_button = QRadioButton('Solid Color')
        background_color_radio_button.setFont(self.gui.standard_font)
        background_color_radio_button.clicked.connect(self.color_chooser)

        from gui.widgets.widgets import ImageCombobox
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
        background_layout.addStretch()

        button_widget = QWidget()
        button_widget.setObjectName('button_widget')
        button_layout = QHBoxLayout()
        button_widget.setLayout(button_layout)

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
        layout.addWidget(button_widget)

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
        else:
            self.background_button_group.button(1).setChecked(True)

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

    def toggle_lyrics(self):
        if self.sender().isChecked():
            lyrics_html = ''
            for i in range(self.lyrics_list_widget.model().rowCount()):
                index = self.lyrics_list_widget.model().index(i, 0)
                data = index.data(Qt.ItemDataRole.UserRole)
                lyrics_html += f'{data[0]}<br />{data[1]}<br />'
            lyrics_html = lyrics_html[:-6]
            self.data['text'] = lyrics_html
            self.data['parsed_text'] = parsers.parse_song_data(self.gui, self.data)
            self.update_song_data()
            self.populate_song_data()
            self.lyrics_list_widget.hide()
            self.lyrics_text_edit.show()
            self.song_order_help_label.show()
            self.song_order_header_widget.hide()
            self.song_order_list_widget.hide()
            self.preview_label_one.hide()
            self.preview_label_two.hide()
            self.tool_bar.show()
        else:
            self.data['text'] = self.get_simplified_text(self.lyrics_text_edit.text_edit.toHtml())
            self.data['parsed_text'] = parsers.parse_song_data(self.gui, self.data)
            self.update_song_data()
            self.populate_song_data()
            self.lyrics_text_edit.hide()
            self.tool_bar.hide()
            self.song_order_help_label.hide()
            self.song_order_header_widget.show()
            self.lyrics_list_widget.show()
            self.song_order_list_widget.show()
            self.preview_label_one.show()
            self.preview_label_two.show()

    def background_combobox_change(self):
        self.background_button_group.button(3).setChecked(True)
        self.font_widget.font_sample.repaint()

    def update_preview_widget(self):
        """
        Method to change what is being displayed in the preview widget.
        """
        display_widget = self.gui.sample_widget
        lyric_widget = self.gui.sample_lyric_widget

        # set the background
        display_widget.background_label.clear()
        display_widget.setStyleSheet('#display_widget { background-color: none } ')

        if not self.data['override_global'] or self.data['override_global'] == 'False':
            if self.data['type'] == 'song':
                display_widget.background_label.setPixmap(self.gui.global_song_background_pixmap)
            else:
                display_widget.background_label.setPixmap(self.gui.global_bible_background_pixmap)
        elif self.data['background'] == 'global_song':
            display_widget.background_label.setPixmap(self.gui.global_song_background_pixmap)
        elif self.data['background'] == 'global_bible':
            display_widget.background_label.setPixmap(self.gui.global_bible_background_pixmap)
        elif 'rgb(' in self.data['background']:
            display_widget.setStyleSheet(
                '#display_widget { background-color: ' + self.data['background'] + '}')
        elif exists(self.gui.main.background_dir + '/' + self.data['background']):
            custom_pixmap = QPixmap(self.gui.main.background_dir + '/' + self.data['background'])
            display_widget.background_label.setPixmap(custom_pixmap)
        else:
            display_widget.background_label.setPixmap(self.gui.global_song_background_pixmap)

        # set the lyrics html
        lyrics_html = None
        self.lyrics_list_widget.currentIndex()
        if self.lyrics_list_widget.currentIndex() is not None:
            index = self.lyrics_list_widget.currentIndex()
            data = index.data(Qt.ItemDataRole.UserRole)
            lyrics_html = self.get_simplified_text(data[1])

        if not lyrics_html:
            return

        # set the font
        if 'override_global' in self.data.keys() and self.data['override_global'] == 'True':
            font_face = self.data['font_family']
            font_size = int(self.data['font_size'])
            font_color = self.data['font_color']

            if 'global' in str(self.data['use_shadow']):
                use_shadow = self.gui.main.settings['song_use_global']
            else:
                use_shadow = self.data['use_shadow']

            if 'global' in str(self.data['shadow_color']):
                shadow_color = self.gui.main.settings['song_shadow_color']
            else:
                shadow_color = self.data['shadow_color']

            if 'global' in str(self.data['shadow_offset']):
                shadow_offset = self.gui.main.settings['song_shadow_offset']
            else:
                shadow_offset = self.data['shadow_offset']

            if 'global' in str(self.data['use_outline']):
                use_outline = self.gui.min.settings['song_use_outline']
            else:
                use_outline = self.data['use_outline']

            if 'global' in str(self.data['outline_color']):
                outline_color = self.gui.main.settings['song_outline_color']
            else:
                outline_color = self.data['outline_color']

            if 'global' in str(self.data['outline_width']):
                outline_width = self.gui.main.settings['song_outline_width']
            else:
                outline_width = self.data['outline_width']

            if 'global' in str(self.data['use_shade']):
                use_shade = self.gui.main.settings['song_use_shade']
            else:
                use_shade = self.data['use_shade']

            if 'global' in str(self.data['shade_color']):
                shade_color = self.gui.main.settings['song_shade_color']
            else:
                shade_color = self.data['shade_color']

            if 'global' in str(self.data['shade_opacity']):
                shade_opacity = self.gui.main.settings['song_shade_opacity']
            else:
                shade_opacity = self.data['shade_opacity']
        else:
            if self.data['type'] == 'custom':
                font_face = self.gui.main.settings['bible_font_face']
                font_size = self.gui.main.settings['bible_font_size']
                font_color = self.gui.main.settings['bible_font_color']
                use_shadow = self.gui.main.settings['bible_use_shadow']
                shadow_color = self.gui.main.settings['bible_shadow_color']
                shadow_offset = self.gui.main.settings['bible_shadow_offset']
                use_outline = self.gui.main.settings['bible_use_outline']
                outline_color = self.gui.main.settings['bible_outline_color']
                outline_width = self.gui.main.settings['bible_outline_width']
                use_shade = self.gui.main.settings['bible_use_shade']
                shade_color = self.gui.main.settings['bible_shade_color']
                shade_opacity = self.gui.main.settings['bible_shade_opacity']
            else:
                font_face = self.gui.main.settings['song_font_face']
                font_size = self.gui.main.settings['song_font_size']
                font_color = self.gui.main.settings['song_font_color']
                use_shadow = self.gui.main.settings['song_use_shadow']
                shadow_color = self.gui.main.settings['song_shadow_color']
                shadow_offset = self.gui.main.settings['song_shadow_offset']
                use_outline = self.gui.main.settings['song_use_outline']
                outline_color = self.gui.main.settings['song_outline_color']
                outline_width = self.gui.main.settings['song_outline_width']
                use_shade = self.gui.main.settings['song_use_shade']
                shade_color = self.gui.main.settings['song_shade_color']
                shade_opacity = self.gui.main.settings['song_shade_opacity']

        lyric_widget.setFont(QFont(font_face, font_size))
        lyric_widget.footer_label.setFont(QFont(font_face, self.gui.global_footer_font_size))
        lyric_widget.use_shadow = use_shadow
        lyric_widget.shadow_color = QColor(shadow_color, shadow_color, shadow_color)
        lyric_widget.shadow_offset = shadow_offset
        lyric_widget.use_outline = use_outline
        lyric_widget.outline_color = QColor(outline_color, outline_color, outline_color)
        lyric_widget.outline_width = outline_width
        lyric_widget.use_shade = use_shade
        if not use_shade:
            shade_opacity = 0
        lyric_widget.shade_color = shade_color
        lyric_widget.shade_opacity = shade_opacity

        # set the font color
        if not font_color == 'global':
            if font_color == 'white':
                lyric_widget.fill_color = QColor(Qt.GlobalColor.white)
            elif font_color == 'black':
                lyric_widget.fill_color = QColor(Qt.GlobalColor.black)
            elif '#' in font_color:
                color = font_color.replace('#', '')
                rgb_color = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
                lyric_widget.fill_color = QColor(rgb_color)
            else:
                color = font_color.replace('rgb(', '')
                color = color.replace(')', '')
                font_color_split = color.split(', ')
                lyric_widget.fill_color = QColor(
                    int(font_color_split[0]), int(font_color_split[1]), int(font_color_split[2]))
        else:
            if self.gui.main.settings['font_color'] == 'black':
                lyric_widget.fill_color = QColor(0, 0, 0)
            elif self.gui.main.settings['font_color'] == 'white':
                lyric_widget.fill_color = QColor(255, 255, 255)
            else:
                font_color_split = self.gui.main.settings['font_color'].split(', ')
                lyric_widget.fill_color = QColor(
                    int(font_color_split[0]), int(font_color_split[1]), int(font_color_split[2]))

        lyric_widget.text = lyrics_html

        # set the footer text
        lyric_widget.footer_label.show()
        footer_text = ''
        if 'use_footer' in self.data.keys() and self.data['use_footer']:
            if len(self.data['author']) > 0:
                footer_text += self.data['author']
            if len(self.data['copyright']) > 0:
                footer_text += '\n\u00A9' + self.data['copyright'].replace('\n', ' ')
            if len(self.data['ccli_song_number']) > 0:
                footer_text += '\nCCLI Song #: ' + self.data['ccli_song_number']
            if len(self.gui.main.settings['ccli_num']) > 0:
                footer_text += '\nCCLI License #: ' + self.gui.main.settings['ccli_num']
            lyric_widget.footer_label.setText(footer_text)
        elif self.data['type'] == 'bible':
            lyric_widget.footer_label.setText(
                self.data['title']
                + ' ('
                + self.data['author']
                + ')'
            )
        else:
            lyric_widget.footer_label.setText('')
            lyric_widget.footer_label.clear()

        qss_font_color = (f'rgb({lyric_widget.fill_color.red()}, '
                          f'{lyric_widget.fill_color.green()}, '
                          f'{lyric_widget.fill_color.blue()})')
        if not font_color == 'global':
            lyric_widget.footer_label.setStyleSheet(f'color: {qss_font_color}')
        else:
            if self.gui.main.settings['font_color'] == 'black':
                lyric_widget.footer_label.setStyleSheet('color: black;')
            elif self.gui.main.settings['font_color'] == 'white':
                lyric_widget.footer_label.setStyleSheet('color: white;')
            else:
                lyric_widget.footer_label.setStyleSheet(f'color: rgb({self.gui.main.settings["font_color"]});')

        if lyric_widget.footer_label.text() == '':
            lyric_widget.footer_label.hide()

        lyrics_rect, footer_height = lyric_widget.calculate_painted_text()
        lyrics_height = lyrics_rect.height()
        target_height = display_widget.height() - footer_height - 40

        # check each segment against the lyric widget's height to see if that segment's text needs to be split in half
        if lyrics_height > target_height:
            segment_text_split = re.split('<br.*?/>', lyrics_html)
            half_lines = int(len(segment_text_split) / 2)
            if half_lines > 1:
                first_lyrics = ''
                for i in range(half_lines):
                    first_lyrics += segment_text_split[i] + '<br />'
                first_lyrics = first_lyrics[:-6]
                lyric_widget.text = first_lyrics
                preview_pixmap = display_widget.grab(display_widget.rect())
                preview_pixmap = preview_pixmap.scaledToWidth(300, Qt.TransformationMode.SmoothTransformation)
                self.preview_label_one.setPixmap(preview_pixmap)

                second_lyrics = ''
                for i in range(half_lines, len(segment_text_split)):
                    second_lyrics += segment_text_split[i] + '<br />'
                second_lyrics = second_lyrics[:-6]
                lyric_widget.text = second_lyrics
                preview_pixmap = display_widget.grab(display_widget.rect())
                preview_pixmap = preview_pixmap.scaledToWidth(300, Qt.TransformationMode.SmoothTransformation)
                self.preview_label_two.setPixmap(preview_pixmap)
            else:
                preview_pixmap = display_widget.grab(display_widget.rect())
                preview_pixmap = preview_pixmap.scaledToWidth(300, Qt.TransformationMode.SmoothTransformation)
                self.preview_label_one.setPixmap(preview_pixmap)
                self.preview_label_two.clear()
        else:
            preview_pixmap = display_widget.grab(display_widget.rect())
            preview_pixmap = preview_pixmap.scaledToWidth(300, Qt.TransformationMode.SmoothTransformation)
            self.preview_label_one.setPixmap(preview_pixmap)
            self.preview_label_two.clear()

    def add_audio_changed(self):
        #self.audio_line_edit.setVisible(self.add_audio_button.isChecked())
        self.audio_combobox.setVisible(self.add_audio_button.isChecked())
        self.choose_file_button.setVisible(self.add_audio_button.isChecked())
        self.loop_audio_button.setVisible(self.add_audio_button.isChecked())
        if self.add_audio_button.isChecked():
            self.add_audio_button.setIcon(QIcon('resources/gui_icons/audio_selected.svg'))
        else:
            self.add_audio_button.setIcon(QIcon('resources/gui_icons/audio.svg'))
            #self.audio_line_edit.clear()

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
        if len(result[0]) == 0:
            return

        file_name = result[0]
        name = file_name.split('/')[-1]
        name = '.'.join(name.split('.')[:-1])
        audio_format = file_name.split('.')[-1].upper()

        dialog = QDialog()
        dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        dialog.setWindowTitle('Audio Name')
        dialog.setWindowIcon(QIcon('resources/branding/icon.svg'))
        layout = QVBoxLayout(dialog)

        message = QLabel('Please provide a name for your audio clip:')
        message.setFont(self.gui.standard_font)
        layout.addWidget(message)

        name_line_edit = QLineEdit(name)
        message.setFont(self.gui.standard_font)
        name_line_edit.selectAll()
        layout.addWidget(name_line_edit)

        button_widget = QWidget()
        layout.addWidget(button_widget)
        button_layout = QHBoxLayout(button_widget)

        ok_button = QPushButton('Ok')
        ok_button.setFont(self.gui.standard_font)
        ok_button.pressed.connect(lambda: dialog.done(0))
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addSpacing(20)

        cancel_button = QPushButton('Cancel')
        cancel_button.setFont(self.gui.standard_font)
        cancel_button.pressed.connect(lambda: dialog.done(-1))
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()

        result = dialog.exec()
        if result == -1:
            return

        if len(name_line_edit.text().strip()) > 0:
            name = name_line_edit.text().strip()

        try:
            with open(file_name, 'rb') as file:
                audio_data = file.read()
            result = self.gui.main.save_audio(name, audio_format, audio_data)
            if result == -2:
                QMessageBox.information(
                    self,
                    'Name Exists',
                    'That audio name already exists in the database. Please try again using a different name.',
                    QMessageBox.StandardButton.Ok
                )
                return
            elif result == 0:
                self.audio_combobox.addItem(name)
                self.audio_combobox.setCurrentText(name)
        except Exception as ex:
            self.gui.main.error_log()
            return

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

    def populate_song_data(self):
        """
        Use the provided data to set the proper widgets.py to match the saved data
        :param list of str song_data: The song's QListWidgetItem data
        """
        self.lyrics_text_edit.text_edit.clear()
        self.lyrics_list_widget.model().clear()
        self.title_line_edit.setText(self.data['title'])
        self.author_line_edit.setText(self.data['author'])
        self.copyright_line_edit.setText(self.data['copyright'])
        self.ccli_num_line_edit.setText(self.data['ccli_song_number'])

        lyrics = self.get_simplified_text(self.data['text'])
        tag_list = re.findall(r'\[.*?]', lyrics, flags=re.S)
        lyrics_split = re.split(r'\[.*?]', lyrics, flags=re.S)
        lyrics_split.pop(0)

        # Tags from some previous versions don't have the space character required in order to properly parse them.
        # Convert them to the new format.
        old_tag_found = False
        for i in range(len(tag_list)):
            if ' ' not in tag_list[i]:
                old_tag_found = True
                old_tag = tag_list[i].replace('[', '').replace(']', '')
                tag_letter = old_tag[0]
                tag_number = old_tag[1]

                new_tag = 'Verse 1'
                if 'v' in tag_letter.lower():
                    new_tag = f'Verse {tag_number}'
                elif 'p' in tag_letter.lower():
                    new_tag = f'Pre-Chorus {tag_number}'
                elif 'c' in tag_letter.lower():
                    new_tag = f'Chorus {tag_number}'
                elif 'b' in tag_letter.lower():
                    new_tag = f'Bridge {tag_number}'
                elif 't' in tag_letter.lower():
                    new_tag = f'Tag {tag_number}'
                elif 'e' in tag_letter.lower():
                    new_tag = f'Ending {tag_number}'

                tag_list[i] = f'[{new_tag}]'

        if old_tag_found: # rewrite the lyrics text to conform to the proper format
            text = ''
            for i in range(len(tag_list)):
                text += f'{tag_list[i]}<br/>{lyrics_split[i]}<br/>'
            text = text[:-6]
            self.data['text'] = text

        all_lyrics = ''
        for i in range(len(tag_list)):
            if lyrics_split[i].startswith('<br />'):
                lyrics_split[i] = lyrics_split[i][6:].strip()
            if lyrics_split[i].endswith('<br />'):
                lyrics_split[i] = lyrics_split[i][:-6].strip()

            plain_tag = tag_list[i].replace('[', '').replace(']', '').strip()
            plain_lyrics = lyrics_split[i].replace('<br />', '\n').strip()
            plain_lyrics = re.sub('<.*?>', '', plain_lyrics).strip()

            all_lyrics += f'<span style="color: darkGreen;">{tag_list[i]}</span><br />'
            all_lyrics += f'{lyrics_split[i]}<br />'

            item = QStandardItem(f'{plain_tag}\n\n{plain_lyrics}')
            item.setData([tag_list[i], lyrics_split[i]], Qt.ItemDataRole.UserRole)
            self.lyrics_list_widget.model().appendRow(item)
        
        all_lyrics = all_lyrics[:-6]
        self.lyrics_text_edit.text_edit.setHtml(all_lyrics)

        order_items = self.data['verse_order'].split(' ')
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

        self.song_order_list_widget.clear()
        for i in range(len(order_items)):
            if len(order_items[i].strip()) > 0:
                item = QListWidgetItem(order_items[i])
                item.setSizeHint(QSize(0, 28))
                self.song_order_list_widget.addItem(item)

        self.font_widget.blockSignals(True)

        # set the override global checkbox
        if self.data['override_global']:
            self.override_global_button.setChecked(True)
        else:
            self.override_global_button.setChecked(False)

        # set the footer checkbox
        if self.data['use_footer']:
            self.footer_checkbox.setChecked(True)
        else:
            self.footer_checkbox.setChecked(False)

        # set the font face list widget
        if len(self.data['font_family'].strip()) == 0 or 'global' in self.data['font_family']:
            font_face = self.gui.main.settings['song_font_face']
        else:
            font_face = self.data['font_family']
        for i in range(self.font_widget.font_face_combobox.count()):
            if self.font_widget.font_face_combobox.itemText(i) == font_face:
                self.font_widget.font_face_combobox.setCurrentIndex(i)
                break

        # check the proper font color radio button
        if len(self.data['font_color']) == 0 or 'global' in self.data['font_color']:
            if self.gui.main.settings['song_font_color'] == 'black':
                self.font_widget.black_radio_button.setChecked(True)
            elif self.gui.main.settings['song_font_color'] == 'white':
                self.font_widget.white_radio_button.setChecked(True)
            else:
                self.font_widget.custom_font_color_radio_button.setChecked(True)
                self.font_widget.custom_font_color_radio_button.setObjectName(self.gui.main.settings['song_font_color'])
        elif self.data['font_color'] == '#FFFFFF':
            self.font_widget.white_radio_button.setChecked(True)
        elif self.data['font_color'] == '#000000':
            self.font_widget.black_radio_button.setChecked(True)
        else:
            self.font_widget.custom_font_color_radio_button.setChecked(True)
            self.font_widget.custom_font_color_radio_button.setObjectName(self.data['font_color'])

        # check the proper background radio button
        if len(self.data['background']) == 0 or self.data['background'] == 'global_song':
            self.background_button_group.button(0).setChecked(True)
        elif self.data['background'] == 'global_bible':
            self.background_button_group.button(1).setChecked(True)
        elif 'rgb(' in self.data['background']:
            self.background_button_group.button(2).setChecked(True)
            self.background_button_group.button(2).setObjectName(self.data['background'])
        else:
            for i in range(self.background_combobox.count()):
                if self.background_combobox.itemData(i, Qt.ItemDataRole.UserRole) == self.data['background']:
                    self.background_combobox.setCurrentIndex(i)
                    break
            self.background_button_group.button(3).setChecked(True)
            self.background_combobox.setEnabled(True)

        # set the font size spinbox's value
        if 'global' in str(self.data['font_size']):
            self.font_widget.font_size_spinbox.setValue(self.gui.main.settings['song_font_size'])
        else:
            self.font_widget.font_size_spinbox.setValue(self.data['font_size'])

        # set the shadow checkbox
        if 'global' in str(self.data['use_shadow']):
            self.font_widget.shadow_checkbox.setChecked(self.gui.main.settings['song_use_shadow'])
        elif self.data['use_shadow']:
            self.font_widget.shadow_checkbox.setChecked(True)
        else:
            self.font_widget.shadow_checkbox.setChecked(False)

        # set the shadow color slider's value
        if 'global' in str(self.data['shadow_color']):
            self.font_widget.shadow_color_slider.color_slider.setValue(self.gui.main.settings['song_shadow_color'])
        else:
            self.font_widget.shadow_color_slider.color_slider.setValue(self.data['shadow_color'])

        # set the shadow offset slider's value
        if 'global' in str(self.data['shadow_offset']):
            self.font_widget.shadow_offset_slider.offset_slider.setValue(self.gui.main.settings['song_shadow_offset'])
        else:
            self.font_widget.shadow_offset_slider.offset_slider.setValue(self.data['shadow_offset'])
        self.font_widget.shadow_offset_slider.current_label.setText(
            str(self.font_widget.shadow_offset_slider.offset_slider.value()) + 'px')

        # set the outline checkbox
        if 'global' in str(self.data['use_outline']):
            self.font_widget.outline_checkbox.setChecked(self.gui.main.settings['song_use_outline'])
        elif self.data['use_outline']:
            self.font_widget.outline_checkbox.setChecked(True)
        else:
            self.font_widget.outline_checkbox.setChecked(False)

        # set the outline color slider's value
        if 'global' in str(self.data['outline_color']):
            self.font_widget.outline_color_slider.color_slider.setValue(self.gui.main.settings['song_outline_color'])
        else:
            self.font_widget.outline_color_slider.color_slider.setValue(self.data['outline_color'])

        # set the outline width slider's value
        if 'global' in str(self.data['outline_width']):
            self.font_widget.outline_width_slider.offset_slider.setValue(self.gui.main.settings['song_outline_width'])
        else:
            self.font_widget.outline_width_slider.offset_slider.setValue(self.data['outline_width'])
        self.font_widget.outline_width_slider.current_label.setText(
            str(self.font_widget.outline_width_slider.offset_slider.value()) + 'px')

        # set the shade behind text checkbox
        if 'global' in str(self.data['use_shade']):
            self.font_widget.shade_behind_text_checkbox.setChecked(self.gui.main.settings['song_use_shade'])
        elif self.data['use_shade']:
            self.font_widget.shade_behind_text_checkbox.setChecked(True)
        else:
            self.font_widget.shade_behind_text_checkbox.setChecked(False)

        # set the shade color slider's value
        if 'global' in str(self.data['shade_color']):
            self.font_widget.shade_color_slider.color_slider.setValue(self.gui.main.settings['song_shade_color'])
        else:
            self.font_widget.shade_color_slider.color_slider.setValue(self.data['shade_color'])

        # set the shade opacity slider's value
        if 'global' in str(self.data['shade_opacity']):
            self.font_widget.shade_opacity_slider.color_slider.setValue(self.gui.main.settings['song_shade_opacity'])
        else:
            self.font_widget.shade_opacity_slider.color_slider.setValue(self.data['shade_opacity'])

        self.font_widget.blockSignals(False)

    def add_lyrics_block(self):
        model = self.lyrics_list_widget.model()
        number = 0
        for i in range(model.rowCount()):
            index = self.lyrics_list_widget.model().index(i, 0)
            data = model.data(index, Qt.ItemDataRole.UserRole)
            if 'Verse' in data[0]:
                this_number = int(data[0].split(' ')[1].replace(']', '').strip())
                number = this_number + 1
        item = QStandardItem(f'Verse {number}')
        item.setData([f'Verse {number}', ''], Qt.ItemDataRole.UserRole)
        self.lyrics_list_widget.model().appendRow(item)
        new_row = self.lyrics_list_widget.model().rowCount() - 1
        index = self.lyrics_list_widget.model().index(new_row, 0)
        self.lyrics_list_widget.edit(index)
        self.lyrics_list_widget.scrollTo(index, QListView.ScrollHint.EnsureVisible)

    def create_lyric_item_widget(self, tag=None, text=None):
        if not tag or not text:
            tag = 'Verse 1'
            text = ''

        text = text.strip()
        if text.startswith('<br />'):
            text = text[6:]
        if text.endswith('<br />'):
            text = text[:-6]

        tag = tag.replace('[', '').replace(']', '').strip()
        tag_split = tag.split(' ')
        if len(tag_split) > 1:
            tag_num = int(tag_split[-1])
        else:
            tag_num = 1

        widget = QWidget()
        widget.setObjectName('song_item_widget')
        widget.setAutoFillBackground(False)
        layout = QVBoxLayout(widget)
        layout.setSpacing(0)

        type_widget = QWidget()
        layout.addWidget(type_widget)
        type_layout = QHBoxLayout(type_widget)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.setSpacing(5)

        type_combobox = QComboBox()
        type_combobox.setObjectName('type_combobox')
        type_combobox.setFont(self.gui.standard_font)
        type_combobox.setToolTip('Lyric type')
        type_combobox.setMinimumWidth(200)
        type_combobox.setMinimumHeight(36)
        types = [
            'Verse',
            'Pre-Chorus',
            'Chorus',
            'Bridge',
            'Tag',
            'Ending'
        ]
        type_combobox.addItems(types)
        type_layout.addWidget(type_combobox)

        number_spinbox = QSpinBox()
        number_spinbox.setObjectName('number_spinbox')
        number_spinbox.setFont(self.gui.standard_font)
        number_spinbox.setToolTip('Number (i.e. Verse 1, Verse 2, ...')
        number_spinbox.setMinimumWidth(50)
        number_spinbox.setMinimumHeight(36)
        number_spinbox.setMinimum(1)
        number_spinbox.setMaximum(10)
        number_spinbox.setValue(tag_num)
        type_layout.addWidget(number_spinbox)
        type_layout.addStretch()

        delete_button = QPushButton()
        delete_button.setIcon(QIcon('resources/gui_icons/x_icon.svg'))
        delete_button.setToolTip('Delete this lyric section')
        delete_button.pressed.connect(self.delete_item)
        type_layout.addWidget(delete_button)

        edit_widget = FormattableTextEdit(self.gui)
        edit_widget.setObjectName('edit_widget')
        edit_widget.text_edit.setMaximumHeight(100)
        edit_widget.text_edit.textChanged.connect(self.update_preview_widget)
        edit_widget.text_edit.setHtml(text)
        layout.addWidget(edit_widget)

        if 'v' in tag.lower():
            type_combobox.setCurrentIndex(types.index('Verse'))
        elif 'p' in tag.lower():
            type_combobox.setCurrentIndex(types.index('Pre-Chorus'))
        elif 'c' in tag.lower():
            type_combobox.setCurrentIndex(types.index('Chorus'))
        elif 'b' in tag.lower():
            type_combobox.setCurrentIndex(types.index('Bridge'))
        elif 't' in tag.lower():
            type_combobox.setCurrentIndex(types.index('Tag'))
        elif 'e' in tag.lower():
            type_combobox.setCurrentIndex(types.index('Ending'))

        return widget

    def delete_item(self):
        button = self.sender()
        if not button:
            return
        point = button.mapTo(self.lyrics_list_widget.viewport(), button.rect().topLeft())
        item = self.lyrics_list_widget.itemAt(point)
        self.lyrics_list_widget.takeItem(self.lyrics_list_widget.row(item))

    def populate_custom_data(self):
        """
        Use the provided data to set the proper widgets.py to match the saved data
        :param list of str custom_data: The custom slide's QListWidgetItem data
        """
        self.old_title = self.data['title']
        self.title_line_edit.setText(self.data['title'])
        self.lyrics_text_edit.text_edit.setHtml(self.get_simplified_text(self.data['text']))
        self.font_widget.blockSignals(True)

        # set the override global checkbox
        if self.data['override_global']:
            self.override_global_button.setChecked(True)
        else:
            self.override_global_button.setChecked(False)
        self.override_global_changed()

        # set the font face list widget
        if 'global' in self.data['font_family']:
            font_face = self.gui.main.settings['bible_font_face']
        else:
            font_face = self.data['font_family']
            for i in range(self.font_widget.font_face_combobox.count()):
                if self.font_widget.font_face_combobox.itemText(i) == font_face:
                    self.font_widget.font_face_combobox.setCurrentIndex(i)
                    break

        # check the proper font color radio button
        if 'global' in self.data['font_color']:
            if self.gui.main.settings['bible_font_color'] == 'black':
                self.font_widget.black_radio_button.setChecked(True)
            elif self.gui.main.settings['bible_font_color'] == 'white':
                self.font_widget.white_radio_button.setChecked(True)
            else:
                self.font_widget.custom_font_color_radio_button.setChecked(True)
                self.font_widget.custom_font_color_radio_button.setObjectName(
                    self.gui.main.settings['bible_font_color'])
        elif self.data['font_color'] == '#FFFFFF':
            self.font_widget.white_radio_button.setChecked(True)
        elif self.data['font_color'] == '#000000':
            self.font_widget.black_radio_button.setChecked(True)
        else:
            self.font_widget.custom_font_color_radio_button.setChecked(True)
            self.font_widget.custom_font_color_radio_button.setObjectName(self.data['font_color'])

        # check the proper background radio button
        if 'song' in self.data['background'].lower():
            self.background_button_group.button(0).setChecked(True)
        elif 'bible' in self.data['background'].lower():
            self.background_button_group.button(1).setChecked(True)
        elif 'rgb(' in self.data['background'].lower():
            self.background_button_group.button(2).setChecked(True)
            self.background_button_group.button(2).setObjectName(self.data['background'].lower())
        else:
            for i in range(self.background_combobox.count()):
                if self.background_combobox.itemData(i, Qt.ItemDataRole.UserRole) == self.data['background']:
                    self.background_combobox.setCurrentIndex(i)
                    break
            self.background_button_group.button(3).setChecked(True)
            self.background_combobox.setEnabled(True)

        # set the font size spinbox's value
        if 'global' in str(self.data['font_size']).lower():
            self.font_widget.font_size_spinbox.setValue(self.gui.main.settings['bible_font_size'])
        else:
            self.font_widget.font_size_spinbox.setValue(self.data['font_size'])

        # set the use shadow checkbox
        if 'global' in str(self.data['use_shadow']).lower():
            self.font_widget.shadow_checkbox.setChecked(self.gui.main.settings['bible_use_shadow'])
        elif self.data['use_shadow']:
            self.font_widget.shadow_checkbox.setChecked(True)
        else:
            self.font_widget.shadow_checkbox.setChecked(False)

        # set the shadow color slider's value
        if 'global' in str(self.data['shadow_color']):
            self.font_widget.shadow_color_slider.color_slider.setValue(self.gui.main.settings['bible_shadow_color'])
        else:
            self.font_widget.shadow_color_slider.color_slider.setValue(self.data['shadow_color'])

        # set the shadow offset slider's value
        if 'global' in str(self.data['shadow_offset']).lower():
            self.font_widget.shadow_offset_slider.offset_slider.setValue(self.gui.main.settings['bible_shadow_offset'])
        else:
            self.font_widget.shadow_offset_slider.offset_slider.setValue(self.data['shadow_offset'])
        self.font_widget.shadow_offset_slider.current_label.setText(
            str(self.font_widget.shadow_offset_slider.offset_slider.value()) + 'px')

        # set the outline checkbox
        if 'global' in str(self.data['use_outline']).lower():
            self.font_widget.outline_checkbox.setChecked(self.gui.main.settings['bible_use_outline'])
        elif self.data['use_outline']:
            self.font_widget.outline_checkbox.setChecked(True)
        else:
            self.font_widget.outline_checkbox.setChecked(False)

        # set the outline color slider value
        if 'global' in str(self.data['outline_color']).lower():
            self.font_widget.outline_color_slider.color_slider.setValue(self.gui.main.settings['bible_outline_color'])
        else:
            self.font_widget.outline_color_slider.color_slider.setValue(self.data['outline_color'])

        # set the outline width slider's value
        if 'global' in str(self.data['outline_width']).lower():
            self.font_widget.outline_width_slider.offset_slider.setValue(self.gui.main.settings['bible_outline_width'])
        else:
            self.font_widget.outline_width_slider.offset_slider.setValue(self.data['outline_width'])
        self.font_widget.outline_width_slider.current_label.setText(
            str(self.font_widget.outline_width_slider.offset_slider.value()) + 'px')

        # set the shade behind text checkbox
        if 'global' in str(self.data['use_shade']).lower():
            self.font_widget.shade_behind_text_checkbox.setChecked(self.gui.main.settings['bible_use_shade'])
        elif self.data['use_shade']:
            self.font_widget.shade_behind_text_checkbox.setChecked(True)
        else:
            self.font_widget.shade_behind_text_checkbox.setChecked(False)

        # set the shade color slider's value
        if 'global' in str(self.data['shade_color']).lower():
            self.font_widget.shade_color_slider.color_slider.setValue(self.gui.main.settings['bible_shade_color'])
        else:
            self.font_widget.shade_color_slider.color_slider.setValue(self.data['shade_color'])

        # set the shade opacity slider's value
        if 'global' in str(self.data['shade_opacity']).lower():
            self.font_widget.shade_opacity_slider.color_slider.setValue(self.gui.main.settings['bible_shade_opacity'])
        else:
            self.font_widget.shade_opacity_slider.color_slider.setValue(self.data['shade_opacity'])

        # set the audio file
        if len(self.data['audio_file'].strip()) > 0:
            self.add_audio_button.setChecked(True)
            self.audio_combobox.setCurrentText(self.data['audio_file'])
        self.add_audio_changed()
        if self.data['loop_audio']:
            self.loop_audio_button.setChecked(True)
        else:
            self.loop_audio_button.setChecked(False)

        # set auto-play
        if self.data['auto_play']:
            self.auto_play_checkbox.setChecked(True)
        else:
            self.auto_play_checkbox.setChecked(False)
        if self.data['slide_delay']:
            self.auto_play_spinbox.setValue(self.data['slide_delay'])

        if self.data['split_slides']:
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
            self.background_button_group.button(2).setObjectName(color_string)
            sender.setChecked(True)

    def image_chooser(self):
        """
        Method to provide a file dialog for the user to import a new image.
        """
        file = QFileDialog.getOpenFileName(self, 'Choose Image File', self.gui.main.background_dir)
        if len(file[0]) > 0:
            file_split = file[0].split('/')
            file_name = file_split[len(file_split) - 1]
            self.gui.main.copy_image(file[0])
        self.background_image_radio_button.setChecked(True)

    def add_tag(self):
        """
        Method to add tags to the song lyrics based on button push.
        :param str type: The tag type to be inserted
        :return:
        """

        slider_pos = self.lyrics_text_edit.text_edit.verticalScrollBar().sliderPosition()

        if self.sender().text() == 'os':
            self.lyrics_text_edit.text_edit.insertPlainText('\n#optional split#')

        else:
            # search first for previous instances of this tag; append numbers to the tag for multiple instances
            tag_name = self.sender().text()
            lyrics_text = self.lyrics_text_edit.text_edit.toHtml()
            occurrences = re.findall(r'\[' + tag_name + '.*?]', lyrics_text)

            # determine if breaks are needed before or after the tag
            tag_start = '<br />'
            tag_end = '<br />'
            cursor = self.lyrics_text_edit.text_edit.textCursor()
            cursor_pos = cursor.position()
            cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter, QTextCursor.MoveMode.KeepAnchor)
            if cursor.selection().toPlainText() == '\n' or cursor.position() == 0:
                tag_start = ''
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.MoveAnchor)
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
            if cursor.selection().toPlainText() == '\n':
                tag_end = ''

            if len(occurrences) == 0:
                self.lyrics_text_edit.text_edit.insertHtml(
                    f'{tag_start}<span style="color:darkGreen;">[{tag_name} 1]</span>{tag_end}')
            else:
                self.lyrics_text_edit.text_edit.insertHtml(
                    f'{tag_start}<span style="color:darkGreen;">[{tag_name + tag_name}]</span>{tag_end}')

                self.lyrics_text_edit.text_edit.setHtml(self.renumber_tags(tag_name, self.lyrics_text_edit.text_edit.toHtml()))
                self.lyrics_text_edit.text_edit.setFocus()

                cursor.setPosition(cursor_pos)
                while True:
                    cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
                    if cursor.selectedText() == ']':
                        break
                    cursor.clearSelection()

                cursor.clearSelection()
                cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.MoveAnchor)
                self.lyrics_text_edit.text_edit.setTextCursor(cursor)

        self.lyrics_text_edit.text_edit.verticalScrollBar().setSliderPosition(slider_pos)
        self.lyrics_text_edit.text_edit.setFocus()

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
                occurrences = re.findall(r'\[' + tag_name + '.*?]', html)
                if len(occurrences) > 1:
                    for i in range(len(occurrences)):
                        html = html.replace(occurrences[i], f'<<{tag_name} {i + 1}>>', 1)
                    html = html.replace('<<', '[').replace('>>', ']')

            return html
        else:
            occurrences = re.findall(r'\[' + tag_name + r'.*?]', html)

            for i in range(len(occurrences)):
                html = html.replace(occurrences[i], f'<<{tag_name} {i + 1}>>', 1)
            html = html.replace('<<', '[').replace('>>', ']')

            return html

    def populate_tag_list(self):
        """
        Method to find tags in the song's lyrics and add those tags to the "segements" QListWidget
        """
        self.song_section_list_widget.clear()

        tags = []
        for i in range(self.lyrics_list_widget.count()):
            widget = self.lyrics_list_widget.itemWidget(self.lyrics_list_widget.item(i))
            tag_name = widget.findChild(QComboBox, 'type_combobox').currentText()
            tag_number = str(widget.findChild(QSpinBox, 'number_spinbox').value())
            tags.append(tag_name + ' ' + tag_number)

        for tag in tags:
            self.song_section_list_widget.addItem(tag)

        return
        lyrics_text = self.lyrics_text_edit.text_edit.toPlainText()
        tag_list = re.findall(r'[.*?]', lyrics_text)
        for tag in tag_list:
            self.song_section_list_widget.addItem(tag.replace('[', '').replace(']', ''))

    def print_lyrics(self):
        lyrics = self.get_simplified_text(self.lyrics_text_edit.text_edit.toHtml())

        song_order = []
        for i in range(self.song_order_list_widget.count()):
            tag = self.song_order_list_widget.item(i).text()
            song_order.append(tag)

        lyric_tags = re.findall(r'\[.*?]', lyrics)
        song_segments = re.split(r'\[.*?]', lyrics)
        song_segments.pop(0)

        song_dict = {}
        for i in range(len(lyric_tags)):
            song_dict[lyric_tags[i].replace('[', '').replace(']', '')] = song_segments[i]

        document = QTextDocument()
        document_html = (f'<span style="font-family: \'Arial\'; font-size: 16pt; font-weight: bold;">'
                         f'{self.title_line_edit.text()}</span><br /><br />')
        for tag in song_order:
            document_html += (f'<span style="font-family: \'Arial\'; font-size: 12pt; font-weight: bold;">'
                              f'{tag}</span><br />')
            document_html += (f'<span style="font-family: \'Arial\'; font-size: 12pt;">'
                              f'{song_dict[tag]}</span><br /><br />')
        document.setHtml(document_html)

        PrintDialog(document)

    def update_song_data(self):
        if self.override_global_button.isChecked():
            self.data['override_global'] = True
        else:
            self.data['override_global'] = False

        if self.footer_checkbox.isChecked():
            self.data['use_footer'] = True
        else:
            self.data['use_footer'] = False

        if self.font_widget.font_face_combobox.currentText():
            self.data['font_family'] = self.font_widget.font_face_combobox.currentText()
        else:
            self.data['font_family'] = self.font_widget.font_face_combobox.itemText(0)

        if self.font_widget.font_color_button_group.checkedButton():
            self.data['font_color'] = self.font_widget.font_color_button_group.checkedButton().objectName()
        else:
            self.data['font_color'] = 'white'

        self.data['title'] = self.title_line_edit.text().strip()
        self.data['author'] = self.author_line_edit.text().strip()
        self.data['copyright'] = self.copyright_line_edit.text().strip()
        self.data['ccli_song_number'] = self.ccli_num_line_edit.text().strip()

        self.data['font_size'] = self.font_widget.font_size_spinbox.value()

        self.data['use_shadow'] = self.font_widget.shadow_checkbox.isChecked()
        self.data['shadow_color'] = self.font_widget.shadow_color_slider.color_slider.value()
        self.data['shadow_offset'] = self.font_widget.shadow_offset_slider.offset_slider.value()

        self.data['use_outline'] = self.font_widget.outline_checkbox.isChecked()
        self.data['outline_color'] = self.font_widget.outline_color_slider.color_slider.value()
        self.data['outline_width'] = self.font_widget.outline_width_slider.offset_slider.value()

        self.data['use_shade'] = self.font_widget.shade_behind_text_checkbox.isChecked()
        self.data['shade_color'] = self.font_widget.shade_color_slider.color_slider.value()
        self.data['shade_opacity'] = self.font_widget.shade_opacity_slider.color_slider.value()

        background_button_text = self.background_button_group.checkedButton().text()
        if 'global song' in background_button_text.lower():
            self.data['background'] = 'global_song'
        elif 'global bible' in background_button_text.lower():
            self.data['background'] = 'global_bible'
        elif 'solid color' in background_button_text.lower():
            self.data['background'] = self.background_button_group.button(2).objectName()
        else:
            self.data['background'] = self.background_combobox.currentData(Qt.ItemDataRole.UserRole)

        if self.lyrics_list_widget.isVisible():
            lyrics_html = ''
            for i in range(self.lyrics_list_widget.model().rowCount()):
                index = self.lyrics_list_widget.model().index(i, 0)
                data = index.data(Qt.ItemDataRole.UserRole)
                lyrics_html += f'{data[0]}<br />{data[1]}<br />'
            lyrics_html = lyrics_html[:-6]
            self.data['text'] = lyrics_html

        verse_order = ''
        for i in range(self.song_order_list_widget.count()):
            tag = self.song_order_list_widget.item(i).text()
            tag_split = tag.split(' ')
            tag_split[0] = tag_split[0][0].lower()
            tag = ''.join(tag_split)
            verse_order += tag + ' '
        self.data['verse_order'] = verse_order.strip()

        self.data['text'] = self.get_simplified_text(self.lyrics_text_edit.text_edit.toHtml())
        self.data['parsed_text'] = parsers.parse_song_data(self.gui, self.data)
        self.populate_song_data()

    def update_custom_data(self):
        if self.override_global_button.isChecked():
            self.data['override_global'] = True
        else:
            self.data['override_global'] = False

        if self.font_widget.font_face_combobox.currentText():
            self.data['font_family'] = self.font_widget.font_face_combobox.currentText()
        else:
            self.data['font_family'] = self.font_widget.font_face_combobox.itemText(0)

        if self.font_widget.font_color_button_group.checkedButton():
            self.data['font_color'] = self.font_widget.font_color_button_group.checkedButton().objectName()
        else:
            self.data['font_color'] = 'white'

        self.data['font_size'] = self.font_widget.font_size_spinbox.value()

        self.data['use_shadow'] = self.font_widget.shadow_checkbox.isChecked()
        self.data['shadow_color'] = self.font_widget.shadow_color_slider.color_slider.value()
        self.data['shadow_offset'] = self.font_widget.shadow_offset_slider.offset_slider.value()

        self.data['use_outline'] = self.font_widget.outline_checkbox.isChecked()
        self.data['outline_color'] = self.font_widget.outline_color_slider.color_slider.value()
        self.data['outline_width'] = self.font_widget.outline_width_slider.offset_slider.value()

        self.data['use_shade'] = self.font_widget.shade_behind_text_checkbox.isChecked()
        self.data['shade_color'] = self.font_widget.shade_color_slider.color_slider.value()
        self.data['shade_opacity'] = self.font_widget.shade_opacity_slider.color_slider.value()

        background_button_text = self.background_button_group.checkedButton().text()
        if 'song' in background_button_text.lower():
            self.data['background'] = 'global_song'
        elif 'bible' in background_button_text.lower():
            self.data['background'] = 'global_bible'
        elif 'color' in background_button_text.lower():
            self.data['background'] = self.background_button_group.button(2).objectName()
        else:
            self.data['background'] = self.background_combobox.currentData(Qt.ItemDataRole.UserRole)

        self.data['text'] = self.get_simplified_text(self.lyrics_text_edit.text_edit.toHtml())

        audio_file = ''
        if self.add_audio_button.isChecked() and not self.audio_combobox.currentText() == 'Choose an Audio File':
            self.data['audio_file'] = self.audio_combobox.currentText()
        if self.loop_audio_button.isChecked():
            self.data['loop_audio'] = True
        else:
            self.data['loop_audio'] = False

        if self.auto_play_checkbox.isChecked():
            self.data['auto_play'] = True
        else:
            self.data['auto_play'] = False
        self.data['slide_delay'] = self.auto_play_spinbox.value()

        if self.split_slides_button.isChecked():
            self.data['split_slides'] = True
        else:
            self.data['split_slides'] = False

    def save_song(self):
        """
        Method to save user's changes for the song type editor.
        """

        self.update_song_data()
        # title is essential for the database, prompt user for title if not inputted
        if len(self.title_line_edit.text()) == 0:
            QMessageBox.information(
                self,
                'No Title',
                'Title field is empty. Please enter a title before saving.',
                QMessageBox.StandardButton.Ok
            )
            return

        self.update_song_data()
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
                    self.data['title'] = line_edit.text()
                else:
                    return

        save_widget = SimpleSplash(self.gui, 'Saving...', parent=self)

        self.gui.main.save_song(self.data, self.old_title)
        self.gui.media_widget.populate_song_list()

        if self.from_oos:
            for i in range(self.gui.oos_widget.oos_list_widget.count()):
                oos_title = self.gui.oos_widget.oos_list_widget.item(i).data(Qt.ItemDataRole.UserRole)['title']
                if oos_title == self.data['title']:
                    item = self.gui.media_widget.song_list.findItems(self.data['title'], Qt.MatchFlag.MatchExactly)[0]
                    item_data = item.data(Qt.ItemDataRole.UserRole).copy()
                    item_data['parsed_text'] = parsers.parse_song_data(self.gui, item_data)
                    self.gui.oos_widget.oos_list_widget.item(i).setData(Qt.ItemDataRole.UserRole, item_data)
                    self.gui.oos_widget.oos_list_widget.setCurrentRow(i)
                    self.gui.send_to_preview(self.gui.oos_widget.oos_list_widget.item(i))
                    break
        else:
            items = self.gui.media_widget.song_list.findItems(self.data['title'], Qt.MatchFlag.MatchExactly)
            if len(items) > 0:
                self.gui.media_widget.song_list.setCurrentItem(items[0])

        self.deleteLater()
        save_widget.widget.deleteLater()

    def save_custom(self):
        """
        Method to save user's changes for the custom slide type editor.
        """

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
                    self.data['title'] = line_edit.text()
                else:
                    return

        self.save_widget = SimpleSplash(self.gui, 'Saving...')

        self.update_custom_data()
        self.gui.main.save_custom(self.data, self.old_title)
        self.gui.media_widget.populate_custom_list()

        if self.from_oos:
            for i in range(self.gui.oos_widget.oos_list_widget.count()):
                if self.gui.oos_widget.oos_list_widget.item(i).data(
                        Qt.ItemDataRole.UserRole)['title'] == self.data['title']:
                    item = self.gui.media_widget.custom_list.findItems(self.data['title'], Qt.MatchFlag.MatchExactly)[0]
                    item_data = item.data(Qt.ItemDataRole.UserRole).copy()
                    self.gui.oos_widget.oos_list_widget.item(i).setData(Qt.ItemDataRole.UserRole, item_data)
                    self.gui.oos_widget.oos_list_widget.setCurrentRow(i)
                    self.gui.send_to_preview(self.gui.oos_widget.oos_list_widget.item(i))
                    break
        else:
            items = self.gui.media_widget.custom_list.findItems(self.data['title'], Qt.MatchFlag.MatchExactly)
            self.gui.media_widget.custom_list.setCurrentItem(items[0])

        self.done(0)
        self.save_widget.widget.deleteLater()

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

        item_widget = StandardItemWidget(self.gui, item.data(Qt.ItemDataRole.UserRole)['title'], '', pixmap)
        item.setSizeHint(item_widget.sizeHint())
        self.gui.oos_widget.oos_list_widget.setItemWidget(item, item_widget)


class LyricsTextEdit(QTextEdit):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui

        self.cursorPositionChanged.connect(self.check_for_tag)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

    def check_for_tag(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.MoveAnchor)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
        text = cursor.selectedText()
        if '[' in text and ']' in text:
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.MoveAnchor)
            cursor.movePosition(QTextCursor.MoveOperation.Right)
            self.setTextCursor(cursor)

    def context_menu(self):
        """
        Method to create a QMenu to be used as a custom context menu.
        """
        self.click_pos = self.mapFromGlobal(self.cursor().pos())

        cursor = self.cursorForPosition(self.click_pos)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.MoveAnchor)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
        text = cursor.selectedText()

        if '[' in text and ']' in text:
                menu = QMenu()
                if self.gui.main.settings['theme'] == 'dark':
                    menu.setStyleSheet(
                        'QMenu {'
                            'background: #000000;'
                            'color: #e0e0e0;'
                        '}'
                        'QMenu::item {'
                            'background: #000000;'
                            'color: #e0e0e0;'
                        '}'
                        'QMenu::item:hover {'
                            'background: #555588;'
                        '}'
                        'QMenu::item:selected {'
                            'background: #444466;'
                        '}'
                        'QMenu::item:pressed {'
                            'background: #444466;'
                        '}'
                    )
                else:
                    menu.setStyleSheet(
                        'QMenu {'
                            'background: #f0f0f0;'
                            'color: #000000;'
                        '}'
                        'QMenu::item {'
                            'background: #f0f0f0;'
                            'color: #000000;'
                        '}'
                        'QMenuBar::item:hover {'
                            'background: #aaaaff;'
                        '}'
                        'QMenu::item:selected {'
                            'background: #aaaaff;'
                        '}'
                        'QMenu::item:pressed {'
                            'background: #aaaaff;'
                        '}'
                    )

                remove_tag_action = QAction('Remove Tag')
                remove_tag_action.triggered.connect(lambda: self.remove_tag(cursor))
                menu.addAction(remove_tag_action)

                menu.exec(self.mapToGlobal(self.click_pos))

    def remove_tag(self, cursor):
        cursor.removeSelectedText()


class SongOrderListWidget(QListWidget):
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

    def dropEvent(self, evt):
        if evt.source().objectName() == 'lyrics_list_widget':
            list_view = evt.source()
            index = list_view.currentIndex()
            data = index.data(Qt.ItemDataRole.UserRole)
            lyric_type = data[0].split(' ')[0].replace('[', '')
            number = data[0].split(' ')[1].replace(']', '')
            item = QListWidgetItem(f'{lyric_type} {number}')
            item.setSizeHint(QSize(0, 28))
            row = self.row(self.itemAt(evt.pos()))
            if row == -1:
                self.addItem(item)
            else:
                self.insertItem(row, item)
            self.update()
        elif evt.source() == self:
            super().dropEvent(evt)


class LyricListWidget(QListView):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.moving_data = None

    def dropEvent(self, evt):
        if evt.source() != self:
            super().dropEvent(evt)

        if self.moving_data is not None:
            data, source_row = self.moving_data
            model = self.model()
            index_at_drop = self.indexAt(evt.pos())
            drop_indicator = self.dropIndicatorPosition()

            if index_at_drop.isValid():
                target_row = index_at_drop.row()

                if drop_indicator in (QAbstractItemView.DropIndicatorPosition.BelowItem,
                                      QAbstractItemView.DropIndicatorPosition.OnItem):
                    insert_row = target_row + 1
                else:
                    insert_row = target_row
            else:
                insert_row = model.rowCount()

            model.removeRow(source_row)
            if source_row < insert_row:
                insert_row -= 1

            plain_tag = data[0].replace('[', '').replace(']', '').strip()
            plain_lyrics = data[1].replace('<br />', '\n').strip()
            plain_lyrics = re.sub('<.*?>', '', plain_lyrics).strip()

            item = QStandardItem(f'{plain_tag}\n\n{plain_lyrics}')
            item.setData(data, Qt.ItemDataRole.UserRole)
            model.insertRow(insert_row, item)
            
            self.setCurrentIndex(model.index(insert_row, 0))
            evt.acceptProposedAction()
            self.moving_data = None

    def startDrag(self, supportedActions):
        drag = QDrag(self)
        mime_data = self.model().mimeData(self.selectedIndexes())
        drag.setMimeData(mime_data)

        data = self.currentIndex().data(Qt.ItemDataRole.UserRole)
        self.moving_data = data, self.currentIndex().row()

        lyric_type = data[0].replace('[', '').replace(']', '')
        font_metrics = QFontMetrics(self.gui.standard_font)
        text_size = font_metrics.size(Qt.TextFlag.TextSingleLine, lyric_type)

        pixmap = QPixmap(text_size.width() + 10, text_size.height() + 10)
        pixmap.fill(QColor(0, 0, 0, 50))
        painter = QPainter(pixmap)
        painter.setFont(self.gui.standard_font)
        painter.setPen(Qt.GlobalColor.white)
        painter.drawText(5, pixmap.height() - 5, lyric_type)
        painter.end()

        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(5, 5))

        result = drag.exec(supportedActions)


class LyricDelegate(QStyledItemDelegate):
    def __init__(self, parent, gui):
        super().__init__(parent)
        self.gui = gui
        self.type_combobox = QComboBox()
        self.number_spinbox = QSpinBox()
        self.lyrics_text_edit = FormattableTextEdit(self.gui)
        self.editing_index = None

    def createEditor(self, parent, option, index):
        # Triggered when the user double-clicks an item
        self.editing_index = index
        
        if self.parent() and hasattr(self.parent(), 'viewport'):
            self.parent().scheduleDelayedItemsLayout()

        editor = self.make_editor(parent, index)
        editor.setGeometry(option.rect)
        return editor

    def setEditorData(self, editor, index):
        # Pull data from the model and put it into the widgets
        # We assume the data is stored as a list or dict in UserRole
        data = index.data(Qt.ItemDataRole.UserRole)
        type = data[0].replace('[', '').replace(']', '')
        number = type.split(' ')[1]
        type = type.split(' ')[0]

        self.type_combobox.setCurrentIndex(self.type_combobox.findText(type))
        self.number_spinbox.setValue(int(number))
        self.lyrics_text_edit.text_edit.setHtml(data[1])

    def setModelData(self, editor, model, index):
        # Take the text from widgets and save it back to the model
        type = f'[{self.type_combobox.currentText()} {self.number_spinbox.value()}]'
        lyrics = self.gui.edit_widget.get_simplified_text(self.lyrics_text_edit.text_edit.toHtml())
        data = [
            type,
            lyrics
        ]
        model.setData(index, data, Qt.ItemDataRole.UserRole)
        
        # Also update the display text
        if lyrics.startswith('<br />'):
            lyrics = lyrics[6:]
        if lyrics.endswith('<br />'):
            lyrics = lyrics[:-6]
        lyrics = lyrics.replace('<br />', '\n')
        lyrics = re.sub('<.*?>', '', lyrics)

        model.setData(
            index,
            f'{type.replace('[', '').replace(']', '')}\n\n{lyrics}',
            Qt.ItemDataRole.DisplayRole
        )

        # then update the data and lyrics text edit to match the changes
        lyrics_html = ''
        for i in range(model.rowCount()):
            index = model.index(i, 0)
            data = index.data(Qt.ItemDataRole.UserRole)
            lyrics_html += f'{data[0]}<br />{data[1]}<br />'
        lyrics_html = lyrics_html[:-6]
        self.gui.edit_widget.data['text'] = lyrics_html
        self.gui.edit_widget.data['parsed_text'] = parsers.parse_song_data(self.gui, self.gui.edit_widget.data)
        self.gui.edit_widget.lyrics_text_edit.text_edit.setHtml(
            self.gui.edit_widget.get_simplified_text(lyrics_html))

    def destroyEditor(self, editor, index):
        # Reset the editing index when done
        self.editing_index = None

        # Refresh layout again to shrink the row back down
        if self.parent() and hasattr(self.parent(), 'viewport'):
            self.parent().scheduleDelayedItemsLayout()

        super().destroyEditor(editor, index)

    def sizeHint(self, option, index):
        data = index.data(Qt.ItemDataRole.UserRole)
        label = QLabel(f'{data[0].replace('[', '').replace(']', '')}\n\n{data[1].replace('<br />', '\n')}')
        label.setFont(self.gui.standard_font)
        label.adjustSize()

        if index == self.editing_index:
            return QSize(label.width(), label.height() + 150)

        return label.sizeHint()

    def make_editor(self, parent=None, index=None):
        widget = QWidget(parent)
        widget.setObjectName('editor_widget')
        widget.setAutoFillBackground(True)
        layout = QVBoxLayout(widget)

        type_widget = QWidget()
        layout.addWidget(type_widget)
        type_layout = QHBoxLayout(type_widget)
        type_layout.setContentsMargins(0, 0, 0, 0)

        types = [
            'Verse',
            'Pre-Chorus',
            'Chorus',
            'Bridge',
            'Tag',
            'Ending'
        ]
        self.type_combobox = QComboBox()
        self.type_combobox.setFont(self.gui.standard_font)
        self.type_combobox.addItems(types)
        self.type_combobox.setMinimumHeight(36)
        type_layout.addWidget(self.type_combobox)

        self.number_spinbox = QSpinBox()
        self.number_spinbox.setFont(self.gui.standard_font)
        self.number_spinbox.setRange(1, 10)
        self.number_spinbox.setMinimumHeight(36)
        type_layout.addWidget(self.number_spinbox)
        type_layout.addStretch()

        self.lyrics_text_edit = FormattableTextEdit(self.gui)
        layout.addWidget(self.lyrics_text_edit)

        button_widget = QWidget()
        layout.addWidget(button_widget)
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(0)

        save_button = QPushButton('Save')
        save_button.pressed.connect(lambda: self.commit_and_close(widget))
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addSpacing(20)

        cancel_button = QPushButton('Cancel')
        cancel_button.pressed.connect(lambda: self.close_without_save(widget))
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()

        delete_button = QPushButton('X')
        delete_button.setToolTip('Delete this block of lyrics')
        delete_button.pressed.connect(lambda: self.delete_hint(index, widget))
        button_layout.addWidget(delete_button)

        return widget

    def commit_and_close(self, editor):
        # This triggers setModelData and then closes the editor widget
        self.commitData.emit(editor)
        self.closeEditor.emit(editor, QStyledItemDelegate.EndEditHint.NoHint)

    def close_without_save(self, editor):
        # Just closes the editor widget without calling setModelData
        self.closeEditor.emit(editor, QStyledItemDelegate.EndEditHint.NoHint)

    def delete_hint(self, index, editor):
        index.model().removeRow(index.row(), index.parent())
        self.closeEditor.emit(editor, QStyledItemDelegate.EndEditHint.NoHint)
