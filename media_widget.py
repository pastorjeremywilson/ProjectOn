import os
import shutil
import sqlite3
import threading
from os.path import exists
from xml.etree import ElementTree

from PyQt5.QtCore import Qt, QSize, QPoint
from PyQt5.QtGui import QCursor, QPixmap, QIcon, QFont, QPainter, QBrush, QColor, QPen
from PyQt5.QtWidgets import QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, \
    QListWidgetItem, QMenu, QComboBox, QTextEdit, QAbstractItemView, QDialog, QFileDialog, QMessageBox, QAction
from unicodedata import numeric

import declarations
import parsers
from edit_widget import EditWidget
from get_scripture import GetScripture
from widgets import AutoSelectLineEdit, StandardItemWidget, SimpleSplash


class MediaWidget(QTabWidget):
    """
    Creates a custom QTabWidget to hold the various types of media that can be displayed.
    """
    song_data = None
    passages = None

    def __init__(self, gui):
        """
        Creates a custom QTabWidget to hold the various types of media that can be displayed.
        :param gui.GUI gui: The current instance of GUI
        """
        super().__init__()
        self.gui = gui
        self.setFont(self.gui.standard_font)
        self.setObjectName('media_widget')
        self.setTabShape(QTabWidget.TabShape.Rounded)
        self.song_list_items = []

        self.formatted_reference = None
        self.scripture_text_edited = False

        self.init_components()

    def init_components(self):
        """
        Calls for the creation of all media tabs contained in this widget.
        """
        self.setObjectName('media_widget')

        self.gui.main.update_status_signal.emit('Loading Songs', 'info')
        self.addTab(self.make_song_tab(), 'Songs')
        self.gui.main.update_status_signal.emit('Loading Bible', 'info')
        self.addTab(self.make_scripture_tab(), 'Bible')
        self.gui.main.update_status_signal.emit('Loading Custom Slides', 'info')
        self.addTab(self.make_custom_tab(), 'Custom Slides')
        self.gui.main.update_status_signal.emit('Loading Images', 'info')
        self.addTab(self.make_image_tab(), 'Images')
        self.gui.main.update_status_signal.emit('Loading Videos', 'info')
        self.addTab(self.make_video_tab(), 'Videos')
        self.gui.main.update_status_signal.emit('Loading Web Slides', 'info')
        self.addTab(self.make_web_tab(), 'Web Slides')

    def make_song_tab(self):
        """
        Creates the song widget to be used in the song tab of this widget.
        :return QWidget: The song widget
        """
        song_widget = QWidget()
        song_widget.setObjectName('tab_widget')
        song_widget.setAutoFillBackground(True)
        song_layout = QVBoxLayout()
        song_widget.setLayout(song_layout)

        add_button = QPushButton()
        add_button.setIcon(QIcon('resources/gui_icons/add_icon.svg'))
        add_button.setToolTip('Add a New Song')
        add_button.setIconSize(QSize(20, 20))
        add_button.setFixedSize(30, 30)
        add_button.clicked.connect(lambda: self.add_song('song'))
        song_layout.addWidget(add_button)

        search_widget = QWidget()
        search_layout = QHBoxLayout()
        search_widget.setLayout(search_layout)
        song_layout.addWidget(search_widget)

        search_label = QLabel('Search:')
        search_label.setFont(self.gui.standard_font)
        search_layout.addWidget(search_label)

        self.search_line_edit = AutoSelectLineEdit()
        self.search_line_edit.setFont(self.gui.standard_font)
        self.search_line_edit.textChanged.connect(self.song_search)
        search_layout.addWidget(self.search_line_edit)

        clear_search_button = QPushButton()
        clear_search_button.setIcon(QIcon('resources/gui_icons/x_icon.svg'))
        clear_search_button.setToolTip('Clear Song Search')
        clear_search_button.setIconSize(QSize(20, 20))
        clear_search_button.setFixedSize(30, 30)
        clear_search_button.clicked.connect(self.search_line_edit.clear)
        search_layout.addWidget(clear_search_button)

        button_widget = QWidget()
        button_widget.setLayout(QHBoxLayout())
        song_layout.addWidget(button_widget)

        add_to_service_button = QPushButton()
        add_to_service_button.setIcon(QIcon('resources/gui_icons/add_to_service_icon.svg'))
        add_to_service_button.setToolTip('Add Song to Service')
        add_to_service_button.setIconSize(QSize(20, 20))
        add_to_service_button.setFixedSize(30, 30)
        add_to_service_button.clicked.connect(self.add_song_to_service)
        button_widget.layout().addWidget(add_to_service_button)
        button_widget.layout().addStretch()

        send_to_live_button = QPushButton()
        send_to_live_button.setIcon(QIcon('resources/gui_icons/send_to_live_icon.svg'))
        send_to_live_button.setToolTip('Send Song to Live')
        send_to_live_button.setIconSize(QSize(20, 20))
        send_to_live_button.setFixedSize(30, 30)
        send_to_live_button.clicked.connect(self.send_to_live)
        button_widget.layout().addWidget(send_to_live_button)

        self.song_list = CustomListWidget(self.gui, 'song')
        self.song_list.setDragEnabled(True)
        self.song_list.setFont(self.gui.standard_font)
        self.populate_song_list()
        song_layout.addWidget(self.song_list)

        return song_widget

    def make_scripture_tab(self):
        """
        Creates the scripture widget to be used in the scripture tab of this widget.
        :return QWidget: The scripture widget
        """
        scripture_widget = QWidget()
        scripture_widget.setObjectName('tab_widget')
        scripture_widget.setAutoFillBackground(True)
        scripture_layout = QVBoxLayout()
        scripture_layout.setSpacing(0)
        scripture_layout.setContentsMargins(10, 0, 10, 10)
        scripture_widget.setLayout(scripture_layout)

        bible_selector_widget = QWidget()
        bible_selector_layout = QHBoxLayout()
        bible_selector_widget.setLayout(bible_selector_layout)
        scripture_layout.addWidget(bible_selector_widget)

        bible_selector_label = QLabel('Choose Bible:')
        bible_selector_label.setFont(self.gui.standard_font)
        bible_selector_layout.addWidget(bible_selector_label)

        self.bible_selector_combobox = QComboBox()
        self.bible_selector_combobox.setFont(self.gui.standard_font)
        bibles = self.get_bibles()

        if len(bibles[0]) > 0:
            for bible in bibles:
                self.bible_selector_combobox.addItem(bible[1])
                self.bible_selector_combobox.setItemData(
                    self.bible_selector_combobox.count() - 1, bible[0], Qt.ItemDataRole.UserRole)
            default_bible_exists = False
            if 'default_bible' in self.gui.main.settings.keys():
                if exists(self.gui.main.settings['default_bible']):
                    tree = ElementTree.parse(self.gui.main.settings['default_bible'])
                    root = tree.getroot()
                    name = root.attrib['biblename']
                    self.bible_selector_combobox.setCurrentText(name)
                    default_bible_exists = True
            if not default_bible_exists:
                self.gui.main.settings['default_bible'] = bibles[0][0]
                self.bible_selector_combobox.setCurrentIndex(0)
                self.gui.main.save_settings()
                tree = ElementTree.parse(self.gui.main.settings['default_bible'])
                root = tree.getroot()
                name = root.attrib['biblename']

        self.bible_selector_combobox.currentIndexChanged.connect(self.change_bible)
        bible_selector_layout.addWidget(self.bible_selector_combobox)

        default_bible_button = QPushButton('Set As Default')
        default_bible_button.setFont(self.gui.standard_font)
        default_bible_button.clicked.connect(self.set_default_bible)
        bible_selector_layout.addWidget(default_bible_button)
        bible_selector_layout.addStretch()

        bible_search_widget = QWidget()
        bible_search_layout = QHBoxLayout()
        bible_search_layout.setContentsMargins(10, 0, 10, 0)
        bible_search_widget.setLayout(bible_search_layout)
        scripture_layout.addWidget(bible_search_widget)

        bible_search_label = QLabel('Enter Passage:')
        bible_search_label.setFont(self.gui.standard_font)
        bible_search_layout.addWidget(bible_search_label)

        self.bible_search_line_edit = AutoSelectLineEdit()
        self.bible_search_line_edit.setFont(self.gui.standard_font)
        self.bible_search_line_edit.textEdited.connect(self.get_scripture)
        self.bible_search_line_edit.textChanged.connect(self.get_scripture)
        bible_search_layout.addWidget(self.bible_search_line_edit)

        clear_search_button = QPushButton()
        clear_search_button.setIcon(QIcon('resources/gui_icons/x_icon.svg'))
        clear_search_button.setToolTip('Clear Passage Search')
        clear_search_button.setIconSize(QSize(20, 20))
        clear_search_button.setFixedSize(30, 30)
        clear_search_button.clicked.connect(self.bible_search_line_edit.clear)
        bible_search_layout.addWidget(clear_search_button)

        self.bible_search_status_label = QLabel()
        self.bible_search_status_label.setFont(QFont('Helvetica', 8))
        fm = bible_search_label.fontMetrics()
        scripture_layout.addWidget(self.bible_search_status_label)

        button_widget = QWidget()
        button_layout = QHBoxLayout()
        button_widget.setLayout(button_layout)
        scripture_layout.addWidget(button_widget)

        self.add_to_service_button = QPushButton()
        self.add_to_service_button.setIcon(QIcon('resources/gui_icons/add_to_service_icon.svg'))
        self.add_to_service_button.setToolTip('Add this Passage to the Service')
        self.add_to_service_button.setIconSize(QSize(20, 20))
        self.add_to_service_button.setFixedSize(30, 30)
        self.add_to_service_button.clicked.connect(self.add_scripture_to_service)
        button_layout.addWidget(self.add_to_service_button)
        button_layout.addStretch()

        self.send_to_live_button = QPushButton()
        self.send_to_live_button.setIcon(QIcon('resources/gui_icons/send_to_live_icon.svg'))
        self.send_to_live_button.setToolTip('Send to Live')
        self.send_to_live_button.setIconSize(QSize(20, 20))
        self.send_to_live_button.setFixedSize(30, 30)
        self.send_to_live_button.clicked.connect(self.send_scripture_to_live)
        button_layout.addWidget(self.send_to_live_button)

        self.scripture_text_edit = QTextEdit()
        self.scripture_text_edit.setFont(self.gui.standard_font)
        self.scripture_text_edit.textChanged.connect(self.text_edited)
        scripture_layout.addWidget(self.scripture_text_edit)

        return scripture_widget

    def make_custom_tab(self):
        """
        Creates the custom slide widget to be used in the custom slide tab of this widget.
        :return QWidget: The custom slide widget
        """
        custom_widget = QWidget()
        custom_widget.setObjectName('tab_widget')
        custom_widget.setAutoFillBackground(True)
        custom_layout = QVBoxLayout()
        custom_widget.setLayout(custom_layout)

        add_custom_button = QPushButton()
        add_custom_button.setIcon(QIcon('resources/gui_icons/add_icon.svg'))
        add_custom_button.setToolTip('Create a New Custom Slide')
        add_custom_button.setIconSize(QSize(20, 20))
        add_custom_button.setFixedSize(30, 30)
        add_custom_button.clicked.connect(lambda: self.add_song('custom'))
        custom_layout.addWidget(add_custom_button)

        button_widget = QWidget()
        button_widget.setLayout(QHBoxLayout())
        custom_layout.addWidget(button_widget)

        add_to_service_button = QPushButton()
        add_to_service_button.setIcon(QIcon('resources/gui_icons/add_to_service_icon.svg'))
        add_to_service_button.setToolTip('Add Custom Slide to Service')
        add_to_service_button.setIconSize(QSize(20, 20))
        add_to_service_button.setFixedSize(30, 30)
        add_to_service_button.clicked.connect(self.add_custom_to_service)
        button_widget.layout().addWidget(add_to_service_button)
        button_widget.layout().addStretch()

        send_to_live_button = QPushButton()
        send_to_live_button.setIcon(QIcon('resources/gui_icons/send_to_live_icon.svg'))
        send_to_live_button.setToolTip('Send Custom Slide to Live')
        send_to_live_button.setIconSize(QSize(20, 20))
        send_to_live_button.setFixedSize(30, 30)
        send_to_live_button.clicked.connect(self.send_to_live)
        button_widget.layout().addWidget(send_to_live_button)

        self.custom_list = CustomListWidget(self.gui, 'custom')
        self.custom_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.custom_list.setDragEnabled(True)
        self.custom_list.setFont(self.gui.standard_font)
        self.populate_custom_list()
        custom_layout.addWidget(self.custom_list)

        return custom_widget

    def make_image_tab(self):
        """
        Creates the image widget to be used in the image tab of this widget.
        :return QWidget: The image widget
        """
        image_widget = QWidget()
        image_widget.setObjectName('tab_widget')
        image_widget.setAutoFillBackground(True)
        image_layout = QVBoxLayout()
        image_widget.setLayout(image_layout)

        add_image_button = QPushButton()
        add_image_button.setIcon(QIcon('resources/gui_icons/add_icon.svg'))
        add_image_button.setToolTip('Import an Image')
        add_image_button.setIconSize(QSize(20, 20))
        add_image_button.setFixedSize(30, 30)
        add_image_button.clicked.connect(self.add_image)
        image_layout.addWidget(add_image_button)

        button_widget = QWidget()
        button_widget.setLayout(QHBoxLayout())
        image_layout.addWidget(button_widget)

        add_to_service_button = QPushButton()
        add_to_service_button.setIcon(QIcon('resources/gui_icons/add_to_service_icon.svg'))
        add_to_service_button.setToolTip('Add Image to Service')
        add_to_service_button.setIconSize(QSize(20, 20))
        add_to_service_button.setFixedSize(30, 30)
        add_to_service_button.clicked.connect(self.add_image_to_service)
        button_widget.layout().addWidget(add_to_service_button)
        button_widget.layout().addStretch()

        send_to_live_button = QPushButton()
        send_to_live_button.setIcon(QIcon('resources/gui_icons/send_to_live_icon.svg'))
        send_to_live_button.setToolTip('Send Image to Live')
        send_to_live_button.setIconSize(QSize(20, 20))
        send_to_live_button.setFixedSize(30, 30)
        send_to_live_button.clicked.connect(self.send_to_live)
        button_widget.layout().addWidget(send_to_live_button)

        self.image_list = CustomListWidget(self.gui, 'image')
        self.image_list.setFont(self.gui.standard_font)
        self.image_list.setDragEnabled(True)
        self.image_list.doubleClicked.connect(self.add_image_to_service)
        image_layout.addWidget(self.image_list)

        self.populate_image_list()

        return image_widget

    def make_video_tab(self):
        """
        Creates the video widget to be used in the video tab of this widget.
        :return QWidget: The video widget
        """
        video_widget = QWidget()
        video_widget.setObjectName('tab_widget')
        video_widget.setAutoFillBackground(True)
        video_layout = QVBoxLayout()
        video_widget.setLayout(video_layout)

        add_video_button = QPushButton()
        add_video_button.setIcon(QIcon('resources/gui_icons/add_icon.svg'))
        add_video_button.setToolTip('Import a Video')
        add_video_button.setIconSize(QSize(20, 20))
        add_video_button.setFixedSize(30, 30)
        add_video_button.clicked.connect(self.add_video)
        video_layout.addWidget(add_video_button)

        button_widget = QWidget()
        button_widget.setLayout(QHBoxLayout())
        video_layout.addWidget(button_widget)

        add_to_service_button = QPushButton()
        add_to_service_button.setIcon(QIcon('resources/gui_icons/add_to_service_icon.svg'))
        add_to_service_button.setToolTip('Add Video to Service')
        add_to_service_button.setIconSize(QSize(20, 20))
        add_to_service_button.setFixedSize(30, 30)
        add_to_service_button.clicked.connect(self.add_video_to_service)
        button_widget.layout().addWidget(add_to_service_button)
        button_widget.layout().addStretch()

        send_to_live_button = QPushButton()
        send_to_live_button.setIcon(QIcon('resources/gui_icons/send_to_live_icon.svg'))
        send_to_live_button.setToolTip('Send Video to Live')
        send_to_live_button.setIconSize(QSize(20, 20))
        send_to_live_button.setFixedSize(30, 30)
        send_to_live_button.clicked.connect(self.send_to_live)
        button_widget.layout().addWidget(send_to_live_button)

        self.video_list = CustomListWidget(self.gui, 'video')
        self.video_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.video_list.setDragEnabled(True)
        self.video_list.setFont(self.gui.standard_font)
        self.populate_video_list()
        video_layout.addWidget(self.video_list)

        return video_widget

    def make_web_tab(self):
        """
        Creates the web widget to be used in the web tab of this widget.
        :return QWidget: The web widget
        """
        web_widget = QWidget()
        web_widget.setObjectName('tab_widget')
        web_widget.setAutoFillBackground(True)
        web_layout = QVBoxLayout()
        web_widget.setLayout(web_layout)

        add_web_button = QPushButton()
        add_web_button.setIcon(QIcon('resources/gui_icons/add_icon.svg'))
        add_web_button.setToolTip('Create a New Web Slide')
        add_web_button.setIconSize(QSize(20, 20))
        add_web_button.setFixedSize(30, 30)
        add_web_button.clicked.connect(self.add_web)
        web_layout.addWidget(add_web_button)

        button_widget = QWidget()
        button_widget.setLayout(QHBoxLayout())
        web_layout.addWidget(button_widget)

        add_to_service_button = QPushButton()
        add_to_service_button.setIcon(QIcon('resources/gui_icons/add_to_service_icon.svg'))
        add_to_service_button.setToolTip('Add Web Page to Service')
        add_to_service_button.setIconSize(QSize(20, 20))
        add_to_service_button.setFixedSize(30, 30)
        add_to_service_button.clicked.connect(self.add_web_to_service)
        button_widget.layout().addWidget(add_to_service_button)
        button_widget.layout().addStretch()

        send_to_live_button = QPushButton()
        send_to_live_button.setIcon(QIcon('resources/gui_icons/send_to_live_icon.svg'))
        send_to_live_button.setToolTip('Send Video to Live')
        send_to_live_button.setIconSize(QSize(20, 20))
        send_to_live_button.setFixedSize(30, 30)
        send_to_live_button.clicked.connect(self.send_to_live)
        button_widget.layout().addWidget(send_to_live_button)

        self.web_list = CustomListWidget(self.gui, 'web')
        self.web_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.web_list.setDragEnabled(True)
        self.web_list.setFont(self.gui.standard_font)
        self.populate_web_list()
        web_layout.addWidget(self.web_list)

        return web_widget

    def song_search(self):
        """
        Method that retrieves the current text in the song widget's search_line_edit and shows/hides songs that do or
        don't contain the text.
        """
        self.song_list.clear()
        search_string = self.search_line_edit.text().strip().lower()
        if len(search_string) == 0:
            for item in self.song_list_items:
                self.song_list.addItem(item.clone())
            return

        show_list_items = []
        show_list_indices = []
        for i in range(len(self.song_list_items)):
            if search_string in self.song_list_items[i].data(Qt.ItemDataRole.UserRole)['title'].strip().lower():
                show_list_items.append(self.song_list_items[i].clone())
                show_list_indices.append(i)

        for i in range(len(self.song_list_items)):
            if search_string in self.song_list_items[i].data(Qt.ItemDataRole.UserRole)['text'].strip().lower() and i not in show_list_indices:
                show_list_items.append(self.song_list_items[i].clone())
                show_list_indices.append(i)

        for item in show_list_items:
            self.song_list.addItem(item)

    def populate_song_list(self):
        """
        Method that uses the data contained in the song table of the database to fill the song widget's QListWidget
        with all of the songs.
        """
        self.song_list.clear()
        self.song_list_items = []
        songs = self.gui.main.get_all_songs()
        if len(songs) > 0:
            for item in songs:
                if self.gui.main.initial_startup:
                    self.gui.main.update_status_signal.emit('Loading Songs - ' + item[0], 'info')

                slide_data = declarations.SLIDE_DATA_DEFAULTS.copy()
                for i in range(len(item)):
                    slide_data['type'] = 'song'
                    slide_data[declarations.SQL_COLUMN_TO_DICTIONARY_SONG[i]] = item[i]

                list_item = QListWidgetItem(slide_data['title'])
                list_item.setData(Qt.ItemDataRole.UserRole, slide_data)

                self.song_list_items.append(list_item)
                self.song_list.addItem(list_item.clone())

    def populate_custom_list(self):
        """
        Method that uses the data contained in the custom slide table of the database to create QListWidgetItems in the
        custom slide widget's QListWidget.
        """
        self.custom_list.clear()
        slides = self.gui.main.get_all_custom_slides()
        if len(slides) > 0:
            for item in slides:
                slide_data = declarations.SLIDE_DATA_DEFAULTS.copy()
                slide_data['type'] = 'custom'
                slide_data['use_footer'] = False
                for i in range(len(item)):
                    slide_data[declarations.SQL_COLUMN_TO_DICTIONARY_CUSTOM[i]] = item[i]

                widget_item = QListWidgetItem(slide_data['title'])
                widget_item.setData(Qt.ItemDataRole.UserRole, slide_data)

                self.custom_list.addItem(widget_item)

    def populate_image_list(self):
        """
        Method that uses the data contained in the image table of the database to create QListWidgetItems in the
        image widget's QListWidget.
        """
        connection = None
        try:
            self.image_list.clear()
            connection = sqlite3.connect(self.gui.main.database)
            cursor = connection.cursor()
            thumbnails = cursor.execute('SELECT * FROM imageThumbnails ORDER BY fileName COLLATE NOCASE ASC').fetchall()

            for record in thumbnails:
                file_name = record[0]
                thumbnail_data = record[1]
                pixmap = QPixmap()
                pixmap.loadFromData(thumbnail_data)

                widget = StandardItemWidget(self.gui, file_name, '', pixmap)
                slide_data = declarations.SLIDE_DATA_DEFAULTS.copy()
                slide_data['type'] = 'image'
                slide_data['title'] = file_name
                slide_data['file_name'] = file_name
                slide_data['thumbnail'] = pixmap
                slide_data['use_footer'] = False

                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, slide_data)
                item.setSizeHint(widget.sizeHint())
                self.image_list.addItem(item)
                self.image_list.setItemWidget(item, widget)
        except Exception:
            self.gui.main.error_log()
            if connection:
                connection.close()

    def populate_video_list(self):
        """
        Method that polls the files contained in the video subdirectory of the data directory to create QListWidgetItems
        in the video widget's QListWidget.
        """
        try:
            self.video_list.clear()
            files = os.listdir(self.gui.main.video_dir)
            for file in files:
                video_file = None
                if file.endswith('.jpg'):
                    name_only = file.split('.')[0]
                    for other_file in files:
                        if other_file.startswith(name_only) and not other_file.endswith('.jpg'):
                            video_file = other_file

                    if video_file:
                        pixmap = QPixmap(self.gui.main.video_dir + '/' + file)
                        pixmap = pixmap.scaled(96, 54, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

                        widget = StandardItemWidget(self.gui, video_file.split('.')[0], '', pixmap)
                        slide_data = declarations.SLIDE_DATA_DEFAULTS.copy()
                        slide_data['type'] = 'video'
                        slide_data['title'] = video_file
                        slide_data['file_name'] = video_file
                        slide_data['use_footer'] = False

                        item = QListWidgetItem()
                        item.setData(Qt.ItemDataRole.UserRole, slide_data)
                        item.setSizeHint(widget.sizeHint())

                        self.video_list.addItem(item)
                        self.video_list.setItemWidget(item, widget)
        except Exception:
            self.gui.main.error_log()

    def populate_web_list(self):
        """
        Method that uses the data contained in the web table of the database to create QListWidgetItems in the
        web widget's QListWidget.
        """
        connection = None
        try:
            self.web_list.clear()
            connection = sqlite3.connect(self.gui.main.database)
            cursor = connection.cursor()
            results = cursor.execute('SELECT * FROM web').fetchall()
            connection.close()

            if len(results) > 0:
                for record in results:
                    title = record[0]
                    url = record[1]
                    item = QListWidgetItem()
                    slide_data = declarations.SLIDE_DATA_DEFAULTS.copy()
                    slide_data['type'] = 'web'
                    slide_data['title'] = title
                    slide_data['url'] = url
                    slide_data['use_footer'] = False
                    item.setData(Qt.ItemDataRole.UserRole, slide_data)

                    widget = StandardItemWidget(self.gui, title, url)

                    self.web_list.addItem(item)
                    item.setSizeHint(widget.sizeHint())
                    self.web_list.setItemWidget(item, widget)
        except Exception:
            self.gui.main.error_log()
            if connection:
                connection.close()

    def get_bibles(self):
        """
        Method that polls the files contained in the bibles subdirectory of the data directory and returns file names
        ending in .xml
        :return list of str bibles: The string paths of the bible files
        """
        bibles = []

        try:
            for file in os.listdir(self.gui.main.data_dir + '/bibles'):
                if file.split('.')[1] == 'xml':
                    tree = ElementTree.parse(self.gui.main.data_dir + '/bibles/' + file)
                    root = tree.getroot()
                    bibles.append([self.gui.main.data_dir + '/bibles/' + file, root.attrib['biblename']])
            return bibles
        except Exception:
            self.gui.main.error_log()
            return -1

    def get_scripture(self):
        """
        Method that retrieves the text in the bible widget's bible_search_line_edit and runs it through GetScripture,
        placing the results in the scripture_text_edit of the bible widget.
        """
        self.passages = None
        self.formatted_reference = False
        text = self.bible_search_line_edit.text()

        # if the current changes means that the line edit is empty, also clear the scripture text edit
        if text == '':
            self.scripture_text_edit.clear()
            self.formatted_reference = None
            return

        # create an instance of GetScripture if one doesn't already exist
        if not self.gui.main.get_scripture:
            self.gui.main.get_scripture = GetScripture(self.gui.main)

        self.scripture_text_edit.clear()
        self.passages = self.gui.main.get_scripture.get_passage(text)

        if self.passages and not self.passages[0] == -1:
            self.formatted_reference = ''
            reference_split = self.bible_search_line_edit.text().split(' ')

            for i in range(len(reference_split)):
                if '-' in reference_split[i]:
                    self.formatted_reference = self.passages[0] + ' ' + reference_split[i]

            scripture = ''
            for passage in self.passages[1]:
                scripture += passage[0] + ' ' + passage[1] + ' '

            self.scripture_text_edit.setText(scripture.strip())
            self.scripture_text_edited = False

    def text_edited(self):
        self.scripture_text_edited = True

    def change_bible(self):
        """
        Method to change the gui's default_bible variable to the currently selected bible in the bible widget's
        bible_selector_combobox. Re-calls get_scripture() if there is text in the bible_search_line_edit.
        """
        self.gui.main.get_scripture = None
        self.gui.main.settings['default_bible'] = self.bible_selector_combobox.itemData(
            self.bible_selector_combobox.currentIndex(), Qt.ItemDataRole.UserRole)
        if len(self.bible_search_line_edit.text()) > 0:
            self.get_scripture()

    def set_default_bible(self):
        """
        Method that changes the default bible saved in the settings.
        """
        name = self.bible_selector_combobox.currentText()
        response = QMessageBox.question(
            self.gui.main_window,
            f'Set {name} as Default',
            f'Set {name} as your default bible?',
            QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.No
        )

        if response == QMessageBox.StandardButton.Yes:
            self.gui.main.settings['default_bible'] = self.bible_selector_combobox.itemData(
                self.bible_selector_combobox.currentIndex(), Qt.ItemDataRole.UserRole)
            self.gui.main.save_settings()

    def send_scripture_to_live(self):
        """
        Method to send the scripture passage contained in the bible widget's scripture_text_edit directly to
        live without adding it to the order of service.
        """
        if self.formatted_reference:
            reference = self.formatted_reference
            version = self.bible_selector_combobox.currentText()

            item = QListWidgetItem()
            slide_data = declarations.SLIDE_DATA_DEFAULTS.copy()
            slide_data['type'] = 'bible'
            slide_data['title'] = reference
            slide_data['text'] = self.passages[1]
            slide_data['parsed_text'] = parsers.parse_scripture_by_verse(self.gui, self.passages[1])
            slide_data['author'] = version
            item.setData(Qt.ItemDataRole.UserRole, slide_data)

            self.gui.send_to_preview(item)
            self.gui.preview_widget.slide_list.setCurrentRow(0)
            self.gui.send_to_live()

            self.formatted_reference = None

    def add_song(self, type):
        """
        Method to create an instance of EditWidget.
        :param str type: Whether the type to be added is a 'song' or a 'custom' slide
        """
        edit_widget = EditWidget(self.gui, type)

    def send_to_live(self):
        self.gui.preview_widget.slide_list.setCurrentRow(0)
        self.gui.send_to_live()

    def add_image(self):
        """
        Method that creates a QFileDialog for the user to add an image to the program's database. Copies that
        image file to the data directory, reindexes the images in the database, and reloads the image widget's
        QListWidget.
        """
        result = QFileDialog.getOpenFileName(
            self.gui.main_window,
            'Choose Image',
            os.path.expanduser('~') + '/Pictures',
            'Image Files (*.jpg *.png *.svg)'
        )
        if len(result[0]) > 0:
            try:
                file_name_split = result[0].split('/')
                file_name = file_name_split[len(file_name_split) - 1]
                shutil.copy(result[0], self.gui.main.image_dir + '/' + file_name)

                from runnables import IndexImages
                ii = IndexImages(self.gui.main, 'images')
                ii.add_image_index(self.gui.main.image_dir + '/' + file_name, 'image')
                self.image_list.blockSignals(True)
                self.populate_image_list()
                self.image_list.update()
                self.image_list.blockSignals(False)
            except Exception:
                self.gui.main.error_log()

    def delete_image(self):
        """
        Method to remove an image from the program's database and data directory. Creates a QMessageBox to
        ask for confirmation, then deletes the file from the data directory and reindexes the images in the database.
        """
        file_name = self.image_list.currentItem().data(Qt.ItemDataRole.UserRole)['file_name']
        response = QMessageBox.question(
            self.gui.main_window,
            'Really Delete',
            'Remove ' + file_name.split('.')[0] + ' from ProjectOn?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if response == QMessageBox.StandardButton.Yes:
            try:
                os.remove(self.gui.main.image_dir + '/' + file_name)
            except FileNotFoundError:
                QMessageBox.information(
                    self.gui.main_window, 'Not Found', 'File not found. Reindexing images.', QMessageBox.StandardButton.Ok)

            from runnables import IndexImages
            ii = IndexImages(self.gui.main, 'images')
            self.gui.main.thread_pool.start(ii)
            self.gui.main.thread_pool.waitForDone()
            self.populate_image_list()
            self.image_list.update()

    def add_web(self):
        """
        Method to add a web item to the web widget's QListWidget.
        """
        web_dialog = QDialog()
        web_layout = QVBoxLayout()
        web_dialog.setLayout(web_layout)

        title_widget = QWidget()
        title_layout = QHBoxLayout()
        title_widget.setLayout(title_layout)
        web_layout.addWidget(title_widget)

        title_label = QLabel('Title:')
        title_label.setFont(self.gui.standard_font)
        title_layout.addWidget(title_label)

        title_line_edit = QLineEdit()
        title_line_edit.setFont(self.gui.standard_font)
        title_layout.addWidget(title_line_edit)

        url_widget = QWidget()
        url_layout = QHBoxLayout()
        url_widget.setLayout(url_layout)
        web_layout.addWidget(url_widget)

        url_label = QLabel('Website Address:')
        url_label.setFont(self.gui.standard_font)
        url_layout.addWidget(url_label)

        url_line_edit = QLineEdit()
        url_line_edit.setFont(self.gui.standard_font)
        url_layout.addWidget(url_line_edit)

        button_widget = QWidget()
        button_layout = QHBoxLayout()
        button_widget.setLayout(button_layout)
        web_layout.addWidget(button_widget)

        ok_button = QPushButton('Add')
        ok_button.clicked.connect(lambda: web_dialog.done(0))
        ok_button.setFont(self.gui.standard_font)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addSpacing(20)

        cancel_button = QPushButton('Cancel')
        cancel_button.clicked.connect(lambda: web_dialog.done(1))
        cancel_button.setFont(self.gui.standard_font)
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()

        result = web_dialog.exec()
        if result == 0:
            item = QListWidgetItem()
            item.setData(20, title_line_edit.text())
            item.setData(21, url_line_edit.text())
            item.setData(40, 'web')

            widget = StandardItemWidget(self.gui, title_line_edit.text(), url_line_edit.text())

            self.web_list.addItem(item)
            item.setSizeHint(widget.sizeHint())
            self.web_list.setItemWidget(item, widget)

            self.gui.main.save_web_item(title_line_edit.text(), url_line_edit.text())
            self.populate_web_list()

    def add_video(self):
        """
        Method to add a video to the video widget's QListWidget and the video table of the database. Creates a
        QFileDialog to ask for the video file then copies that file to the data directory, pulls still frames from
        the video, asks the user to choose a frame as a thumbnail, then reloads the QListWidget of the video widget.
        """
        result = QFileDialog.getOpenFileName(
            self.gui.main_window,
            'Choose Video to Import',
            os.path.expanduser('~') + '/Videos',
            'Video Files (*.mp4 *.avi *.wmv *.mkv *.mov)'
        )

        if len(result[0]) > 0:
            wait_widget = SimpleSplash(self.gui, 'Please wait...')

            file_name_split = result[0].split('/')
            file_name = file_name_split[len(file_name_split) - 1]
            shutil.copy(result[0], self.gui.main.video_dir + '/' + file_name)

            try:
                import cv2
                cap = cv2.VideoCapture(self.gui.main.video_dir + '/' + file_name)
                iteration = 0
                while True:
                    result, frame = cap.read()
                    if iteration % 100 == 0:
                        if result:
                            cv2.imwrite(f'{os.path.expanduser("~/AppData/Roaming/ProjectOn")}/thumbnail{str(iteration)}.jpg', frame)
                        else:
                            break
                    iteration += 1
                    if iteration > 500:
                        break
                cap.release()
                cv2.destroyAllWindows()

                thumbnail_widget = QDialog()
                thumbnail_layout = QVBoxLayout()
                thumbnail_widget.setLayout(thumbnail_layout)

                label = QLabel('Choose a thumbnail to go with this video:')
                label.setFont(self.gui.list_title_font)
                thumbnail_layout.addWidget(label)

                thumbnail_list = QListWidget()
                thumbnail_list.setObjectName('thumbnail_list')
                thumbnail_list.currentItem()
                thumbnail_list.itemClicked.connect(
                    lambda: self.copy_video(
                        file_name, thumbnail_list.currentItem().data(20),
                        thumbnail_widget
                    )
                )
                thumbnail_layout.addWidget(thumbnail_list)

                file_list = os.listdir(os.path.expanduser("~/AppData/Roaming/ProjectOn"))
                for file in file_list:
                    if file.startswith('thumbnail'):
                        pixmap = QPixmap(os.path.expanduser("~/AppData/Roaming/ProjectOn") + '/' + file)
                        pixmap = pixmap.scaled(
                            96,
                            54,
                            Qt.AspectRatioMode.IgnoreAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )

                        widget = StandardItemWidget(
                            self.gui, 'Frame ' + file.split('.')[0].replace('thumbnail', ''), '', pixmap)

                        item = QListWidgetItem()
                        item.setData(20, file)
                        item.setSizeHint(widget.sizeHint())
                        thumbnail_list.addItem(item)
                        thumbnail_list.setItemWidget(item, widget)

                wait_widget.widget.deleteLater()
                thumbnail_widget.exec()

                for file in os.listdir(os.path.expanduser("~/AppData/Roaming/ProjectOn")):
                    if file.startswith('thumbnail'):
                        os.remove(os.path.expanduser("~/AppData/Roaming/ProjectOn") + '/' + file)

            except Exception:
                self.gui.main.error_log()

    def copy_video(self, video_file, image_file, dialog):
        """
        Method to copy the user's video file and its thumbnail image file to the video subdirectory of the data
        directory, then repopulate the video widget's QListWidget. Provides a QMessageBox to confirm that the
        import has completed successfully.
        :param str video_file: The path to the video file
        :param image_file: The path to the thumbnail image file
        :param dialog: The currently showing thumbnail dialog
        :return:
        """
        try:
            new_image_file_name = video_file.split('.')[0] + '.jpg'
            shutil.copy(
                os.path.expanduser('~/AppData/Roaming/ProjectOn') + '/' + image_file,
                self.gui.main.video_dir + '/' + new_image_file_name
            )
        except Exception:
            self.gui.main.error_log()
            return

        QMessageBox.information(
            self.gui.main_window,
            'Video Imported',
            'Video has been successfully imported.',
            QMessageBox.StandardButton.Ok
        )
        dialog.done(0)

        self.populate_video_list()

    def add_song_to_service(self, item=None, row=None, from_load_service=False):
        """
        Method to add a song QListWidgetItem to the order of service's QListWidget
        :param QListWidgetItem item: Optional: a specific song item
        :param int row: Optional: a specific row of the song widget's QListWidget
        :param bool from_load_service: Whether this call is occurring while loading a service file
        """
        if not item and self.song_list.currentItem():
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, self.song_list.currentItem().data(Qt.ItemDataRole.UserRole).copy())

        if item and not from_load_service:
            item.setText(None)

            # Create a thumbnail of either the global song background or the custom background associated with this song
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if (not item_data['background']
                    or item_data['background'] == 'False'
                    or item_data['background'] == 'global_song'):
                pixmap = self.gui.global_song_background_pixmap
                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            elif item_data['background'] == 'global_bible':
                pixmap = self.gui.global_bible_background_pixmap
                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            elif 'rgb(' in item_data['background']:
                pixmap = QPixmap(50, 27)
                painter = QPainter(pixmap)
                rgb = item_data['background'].replace('rgb(', '')
                rgb = rgb.replace(')', '')
                rgb_split = rgb.split(',')
                brush = QBrush(QColor.fromRgb(
                    int(rgb_split[0].strip()), int(rgb_split[1].strip()), int(rgb_split[2].strip())))
                painter.setBrush(brush)
                painter.fillRect(pixmap.rect(), brush)
                painter.end()
            else:
                pixmap = QPixmap(self.gui.main.background_dir + '/' + item_data['background'])
                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

            widget = StandardItemWidget(self.gui, item_data['title'], 'Song', pixmap)

            item.setSizeHint(widget.sizeHint())
            if not row:
                self.gui.oos_widget.oos_list_widget.addItem(item)
            else:
                self.gui.oos_widget.oos_list_widget.insertItem(row, item)
            self.gui.oos_widget.oos_list_widget.setItemWidget(item, widget)
            self.gui.changes = True

        if item and from_load_service:
            # handle this differently if it's being created while loading a service file
            widget_item = QListWidgetItem()
            slide_data = item.data(Qt.ItemDataRole.UserRole).copy()
            slide_data['parsed_text'] = (parsers.parse_song_data(self.gui, slide_data))
            widget_item.setData(Qt.ItemDataRole.UserRole, slide_data)

            if (slide_data['override_global'] == 'False'
                or not slide_data['background']
                or slide_data['background'] == 'False'
                or slide_data['background'] == 'global_song'):
                pixmap = self.gui.global_song_background_pixmap
                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
            elif slide_data['background'] == 'global_bible':
                pixmap = self.gui.global_bible_background_pixmap
                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
            elif 'rgb(' in slide_data['background']:
                pixmap = QPixmap(50, 27)
                painter = QPainter(pixmap)
                brush = QBrush(QColor(slide_data['background']))
                painter.setBrush(brush)
                painter.fillRect(pixmap.rect(), brush)
                painter.end()
            else:
                pixmap = QPixmap(self.gui.main.background_dir + '/' + slide_data['background'])
                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)

            widget = StandardItemWidget(self.gui, slide_data['title'], 'Song', pixmap)

            widget_item.setSizeHint(widget.sizeHint())
            self.gui.oos_widget.oos_list_widget.addItem(widget_item)
            self.gui.oos_widget.oos_list_widget.setItemWidget(widget_item, widget)

    def add_scripture_to_service(self):
        """
        Method to add the scripture passage contained in the bible widget's scripture_text_edit to the order of
        service's QListWidget
        :return: None
        """
        if self.formatted_reference:
            passages = []
            text_split = self.scripture_text_edit.toPlainText().split()
            add_verse = False
            verse_number = False
            verse_words = []
            for item in text_split:
                item = item.strip()
                if add_verse and not item.isdigit():
                    verse_words.append(item)
                else:
                    if verse_number:
                        passages.append([verse_number, ' '.join(verse_words).strip()])
                        verse_words = []
                    verse_number = item
                    add_verse = True
            passages.append([verse_number, ' '.join(verse_words).strip()])

            reference = self.formatted_reference
            version = self.bible_selector_combobox.currentText()
            self.gui.add_scripture_item(reference, passages, version, self.scripture_text_edited)
            self.gui.changes = True

    def add_custom_to_service(self, item=None, row=None):
        """
        Method to add a custom slide QListWidgetItem to the order of service's QListWidget
        :param QListWidgetItem item: Optional: a specific custom slide item
        :param int row: Optional: a specific row of the custom slide widget's QListWidget
        """
        if not item and self.custom_list.currentItem():
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, self.custom_list.currentItem().data(Qt.ItemDataRole.UserRole))
            for i in range(20, 50):
                item.setData(i, self.custom_list.currentItem().data(i))
        elif not item and not self.custom_list.currentItem():
            return

        item_data = item.data(Qt.ItemDataRole.UserRole)
        if item_data['override_global'] == 'False' or not item_data['background']:
            pixmap = self.gui.global_bible_background_pixmap
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        elif item_data['background'] == 'global_song':
            pixmap = self.gui.global_song_background_pixmap
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        elif item_data['background'] == 'global_bible':
            pixmap = self.gui.global_bible_background_pixmap
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        elif 'rgb(' in item_data['background']:
            pixmap = QPixmap(50, 27)
            painter = QPainter(pixmap)
            brush = QBrush(QColor(item_data['background']))
            painter.fillRect(pixmap.rect(), brush)
            painter.end()
        else:
            pixmap = QPixmap(self.gui.main.background_dir + '/' + item_data['background'])
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

        widget = StandardItemWidget(self.gui, item_data['title'], 'Custom Slide', pixmap)
        item.setText(None)
        item.setSizeHint(widget.sizeHint())
        if not row:
            self.gui.oos_widget.oos_list_widget.addItem(item)
        else:
            self.gui.oos_widget.oos_list_widget.insertItem(row, item)
        self.gui.oos_widget.oos_list_widget.setItemWidget(item, widget)
        self.gui.changes = True

    def add_image_to_service(self, item=None, row=None):
        """
        Method to add an image QListWidgetItem to the order of service's QListWidget
        :param QListWidgetItem item: Optional: a specific image item
        :param int row: Optional: a specific row of the image widget's QListWidget
        """
        add_item = False
        if self.image_list.currentItem():
            if not item:
                item = QListWidgetItem()
                add_item = True

            slide_data = self.image_list.currentItem().data(Qt.ItemDataRole.UserRole).copy()
            item.setData(Qt.ItemDataRole.UserRole, slide_data)

            pixmap = slide_data['thumbnail']
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            widget = StandardItemWidget(self.gui, slide_data['title'], 'Image', pixmap)

            item.setSizeHint(widget.sizeHint())
            if add_item:
                self.gui.oos_widget.oos_list_widget.addItem(item)
            else:
                self.gui.oos_widget.oos_list_widget.insertItem(row, item)
            self.gui.oos_widget.oos_list_widget.setItemWidget(item, widget)
            self.gui.changes = True

    def add_web_to_service(self, item=None, row=None):
        """
        Method to add a web QListWidgetItem to the order of service's QListWidget
        :param QListWidgetItem item: Optional: a specific web item
        :param int row: Optional: a specific row of the web widget's QListWidget
        """
        add_item = False
        if self.web_list.currentItem():
            if not item:
                item = QListWidgetItem()
                add_item = True
            item.setData(Qt.ItemDataRole.UserRole, self.web_list.currentItem().data(Qt.ItemDataRole.UserRole).copy())

            pixmap = QPixmap(50, 27)
            painter = QPainter(pixmap)
            brush = QBrush(Qt.GlobalColor.black)
            pen = QPen(Qt.GlobalColor.white)
            painter.setPen(pen)
            painter.setBrush(brush)
            painter.fillRect(pixmap.rect(), brush)
            painter.setFont(self.gui.bold_font)
            painter.drawText(QPoint(2, 20), 'WWW')
            painter.end()

            widget = StandardItemWidget(
                self.gui, item.data(
                    Qt.ItemDataRole.UserRole)['title'], item.data(Qt.ItemDataRole.UserRole)['url'], pixmap)

            item.setSizeHint(widget.sizeHint())
            if add_item:
                self.gui.oos_widget.oos_list_widget.addItem(item)
            else:
                self.gui.oos_widget.oos_list_widget.insertItem(row, item)
            self.gui.oos_widget.oos_list_widget.setItemWidget(item, widget)
            self.gui.changes = True

    def add_video_to_service(self, item=None, row=None):
        """
        Method to add a video QListWidgetItem to the order of service's QListWidget
        :param QListWidgetItem item: Optional: a specific video item
        :param int row: Optional: a specific row of the video widget's QListWidget
        """
        add_item = False
        if self.video_list.currentItem():
            if not item:
                item = QListWidgetItem()
                add_item = True
            slide_data = self.video_list.currentItem().data(Qt.ItemDataRole.UserRole).copy()
            item.setData(Qt.ItemDataRole.UserRole, slide_data)

            pixmap = QPixmap(
                self.gui.main.video_dir + '/' + slide_data['file_name'].split('.')[0] + '.jpg')
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)

            widget = StandardItemWidget(
                self.gui, slide_data['title'].split('.')[0], 'Video', pixmap)

            item.setSizeHint(widget.sizeHint())
            if add_item:
                self.gui.oos_widget.oos_list_widget.addItem(item)
            else:
                self.gui.oos_widget.oos_list_widget.insertItem(row, item)
            self.gui.oos_widget.oos_list_widget.setItemWidget(item, widget)
            self.gui.changes = True


class CustomListWidget(QListWidget):
    """
    Implements QListWidget to add custom functionality.
    """
    def __init__(self, gui, type):
        """
        Implements QListWidget to add custom functionality.
        :param gui.GUI gui: The current instance of GUI
        :param str type: Whether this QListWidget will contain 'song' or 'custom' slides
        """
        super().__init__()
        self.gui = gui
        self.type = type
        self.item_pos = None
        self.setObjectName('song_list_widget')

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)
        self.currentItemChanged.connect(self.current_item_changed)

    def context_menu(self):
        """
        Creates a QMenu to be used as a custom context menu.
        """
        self.item_pos = self.mapFromGlobal(self.cursor().pos())
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

        add_to_service_action = QAction('Add to Order of Service')
        if self.type == 'song':
            add_to_service_action.triggered.connect(self.gui.media_widget.add_song_to_service)
        elif self.type == 'custom':
            add_to_service_action.triggered.connect(self.gui.media_widget.add_custom_to_service)
        elif self.type == 'image':
            add_to_service_action.triggered.connect(self.gui.media_widget.add_image_to_service)
        elif self.type == 'video':
            add_to_service_action.triggered.connect(self.gui.media_widget.add_video_to_service)
        elif self.type == 'web':
            add_to_service_action.triggered.connect(self.gui.media_widget.add_web_to_service)
        menu.addAction(add_to_service_action)

        edit_action = None
        if self.type == 'song':
            edit_action = QAction('Edit Song')
        elif self.type == 'custom':
            edit_action = QAction('Edit Slide')

        if edit_action:
            edit_action.triggered.connect(self.edit_song)
            menu.addAction(edit_action)

        delete_action = None
        if self.type == 'image':
            delete_action = QAction('Remove Image')
            delete_action.triggered.connect(self.gui.media_widget.delete_image) # TODO: move this to self.delete_item
        elif self.type == 'custom':
            delete_action = QAction('Delete Slide')
            delete_action.triggered.connect(self.delete_item)
        elif self.type == 'song':
            delete_action = QAction('Delete Song')
            delete_action.triggered.connect(self.delete_item)
        elif self.type == 'video':
            delete_action = QAction('Remove Video')
            delete_action.triggered.connect(self.delete_item)
        elif self.type == 'web':
            delete_action = QAction('Remove Web Item')
            delete_action.triggered.connect(self.delete_item)

        if delete_action:
            menu.addAction(delete_action)

        menu.exec(QCursor.pos())

    def mouseDoubleClickEvent(self, evt):
        """
        Overrides mouseDoubleClickEvent to provide the ability to add an item to the order of service upon double-click.
        :param QMouseEvent evt: mouseEvent
        """
        if self.currentItem().data(Qt.ItemDataRole.UserRole)['type'] == 'song':
            self.gui.media_widget.add_song_to_service()
        elif self.currentItem().data(Qt.ItemDataRole.UserRole)['type'] == 'custom':
            self.gui.media_widget.add_custom_to_service()
        elif self.currentItem().data(Qt.ItemDataRole.UserRole)['type'] == 'web':
            self.gui.media_widget.add_web_to_service()
        elif self.currentItem().data(Qt.ItemDataRole.UserRole)['type'] == 'image':
            self.gui.media_widget.add_image_to_service()
        elif self.currentItem().data(Qt.ItemDataRole.UserRole)['type'] == 'video':
            self.gui.media_widget.add_video_to_service()

        self.gui.oos_widget.oos_list_widget.setCurrentRow(self.gui.oos_widget.oos_list_widget.count() - 1)
        self.gui.oos_widget.oos_list_widget.setFocus()

    def current_item_changed(self):
        """
        Method to send the current item to the preview widget upon the current item being changed.
        """
        if self.currentItem():
            if self.currentItem().data(Qt.ItemDataRole.UserRole)['type'] == 'song':
                item_data = self.currentItem().data(Qt.ItemDataRole.UserRole)
                item_data['parsed_text'] = parsers.parse_song_data(self.gui, item_data)
                self.currentItem().setData(Qt.ItemDataRole.UserRole, item_data)
            self.gui.send_to_preview(self.currentItem())

    def edit_song(self):
        """
        Method to create a EditWidget for a song or custom slide.
        """
        if self.itemAt(self.item_pos):
            if self.currentItem().data(Qt.ItemDataRole.UserRole)['type'] == 'song':
                item_text = self.itemAt(self.item_pos).text()
                song_info = self.gui.main.get_song_data(item_text)
                song_data = self.itemAt(self.item_pos).data(Qt.ItemDataRole.UserRole)
                self.gui.edit_widget = EditWidget(self.gui, 'song', song_info, item_text, song_data)
            elif self.currentItem().data(Qt.ItemDataRole.UserRole)['type'] == 'custom':
                item_text = self.itemAt(self.item_pos).text()
                custom_info = self.gui.main.get_custom_data(item_text)
                custom_data = self.itemAt(self.item_pos).data(Qt.ItemDataRole.UserRole)
                self.gui.edit_widget = EditWidget(self.gui, 'custom', custom_info, item_text, custom_data)

    def delete_item(self):
        """
        Method to remove an item from this widget. Creates a QMessageBox to confirm removal.
        """
        response = QMessageBox.question(
            self.gui.main_window,
            'Really Delete',
            'Really delete '
                + self.currentItem().data(Qt.ItemDataRole.UserRole)['type']
                + '? This action cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if response == QMessageBox.StandardButton.Yes:
            thread = threading.Thread(target=self.gui.main.delete_item, args=(self.currentItem(),))
            thread.start()
            thread.join()

        if self.currentItem().data(Qt.ItemDataRole.UserRole)['type'] == 'song':
            self.gui.media_widget.populate_song_list()
        elif self.currentItem().data(Qt.ItemDataRole.UserRole)['type'] == 'custom':
            self.gui.media_widget.populate_custom_list()
        elif self.currentItem().data(Qt.ItemDataRole.UserRole)['type'] == 'image':
            self.gui.media_widget.populate_image_list()
        elif self.currentItem().data(Qt.ItemDataRole.UserRole)['type'] == 'video':
            self.gui.media_widget.populate_video_list()
        elif self.currentItem().data(Qt.ItemDataRole.UserRole)['type'] == 'web':
            self.gui.media_widget.populate_web_list()

        self.gui.preview_widget.slide_list.clear()