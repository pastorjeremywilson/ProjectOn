import os
import re
import shutil
import sqlite3
import threading
from os.path import exists
from threading import Thread
from xml.etree import ElementTree

from PyQt5.QtCore import Qt, QSize, QPoint
from PyQt5.QtGui import QCursor, QPixmap, QIcon, QFont, QPainter, QBrush, QColor, QPen
from PyQt5.QtWidgets import QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, \
    QListWidgetItem, QMenu, QComboBox, QTextEdit, QAbstractItemView, QDialog, QFileDialog, QMessageBox, QAction, \
    QApplication, QTreeWidgetItem

from dataHandling import parsers, declarations
from dataHandling.declarations import SLIDE_DATA_DEFAULTS
from dataHandling.parsers import parse_song_data
from gui.widgets.editWidget import EditWidget
from dataHandling.getScripture import GetScripture
from gui.widgets.widgets import AutoSelectLineEdit, StandardItemWidget, SimpleSplash, CustomTreeWidget


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

        add_folder_button = QPushButton()
        add_folder_button.setIcon(QIcon('resources/gui_icons/new_folder.svg'))
        add_folder_button.setIconSize(QSize(20, 20))
        add_folder_button.setFixedSize(30, 30)
        add_folder_button.setToolTip('Add a new folder')
        button_widget.layout().addWidget(add_folder_button)
        button_widget.layout().addStretch()

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

        self.song_list = CustomTreeWidget(self.gui)
        self.song_list.setFont(self.gui.standard_font)
        self.song_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.song_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.song_list.verticalScrollBar().setSingleStep(10)
        self.song_list.setDragEnabled(True)
        song_layout.addWidget(self.song_list)

        add_folder_button.clicked.connect(self.song_list.add_folder)
        self.populate_song_list()

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

        if len(bibles) > 0 and len(bibles[0]) > 0:
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

        add_folder_button = QPushButton()
        add_folder_button.setIcon(QIcon('resources/gui_icons/new_folder.svg'))
        add_folder_button.setIconSize(QSize(20, 20))
        add_folder_button.setFixedSize(30, 30)
        add_folder_button.setToolTip('Add a new folder')
        button_widget.layout().addWidget(add_folder_button)
        button_widget.layout().addStretch()

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

        self.custom_list = CustomTreeWidget(self.gui)
        self.custom_list.setFont(self.gui.standard_font)
        self.custom_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.custom_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.custom_list.verticalScrollBar().setSingleStep(10)
        self.custom_list.setDragEnabled(True)
        custom_layout.addWidget(self.custom_list)

        add_folder_button.clicked.connect(self.custom_list.add_folder)
        self.populate_custom_list()

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

        add_folder_button = QPushButton()
        add_folder_button.setIcon(QIcon('resources/gui_icons/new_folder.svg'))
        add_folder_button.setIconSize(QSize(20, 20))
        add_folder_button.setFixedSize(30, 30)
        add_folder_button.setToolTip('Add a new folder')
        button_widget.layout().addWidget(add_folder_button)
        button_widget.layout().addStretch()

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

        self.image_list = CustomTreeWidget(self.gui)
        self.image_list.setFont(self.gui.standard_font)
        self.image_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.image_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.image_list.verticalScrollBar().setSingleStep(10)
        self.image_list.setDragEnabled(True)
        image_layout.addWidget(self.image_list)

        add_folder_button.clicked.connect(self.image_list.add_folder)
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

        add_folder_button = QPushButton()
        add_folder_button.setIcon(QIcon('resources/gui_icons/new_folder.svg'))
        add_folder_button.setIconSize(QSize(20, 20))
        add_folder_button.setFixedSize(30, 30)
        add_folder_button.setToolTip('Add a new folder')
        button_widget.layout().addWidget(add_folder_button)
        button_widget.layout().addStretch()

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

        self.video_list = CustomTreeWidget(self.gui)
        self.video_list.setFont(self.gui.standard_font)
        self.video_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.video_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.video_list.verticalScrollBar().setSingleStep(10)
        self.video_list.setDragEnabled(True)
        video_layout.addWidget(self.video_list)

        add_folder_button.clicked.connect(self.video_list.add_folder)
        self.populate_video_list()

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

        add_folder_button = QPushButton()
        add_folder_button.setIcon(QIcon('resources/gui_icons/new_folder.svg'))
        add_folder_button.setIconSize(QSize(20, 20))
        add_folder_button.setFixedSize(30, 30)
        add_folder_button.setToolTip('Add a new folder')
        button_widget.layout().addWidget(add_folder_button)
        button_widget.layout().addStretch()

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

        self.web_list = CustomTreeWidget(self.gui)
        self.video_list.setFont(self.gui.standard_font)
        self.video_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.video_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.video_list.verticalScrollBar().setSingleStep(10)
        self.video_list.setDragEnabled(True)
        web_layout.addWidget(self.web_list)

        add_folder_button.clicked.connect(self.web_list.add_folder)
        self.populate_web_list()

        return web_widget

    def song_search(self):
        """
        Method that retrieves the current text in the song widget's search_line_edit and shows/hides songs that do or
        don't contain the text. Results are weighted according to whether the full text is found first in the song
        title, then if the full text is found in the lyrics, then if any of the search words are found in the title or
        lyrics. Sorting within the QTreeWidget is enabled by adding the weight plus '|' in front of the hidden text
        of the QTreeWidgetItem.
        """
        search_string = self.search_line_edit.text().strip().lower()
        if len(search_string) == 0:
            for i in range(self.song_list.topLevelItemCount()):
                item = self.song_list.topLevelItem(i)
                item.setHidden(False)

                if item.data(0, Qt.ItemDataRole.UserRole)['type'] == 'folder':
                    item.setExpanded(False)
                    if '|' in item.text(0):
                        item.setText(0, item.text(0).split('|')[1])
                    for j in range(item.childCount()):
                        item.child(j).setHidden(False)
                        if '|' in item.child(j).text(0):
                            item.child(j).setText(0, item.child(j).text(0).split('|')[0])
            return

        show_list_rankings = {}
        # first, search for the full search term in titles
        for i in range(len(self.song_list_items)):
            data = self.song_list_items[i]
            if search_string in data['stripped_title'].lower() and data['title'] not in show_list_rankings.keys():
                show_list_rankings[data['title']] = int(f'{100}{i}')

        # then, search for the full search term in texts
        for i in range(len(self.song_list_items)):
            data = self.song_list_items[i]
            if search_string in data['text'].lower() and data['title'] not in show_list_rankings.keys():
                show_list_rankings[data['title']] = int(f'{110}{i}')

        # now, search for each search term in the titles
        search_term_split = search_string.split()
        for word in search_term_split:
            for i in range(len(self.song_list_items)):
                data = self.song_list_items[i]
                if word in data['stripped_title'].lower() and data['title'] not in show_list_rankings.keys():
                    show_list_rankings[data['title']] = int(f'{120}{i}')

        # finally, search for each search term in the texts
        for word in search_term_split:
            for i in range(len(self.song_list_items)):
                data = self.song_list_items[i]
                if word in data['text'].lower() and data['title'] not in show_list_rankings.keys():
                    show_list_rankings[data['title']] = int(f'{130}{i}')

        # hide whichever items aren't in the list of titles
        all_titles = show_list_rankings.keys()
        folder_counter = 0
        for i in range(self.song_list.topLevelItemCount()):
            item = self.song_list.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole)['type'] == 'folder':
                item.setHidden(False)
                found_in_folder = False
                for j in range(item.childCount()):
                    title = item.child(j).data(0, Qt.ItemDataRole.UserRole)['title']
                    if title in all_titles:
                        found_in_folder = True
                        item.setExpanded(True)
                        if '|' in item.text(0):
                            item.setText(0, item.text(0).split('|')[1])
                        item.setText(0, f'{folder_counter}|{item.text(0)}')
                        folder_counter += 1

                        item.child(j).setHidden(False)
                        if '|' in title:
                            title = title.split('|')[1]
                        item.child(j).setText(0, f'{show_list_rankings[title]}|{title.lower()}')
                    else:
                        item.child(j).setHidden(True)
                        if '|' in item.text(0):
                            item.setText(0, item.text(0).split('|')[1])
                        if '|' in title:
                            item.child(j).setData(0, Qt.ItemDataRole.DisplayRole, title.split('|')[1])
                if not found_in_folder:
                    item.setHidden(True)
                    if '|' in item.text(0):
                        item.setText(0, item.text(0).split('|')[1])
            else:
                title = item.data(0, Qt.ItemDataRole.UserRole)['title']
                if title in all_titles:
                    item.setHidden(False)
                    if '|' in title:
                        title = title.split('|')[1]
                    item.setText(0, f'{show_list_rankings[title]}|{title.lower()}')
                else:
                    item.setHidden(True)
                    if '|' in title:
                        item.setText(0, title)
        self.song_list.custom_sort()

    def populate_song_list(self):
        """
        Method that uses the data contained in the song table of the database to fill the song widget's QTreeWidget
        with all of the songs.
        """
        self.song_list.clear()
        all_songs = self.gui.main.get_all_songs()
        all_folders = self.gui.main.get_folders('song')

        pixmap = QPixmap('resources/gui_icons/song_icon.svg')
        pixmap = pixmap.scaled(
            20,
            20,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # first, create the folders the custom slides belong to
        folder_items = {}
        for folder in all_folders:
            folder_items[folder] = self.song_list.add_folder(name=folder, from_populate=True)

        # then, add the custom slides, putting them under their folder, if applicable
        for song_data in all_songs:
            if self.gui.main.initial_startup:
                self.gui.main.update_status_signal.emit(f'Loading Songs - {song_data['title']}', 'info')

            if not 'folder' in song_data.keys() or song_data['folder'].strip() == '':
                self.song_list.add_item(song_data['title'], song_data, item_pixmap=pixmap)
            else:
                self.song_list.add_item(
                    song_data['title'],
                    song_data,
                    item_pixmap=pixmap,
                    item_parent=folder_items[song_data['folder']]
                )
        thread = Thread(target=self.build_song_search_index())
        thread.start()

    def build_song_search_index(self):
        punctuation = ['"', '\'', '`', '(', ')', ':', ';', '?', '!', '.', ',', '-', '*', '#']
        self.song_list_items = []
        for i in range(self.song_list.topLevelItemCount()):
            item = self.song_list.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole)['type'] == 'folder':
                for j in range(item.childCount()):
                    title = item.child(j).data(0, Qt.ItemDataRole.UserRole)['title']
                    text = item.child(j).data(0, Qt.ItemDataRole.UserRole)['text']
                    stripped_title = title
                    for punct in punctuation:
                        stripped_title = title.replace(punct, '')
                        text = text.replace(punct, '')
                        text = re.sub(r'\[.*?]', '', text)
                        text = re.sub(f'<.*?>', ' ', text)
                        text = re.sub(r'\s+', ' ', text)
                    self.song_list_items.append({'title': title, 'stripped_title': stripped_title, 'text': text})
            else:
                title = item.data(0, Qt.ItemDataRole.UserRole)['title']
                text = item.data(0, Qt.ItemDataRole.UserRole)['text']
                stripped_title = title
                for punct in punctuation:
                    stripped_title = title.replace(punct, '')
                    text = text.replace(punct, '')
                    text = re.sub(r'\[.*?]', '', text)
                    text = re.sub(f'<.*?>', ' ', text)
                    text = re.sub(r'\s+', ' ', text)
                self.song_list_items.append({'title': title, 'stripped_title': stripped_title, 'text': text})

    def populate_custom_list(self):
        """
        Method that uses the data contained in the custom slide table of the database to create QTreeWidgetItems in the
        custom slide widget's QTreeWidget.
        """
        self.custom_list.clear()
        slides = self.gui.main.get_all_custom_slides()
        all_folders = self.gui.main.get_folders('custom')

        pixmap = QPixmap('resources/gui_icons/custom_slide_icon.svg')
        pixmap = pixmap.scaled(
            20,
            20,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # first, create the folders the custom slides belong to
        folder_items = {}
        for folder in all_folders:
            folder_items[folder] = self.custom_list.add_folder(name=folder, from_populate=True)

        # then, add the custom slides, putting them under their folder, if applicable
        for data in slides:
            data['use_footer'] = False

            if not 'folder' in data.keys() or data['folder'].strip() == '':
                self.custom_list.add_item(data['title'], data, item_pixmap=pixmap)
            else:
                self.custom_list.add_item(
                    data['title'],
                    data,
                    item_pixmap=pixmap,
                    item_parent=folder_items[data['folder']]
                )

    def populate_image_list(self):
        """
        Method that uses the data contained in the image table of the database to create QTreeWidgetItems in the
        image widget's QTreeWidget.
        """
        self.image_list.clear()
        all_images = self.gui.main.get_all_images()
        all_folders = self.gui.main.get_folders('images')

        # first, create the folders the image slides belong to
        folder_items = {}
        for folder in all_folders:
            folder_items[folder] = self.image_list.add_folder(name=folder, from_populate=True)

        # then, add the image slides, putting them under their folder, if applicable
        for data in all_images:
            if self.gui.main.initial_startup:
                self.gui.main.update_status_signal.emit(f'Loading Images - {data['title']}', 'info')

            data['use_footer'] = False
            pixmap = data['background'].scaledToHeight(20, Qt.TransformationMode.SmoothTransformation)

            if not 'folder' in data.keys() or data['folder'].strip() == '':
                self.image_list.add_item(data['title'], data, item_pixmap=pixmap)
            else:
                self.image_list.add_item(
                    data['title'],
                    data,
                    item_pixmap=pixmap,
                    item_parent=folder_items[data['folder']]
                )

    def populate_video_list(self):
        """
        Method that polls the files contained in the video subdirectory of the data directory to create QListWidgetItems
        in the video widget's QListWidget.
        """
        self.video_list.clear()
        all_videos = self.gui.main.get_all_videos()
        all_folders = self.gui.main.get_folders('videos')

        # first, create the folders the image slides belong to
        folder_items = {}
        for folder in all_folders:
            folder_items[folder] = self.video_list.add_folder(name=folder, from_populate=True)

        # then, add the image slides, putting them under their folder, if applicable
        for data in all_videos:
            if self.gui.main.initial_startup:
                self.gui.main.update_status_signal.emit(f'Loading Videos - {data['title']}', 'info')

            pixmap = data['background'].scaledToHeight(20, Qt.TransformationMode.SmoothTransformation)

            if not 'folder' in data.keys() or data['folder'].strip() == '':
                self.video_list.add_item(data['title'], data, item_pixmap=pixmap)
            else:
                self.video_list.add_item(
                    data['title'],
                    data,
                    item_pixmap=pixmap,
                    item_parent=folder_items[data['folder']]
                )

    def populate_web_list(self):
        """
        Method that uses the data contained in the web table of the database to create QListWidgetItems in the
        web widget's QListWidget.
        """
        self.web_list.clear()
        all_web = self.gui.main.get_all_web()
        all_folders = self.gui.main.get_folders('web')

        # first, create the folders the image slides belong to
        folder_items = {}
        for folder in all_folders:
            folder_items[folder] = self.web_list.add_folder(name=folder, from_populate=True)
        print(folder_items)

        # then, add the image slides, putting them under their folder, if applicable
        for data in all_web:
            if self.gui.main.initial_startup:
                self.gui.main.update_status_signal.emit(f'Loading Websites - {data['title']}', 'info')

            pixmap = QPixmap('resources/gui_icons/web_icon.svg')
            pixmap = pixmap.scaledToHeight(20, Qt.TransformationMode.SmoothTransformation)

            if not 'folder' in data.keys() or data['folder'].strip() == '':
                self.web_list.add_item(data['title'], data, item_pixmap=pixmap)
            else:
                self.web_list.add_item(
                    data['title'],
                    data,
                    item_pixmap=pixmap,
                    item_parent=folder_items[data['folder']]
                )

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

            if not self.formatted_reference:
                self.formatted_reference = self.passages[0] + ' ' + reference_split[1]

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
        song_data = SLIDE_DATA_DEFAULTS
        song_data['type'] = type
        self.gui.edit_widget = EditWidget(self.gui, song_data, type)

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
                # first, copy the user's file to the ProjectOn data/images folder
                simple_splash = SimpleSplash(self.gui, 'Importing image, please wait...')

                file_name_split = result[0].split('/')
                file_name = file_name_split[len(file_name_split) - 1]
                shutil.copy(result[0], self.gui.main.image_dir + '/' + file_name)

                # create the thumbnail and data for saving to the database
                pixmap = QPixmap(self.gui.main.image_dir + '/' + file_name)
                pixmap = pixmap.scaled(
                    96,
                    54,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

                data = SLIDE_DATA_DEFAULTS.copy()
                data['type'] = 'image'
                data['title'] = file_name
                data['background'] = pixmap
                data['folder'] = ''
                self.gui.main.save_image(data)

                # create the new image item in the image_list
                pixmap = data['background'].scaledToHeight(20, Qt.TransformationMode.SmoothTransformation)
                item = self.image_list.add_item(data['title'], data, item_pixmap=pixmap)
                self.image_list.setCurrentItem(item)
                self.image_list.scrollToItem(item)

                simple_splash.widget.deleteLater()
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
            simple_splash = SimpleSplash(self.gui, 'Removing image, please wait...')

            try:
                os.remove(self.gui.main.image_dir + '/' + file_name)
            except FileNotFoundError:
                QMessageBox.information(
                    self.gui.main_window,
                    'Not Found',
                    'File not found. Reindexing images.',
                    QMessageBox.StandardButton.Ok
                )

            from core.runnables import IndexImages
            ii = IndexImages(self.gui.main, 'images')
            self.gui.main.thread_pool.start(ii)
            self.gui.main.thread_pool.waitForDone()
            self.populate_image_list()
            self.image_list.update()

            simple_splash.widget.deleteLater()

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
            title = title_line_edit.text().strip()
            url = url_line_edit.text().strip()
            self.save_web(title, url)

    def save_web(self, title, url, old_title=None):
        message = None
        if len(title) == 0:
            message = 'Title is required to save a web item. Please try again.'
        elif len(url) == 0:
            message = 'URL is required to save a web item. Please try again.'
        if message:
            QMessageBox.information(
                self.gui.main_window,
                'Info Missing',
                message
            )
            return

        data = SLIDE_DATA_DEFAULTS.copy()
        data['type'] = 'web'
        data['title'] = title
        data['url'] = url
        if old_title:
            self.gui.main.save_web_item(data, old_title)
        else:
            self.gui.main.save_web_item(data)
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
            wait_widget = SimpleSplash(self.gui, 'Importing video, please wait...')

            file_name_split = result[0].split('/')
            file_name = file_name_split[len(file_name_split) - 1]
            shutil.copy(result[0], self.gui.main.video_dir + '/' + file_name)

            try:
                wait_widget.label.setText('Getting thumbnails, please wait...')
                wait_widget.widget.adjustSize()
                QApplication.processEvents()
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
            data = self.song_list.currentItem().data(0, Qt.ItemDataRole.UserRole).copy()
            item = QListWidgetItem(data['title'])
            item.setData(Qt.ItemDataRole.UserRole, data)

        if item and not from_load_service:
            # Create a thumbnail of either the global song background or the custom background associated with this song
            data = item.data(Qt.ItemDataRole.UserRole)
            if (not data['background']
                    or data['background'] == 'False'
                    or data['background'] == 'global_song'):
                pixmap = self.gui.global_song_background_pixmap
                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            elif data['background'] == 'global_bible':
                pixmap = self.gui.global_bible_background_pixmap
                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            elif 'rgb(' in data['background']:
                pixmap = QPixmap(50, 27)
                painter = QPainter(pixmap)
                rgb = data['background'].replace('rgb(', '')
                rgb = rgb.replace(')', '')
                rgb_split = rgb.split(',')
                brush = QBrush(QColor.fromRgb(
                    int(rgb_split[0].strip()), int(rgb_split[1].strip()), int(rgb_split[2].strip())))
                painter.setBrush(brush)
                painter.fillRect(pixmap.rect(), brush)
                painter.end()
            else:
                pixmap = QPixmap(self.gui.main.background_dir + '/' + data['background'])
                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

            widget = StandardItemWidget(self.gui, data['title'], 'Song', pixmap)

            item.setSizeHint(widget.sizeHint())
            if not row:
                self.gui.oos_widget.oos_list_widget.addItem(item)
            else:
                self.gui.oos_widget.oos_list_widget.insertItem(row, item)
            self.gui.oos_widget.oos_list_widget.setItemWidget(item, widget)
            self.gui.oos_widget.oos_list_widget.scrollToItem(item)
            self.gui.oos_widget.oos_list_widget.setCurrentItem(item)
            self.gui.changes = True

        if item and from_load_service:
            # handle this differently if it's being created while loading a service file
            data = item.data(Qt.ItemDataRole.UserRole).copy()
            widget_item = QListWidgetItem(data['title'])
            widget_item.setData(Qt.ItemDataRole.UserRole, data)

            if (data['override_global'] == 'False'
                or not data['background']
                or data['background'] == 'False'
                or data['background'] == 'global_song'):
                pixmap = self.gui.global_song_background_pixmap
                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
            elif data['background'] == 'global_bible':
                pixmap = self.gui.global_bible_background_pixmap
                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
            elif 'rgb(' in data['background']:
                pixmap = QPixmap(50, 27)
                painter = QPainter(pixmap)
                brush = QBrush(QColor(data['background']))
                painter.setBrush(brush)
                painter.fillRect(pixmap.rect(), brush)
                painter.end()
            else:
                pixmap = QPixmap(self.gui.main.background_dir + '/' + data['background'])
                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)

            widget = StandardItemWidget(self.gui, data['title'], 'Song', pixmap)

            widget_item.setSizeHint(widget.sizeHint())
            self.gui.oos_widget.oos_list_widget.addItem(widget_item)
            self.gui.oos_widget.oos_list_widget.setItemWidget(widget_item, widget)
            self.gui.oos_widget.oos_list_widget.scrollToItem(item)
            self.gui.oos_widget.oos_list_widget.setCurrentItem(item)

    def add_scripture_to_service(self):
        """
        Method to add the scripture passage contained in the bible widget's scripture_text_edit to the order of
        service's QListWidget
        :return: None
        """
        if not self.formatted_reference:
            return

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
            data = self.custom_list.currentItem().data(0, Qt.ItemDataRole.UserRole)
            item = QListWidgetItem(data['title'])
            item.setData(Qt.ItemDataRole.UserRole, data)
        elif not item and not self.custom_list.currentItem():
            return
        else:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            item.setData(Qt.ItemDataRole.DisplayRole, data['title'])

        if data['override_global'] == 'False' or not data['background']:
            pixmap = self.gui.global_bible_background_pixmap
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        elif data['background'] == 'global_song':
            pixmap = self.gui.global_song_background_pixmap
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        elif data['background'] == 'global_bible':
            pixmap = self.gui.global_bible_background_pixmap
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        elif 'rgb(' in data['background']:
            pixmap = QPixmap(50, 27)
            painter = QPainter(pixmap)
            brush = QBrush(QColor(data['background']))
            painter.fillRect(pixmap.rect(), brush)
            painter.end()
        else:
            pixmap = QPixmap(self.gui.main.background_dir + '/' + data['background'])
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

        widget = StandardItemWidget(self.gui, data['title'], 'Custom Slide', pixmap)
        item.setSizeHint(widget.sizeHint())
        if not row:
            self.gui.oos_widget.oos_list_widget.addItem(item)
        else:
            self.gui.oos_widget.oos_list_widget.insertItem(row, item)
        self.gui.oos_widget.oos_list_widget.setItemWidget(item, widget)
        self.gui.oos_widget.oos_list_widget.scrollToItem(item)
        self.gui.oos_widget.oos_list_widget.setCurrentItem(item)
        self.gui.changes = True

    def add_image_to_service(self, item=None, row=None):
        """
        Method to add an image QListWidgetItem to the order of service's QListWidget
        :param QListWidgetItem item: Optional: a specific image item
        :param int row: Optional: a specific row of the image widget's QListWidget
        """
        add_item = False
        if not self.image_list.currentItem():
            return

        data = self.image_list.currentItem().data(0, Qt.ItemDataRole.UserRole).copy()
        if not item:
            item = QListWidgetItem(data['title'])
            add_item = True

        item.setData(Qt.ItemDataRole.UserRole, data)

        pixmap = data['background']
        pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        widget = StandardItemWidget(self.gui, data['title'], 'Image', pixmap)

        item.setSizeHint(widget.sizeHint())
        if add_item:
            self.gui.oos_widget.oos_list_widget.addItem(item)
        else:
            self.gui.oos_widget.oos_list_widget.insertItem(row, item)
        self.gui.oos_widget.oos_list_widget.setItemWidget(item, widget)
        self.gui.oos_widget.oos_list_widget.scrollToItem(item)
        self.gui.oos_widget.oos_list_widget.setCurrentItem(item)
        self.gui.changes = True

    def add_video_to_service(self, item=None, row=None):
        """
        Method to add a video QListWidgetItem to the order of service's QListWidget
        :param QListWidgetItem item: Optional: a specific video item
        :param int row: Optional: a specific row of the video widget's QListWidget
        """
        add_item = False
        if not self.video_list.currentItem():
            return

        if not item:
            item = QListWidgetItem()
            add_item = True
        slide_data = self.video_list.currentItem().data(0, Qt.ItemDataRole.UserRole).copy()
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
        self.gui.oos_widget.oos_list_widget.scrollToItem(item)
        self.gui.oos_widget.oos_list_widget.setCurrentItem(item)
        self.gui.changes = True

    def add_web_to_service(self, item=None, row=None):
        """
        Method to add a web QListWidgetItem to the order of service's QListWidget
        :param QListWidgetItem item: Optional: a specific web item
        :param int row: Optional: a specific row of the web widget's QListWidget
        """
        add_item = False
        if not self.web_list.currentItem():
            return

        if not item:
            item = QListWidgetItem()
            add_item = True
        item.setData(Qt.ItemDataRole.UserRole, self.web_list.currentItem().data(0, Qt.ItemDataRole.UserRole).copy())

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
        self.gui.oos_widget.oos_list_widget.scrollToItem(item)
        self.gui.oos_widget.oos_list_widget.setCurrentItem(item)
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
        elif self.type == 'web':
            edit_action = QAction('Edit Web Item')

        if edit_action:
            if self.type == 'web':
                edit_action.triggered.connect(self.edit_web)
            else:
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
            self.gui.send_to_preview(self.currentItem())

    def edit_song(self):
        """
        Method to create a EditWidget for a song or custom slide.
        """

        if self.itemAt(self.item_pos):
            data = self.itemAt(self.item_pos).data(Qt.ItemDataRole.UserRole)
            if data['type'] == 'song':
                self.gui.edit_widget = EditWidget(self.gui, data, 'song')
            elif data['type'] == 'custom':
                self.gui.edit_widget = EditWidget(self.gui, data, 'custom')

    def edit_web(self):
        if self.itemAt(self.item_pos):
            data = self.itemAt(self.item_pos).data(Qt.ItemDataRole.UserRole)
            dialog = QDialog(self.gui.main_window)
            dialog.setMinimumWidth(500)
            dialog.setWindowTitle('Edit Web Item')
            dialog.setWindowIcon(QIcon('resources/branding/logo.svg'))
            layout = QVBoxLayout(dialog)
            layout.setSpacing(0)

            layout.addSpacing(20)
            title_label = QLabel('Title')
            title_label.setFont(self.gui.bold_font)
            layout.addWidget(title_label)

            title_line_edit = QLineEdit(data['title'])
            title_line_edit.setFont(self.gui.standard_font)
            layout.addWidget(title_line_edit)
            layout.addSpacing(20)

            url_label = QLabel('URL')
            url_label.setFont(self.gui.bold_font)
            layout.addWidget(url_label)

            url_line_edit = QLineEdit(data['url'])
            url_line_edit.setFont(self.gui.standard_font)
            layout.addWidget(url_line_edit)
            layout.addSpacing(20)

            button_widget = QWidget()
            layout.addWidget(button_widget)
            button_layout = QHBoxLayout(button_widget)

            ok_button = QPushButton('Save')
            ok_button.setFont(self.gui.standard_font)
            ok_button.pressed.connect(lambda: dialog.done(1))
            button_layout.addStretch()
            button_layout.addWidget(ok_button)

            cancel_button = QPushButton('Cancel')
            cancel_button.setFont(self.gui.standard_font)
            cancel_button.pressed.connect(lambda: dialog.done(-1))
            button_layout.addWidget(cancel_button)
            button_layout.addStretch()

            result = dialog.exec()
            if result == 1:
                self.gui.main.save_web_item(title_line_edit.text(), url_line_edit.text())
                self.gui.media_widget.populate_web_list()

    def delete_item(self):
        """
        Method to remove an item from this widget. Creates a QMessageBox to confirm removal.
        """
        if not self.currentItem():
            return

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

            QMessageBox.information(
                self.gui.main_window,
                'Removed',
                self.currentItem().data(Qt.ItemDataRole.UserRole)['title'] + ' has been removed.',
                QMessageBox.StandardButton.Ok
            )

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