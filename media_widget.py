import os
import re
import shutil
import sqlite3
from os.path import exists
from xml.etree import ElementTree

from PyQt6.QtCore import Qt, QSize, QPoint, QEvent
from PyQt6.QtGui import QCursor, QPixmap, QIcon, QFont, QPainter, QBrush, QColor, QPen, QAction
from PyQt6.QtWidgets import QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, \
    QListWidgetItem, QMenu, QComboBox, QTextEdit, QAbstractItemView, QDialog, QFileDialog, QMessageBox, \
    QGridLayout, QStyleOption, QStyle

from edit_widget import EditWidget
from get_scripture import GetScripture
from widgets import AutoSelectLineEdit, StandardItemWidget


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
        self.setStyleSheet(
            'QTabBar:tab { background: lightGrey; border: 1px solid black; border-top-left-radius: 5px; '
            'border-top-right-radius: 5px; padding: 5px; }'
            'QTabBar:tab:selected { background: white; border: 1px solid black; padding: 5px; }'
            'QTabBar:tab:hover { background: white; border: 1px solid black; padding: 5px; }'
            '#media_widget::pane { border: 2px solid black; }'
        )
        self.setTabShape(QTabWidget.TabShape.Rounded)

        self.formatted_reference = None

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
        song_widget.setObjectName('song_widget')
        song_layout = QVBoxLayout()
        song_widget.setLayout(song_layout)

        add_button = QPushButton()
        add_button.setIcon(QIcon('./resources/add_icon.svg'))
        add_button.setToolTip('Add a New Song')
        add_button.setIconSize(QSize(20, 20))
        add_button.setFixedSize(30, 30)
        add_button.pressed.connect(lambda: self.add_song('song'))
        song_layout.addWidget(add_button)

        search_widget = QWidget()
        search_layout = QHBoxLayout()
        search_widget.setLayout(search_layout)
        song_layout.addWidget(search_widget)

        search_label = QLabel('Search:')
        search_label.setFont(self.gui.standard_font)
        search_layout.addWidget(search_label)

        self.search_line_edit = AutoSelectLineEdit()
        self.search_line_edit.textChanged.connect(self.song_search)
        search_layout.addWidget(self.search_line_edit)

        clear_search_button = QPushButton()
        clear_search_button.setIcon(QIcon('./resources/x_icon.svg'))
        clear_search_button.setToolTip('Clear Song Search')
        clear_search_button.setIconSize(QSize(20, 20))
        clear_search_button.setFixedSize(30, 30)
        clear_search_button.pressed.connect(self.search_line_edit.clear)
        search_layout.addWidget(clear_search_button)

        button_widget = QWidget()
        button_widget.setLayout(QHBoxLayout())
        song_layout.addWidget(button_widget)

        add_to_service_button = QPushButton()
        add_to_service_button.setIcon(QIcon('./resources/add_to_service_icon.svg'))
        add_to_service_button.setToolTip('Add Song to Service')
        add_to_service_button.setIconSize(QSize(20, 20))
        add_to_service_button.setFixedSize(30, 30)
        add_to_service_button.pressed.connect(self.add_song_to_service)
        button_widget.layout().addWidget(add_to_service_button)
        button_widget.layout().addStretch()

        send_to_live_button = QPushButton()
        send_to_live_button.setIcon(QIcon('./resources/send_to_live_icon.svg'))
        send_to_live_button.setToolTip('Send Song to Live')
        send_to_live_button.setIconSize(QSize(20, 20))
        send_to_live_button.setFixedSize(30, 30)
        send_to_live_button.pressed.connect(self.send_to_live)
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
        scripture_widget.setObjectName('scripture_widget')
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
        default_bible_button.pressed.connect(self.set_default_bible)
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
        clear_search_button.setIcon(QIcon('./resources/x_icon.svg'))
        clear_search_button.setToolTip('Clear Passage Search')
        clear_search_button.setIconSize(QSize(20, 20))
        clear_search_button.setFixedSize(30, 30)
        clear_search_button.pressed.connect(self.bible_search_line_edit.clear)
        bible_search_layout.addWidget(clear_search_button)

        self.bible_search_status_label = QLabel()
        self.bible_search_status_label.setFont(QFont('Helvetica', 8))
        fm = bible_search_label.fontMetrics()
        label_width = fm.boundingRect('Enter Passage:').width()
        self.bible_search_status_label.setStyleSheet(
            'color: white; padding-left: ' + str(label_width + (bible_search_layout.spacing() * 2)) + 'px;')
        scripture_layout.addWidget(self.bible_search_status_label)

        button_widget = QWidget()
        button_layout = QHBoxLayout()
        button_widget.setLayout(button_layout)
        scripture_layout.addWidget(button_widget)

        self.add_to_service_button = QPushButton()
        self.add_to_service_button.setIcon(QIcon('./resources/add_to_service_icon.svg'))
        self.add_to_service_button.setToolTip('Add this Passage to the Service')
        self.add_to_service_button.setIconSize(QSize(20, 20))
        self.add_to_service_button.setFixedSize(30, 30)
        self.add_to_service_button.pressed.connect(self.add_scripture_to_service)
        button_layout.addWidget(self.add_to_service_button)
        button_layout.addStretch()

        self.send_to_live_button = QPushButton()
        self.send_to_live_button.setIcon(QIcon('./resources/send_to_live_icon.svg'))
        self.send_to_live_button.setToolTip('Send to Live')
        self.send_to_live_button.setIconSize(QSize(20, 20))
        self.send_to_live_button.setFixedSize(30, 30)
        self.send_to_live_button.pressed.connect(self.send_scripture_to_live)
        button_layout.addWidget(self.send_to_live_button)

        self.scripture_text_edit = QTextEdit()
        self.scripture_text_edit.setFont(self.gui.standard_font)
        scripture_layout.addWidget(self.scripture_text_edit)

        return scripture_widget

    def make_custom_tab(self):
        """
        Creates the custom slide widget to be used in the custom slide tab of this widget.
        :return QWidget: The custom slide widget
        """
        custom_widget = QWidget()
        custom_widget.setObjectName('custom_widget')
        custom_layout = QVBoxLayout()
        custom_widget.setLayout(custom_layout)

        add_custom_button = QPushButton()
        add_custom_button.setIcon(QIcon('./resources/add_icon.svg'))
        add_custom_button.setToolTip('Create a New Custom Slide')
        add_custom_button.setIconSize(QSize(20, 20))
        add_custom_button.setFixedSize(30, 30)
        add_custom_button.pressed.connect(lambda: self.add_song('custom'))
        custom_layout.addWidget(add_custom_button)

        button_widget = QWidget()
        button_widget.setLayout(QHBoxLayout())
        custom_layout.addWidget(button_widget)

        add_to_service_button = QPushButton()
        add_to_service_button.setIcon(QIcon('./resources/add_to_service_icon.svg'))
        add_to_service_button.setToolTip('Add Custom Slide to Service')
        add_to_service_button.setIconSize(QSize(20, 20))
        add_to_service_button.setFixedSize(30, 30)
        add_to_service_button.pressed.connect(self.add_custom_to_service)
        button_widget.layout().addWidget(add_to_service_button)
        button_widget.layout().addStretch()

        send_to_live_button = QPushButton()
        send_to_live_button.setIcon(QIcon('./resources/send_to_live_icon.svg'))
        send_to_live_button.setToolTip('Send Custom Slide to Live')
        send_to_live_button.setIconSize(QSize(20, 20))
        send_to_live_button.setFixedSize(30, 30)
        send_to_live_button.pressed.connect(self.send_to_live)
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
        image_widget.setObjectName('image_widget')
        image_layout = QVBoxLayout()
        image_widget.setLayout(image_layout)

        add_image_button = QPushButton()
        add_image_button.setIcon(QIcon('./resources/add_icon.svg'))
        add_image_button.setToolTip('Import an Image')
        add_image_button.setIconSize(QSize(20, 20))
        add_image_button.setFixedSize(30, 30)
        add_image_button.pressed.connect(self.add_image)
        image_layout.addWidget(add_image_button)

        button_widget = QWidget()
        button_widget.setLayout(QHBoxLayout())
        image_layout.addWidget(button_widget)

        add_to_service_button = QPushButton()
        add_to_service_button.setIcon(QIcon('./resources/add_to_service_icon.svg'))
        add_to_service_button.setToolTip('Add Image to Service')
        add_to_service_button.setIconSize(QSize(20, 20))
        add_to_service_button.setFixedSize(30, 30)
        add_to_service_button.pressed.connect(self.add_image_to_service)
        button_widget.layout().addWidget(add_to_service_button)
        button_widget.layout().addStretch()

        send_to_live_button = QPushButton()
        send_to_live_button.setIcon(QIcon('./resources/send_to_live_icon.svg'))
        send_to_live_button.setToolTip('Send Image to Live')
        send_to_live_button.setIconSize(QSize(20, 20))
        send_to_live_button.setFixedSize(30, 30)
        send_to_live_button.pressed.connect(self.send_to_live)
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
        video_widget.setObjectName('video_widget')
        video_layout = QVBoxLayout()
        video_widget.setLayout(video_layout)

        add_video_button = QPushButton()
        add_video_button.setIcon(QIcon('./resources/add_icon.svg'))
        add_video_button.setToolTip('Import a Video')
        add_video_button.setIconSize(QSize(20, 20))
        add_video_button.setFixedSize(30, 30)
        add_video_button.pressed.connect(self.add_video)
        video_layout.addWidget(add_video_button)

        button_widget = QWidget()
        button_widget.setLayout(QHBoxLayout())
        video_layout.addWidget(button_widget)

        add_to_service_button = QPushButton()
        add_to_service_button.setIcon(QIcon('./resources/add_to_service_icon.svg'))
        add_to_service_button.setToolTip('Add Video to Service')
        add_to_service_button.setIconSize(QSize(20, 20))
        add_to_service_button.setFixedSize(30, 30)
        add_to_service_button.pressed.connect(self.add_video_to_service)
        button_widget.layout().addWidget(add_to_service_button)
        button_widget.layout().addStretch()

        send_to_live_button = QPushButton()
        send_to_live_button.setIcon(QIcon('./resources/send_to_live_icon.svg'))
        send_to_live_button.setToolTip('Send Video to Live')
        send_to_live_button.setIconSize(QSize(20, 20))
        send_to_live_button.setFixedSize(30, 30)
        send_to_live_button.pressed.connect(self.send_to_live)
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
        web_widget.setObjectName('web_widget')
        web_layout = QVBoxLayout()
        web_widget.setLayout(web_layout)

        add_web_button = QPushButton()
        add_web_button.setIcon(QIcon('./resources/add_icon.svg'))
        add_web_button.setToolTip('Create a New Web Slide')
        add_web_button.setIconSize(QSize(20, 20))
        add_web_button.setFixedSize(30, 30)
        add_web_button.pressed.connect(self.add_web)
        web_layout.addWidget(add_web_button)

        button_widget = QWidget()
        button_widget.setLayout(QHBoxLayout())
        web_layout.addWidget(button_widget)

        add_to_service_button = QPushButton()
        add_to_service_button.setIcon(QIcon('./resources/add_to_service_icon.svg'))
        add_to_service_button.setToolTip('Add Web Page to Service')
        add_to_service_button.setIconSize(QSize(20, 20))
        add_to_service_button.setFixedSize(30, 30)
        add_to_service_button.pressed.connect(self.add_web_to_service)
        button_widget.layout().addWidget(add_to_service_button)
        button_widget.layout().addStretch()

        send_to_live_button = QPushButton()
        send_to_live_button.setIcon(QIcon('./resources/send_to_live_icon.svg'))
        send_to_live_button.setToolTip('Send Video to Live')
        send_to_live_button.setIconSize(QSize(20, 20))
        send_to_live_button.setFixedSize(30, 30)
        send_to_live_button.pressed.connect(self.send_to_live)
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
        search_string = self.search_line_edit.text().lower()

        for i in reversed(range(self.song_list.count())):
            if self.song_list.item(i):
                self.song_list.item(i).setHidden(False)
                song_title = self.song_list.item(i).text().lower()
                if search_string not in song_title:
                    self.song_list.item(i).setHidden(True)

    def populate_song_list(self):
        """
        Method that uses the data contained in the song table of the database to fill the song widget's QListWidget
        with all of the songs.
        """
        self.song_list.clear()
        songs = self.gui.main.get_all_songs()
        if len(songs) > 0:
            for item in songs:
                if self.gui.main.initial_startup:
                    self.gui.main.update_status_signal.emit('Loading Songs - ' + item[0], 'info')
                list_item = QListWidgetItem(item[0])
                for i in range(len(item)):
                    list_item.setData(i + 20, item[i])
                list_item.setData(24, self.gui.format_display_lyrics(list_item.data(24)))
                list_item.setData(40, 'song')

                self.song_list.addItem(list_item)
        """
        data 20: Title
        data 21: Author
        data 22: Copyright
        data 23: CCLI Song Num
        data 24: Lyrics (with <br />)
        data 25: Verse Order
        data 26: Footer (bool)
        data 27: Font (global or name)
        data 28: Font Color (global or color)
        data 29: Background (with file type ending)
        data 30: Font Size
        data 31: Use Shadow
        data 32: Shadow Color
        data 33: Shadow Offset
        data 34: Use Outline
        data 35: Outline Color
        data 36: Outline Width
        data 37: Override Global
        data 40: Type
        """

    def parse_song_data(self, item):
        """
        Method that takes the raw song lyric data associated with this song and parses it into individual sections,
        based on verse/chorus/etc tags or blank lines.
        :param QListWidgetItem item: The item containing the song data
        :return list of str segments: The song's individual segments
        """
        self.lyric_dictionary = item.data(24)
        segments = []

        if len(item.data(25)) > 0:
            song_order = item.data(25)
            if ',' in song_order:
                song_order = song_order.replace(', ', ' ')
                song_order = song_order.replace(',', ' ')
            song_order = re.sub(' +', ' ', song_order)
            iterable = song_order.split(' ')
            for i in range(len(iterable)):
                iterable[i] = '[' + iterable[i] + ']'
        else:
            iterable = self.lyric_dictionary

        for segment in iterable:
            item_num = [i for i in segment if i.isdigit()]

            if 'v' in segment:
                segment_title = 'Verse ' + ''.join(item_num)
            elif 'c' in segment:
                segment_title = 'Chorus ' + ''.join(item_num)
            elif 'p' in segment:
                segment_title = 'Pre-Chorus ' + ''.join(item_num)
            elif 'b' in segment:
                segment_title = 'Bridge ' + ''.join(item_num)
            elif 't' in segment:
                segment_title = 'Tag ' + ''.join(item_num)
            else:
                segment_title = 'Ending ' + ''.join(item_num)

            try:
                segment_text = self.lyric_dictionary[segment].rstrip()
                segment_text = re.sub('<p.*?>', '', segment_text)
                segment_text = segment_text.replace('</p>', '')
            except Exception:
                segment_text = ''
                pass

            if segment_text.startswith('<br />'):
                segment_text = segment_text[6:]
            if segment_text.endswith('<br />'):
                segment_text = segment_text[:len(segment_text) - 6]

            segment_text = segment_text.replace('\n', '<br />')
            segment_text = segment_text.replace('&quot;', '"')

            if 'span' in segment_text and 'italic' in segment_text:
                italicized_text = re.findall('<span style=" font-style:italic;">.*?</span>', segment_text)
                for text in italicized_text:
                    new_text = re.sub('<span.*?italic.*?>', '<i>', text)
                    new_text = re.sub('</span>', '</i>', new_text)
                    segment_text = segment_text.replace(text, new_text)

            if 'span' in segment_text and 'font-weight' in segment_text:
                bold_text = re.findall('<span style=" font-weight:700;">.*?</span>', segment_text)
                for text in bold_text:
                    new_text = re.sub('<span.*?font-weight.*?>', '<b>', text)
                    new_text = re.sub('</span>', '</b>', new_text)
                    segment_text = segment_text.replace(text, new_text)

            if 'span' in segment_text and 'text-decoration' in segment_text:
                underline_text = re.findall('<span.*?text-decoration.*?5px;">.*?</span>', segment_text)
                for text in underline_text:
                    new_text = re.sub('<span.*?text-decoration.*?>', '<u>', text)
                    new_text = re.sub('</span>', '</u>', new_text)
                    segment_text = segment_text.replace(text, new_text)

            # set the font, using the song's font data if override_global is True
            if item.data(37) == 'True':
                font_face = item.data(27)
                font_size = int(item.data(30))
                font_color = item.data(28)
                use_shadow = False
                if item.data(31) == 'True':
                    use_shadow = True
                if item.data(32) and not item.data(32) == 'None':
                    shadow_color = int(item.data(32))
                else:
                    shadow_color = self.gui.main.settings['shadow_color']
                if item.data(33) and not item.data(33) == 'None':
                    shadow_offset = int(item.data(33))
                else:
                    shadow_offset = self.gui.main.settings['shadow_offset']
                use_outline = False
                if item.data(34) == 'True':
                    use_outline = True
                if item.data(35) and not item.data(35) == 'None':
                    outline_color = int(item.data(35))
                else:
                    outline_color = self.gui.main.settings['outline_color']
                if item.data(36) and not item.data(36) == 'None':
                    outline_width = int(item.data(36))
                else:
                    outline_width = self.gui.main.settings['outline_width']
            else:
                font_face = self.gui.main.settings['font_face']
                font_size = self.gui.main.settings['font_size']
                font_color = self.gui.main.settings['font_color']
                use_shadow = self.gui.main.settings['use_shadow']
                shadow_color = self.gui.main.settings['shadow_color']
                shadow_offset = self.gui.main.settings['shadow_offset']
                use_outline = self.gui.main.settings['use_outline']
                outline_color = self.gui.main.settings['outline_color']
                outline_width = self.gui.main.settings['outline_width']

            lyric_widget = self.gui.sample_lyric_widget

            lyric_widget.setFont(QFont(font_face, font_size, QFont.Weight.Bold))
            lyric_widget.footer_label.setFont(QFont(font_face, self.gui.global_footer_font_size))
            lyric_widget.use_shadow = use_shadow
            lyric_widget.shadow_color = QColor(shadow_color, shadow_color, shadow_color)
            lyric_widget.shadow_offset = shadow_offset
            lyric_widget.use_outline = use_outline
            lyric_widget.outline_color = QColor(outline_color, outline_color, outline_color)
            lyric_widget.outline_width = outline_width

            segment_text = '<p style="text-align: center; line-height: 120%;">' + segment_text + '</p>'

            segment_text = re.sub('<span.*?>', '', segment_text)
            segment_text = re.sub('</span>', '', segment_text)
            self.gui.sample_lyric_widget.setText(segment_text)

            segment_count = 1

            footer_text = ''
            if item.data(26) and item.data(26) == 'true':
                if len(item.data(21)) > 0:
                    footer_text += item.data(21)
                if len(item.data(22)) > 0:
                    footer_text += '\n\u00A9' + item.data(22).replace('\n', ' ')
                if len(item.data(23)) > 0:
                    footer_text += '\nCCLI Song #: ' + item.data(23)
                if len(self.gui.main.settings['ccli_num']) > 0:
                    footer_text += '\nCCLI License #: ' + self.gui.main.settings['ccli_num']
                self.gui.sample_lyric_widget.footer_label.setText(footer_text)

            if len(self.gui.sample_lyric_widget.footer_label.text()) > 0:
                footer_height = self.gui.sample_lyric_widget.footer_label.height()
            else:
                footer_height = 0
            self.gui.sample_lyric_widget.paint_text()
            lyric_widget_height = self.gui.sample_lyric_widget.path.boundingRect().height()
            secondary_screen_height = self.gui.secondary_screen.size().height()
            preferred_height = secondary_screen_height - footer_height

            if lyric_widget_height > preferred_height:
                segment_text_split = re.split('<br.*?/>', segment_text)
                half_lines = int(len(segment_text_split) / 2)

                halves = [[], []]
                for i in range(half_lines):
                    halves[0].append(segment_text_split[i])

                for i in range(half_lines, len(segment_text_split)):
                    halves[1].append(segment_text_split[i])

                half_num = 1
                for half in halves:
                    text = '<br />'.join(half)

                    if text.startswith('<p'):
                        text = text + '</p>'
                    else:
                        text = '<p style="text-align: center; line-height: 120%;">' + text

                    segment_count += 1

                    if '</b>' in text and '<b>' not in text:
                        text = '<b>' + text
                    if '</i>' in text and '<i>' not in text:
                        text = '<i>' + text
                    if '</u>' in text and '<u>' not in text:
                        text = '<u>' + text

                    if '<b>' in text and '</b>' not in text:
                        text = text + '</b>'
                    if '<i>' in text and '</i>' not in text:
                        text = text + '</i>'
                    if '<u>' in text and '</u>' not in text:
                        text = text + '</u>'

                    segments.append([segment, segment_title + ' - ' + str(half_num), text])
                    half_num += 1
            else:
                segments.append([segment, segment_title, segment_text])

        return segments

    def populate_custom_list(self):
        """
        Method that uses the data contained in the custom slide table of the database to create QListWidgetItems in the
        custom slide widget's QListWidget.
        """
        self.custom_list.clear()
        slides = self.gui.main.get_all_custom_slides()
        if len(slides) > 0:
            for item in slides:
                text = item[1]
                text = re.sub('<p.*?>', '', text)
                text = text.replace('</p>', '')

                if text.startswith('<br />'):
                    text = text[6:]
                if text.endswith('<br />'):
                    text = text[:len(text) - 6]

                text = text.replace('\n', '<br />')
                text = '<p style="text-align: center; line-height: 120%;">' + text + '</p>'

                widget_item = QListWidgetItem(item[0])
                widget_item.setData(20, item[0])
                widget_item.setData(21, text)

                for i in range(2, 13):
                    widget_item.setData(25 + i, item[i])
                widget_item.setData(40, 'custom')

                widget_item.setData(24, ['', item[0], text])
                self.custom_list.addItem(widget_item)

        """
        data 20: title
        data 21: text
        data 27: Font (global or name)
        data 28: Font Color (global or color)
        data 29: Background (with file type ending)
        data 30: Font Size
        data 31: Use Shadow
        data 32: Shadow Color
        data 33: Shadow Offset
        data 34: Use Outline
        data 35: Outline Color
        data 36: Outline Width
        data 37: Override Global
        data 40: Type
        """

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
            thumbnails = cursor.execute('SELECT * FROM imageThumbnails ORDER BY fileName').fetchall()

            for record in thumbnails:
                pixmap = QPixmap()
                pixmap.loadFromData(record[1])

                widget = StandardItemWidget(self.gui, record[0], '', pixmap)

                item = QListWidgetItem()
                item.setData(20, record[0])
                item.setData(21, record[1])
                item.setData(40, 'image')
                item.setData(24, ['', record[0], record[1]])
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

                        item = QListWidgetItem()
                        item.setData(20, video_file)
                        item.setData(40, 'video')
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
                    item = QListWidgetItem()
                    item.setData(20, record[0])
                    item.setData(21, record[1])
                    item.setData(40, 'web')
                    item.setData(24, ['', record[0], record[1]])

                    widget = StandardItemWidget(self.gui, record[0], record[1])

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
            return (bibles)
        except Exception:
            self.gui.main.error_log()
            return -1

    def get_scripture(self):
        """
        Method that retrieves the text in the bible widget's bible_search_line_edit and runs it through GetScripture,
        placing the results in the scripture_text_edit of the bible widget.
        """
        self.passages = None
        text = self.bible_search_line_edit.text()

        # if the current changes means that the line edit is empty, also clear the scripture text edit
        if text == '':
            self.scripture_text_edit.clear()
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
                if ':' in reference_split[i]:
                    self.formatted_reference = self.passages[0] + ' ' + reference_split[i]

            scripture = ''
            for passage in self.passages[1]:
                scripture += passage[0] + ' ' + passage[1] + ' '

            self.scripture_text_edit.setText(scripture.strip())

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

    def add_scripture_to_service(self):
        """
        Method to add the scripture passage contained in the bible widget's scripture_text_edit to the order of
        service's QListWidget
        :return:
        """
        if self.formatted_reference:
            reference = self.formatted_reference
            version = self.bible_selector_combobox.currentText()
            self.gui.add_scripture_item(reference, self.passages[1], version)
            self.formatted_reference = None
            self.gui.changes = True

    def send_scripture_to_live(self):
        """
        Method to send the scripture passage contained in the bible widget's scripture_text_edit directly to
        live without adding it to the order of service.
        """
        if self.formatted_reference:
            reference = self.formatted_reference
            version = self.bible_selector_combobox.currentText()

            item = QListWidgetItem()
            item.setData(20, reference)
            item.setData(21, self.gui.parse_scripture_by_verse(self.passages[1]))
            item.setData(23, version)
            item.setData(40, 'bible')
            item.setData(24, ['', reference, self.passages[1]])

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

                from main import IndexImages
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
        file_name = self.image_list.currentItem().data(20)
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

            from main import IndexImages
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
        ok_button.pressed.connect(lambda: web_dialog.done(0))
        ok_button.setFont(self.gui.standard_font)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addSpacing(20)

        cancel_button = QPushButton('Cancel')
        cancel_button.pressed.connect(lambda: web_dialog.done(1))
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
            file_name_split = result[0].split('/')
            file_name = file_name_split[len(file_name_split) - 1]
            shutil.copy(result[0], self.gui.main.video_dir + '/' + file_name)

            try:
                import cv2
                cap = cv2.VideoCapture(self.gui.main.video_dir + '/' + file_name)
                iteration = 0
                while True:
                    result, frame = cap.read()
                    if iteration % 50 == 0 and iteration <= 250:
                        if result:
                            cv2.imwrite(f'./thumbnail{str(iteration)}.jpg', frame)
                        else:
                            break
                    iteration += 1
                    if iteration > 250:
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
                    lambda: self.copy_video(file_name, thumbnail_list.currentItem().data(20), thumbnail_widget))
                thumbnail_layout.addWidget(thumbnail_list)

                file_list = os.listdir('./')
                for file in file_list:
                    if file.startswith('thumbnail'):
                        pixmap = QPixmap('./' + file)
                        pixmap = pixmap.scaled(96, 54, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

                        widget = StandardItemWidget(
                            self.gui, 'Frame ' + file.split('.')[0].replace('thumbnail', ''), '', pixmap)

                        item = QListWidgetItem()
                        item.setData(20, file)
                        item.setSizeHint(widget.sizeHint())
                        thumbnail_list.addItem(item)
                        thumbnail_list.setItemWidget(item, widget)

                thumbnail_widget.exec()

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
            shutil.copy('./' + image_file, self.gui.main.video_dir + '/' + new_image_file_name)
            file_list = os.listdir('./')
            for file in file_list:
                if file.startswith('thumbnail'):
                    os.remove('./' + file)
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
            for i in range(20, 41):
                item.setData(i, self.song_list.currentItem().data(i))

        if item and not from_load_service:
            item.setText(None)
            #item.setData(24, self.parse_song_data(item))

            # Create a thumbnail of either the global song background or the custom background associated with this song
            if item.data(29) == 'global_song':
                pixmap = self.gui.global_song_background_pixmap
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

            widget = StandardItemWidget(self.gui, item.data(20), 'Song', pixmap)

            item.setSizeHint(widget.sizeHint())
            if not row:
                self.gui.oos_widget.oos_list_widget.addItem(item)
            else:
                self.gui.oos_widget.oos_list_widget.insertItem(row, item)
            self.gui.oos_widget.oos_list_widget.setItemWidget(item, widget)
            self.gui.changes = True
        else:
            # handle this differently if it's being created while loading a service file
            widget_item = QListWidgetItem()
            for i in range(20, 41):
                widget_item.setData(i, item.data(i))
            widget_item.setData(24, self.parse_song_data(item))

            if widget_item.data(29) == 'global_song':
                pixmap = self.gui.global_song_background_pixmap
                pixmap = pixmap.scaled(
                    50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
            elif widget_item.data(29) == 'global_bible':
                pixmap = self.gui.global_bible_background_pixmap
                pixmap = pixmap.scaled(
                    50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
            elif 'rgb(' in widget_item.data(29):
                pixmap = QPixmap(50, 27)
                painter = QPainter(pixmap)
                brush = QBrush(QColor(widget_item.data(29)))
                painter.setBrush(brush)
                painter.fillRect(pixmap.rect(), brush)
                painter.end()
            else:
                pixmap = QPixmap(self.gui.main.background_dir + '/' + widget_item.data(29))
                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)

            widget = StandardItemWidget(self.gui, item.data(20), 'Song', pixmap)

            widget_item.setSizeHint(widget.sizeHint())
            self.gui.oos_widget.oos_list_widget.addItem(widget_item)
            self.gui.oos_widget.oos_list_widget.setItemWidget(widget_item, widget)

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

            for i in range(20, 41):
                item.setData(i, self.image_list.currentItem().data(i))

            pixmap = QPixmap()
            pixmap.loadFromData(self.image_list.currentItem().data(21), 'JPG')
            pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)

            widget = StandardItemWidget(self.gui, item.data(20), 'Image', pixmap)

            item.setSizeHint(widget.sizeHint())
            if add_item:
                self.gui.oos_widget.oos_list_widget.addItem(item)
            else:
                self.gui.oos_widget.oos_list_widget.insertItem(row, item)
            self.gui.oos_widget.oos_list_widget.setItemWidget(item, widget)
            self.gui.changes = True

    def add_custom_to_service(self, item=None, row=None):
        """
        Method to add a custom slide QListWidgetItem to the order of service's QListWidget
        :param QListWidgetItem item: Optional: a specific custom slide item
        :param int row: Optional: a specific row of the custom slide widget's QListWidget
        """
        add_item = False
        if self.custom_list.currentItem():
            if not item:
                item = QListWidgetItem()
                add_item = True
            for i in range(20, 41):
                item.setData(i, self.custom_list.currentItem().data(i))

            if item.data(29) == 'global_song':
                pixmap = self.gui.global_song_background_pixmap
                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            elif item.data(29) == 'global_bible':
                pixmap = self.gui.global_bible_background_pixmap
                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            elif 'rgb(' in item.data(29):
                pixmap = QPixmap(50, 27)
                painter = QPainter(pixmap)
                brush = QBrush(QColor(item.data(29)))
                painter.fillRect(pixmap.rect(), brush)
                painter.end()
            else:
                pixmap = QPixmap(self.gui.main.background_dir + '/' + item.data(29))
                pixmap = pixmap.scaled(50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

            widget = StandardItemWidget(self.gui, self.custom_list.currentItem().text(), 'Custom Slide', pixmap)

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
            item.setData(20, self.web_list.currentItem().data(20))
            item.setData(21, self.web_list.currentItem().data(21))
            item.setData(40, 'web')
            item.setData(24, ['', self.web_list.currentItem().data(20), self.web_list.currentItem().data(21)])

            pixmap = QPixmap(50, 27)
            painter = QPainter(pixmap)
            brush = QBrush(Qt.GlobalColor.black)
            pen = QPen(Qt.GlobalColor.white)
            painter.setPen(pen)
            painter.setBrush(brush)
            painter.begin(pixmap)
            painter.fillRect(pixmap.rect(), brush)
            painter.setFont(self.gui.bold_font)
            painter.drawText(QPoint(2, 20), 'WWW')
            painter.end()

            widget = StandardItemWidget(
                self.gui, item.data(20), self.web_list.currentItem().data(21), pixmap)

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
            item.setData(20,  self.video_list.currentItem().data(20))
            item.setData(40, 'video')

            pixmap = QPixmap(
                self.gui.main.video_dir + '/' + self.video_list.currentItem().data(20).split('.')[0] + '.jpg')
            pixmap = pixmap.scaled(96, 54, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

            widget = StandardItemWidget(
                self.gui, self.video_list.currentItem().data(20).split('.')[0], 'Video', pixmap)

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

        add_song_action = QAction('Add to Order of Service')
        add_song_action.triggered.connect(self.gui.media_widget.add_song_to_service)
        menu.addAction(add_song_action)

        edit_song_action = None
        if self.type == 'song':
            edit_song_action = QAction('Edit Song')
        elif self.type == 'custom':
            edit_song_action = QAction('Edit Slide')

        if edit_song_action:
            edit_song_action.triggered.connect(self.edit_song)
            menu.addAction(edit_song_action)

        delete_action = None
        if self.type == 'image':
            delete_action = QAction('Remove Image')
            delete_action.triggered.connect(self.gui.media_widget.delete_image)
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
        if self.currentItem().data(40) == 'song':
            self.gui.media_widget.add_song_to_service()
        elif self.currentItem().data(40) == 'custom':
            self.gui.media_widget.add_custom_to_service()
        elif self.currentItem().data(40) == 'web':
            self.gui.media_widget.add_web_to_service()
        elif self.currentItem().data(40) == 'image':
            self.gui.media_widget.add_image_to_service()
        elif self.currentItem().data(40) == 'video':
            self.gui.media_widget.add_video_to_service()

        self.gui.oos_widget.oos_list_widget.setCurrentRow(self.gui.oos_widget.oos_list_widget.count() - 1)
        self.gui.oos_widget.oos_list_widget.setFocus()

    def current_item_changed(self):
        """
        Method to send the current item to the preview widget upon the current item being changed.
        """
        if self.currentItem():
            if self.currentItem().data(40) == 'song' and isinstance(self.currentItem().data(24), dict):
                self.currentItem().setData(24, self.gui.media_widget.parse_song_data(self.currentItem()))
            self.gui.send_to_preview(self.currentItem())

    def edit_song(self):
        """
        Method to create a EditWidget for a song or custom slide.
        """
        if self.itemAt(self.item_pos):
            if self.currentItem().data(40) == 'song':
                item_text = self.itemAt(self.item_pos).text()
                song_info = self.gui.main.get_song_data(item_text)
                EditWidget(self.gui, 'song', song_info, item_text)
            elif self.currentItem().data(40) == 'custom':
                item_text = self.itemAt(self.item_pos).text()
                custom_info = self.gui.main.get_custom_data(item_text)
                EditWidget(self.gui, 'custom', custom_info, item_text)

    def delete_item(self):
        """
        Method to remove an item from this widget. Creates a QMessageBox to confirm removal.
        """
        response = QMessageBox.question(
            self.gui.main_window,
            'Really Delete',
            'Really delete ' + self.currentItem().data(20) + '? This action cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if response == QMessageBox.StandardButton.Yes:
            self.gui.main.delete_item(self.currentItem())

        if self.currentItem().data(40) == 'song':
            self.gui.media_widget.populate_song_list()
        elif self.currentItem().data(40) == 'custom':
            self.gui.media_widget.populate_custom_list()
        elif self.currentItem().data(40) == 'video':
            self.gui.media_widget.populate_video_list()
        elif self.currentItem().data(40) == 'web':
            self.gui.media_widget.populate_web_list()

        self.gui.preview_widget.slide_list.clear()