import re
import time

from PyQt6.QtCore import Qt, pyqtSignal, QObject, QUrl, QRunnable
from PyQt6.QtGui import QFont, QPixmap, QColor, QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QWidget, QGridLayout, QLabel, QVBoxLayout, QListWidgetItem, \
    QMessageBox, QHBoxLayout, QTextBrowser, QPushButton

from help import Help
from importers import Importers
from live_widget import LiveWidget
from media_widget import MediaWidget
from oos_widget import OOSWidget
from openlyrics_export import OpenlyricsExport
from preview_widget import PreviewWidget
from songselect_import import SongselectImport
from toolbar import Toolbar
from widgets import CustomMainWindow, CustomScrollArea, DisplayWidget, LyricDisplayWidget, LyricItemWidget


class GUI(QObject):
    """
    Creates the user interface and handles user input that will change the interface or the display widget.
    """
    media_widget = None
    oos_widget = None
    preview_widget = None
    live_widget = None
    display_widget = None
    lyric_label = None
    preview_display_widget = None
    current_file = None
    default_bible = None

    current_background = None
    global_song_background_pixmap = None
    global_bible_background_pixmap = None
    custom_pixmap = None
    last_pixmap = None
    display_widget = None
    sample_widget = None
    lyric_widget = None
    sample_lyric_widget = None
    blackout_widget = None
    logo_widget = None
    web_view = None
    video_widget = None
    media_player = None
    timed_update = None

    standard_font = QFont('Helvetica', 12)
    bold_font = QFont('Helvetica', 12, QFont.Weight.Bold)
    list_title_font = QFont('Helvetica', 10, QFont.Weight.Bold)
    list_font = QFont('Helvetica', 10)

    global_font_face = 'Helvetica'
    global_font_size = 48
    global_font_color = 'rgb(255, 255, 255)'
    global_footer_font_face = 'Helvetica'
    global_footer_font_size = 24
    stage_font_size = 60
    block_remote_input = False
    black_display = False
    current_display_background_color = None
    changes = False
    sink = None

    live_from_remote_signal = pyqtSignal(int)
    live_slide_from_remote_signal = pyqtSignal(int)
    display_black_screen_signal = pyqtSignal()
    display_logo_screen_signal = pyqtSignal()
    grab_display_signal = pyqtSignal()
    server_alert_signal = pyqtSignal()

    def __init__(self, main):
        """
        :param ProjectOn main: The current instance of ProjectOn
        """
        super().__init__()
        self.main = main

        # if settings exist, set the secondary screen (the display screen) to the one in the settings
        if len(self.main.settings) > 0:
            self.secondary_screen = self.main.settings['selected_screen_name']

        self.live_from_remote_signal.connect(self.live_from_remote)
        self.live_slide_from_remote_signal.connect(self.live_slide_from_remote)
        self.display_black_screen_signal.connect(self.display_black_screen)
        self.display_logo_screen_signal.connect(self.display_logo_screen)
        self.grab_display_signal.connect(self.grab_display)
        self.server_alert_signal.connect(self.show_server_alert)
        self.shadow_color = 0
        self.shadow_offset = 6

        self.main.update_status_signal.emit('Creating GUI: Configuring Screens', 'status')

        self.screens = self.main.app.screens()
        screen_found = False
        for screen in self.screens:
            if screen.name == self.secondary_screen:
                self.primary_screen = self.main.app.primaryScreen()
                screen_found = True

        if not screen_found:
            self.primary_screen = self.main.app.primaryScreen()
            self.secondary_screen = None
            secondary_found = False
            for screen in self.screens:
                if not screen.name() == self.primary_screen.name():
                    self.secondary_screen = screen
                    secondary_found = True
            if not secondary_found:
                self.secondary_screen = self.primary_screen

        self.main.update_status_signal.emit('Creating GUI: Building Main Window', 'status')

        self.init_components()

        self.main.update_status_signal.emit('Creating GUI: Building Menu Bar', 'status')
        self.create_menu_bar()
        self.main.update_status_signal.emit('Creating GUI: Creating Special Display Widgets', 'status')
        self.make_special_display_widgets()

    def init_components(self):
        """
        Creates and positions the main window, the display widget, and the hidden sample_widget needed for properly
        formatting the display widget.
        """
        self.main_window = CustomMainWindow(self)
        self.main_window.setObjectName('main_window')
        self.main_window.setStyleSheet('#main_window { background: darkGrey; }')
        self.main_window.setWindowIcon(QIcon('resources/logo.ico'))
        self.main_window.setWindowTitle('ProjectOn')
        self.central_widget = QWidget()
        self.main_window.setCentralWidget(self.central_widget)

        self.main.update_status_signal.emit('Creating GUI: Building Display Widget', 'status')
        self.display_widget = DisplayWidget(self)
        self.display_widget.setWindowIcon(QIcon('resources/logo.ico'))
        self.display_widget.setWindowTitle('ProjectOn Display Window')
        self.display_widget.setCursor(Qt.CursorShape.BlankCursor)
        self.display_widget.setStyleSheet('background: black;')
        self.display_widget.background_label.setStyleSheet('background: black')
        self.display_layout = QVBoxLayout()
        self.display_layout.setContentsMargins(0, 0, 0, 0)
        self.display_widget.setLayout(self.display_layout)
        self.lyric_widget = LyricDisplayWidget(self)
        self.display_layout.addWidget(self.lyric_widget)

        self.main.update_status_signal.emit('Creating GUI: Building Sample Widget', 'status')
        self.sample_widget = DisplayWidget(self, sample=True)
        self.sample_layout = QVBoxLayout()
        self.sample_layout.setContentsMargins(0, 0, 0, 0)
        self.sample_widget.setLayout(self.sample_layout)
        self.sample_lyric_widget = LyricDisplayWidget(self, for_sample=True)
        self.sample_layout.addWidget(self.sample_lyric_widget)

        self.position_screens(self.primary_screen, self.secondary_screen)
        self.sample_widget.show()
        self.sample_widget.hide()

        self.central_layout = QGridLayout()
        self.central_widget.setLayout(self.central_layout)

        self.add_widgets()

        self.main_window.showMaximized()

        if len(self.screens) > 1:
            self.display_widget.show()
        else:
            self.tool_bar.show_display_button.setStyleSheet('background: white')

    def add_widgets(self):
        """
        Adds all of the necessary widgets.py to the main window, display screen, and sample widget
        """
        self.main.update_status_signal.emit('Creating GUI: Adding Tool Bar', 'status')
        self.tool_bar = Toolbar(self)
        self.tool_bar.init_components()

        toolbar_scroll_area = CustomScrollArea()
        toolbar_scroll_area.setWidget(self.tool_bar)
        toolbar_scroll_area.setFixedHeight(self.tool_bar.height() + toolbar_scroll_area.horizontalScrollBar().height())
        toolbar_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        toolbar_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        toolbar_scroll_area.setStyleSheet('QScrollArea { background: white }')
        self.central_layout.addWidget(toolbar_scroll_area, 0, 0, 1, 4)

        self.main.update_status_signal.emit('Creating GUI: Adding Media Widget', 'status')
        self.media_widget = MediaWidget(self)
        self.media_widget.setMinimumWidth(100)
        self.central_layout.addWidget(self.media_widget, 2, 0)

        self.main.update_status_signal.emit('Creating GUI: Adding OOS Widget', 'status')
        self.oos_widget = OOSWidget(self)
        self.oos_widget.setMinimumWidth(100)
        self.central_layout.addWidget(self.oos_widget, 1, 0)

        self.main.update_status_signal.emit('Creating GUI: Adding Preview Widget', 'status')
        self.preview_widget = PreviewWidget(self)
        self.preview_widget.setMinimumWidth(100)
        self.central_layout.addWidget(self.preview_widget, 1, 2, 2, 1)

        self.main.update_status_signal.emit('Creating GUI: Adding Live Widget', 'status')
        self.live_widget = LiveWidget(self)
        self.live_widget.setMinimumWidth(100)
        self.central_layout.addWidget(self.live_widget, 1, 3, 2, 1)

    def create_menu_bar(self):
        """
        Creates the main window's menu bar
        """
        menu_bar = self.main_window.menuBar()
        file_menu = menu_bar.addMenu('File')

        new_action = file_menu.addAction('Create a New Service')
        new_action.triggered.connect(self.new_service)

        open_action = file_menu.addAction('Open a Service')
        open_action.triggered.connect(self.main.load_service)

        self.open_recent_menu = file_menu.addMenu('Open Recent Service')
        if 'used_services' in self.main.settings.keys():
            for item in self.main.settings['used_services']:
                open_recent_action = self.open_recent_menu.addAction(item[1])
                open_recent_action.setData(item[0] + '/' + item[1])
                open_recent_action.triggered.connect(lambda: self.main.load_service(open_recent_action.data()))

        save_action = file_menu.addAction('Save Service')
        save_action.triggered.connect(self.main.save_service)

        file_menu.addSeparator()

        import_menu = file_menu.addMenu('Import')

        openlp_import_action = import_menu.addAction('Import Songs from OpenLP')
        openlp_import_action.triggered.connect(self.tool_bar.import_songs)

        ccli_import_action = import_menu.addAction('Import Songs from CCLI SongSelect')
        ccli_import_action.triggered.connect(self.ccli_import)

        chord_pro_import_action = import_menu.addAction('Import a ChordPro Song')
        chord_pro_import_action.triggered.connect(self.chord_pro_import)

        open_lyrics_import_action = import_menu.addAction('Import an OpenLyrics Song')
        open_lyrics_import_action.triggered.connect(self.open_lyrics_import)

        export_action = file_menu.addAction('Export Songs')
        export_action.triggered.connect(lambda: OpenlyricsExport(self))

        file_menu.addSeparator()

        exit_action = file_menu.addAction('Exit')
        exit_action.triggered.connect(self.main_window.close)

        tool_menu = menu_bar.addMenu('Tools')

        hide_action = tool_menu.addAction('Show/Hide Display Screen')
        hide_action.triggered.connect(self.show_hide_display_screen)

        black_action = tool_menu.addAction('Show/Hide Black Screen')
        black_action.triggered.connect(self.display_black_screen)

        logo_action = tool_menu.addAction('Show/Hide Logo Screen')
        logo_action.triggered.connect(self.display_logo_screen)

        tool_menu.addSeparator()

        block_remote_action = tool_menu.addAction('Block Remote Inputs')
        block_remote_action.setCheckable(True)
        block_remote_action.setChecked(False)
        block_remote_action.triggered.connect(self.block_unblock_remote)

        tool_menu.addSeparator()

        settings_action = tool_menu.addAction('Settings')
        settings_action.triggered.connect(self.tool_bar.open_settings)

        import_bible_action = tool_menu.addAction('Import XML Bible')
        import_bible_action.triggered.connect(self.main.import_xml_bible)

        delete_songs_action = tool_menu.addAction('Clear Song Database')
        delete_songs_action.triggered.connect(self.main.delete_all_songs)

        ccli_credentials_action = tool_menu.addAction('Save/Change CCLI SongSelect Password')
        ccli_credentials_action.triggered.connect(self.save_ccli_password)

        help_menu = menu_bar.addMenu('Help')

        help_action = help_menu.addAction('Help Contents')
        help_action.triggered.connect(self.show_help)

        about_action = help_menu.addAction('About')
        about_action.triggered.connect(self.show_about)

    def ccli_import(self):
        from songselect_import import SongselectImport
        SongselectImport(self)

    def chord_pro_import(self):
        importer = Importers(self)
        importer.do_import(importer.CHORDPRO)

    def open_lyrics_import(self):
        importer = Importers(self)
        importer.do_import(importer.OPENLYRICS)

    def save_ccli_password(self):
        importer = SongselectImport(self, suppress_browser=True)
        importer.store_credentials()

    def show_help(self):
        self.help = Help(self)

    def show_about(self):
        widget = QWidget()
        widget.setObjectName('widget')
        widget.setParent(self.main_window)
        widget.setStyleSheet('#widget { border: 3px solid black; background: white; }')
        widget.setLayout(QVBoxLayout())

        title_widget = QWidget()
        title_widget.setLayout(QHBoxLayout())
        widget.layout().addWidget(title_widget)

        title_pixmap = QPixmap('resources/logo.svg')
        title_pixmap = title_pixmap.scaled(
            36, 36, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        title_pixmap_label = QLabel()
        title_pixmap_label.setPixmap(title_pixmap)
        title_widget.layout().addWidget(title_pixmap_label)

        title_label = QLabel('ProjectOn v.1.0b')
        title_label.setFont(QFont('Helvetica', 24, QFont.Weight.Bold))
        title_widget.layout().addWidget(title_label)
        title_widget.layout().addStretch()

        remote_widget = QWidget()
        remote_layout = QGridLayout()
        remote_widget.setLayout(remote_layout)
        widget.layout().addWidget(remote_widget)

        remote_title_label = QLabel('Remote Web Pages:')
        remote_title_label.setFont(self.standard_font)
        remote_layout.addWidget(remote_title_label, 0, 0)

        remote_label = QLabel('Standard Remote-Control:')
        remote_label.setFont(self.bold_font)
        remote_layout.addWidget(remote_label, 1, 0)

        remote_url_label = QLabel('http://' + self.main.ip + ':15171/remote')
        remote_url_label.setFont(self.standard_font)
        remote_layout.addWidget(remote_url_label, 1, 1)

        mremote_label = QLabel('Mobile-Friendly Remote-Control:')
        mremote_label.setFont(self.bold_font)
        remote_layout.addWidget(mremote_label, 2, 0)

        mremote_url_label = QLabel('http://' + self.main.ip + ':15171/mremote')
        mremote_url_label.setFont(self.standard_font)
        remote_layout.addWidget(mremote_url_label, 2, 1)

        stage_label = QLabel('Stage View:')
        stage_label.setFont(self.bold_font)
        remote_layout.addWidget(stage_label, 3, 0)

        stage_url_label = QLabel('http://' + self.main.ip + ':15171/stage')
        stage_url_label.setFont(self.standard_font)
        remote_layout.addWidget(stage_url_label, 3, 1)

        about_text = QTextBrowser()
        about_text.setStyleSheet('border: 0;')
        about_text.setOpenExternalLinks(True)
        about_text.setHtml('''
                    <p>ProjectOn is free software: you can redistribute it and/or
                    modify it under the terms of the GNU General Public License (GNU GPL)
                    published by the Free Software Foundation, either version 3 of the
                    License, or (at your option) any later version.</p>

                    <p>This program is distributed in the hope that it will be useful,
                    but WITHOUT ANY WARRANTY; without even the implied warranty of
                    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
                    GNU General Public License for more details.</p>

                    <p>You should have received a copy of the GNU General Public License
                    along with this program.  If not, see <a href="http://www.gnu.org/licenses/">http://www.gnu.org/licenses/</a>.</p>

                    <p>This program is a work-in-progress by a guy who is not, in no way, a
                    professional programmer. If you run into any problems, unexpected behavior,
                    missing features, or attempts to assimilate your unique biological and
                    technological distinctiveness, email <a href="mailto:pastorjeremywilson@gmail.com">pastorjeremywilson@gmail.com</a></p>
                ''')
        widget.layout().addWidget(about_text)

        ok_button = QPushButton('OK')
        ok_button.setFont(self.standard_font)
        ok_button.setObjectName('ok_button')
        ok_button.setStyleSheet('#ok_button { background: #5555aa; color: white; }'
                                '#ok_button:hover { background: white; color: black; }')
        ok_button.setMaximumWidth(60)
        ok_button.pressed.connect(widget.deleteLater)
        widget.layout().addWidget(ok_button, Qt.AlignmentFlag.AlignCenter)

        widget.show()

    def block_unblock_remote(self):
        """
        Provides a method for blocking signals coming in through the remote interface. Needed during live situations
        when someone on the remote may perform undesired clicks.
        """
        if self.block_remote_input:
            if self.main_window.menuBar().findChild(QLabel, 'block_label'):
                self.main_window.menuBar().findChild(QLabel, 'block_label').setText('')
            self.block_remote_input = False
        else:
            self.block_remote_input = True
            if self.main_window.menuBar().findChild(QLabel, 'block_label'):
                self.main_window.menuBar().findChild(QLabel, 'block_label').setText('REMOTE INPUT IS BLOCKED')
            else:
                block_label = QLabel('REMOTE INPUT IS BLOCKED')
                block_label.setParent(self.main_window.menuBar())
                block_label.setObjectName('block_label')
                block_label.setStyleSheet('color: red')
                block_label.setFont(self.bold_font)
                block_label.adjustSize()
                block_label.move(int(self.main_window.menuBar().width() / 2) - int(block_label.width() / 2),
                                 int(self.main_window.menuBar().height() / 2) - int(block_label.height() / 2))
                block_label.show()

    def grab_display(self):
        """
        Provides a method to grab the display widget and scale it down as a preview.
        """
        if not self.video_widget.isHidden():
            try:
                frame = self.sink.videoFrame()
                image = frame.toImage()
                pixmap = QPixmap(image)
            except Exception as ex:
                self.main.error_log()
        else:
            pixmap = self.display_widget.grab(self.display_widget.rect())

        try:
            pixmap = pixmap.scaled(
                int(self.display_widget.width() / 5), int(self.display_widget.height() / 5),
                Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.live_widget.preview_label.setPixmap(pixmap)
        except Exception:
            self.main.error_log()

    def apply_settings(self):
        """
        Provides a method to apply all of the settings obtained from the settings json file.
        """
        try:
            # if/else all the settings because things occur
            if 'global_song_background' in self.main.settings.keys():
                self.global_song_background_pixmap = QPixmap(
                    self.main.image_dir + '/' + self.main.settings['global_song_background'])
            if 'global_bible_background' in self.main.settings.keys():
                self.global_bible_background_pixmap = QPixmap(
                    self.main.image_dir + '/' + self.main.settings['global_bible_background'])
            if 'font_face' in self.main.settings.keys():
                self.global_font_face = self.main.settings['font_face']
            else:
                self.global_font_face = 'Helvetica'
            if 'font_size' in self.main.settings.keys():
                self.global_font_size = self.main.settings['font_size']
            else:
                self.global_font_size = 60
            if 'font_color' in self.main.settings.keys():
                self.global_font_color = self.main.settings['font_color']
            else:
                self.global_font_color = 'white'
            if 'use_shadow' in self.main.settings.keys():
                self.use_shadow = self.main.settings['use_shadow']
            else:
                self.use_shadow = True
            if 'shadow_color' in self.main.settings.keys():
                self.shadow_color = self.main.settings['shadow_color']
            else:
                self.shadow_color = 0
            if 'shadow_offset' in self.main.settings.keys():
                self.shadow_offset = self.main.settings['shadow_offset']
            else:
                self.shadow_offset = 5
            if 'use_outline' in self.main.settings.keys():
                self.use_outline = self.main.settings['use_outline']
            else:
                self.use_outline = False
            if 'outline_color' in self.main.settings.keys():
                self.outline_color = self.main.settings['outline_color']
            else:
                self.outline_color = 0
            if 'outline_width' in self.main.settings.keys():
                self.outline_width = self.main.settings['outline_width']
            else:
                self.outline_width = 3
            if 'stage_font_size' in self.main.settings.keys():
                self.stage_font_size = self.main.settings['stage_font_size']
            else:
                self.stage_font_size = 60
            if 'default_bible' in self.main.settings.keys():
                self.default_bible = self.main.settings['default_bible']

            # apply the font, shadow, and outline settings to main and sample lyric widgets.py
            for lyric_widget in [self.lyric_widget, self.sample_lyric_widget]:
                if self.global_font_color == 'black':
                    lyric_widget.fill_color = QColor(0, 0, 0)
                elif self.global_font_color == 'white':
                    lyric_widget.fill_color = QColor(255, 255, 255)
                else:
                    font_color_split = self.global_font_color.split(', ')
                    lyric_widget.fill_color = QColor(
                        int(font_color_split[0]), int(font_color_split[1]), int(font_color_split[2]))

                lyric_widget.use_shadow = self.use_shadow
                lyric_widget.shadow_color = QColor(self.shadow_color, self.shadow_color, self.shadow_color)
                lyric_widget.shadow_offset = int(self.shadow_offset)
                lyric_widget.use_outline = self.use_outline
                lyric_widget.outline_color = QColor(self.outline_color, self.outline_color, self.outline_color)
                lyric_widget.outline_width = int(self.outline_width)

            self.tool_bar.song_background_combobox.blockSignals(True)
            self.tool_bar.bible_background_combobox.blockSignals(True)

            # check that the saved song background exists in the combobox
            index = None
            for i in range(self.tool_bar.bible_background_combobox.count()):
                if self.tool_bar.bible_background_combobox.itemData(i, Qt.ItemDataRole.UserRole):
                    if (self.main.settings['global_song_background']
                            in self.tool_bar.bible_background_combobox.itemData(i, Qt.ItemDataRole.UserRole)):
                        index = i

            # set the song background combobox to the saved song background
            if index and not index == -1:
                self.tool_bar.song_background_combobox.setCurrentIndex(index)
                pixmap = QPixmap(self.main.background_dir + '/' + self.main.settings['global_song_background'])
                pixmap = pixmap.scaled(
                    self.secondary_screen.size().width(),
                    self.secondary_screen.size().height(),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.global_song_background_pixmap = pixmap
            # show a message and set to default if the song background wasn't found
            else:
                if not self.main.settings["global_song_background"] == 'choose_global':
                    QMessageBox.information(
                        self.main_window,
                        'Song Background Missing',
                        f'Saved song background "{self.main.settings["global_song_background"]}" not found in current list. Using current default.',
                        QMessageBox.StandardButton.Ok
                    )

            # check that the saved bible background exists in the combobox
            index = None
            for i in range(self.tool_bar.bible_background_combobox.count()):
                if self.tool_bar.bible_background_combobox.itemData(i, Qt.ItemDataRole.UserRole):
                    if (self.main.settings['global_bible_background']
                            in self.tool_bar.bible_background_combobox.itemData(i, Qt.ItemDataRole.UserRole)):
                        index = i
                        self.main.settings['global_bible_background'] = (
                            self.tool_bar.bible_background_combobox.itemData(i, Qt.ItemDataRole.UserRole))

            # set the bible background combobox to the saved bible background
            if index and not index == -1:
                self.tool_bar.bible_background_combobox.setCurrentIndex(index)

                pixmap = QPixmap(self.main.background_dir + '/' + self.main.settings['global_bible_background'])
                pixmap = pixmap.scaled(
                    self.secondary_screen.size().width(),
                    self.secondary_screen.size().width(),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.global_bible_background_pixmap = pixmap
            # show a message and set to default if the song background wasn't found
            else:
                if not self.main.settings["global_song_background"] == 'choose_global':
                    QMessageBox.information(
                        self.main_window,
                        'Song Background Missing',
                        f'Saved song background "{self.main.settings["global_bible_background"]}" '
                        f'not found in current list. Using current default.',
                        QMessageBox.StandardButton.Ok
                    )

            self.tool_bar.song_background_combobox.blockSignals(False)
            self.tool_bar.bible_background_combobox.blockSignals(False)

            try:
                self.tool_bar.font_list_widget.setCurrentText(self.global_font_face)
                found = True
            except Exception:
                found = False

            if not found:
                QMessageBox.information(
                    self.gui.main_window,
                    'Font Missing',
                    f'Saved font "{self.settings["global_font"]}" not found in current list. Using current default.',
                    QMessageBox.StandardButton.Ok
                )

            self.tool_bar.font_list_widget.blockSignals(True)
            self.tool_bar.font_list_widget.setCurrentText(self.main.settings['font_face'])
            self.tool_bar.font_list_widget.blockSignals(False)

            self.set_logo_image(self.main.image_dir + '/' + self.main.settings['logo_image'])
        except Exception:
            self.main.error_log()

    def new_service(self):
        """
        Provides a function for clearing the order of service, preview, and live list widgets.py when
        the user wants to create a new service. Checks for changes first.
        """
        response = -1
        if self.oos_widget.oos_list_widget.count() > 0 and self.changes:
            response = QMessageBox.question(
                self.main_window,
                'Save Changes',
                'Changes have been made. Save changes?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )

        save_result = 1
        if response == QMessageBox.StandardButton.Cancel:
            return
        elif response == QMessageBox.StandardButton.Yes:
            save_result = self.main.save_service()

        if save_result == -1:
            return

        self.oos_widget.oos_list_widget.blockSignals(True)
        self.preview_widget.slide_list.blockSignals(True)
        self.live_widget.slide_list.blockSignals(True)

        self.oos_widget.oos_list_widget.clear()
        self.preview_widget.slide_list.clear()
        self.live_widget.slide_list.clear()
        self.current_file = None

        self.oos_widget.oos_list_widget.blockSignals(False)
        self.preview_widget.slide_list.blockSignals(False)
        self.live_widget.slide_list.blockSignals(False)

        self.changes = False

    def position_screens(self, primary_screen, secondary_screen=None):
        """
        Correctly sizes and positions the GUI and display widgets.py according to the screen layout
        :param primary_screen: The main screen from the settings or from discovery
        :param secondary_screen: The second screen if it exists, the main screen if not
        :return:
        """
        if secondary_screen:
            self.primary_screen = primary_screen
            self.secondary_screen = secondary_screen
            display_geometry = self.secondary_screen.geometry()

            self.display_widget.setFixedSize(self.secondary_screen.size())
            self.display_widget.background_label.setFixedSize(self.secondary_screen.size())

            self.sample_widget.setFixedSize(self.secondary_screen.size())
            self.sample_widget.background_label.setFixedSize(self.secondary_screen.size())
            self.sample_lyric_widget.set_geometry()

            self.main_window.setGeometry(self.primary_screen.geometry())
        # place the display widget in the main screen and hide it if there is only one screen
        else:
            self.primary_screen = primary_screen
            self.secondary_screen = primary_screen

            display_geometry = self.primary_screen.geometry()
            self.display_widget.setFixedSize(self.primary_screen.size())
            self.display_widget.background_label.setGeometry(self.display_widget.geometry())

            self.sample_widget.setFixedSize(self.primary_screen.size())
            self.sample_widget.background_label.setGeometry(self.sample_widget.geometry())
            self.sample_lyric_widget.set_geometry()

            self.main_window.setGeometry(self.primary_screen.geometry())

        self.display_widget.move(display_geometry.left(), display_geometry.top())
        self.sample_widget.move(display_geometry.left(), display_geometry.top())
        self.main_window.move(self.primary_screen.geometry().left(), self.primary_screen.geometry().top())
        if not self.main.initial_startup:
            self.main_window.showMaximized()

    def show_server_alert(self):
        """
        Provides a message box if the server check has failed.
        """
        QMessageBox.critical(
            self.main_window,
            'Server Error',
            'The remote server has failed. Save your work and restart the program to restart the server.',
            QMessageBox.StandardButton.Ok
        )

    def live_from_remote(self, num):
        """
        Takes a row number from remote input's order of service and sets the order of service list widget to that row,
        then calls send_to_live.
        :param int num: The row number signaled from the web remote
        """
        self.oos_widget.oos_list_widget.setCurrentRow(num)
        self.main.app.processEvents()
        self.send_to_live()

    def live_slide_from_remote(self, num):
        """
        Takes a row number from the remote input's live slides and sets the live widget to that row.
        :param int num: The row number signaled from the web remote
        """
        self.live_widget.slide_list.setCurrentRow(num)

    def set_song_background(self, file):
        """
        Provides a method for setting the global_song_background_pixmap variable, scaling it to the display size
        :param str file: The location of the background image file
        """
        self.global_song_background_pixmap = QPixmap(file)
        self.global_song_background_pixmap = self.global_song_background_pixmap.scaled(
            self.display_widget.size().width(), self.display_widget.size().height(),
            Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
        )

        file_name_split = file.split('/')
        file_name = file_name_split[len(file_name_split) - 1]
        self.main.settings['global_song_background'] = file_name
        self.main.save_settings()

    def set_bible_background(self, file):
        """
        Provides a method for setting the global_bible_background_pixmap variable, scaling it to the display size
        :param str file: The location of the background image file
        """
        self.global_bible_background_pixmap = QPixmap(file)
        self.global_bible_background_pixmap = self.global_bible_background_pixmap.scaled(
            self.display_widget.size().width(), self.display_widget.size().height(),
            Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
        )

        file_name_split = file.split('/')
        file_name = file_name_split[len(file_name_split) - 1]
        self.main.settings['global_bible_background'] = file_name
        self.main.save_settings()

    def set_logo_image(self, file):
        """
        Provides a method for setting the logo_pixmap variable, scaling it to the display size
        :param str file: The location of the background image file
        """
        self.logo_pixmap = QPixmap(file)
        self.logo_pixmap = self.logo_pixmap.scaled(
            self.display_widget.size().width(), self.display_widget.size().height(),
            Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.logo_label.setPixmap(self.logo_pixmap)

        file_name_split = file.split('/')
        file_name = file_name_split[len(file_name_split) - 1]
        self.main.settings['logo_image'] = file_name
        self.main.save_settings()

    def send_to_preview(self, item):
        """
        Provides a method for sending an item, selected in the order of service list widget, to the preview list widget.
        :param QListWidgetItem item: The item selected
        """
        if item:
            self.preview_widget.slide_list.clear()

            if item.data(30) == 'song':
                if item.data(31):
                    for i in range(len(item.data(31))):
                        list_item = QListWidgetItem()
                        for j in range(20, 31):
                            list_item.setData(j, item.data(j))

                        list_item.setData(31, [item.data(31)[i][0], item.data(31)[i][1], item.data(31)[i][2]])
                        list_item.setData(32, item.data(32))
                        lyric_widget = LyricItemWidget(self, list_item.data(31)[1], list_item.data(31)[2])
                        list_item.setSizeHint(lyric_widget.sizeHint())
                        self.preview_widget.slide_list.addItem(list_item)
                        self.preview_widget.slide_list.setItemWidget(list_item, lyric_widget)

            elif item.data(30) == 'bible':
                slide_texts = item.data(21)
                for i in range(len(slide_texts)):
                    title = item.data(20)
                    list_item = QListWidgetItem()
                    for j in range(20, 32):
                        list_item.setData(j, item.data(j))
                    list_item.setData(20, title)
                    list_item.setData(21, slide_texts[i])
                    list_item.setData(22, item.text())
                    list_item.setData(30, 'bible')

                    new_title = title.split(':')[0] + ':'
                    first_num_found = False
                    first_num = ''
                    last_num = ''
                    skip_next = False

                    # find the verse range for each segment of scripture
                    scripture_text = re.sub('<.*?>', '', list_item.data(21))
                    for j in range(len(scripture_text)):
                        data = scripture_text[j]
                        next_data = None
                        if j < len(scripture_text) - 1:
                            next_data = scripture_text[j + 1]
                        num = ''
                        if not skip_next:
                            if data.isnumeric():
                                num += data
                                if next_data.isnumeric():
                                    num += next_data
                                    skip_next = True
                                if not first_num_found:
                                    first_num = num
                                    first_num_found = True
                                else:
                                    last_num = num
                        else:
                            skip_next = False

                    if last_num == '':
                        new_title += first_num
                    else:
                        new_title += first_num + '-' + last_num

                    list_item.setData(31, ['', new_title, slide_texts[i]])

                    lyric_widget = LyricItemWidget(self, new_title, slide_texts[i])
                    list_item.setSizeHint(lyric_widget.sizeHint())
                    self.preview_widget.slide_list.addItem(list_item)
                    self.preview_widget.slide_list.setItemWidget(list_item, lyric_widget)

            elif item.data(30) == 'image':
                lyric_widget = LyricItemWidget(self, item.data(20), '')
                list_item = QListWidgetItem()
                for j in range(20, 32):
                    list_item.setData(j, item.data(j))
                list_item.setSizeHint(lyric_widget.sizeHint())
                self.preview_widget.slide_list.addItem(list_item)
                self.preview_widget.slide_list.setItemWidget(list_item, lyric_widget)

            elif item.data(30) == 'custom':
                lyric_widget = LyricItemWidget(self, item.data(20), item.data(21))
                list_item = QListWidgetItem()
                list_item.setData(32, item.data(32))
                for j in range(20, 32):
                    list_item.setData(j, item.data(j))
                list_item.setSizeHint(lyric_widget.sizeHint())
                self.preview_widget.slide_list.addItem(list_item)
                self.preview_widget.slide_list.setItemWidget(list_item, lyric_widget)

            elif item.data(30) == 'web':
                lyric_widget = LyricItemWidget(self, item.data(20), item.data(21))
                list_item = QListWidgetItem()
                for j in range(20, 32):
                    list_item.setData(j, item.data(j))
                list_item.setSizeHint(lyric_widget.sizeHint())
                self.preview_widget.slide_list.addItem(list_item)
                self.preview_widget.slide_list.setItemWidget(list_item, lyric_widget)

            elif item.data(30) == 'video':
                self.preview_widget.slide_list.clear()

                widget = QWidget()
                layout = QHBoxLayout()
                widget.setLayout(layout)

                image_label = QLabel()
                pixmap = QPixmap(
                    self.main.video_dir + '/' + item.data(20).split('.')[0] + '.jpg')
                pixmap = pixmap.scaled(96, 54, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                image_label.setPixmap(pixmap)
                layout.addWidget(image_label)

                label = QLabel(item.data(20).split('.')[0])
                label.setFont(self.list_font)
                layout.addWidget(label)

                list_item = QListWidgetItem()
                list_item.setData(20, item.data(20))
                list_item.setData(30, 'video')
                list_item.setSizeHint(widget.sizeHint())

                self.preview_widget.slide_list.addItem(list_item)
                self.preview_widget.slide_list.setItemWidget(list_item, widget)

            self.preview_widget.slide_list.setFocus()
            self.preview_widget.slide_list.setCurrentRow(0)

    def send_to_live(self):
        """
        Method to send the current order of service item to live, using the current index of the preview widget,
        if available.
        """
        try:
            self.oos_widget.oos_list_widget.blockSignals(True)
            self.live_widget.blockSignals(True)
            self.live_widget.slide_list.clear()

            for i in range(self.oos_widget.oos_list_widget.count()):
                widget = self.oos_widget.oos_list_widget.itemWidget(self.oos_widget.oos_list_widget.item(i))
                if widget:
                    widget.setStyleSheet('QWidget#item_widget { border: 0; }')

            item_index = self.preview_widget.slide_list.currentRow()
            for i in range(self.preview_widget.slide_list.count()):
                original_item = self.preview_widget.slide_list.item(i)
                size_hint = original_item.sizeHint()
                item = QListWidgetItem()
                for j in range(20, 33):
                    item.setData(j, original_item.data(j))

                if item.data(30) == 'image':
                    lyric_widget = LyricItemWidget(self, original_item.data(20), '')
                elif item.data(30) == 'video':
                    lyric_widget = LyricItemWidget(self, item.data(20), '')
                else:
                    lyric_widget = LyricItemWidget(self, item.data(31)[1], item.data(31)[2])

                self.live_widget.slide_list.addItem(item)
                self.live_widget.slide_list.setItemWidget(item, lyric_widget)
                item.setSizeHint(size_hint)

            if item_index:
                self.live_widget.slide_list.setCurrentRow(item_index)
            else:
                self.live_widget.slide_list.setCurrentRow(0)

            # create the slide buttons to be sent to the remote web page
            slide_buttons = ''
            for i in range(self.live_widget.slide_list.count()):
                if self.live_widget.slide_list.item(i).data(30) == 'video':
                    title = self.live_widget.slide_list.item(i).data(20)
                else:
                    title = self.live_widget.slide_list.item(i).data(31)[1]
                if (not self.live_widget.slide_list.item(i).data(30) == 'image'
                        and not self.live_widget.slide_list.item(i).data(30) == 'video'):
                    text = self.live_widget.slide_list.item(i).data(31)[2]
                    text = re.sub('<p.*?>', '', text)
                    text = text.replace('</p>', '')
                else:
                    text = ''

                if i == 0:
                    class_tag = 'class="current"'
                else:
                    class_tag = ''

                slide_buttons += f"""
                    <button id="{str(i)}" {class_tag} type="submit" name="slide_button" value="{str(i)}">
                        <span class="title">{title}</span>
                        <br>
                        <div class="text">{text}</div>
                    </button>
                    <br>"""
            self.main.remote_server.socketio.emit('update_slides', slide_buttons)
            self.main.remote_server.socketio.emit(
                'change_current_oos', str(self.oos_widget.oos_list_widget.currentRow()))

            if self.oos_widget.oos_list_widget.currentRow() < self.oos_widget.oos_list_widget.count() - 1:
                self.send_to_preview(
                    self.oos_widget.oos_list_widget.item(self.oos_widget.oos_list_widget.currentRow() + 1))
            elif self.oos_widget.oos_list_widget.currentRow() == self.oos_widget.oos_list_widget.count() - 1:
                self.send_to_preview(self.oos_widget.oos_list_widget.currentItem())

            self.live_widget.blockSignals(False)
            self.oos_widget.oos_list_widget.blockSignals(False)
            self.live_widget.slide_list.setFocus()
        except Exception:
            self.main.error_log()

    def change_display(self, widget):
        """
        Method to change what it being displayed in the display widget or the hidden sample widget.
        :param str widget: 'live' or 'sample' widget that is being changed
        """
        display_widget = None
        lyric_widget = None
        current_item = None
        if widget == 'live':
            display_widget = self.display_widget
            lyric_widget = self.lyric_widget
            current_item = self.live_widget.slide_list.currentItem()

            self.live_widget.preview_label.clear()
            if self.media_player.isPlaying():
                self.media_player.stop()
                self.media_player.setPosition(0)
                self.live_widget.player_controls.hide()
            if self.timed_update:
                self.timed_update.stop = True
                self.main.thread_pool.waitForDone()
            if not self.blackout_widget.isHidden():
                self.tool_bar.black_screen_button.setStyleSheet('background: darkGrey')
            if self.logo_widget and not self.logo_widget.isHidden():
                self.tool_bar.logo_screen_button.setStyleSheet('background: darkGrey')
            if display_widget.isHidden():
                if not self.primary_screen == self.secondary_screen:
                    display_widget.show()
                    self.tool_bar.show_display_button.setStyleSheet('background: darkGrey')

        elif widget == 'sample':
            display_widget = self.sample_widget
            lyric_widget = self.sample_lyric_widget
            current_item = self.preview_widget.slide_list.currentItem()

        display_widget.background_label.clear()

        if current_item:
            # set the background
            if current_item.data(30) == 'song' or current_item.data(30) == 'custom':
                if current_item.data(29) == 'global_song':
                    display_widget.background_label.clear()
                    display_widget.setStyleSheet('#display_widget { background-color: none } ')
                    display_widget.background_label.setPixmap(self.global_song_background_pixmap)
                elif current_item.data(29) == 'global_bible':
                    display_widget.background_label.clear()
                    display_widget.setStyleSheet('#display_widget { background-color: none } ')
                    display_widget.background_label.setPixmap(self.global_bible_background_pixmap)
                elif 'rgb(' in current_item.data(29):
                    display_widget.background_label.clear()
                    display_widget.setStyleSheet(
                        '#display_widget { background-color: ' + current_item.data(29) + '}')
                else:
                    display_widget.background_label.clear()
                    display_widget.setStyleSheet('#display_widget { background-color: none } ')
                    self.custom_pixmap = QPixmap(self.main.background_dir + '/' + current_item.data(29))
                    display_widget.background_label.setPixmap(self.custom_pixmap)
            elif current_item.data(30) == 'bible':
                display_widget.background_label.setPixmap(self.global_bible_background_pixmap)
            elif current_item.data(30) == 'image':
                pixmap = QPixmap(self.main.image_dir + '/' + current_item.data(20))
                display_widget.background_label.setPixmap(pixmap)
            elif current_item.data(30) == 'video':
                display_widget.background_label.clear()
                pixmap = QPixmap(self.main.video_dir + '/' + current_item.data(20).split('.')[0] + '.jpg')
                pixmap = pixmap.scaled(
                    display_widget.width(), display_widget.height(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                display_widget.background_label.setPixmap(pixmap)

            # set the lyrics html
            if current_item.data(30) == 'song':
                lyrics_html = current_item.data(31)[2]
            elif current_item.data(30) == 'bible' or current_item.data(23) == 'custom':
                lyrics_html = current_item.data(21)
            elif current_item.data(30) == 'image':
                lyrics_html = ''
            elif current_item.data(30) == 'custom':
                lyrics_html = current_item.data(21)
            elif current_item.data(30) == 'web':
                if widget == 'sample':
                    lyrics_html = '<p style="align-text: center;">' + current_item.data(20) + '</p>'
                else:
                    lyrics_html = ''
                    self.web_view.load(QUrl(current_item.data(21)))
            elif current_item.data(30) == 'video':
                if widget == 'sample':
                    lyrics_html = '<p style="align-text: center;">' + current_item.data(20) + '</p>'
                else:
                    lyrics_html = ''
                    self.media_player.setSource(QUrl.fromLocalFile(self.main.video_dir + '/' + current_item.data(20)))
                    self.live_widget.player_controls.show()

            #set the font
            if current_item.data(27) and not current_item.data(27) == 'global':
                font_face = current_item.data(27)
            else:
                font_face = self.global_font_face

            if current_item.data(32) and not current_item.data(32) == 'global':
                font_size = int(current_item.data(32))
            else:
                font_size = self.global_font_size

            lyric_widget.setFont(QFont(font_face, font_size, QFont.Weight.Bold))
            lyric_widget.footer_label.setFont(QFont(font_face, self.global_footer_font_size))
            lyric_widget.use_shadow = self.use_shadow
            lyric_widget.shadow_color = QColor(self.shadow_color, self.shadow_color, self.shadow_color)
            lyric_widget.shadow_offset = self.shadow_offset
            lyric_widget.use_outline = self.use_outline
            lyric_widget.outline_color = QColor(self.outline_color, self.outline_color, self.outline_color)
            lyric_widget.outline_width = self.outline_width

            #set the font color
            if current_item.data(28) and not current_item.data(28) == 'global':
                color = current_item.data(28).replace('rgb(', '')
                color = color.replace(')', '')
                font_color_split = color.split(', ')
                lyric_widget.fill_color = QColor(
                    int(font_color_split[0]), int(font_color_split[1]), int(font_color_split[2]))
            else:
                if self.global_font_color == 'black':
                    lyric_widget.fill_color = QColor(0, 0, 0)
                elif self.global_font_color == 'white':
                    lyric_widget.fill_color = QColor(255, 255, 255)
                else:
                    font_color_split = self.global_font_color.split(', ')
                    lyric_widget.fill_color = QColor(
                        int(font_color_split[0]), int(font_color_split[1]), int(font_color_split[2]))

            lyric_widget.text = lyrics_html

            # set the footer text
            lyric_widget.footer_label.show()
            footer_text = ''
            if current_item.data(26) and current_item.data(26) == 'true':
                if len(current_item.data(21)) > 0:
                    footer_text += current_item.data(21)
                if len(current_item.data(22)) > 0:
                    footer_text += '\n\u00A9' + current_item.data(22).replace('\n', ' ')
                if len(current_item.data(23)) > 0:
                    footer_text += '\nCCLI Song #: ' + current_item.data(23)
                if len(self.main.settings['ccli_num']) > 0:
                    footer_text += '\nCCLI License #: ' + self.main.settings['ccli_num']
                lyric_widget.footer_label.setText(footer_text)
            elif current_item.data(30) == 'bible':
                lyric_widget.footer_label.setText(
                    current_item.data(20) + ' (' + current_item.data(23) + ')')
            else:
                lyric_widget.footer_label.clear()

            if lyric_widget.footer_label.text() == '':
                lyric_widget.footer_label.hide()

            # hide or show the appropriate widgets.py
            if widget == 'live':
                if not current_item.data(30) == 'video' and not current_item.data(30) == 'web':
                    if not self.web_view.isHidden():
                        self.web_view.hide()
                    if not self.video_widget.isHidden():
                        self.video_widget.hide()
                    if not self.blackout_widget.isHidden():
                        self.blackout_widget.hide()
                    if not self.logo_widget.isHidden():
                        self.logo_widget.hide()
                    if self.lyric_widget.isHidden():
                        self.lyric_widget.show()
                    if current_item.data(30) == 'image':
                        self.lyric_widget.hide()
                elif current_item.data(30) == 'video':
                    if not self.lyric_widget.isHidden():
                        self.lyric_widget.hide()
                    if not self.web_view.isHidden():
                        self.web_view.hide()
                    if not self.blackout_widget.isHidden():
                        self.blackout_widget.hide()
                    if not self.logo_widget.isHidden():
                        self.logo_widget.hide()
                    if self.video_widget.isHidden():
                        self.video_widget.show()
                    self.media_player.play()

                    self.timed_update = TimedPreviewUpdate(self)
                    self.main.thread_pool.start(self.timed_update)
                elif current_item.data(30) == 'web':
                    if not self.lyric_widget.isHidden():
                        self.lyric_widget.hide()
                    if not self.blackout_widget.isHidden():
                        self.blackout_widget.hide()
                    if not self.logo_widget.isHidden():
                        self.logo_widget.hide()
                    if not self.video_widget.isHidden():
                        self.video_widget.hide()
                    if self.web_view.isHidden():
                        self.web_view.show()

                    self.timed_update = TimedPreviewUpdate(self)
                    self.main.thread_pool.start(self.timed_update)
                    self.live_widget.slide_list.setFocus()

            # change the preview image
            if widget == 'live':
                if not current_item.data(30) == 'web' and not current_item.data(30) == 'video':
                    pixmap = display_widget.grab(display_widget.rect())
                    pixmap = pixmap.scaled(
                        int(display_widget.width() / 5), int(display_widget.height() / 5),
                        Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

                    self.live_widget.preview_label.setPixmap(pixmap)

                    stage_html = re.sub('<p.*?>', '', lyrics_html)
                    stage_html = stage_html.replace('</p>', '')
                    self.main.remote_server.socketio.emit('update_stage', [stage_html, self.stage_font_size])
                elif current_item.data(30) == 'web':
                    lyrics_html = '<p style="align-text: center;">' + current_item.data(20) + '</p>'
                    self.main.remote_server.socketio.emit('update_stage', [lyrics_html, self.stage_font_size])
                elif current_item.data(30) == 'video':
                    lyrics_html = '<p style="align-text: center;">' + current_item.data(20) + '</p>'
                    self.main.remote_server.socketio.emit('update_stage', [lyrics_html, self.stage_font_size])
            elif widget == 'sample':
                pixmap = display_widget.grab(display_widget.rect())
                pixmap = pixmap.scaled(
                    int(display_widget.width() / 5), int(display_widget.height() / 5),
                    Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

                self.preview_widget.preview_label.setPixmap(pixmap)

    def make_special_display_widgets(self):
        """
        Create all the widgets.py that could be used on the display widget.
        """
        self.web_view = QWebEngineView()
        self.display_layout.addWidget(self.web_view)

        self.video_widget = QVideoWidget()
        self.video_widget.setGeometry(self.display_widget.geometry())
        self.media_player = QMediaPlayer()
        self.media_player.playingChanged.connect(self.media_playing_change)
        self.media_player.errorOccurred.connect(self.media_error)
        self.media_player.setVideoOutput(self.video_widget)
        devices = QMediaDevices.audioOutputs()
        for device in devices:
            if device.isDefault():
                self.audio_output = QAudioOutput(device)
                self.audio_output.setVolume(1.0)
                self.media_player.setAudioOutput(self.audio_output)
        self.sink = self.media_player.videoSink()
        self.display_layout.addWidget(self.video_widget)

        self.blackout_widget = QWidget()
        self.blackout_widget.setStyleSheet('background-color: black;')
        self.display_layout.addWidget(self.blackout_widget)

        self.logo_widget = QWidget()
        self.logo_widget.setContentsMargins(0, 0, 0, 0)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.logo_widget.setLayout(layout)

        self.logo_label = QLabel()
        layout.addWidget(self.logo_label)
        self.display_layout.addWidget(self.logo_widget)

        if len(self.main.settings['logo_image']) > 0:
            pixmap = QPixmap(self.main.image_dir + '/' + self.main.settings['logo_image'])
            pixmap = pixmap.scaled(
                self.display_widget.size().width(), self.display_widget.size().height(),
                Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.logo_label.setPixmap(pixmap)
            self.logo_widget.show()
            self.tool_bar.logo_screen_button.setStyleSheet('background: white')
        else:
            self.logo_widget.hide()

        self.lyric_widget.hide()
        self.web_view.hide()
        self.video_widget.hide()
        self.blackout_widget.hide()

    def media_playing_change(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
            self.media_player.setPosition(0)

    def media_error(self):
        """
        Show a message box letting the user know that an error occurred playing the video.
        """
        QMessageBox.information(self.main_window, 'Media Error', 'Unable to play video.', QMessageBox.StandardButton.Ok)

    def show_hide_display_screen(self):
        """
        Method to toggle between showing and hiding the display screen.
        """
        if self.display_widget.isHidden():
            self.display_widget.show()
            self.tool_bar.show_display_button.setStyleSheet('background: darkGrey')
        else:
            self.display_widget.hide()
            self.tool_bar.show_display_button.setStyleSheet('background: white')
        self.live_widget.slide_list.setFocus()

    def display_black_screen(self):
        """
        Method to toggle a black screen on and off
        """
        # ensure that the display widget is showing and hide the other widgets.py
        if self.blackout_widget.isHidden():
            if not self.lyric_widget.isHidden():
                self.lyric_widget.hide()
            if not self.video_widget.isHidden():
                self.video_widget.hide()
            if not self.logo_widget.isHidden():
                self.logo_widget.hide()
                self.tool_bar.logo_screen_button.setStyleSheet('background: darkGrey')
            if not self.web_view.isHidden():
                self.web_view.hide()
            if self.display_widget.isHidden():
                self.display_widget.show()

                self.tool_bar.show_display_button.setStyleSheet('background: darkGrey')
            self.blackout_widget.show()
            self.tool_bar.black_screen_button.setStyleSheet('background: white')

        else:
            self.blackout_widget.hide()
            self.tool_bar.black_screen_button.setStyleSheet('background: darkGrey')

            if self.live_widget.slide_list.currentItem():
                if self.live_widget.slide_list.currentItem().data(30) == 'web':
                    self.web_view.show()
                elif self.live_widget.slide_list.currentItem().data(30) == 'video':
                    self.video_widget.show()
                else:
                    self.lyric_widget.show()
        self.live_widget.slide_list.setFocus()

    def display_logo_screen(self):
        """
        Method to toggle the logo widget on and off
        """
        if len(self.main.settings['logo_image']) > 0:
            if self.logo_widget.isHidden():
                if not self.lyric_widget.isHidden():
                    self.lyric_widget.hide()
                if not self.video_widget.isHidden():
                    self.video_widget.hide()
                if not self.web_view.isHidden():
                    self.web_view.hide()
                if not self.blackout_widget.isHidden():
                    self.blackout_widget.hide()
                    self.tool_bar.black_screen_button.setStyleSheet('background: darkGrey')
                if self.display_widget.isHidden():
                    self.display_widget.show()
                    self.tool_bar.show_display_button.setStyleSheet('background: darkGrey')

                self.logo_widget.show()
                self.logo_label.show()
                self.tool_bar.logo_screen_button.setStyleSheet('background: white')

            else:
                self.logo_widget.hide()
                self.tool_bar.logo_screen_button.setStyleSheet('background: darkGrey')

                if self.live_widget.slide_list.currentItem():
                    if self.live_widget.slide_list.currentItem().data(30) == 'web':
                        self.web_view.show()
                    elif self.live_widget.slide_list.currentItem().data(30) == 'video':
                        self.video_widget.show()
                    else:
                        self.lyric_widget.show()
        self.live_widget.slide_list.setFocus()

    def format_display_lyrics(self, lyrics):
        """
        Method to take the stored lyrics of a song and parse them out according to their segment markers (i.e. [V1])
        :param str lyrics: The raw lyrics data
        """
        lyric_dictionary = {}
        if lyrics:
            if '<body' in lyrics:
                lyrics_split = re.split('<body.*?>', lyrics)
                lyrics = lyrics_split[1].split('</body>')[0].strip()
                lyrics = re.sub('<p.*?>', '<p style="text-align: center;">', lyrics)

            segment_markers = re.findall('\[.*?\]', lyrics)
            segment_split = re.split('\[.*?\]', lyrics)

            if len(segment_markers) > 0:
                for i in range(len(segment_markers)):
                    try:
                        this_segment = segment_split[i + 1]
                        lyric_dictionary.update({segment_markers[i]: this_segment.strip()})
                    except IndexError:
                        lyric_dictionary.update({segment_markers[i]: segment_split[i + 1].strip()})
            else:
                lyric_dictionary.update({'[v1]': lyrics})

        return lyric_dictionary

    def add_scripture_item(self, reference, text, version):
        """
        Method to take a block of scripture and add it as a QListWidgetItem to the order of service widget.
        :param str reference: The scripture passage's reference from the bible
        :param str text: The text of the scripture passage
        :param str version: The version of the bible this passage is from
        :return:
        """
        item = QListWidgetItem()
        item.setData(20, reference)
        item.setData(21, self.parse_scripture_by_verse(text))
        item.setData(23, version)
        item.setData(30, 'bible')
        item.setData(31, ['', reference, text])

        from media_widget import OOSItemWidget
        label_pixmap = self.global_bible_background_pixmap.scaled(
            50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        widget = OOSItemWidget(self, label_pixmap, reference, 'Scripture')

        item.setSizeHint(widget.sizeHint())
        self.oos_widget.oos_list_widget.addItem(item)
        self.oos_widget.oos_list_widget.setItemWidget(item, widget)

    def parse_scripture_item(self, text):
        """
        Method to take a scripture passage and divide it up according to what will fit on the screen given the current
        font and size.
        :param str text: The scripture text to be parsed
        """
        self.sample_lyric_widget.lyric_label.setFont(
            QFont(self.global_font_face, self.global_font_size, QFont.Weight.Bold))
        self.sample_lyric_widget.lyric_label.setText(
            '<p style="text-align: center; line-height: 120%;">' + text + '<p>')
        self.sample_lyric_widget.footer_label.setText('bogus reference') # just a placeholder
        self.sample_lyric_widget.lyric_label.adjustSize()

        slide_texts = []
        if self.sample_lyric_widget.lyric_label.sizeHint().height() > 920:
            words = text.split(' ')

            self.sample_lyric_widget.lyric_label.setText('<p style="text-align: center; line-height: 120%;">')
            self.sample_lyric_widget.lyric_label.adjustSize()
            count = 0
            word_index = 0
            segment_indices = []
            current_segment_index = 0
            while word_index < len(words) - 1:
                segment_indices.append([])
                while (self.sample_lyric_widget.lyric_label.sizeHint().height() <= 920 and word_index < len(words) - 1):
                    if count > 0:
                        self.sample_lyric_widget.lyric_label.setText(
                            self.sample_lyric_widget.lyric_label.text().replace(
                                '</p>', '') + ' ' + words[word_index].strip() + ' </p>')
                    else:
                        self.sample_lyric_widget.lyric_label.setText(
                            '<p style="text-align: center; line-height: 120%;">' + words[
                                word_index].strip() + ' </p>')
                    self.sample_lyric_widget.lyric_label.adjustSize()
                    segment_indices[current_segment_index].append(word_index)
                    word_index += 1
                    count += 1

                if len(segment_indices[current_segment_index]) > 1 and word_index < len(words) - 1:
                    segment_indices[current_segment_index].pop(len(segment_indices[current_segment_index]) - 1)
                    word_index -= 1
                    current_segment_index += 1
                elif word_index == len(words) - 1:
                    segment_indices[current_segment_index].append(word_index)

                self.sample_lyric_widget.lyric_label.setText('<p style="text-align: center; line-height: 120%;">')
                self.sample_lyric_widget.lyric_label.adjustSize()
                count = 0

            for indices in segment_indices:
                if len(indices) > 0:
                    current_segment = ''
                    for index in indices:
                        current_segment += words[index] + ' '
                    slide_texts.append(current_segment)
        else:
            slide_texts.append(f'<p style="text-align: center; line-height: 120%;">{text}</p>')

        return slide_texts

    def parse_scripture_by_verse(self, text):
        """
        Take a passage of scripture and split it according to how many verses will fit on the display screen, given
        the current font and size.
        :param str text: The bible passage to be split
        """
        # configure the hidden sample widget according to the current font
        self.sample_lyric_widget.setFont(
            QFont(self.global_font_face, self.global_font_size, QFont.Weight.Bold))
        self.sample_lyric_widget.setText(
            '<p style="text-align: center; line-height: 120%;">' + text + '<p>')
        self.sample_lyric_widget.footer_label.setText('bogus reference') # just a placeholder
        self.sample_lyric_widget.footer_label.adjustSize()
        self.sample_lyric_widget.paint_text()

        # get the size values for the lyric widget, footer label, and font metrics
        slide_texts = []
        lyric_widget_height = self.sample_lyric_widget.path.boundingRect().adjusted(
            0, 0, self.sample_lyric_widget.outline_width, self.sample_lyric_widget.outline_width).height()
        secondary_screen_height = self.secondary_screen.size().height()
        font_height = self.sample_lyric_widget.fontMetrics().height()
        footer_label_height = self.sample_lyric_widget.footer_label.height()
        preferred_height = secondary_screen_height - footer_label_height

        if lyric_widget_height > preferred_height:
            # walk through the text to locate and index the verse numbers
            verse_indices = []
            skip_next = False
            for i in range(len(text)):
                if text[i].isnumeric() and not skip_next:
                    verse_indices.append(i)
                    if i < len(text) - 1 and text[i + 1].isnumeric():
                        skip_next = True
                else:
                    skip_next = False

            verses = []
            start_index = 0
            for index in verse_indices:
                verses.append(text[start_index:index].strip())
                start_index = index
            verses.append(text[start_index:].strip())
            verses.pop(0)

            self.sample_lyric_widget.setText('<p style="text-align: center; line-height: 120%;">')
            self.sample_lyric_widget.paint_text()

            verse_index = 0
            segment_indices = []
            current_segment_index = 0
            recursion_count = 0
            parse_failed = False
            while verse_index < len(verses):
                recursion_count += 1
                if recursion_count > 1000:
                    parse_failed = True
                    break

                # keep adding verses until the text overflows its widget, remove the last verse, and add to the slide texts
                segment_indices.append([])
                lyric_widget_height = 0
                count = 0
                while lyric_widget_height < preferred_height:
                    if count > 0:
                        if verse_index < len(verses):
                            self.sample_lyric_widget.setText(self.sample_lyric_widget.text + ' ' + verses[verse_index])
                            self.sample_lyric_widget.paint_text()

                            lyric_widget_height = self.sample_lyric_widget.path.boundingRect().adjusted(
                                0, 0, self.sample_lyric_widget.outline_width,
                                self.sample_lyric_widget.outline_width).height()
                        else:
                            break
                    else:
                        self.sample_lyric_widget.setText(verses[verse_index])
                        self.sample_lyric_widget.paint_text()

                        lyric_widget_height = self.sample_lyric_widget.path.boundingRect().adjusted(
                        0, 0, self.sample_lyric_widget.outline_width,
                            self.sample_lyric_widget.outline_width).height()

                    segment_indices[current_segment_index].append(verse_index)
                    count += 1
                    verse_index += 1

                if len(segment_indices[current_segment_index]) > 1:
                    segment_indices[current_segment_index].pop(len(segment_indices[current_segment_index]) - 1)
                    verse_index -= 1
                elif not verse_index == len(verses):
                    verse_index -= 1
                current_segment_index += 1

            # show an error message should parsing fail for some reason
            if parse_failed:
                QMessageBox.information(
                    self.main_window,
                    'Scripture parsing failed',
                    f'Failed parsing scripture into slides. Using one verse per slide.'
                    f'\n\n"{verses[0][:30]}..."',
                    QMessageBox.StandardButton.Ok
                )
                for verse in verses:
                    if len(verse.strip()) > 0:
                        slide_texts.append(verse.strip())
            else:
                for indices in segment_indices:
                    if len(indices) > 0:
                        current_segment = ''
                        for index in indices:
                            current_segment += verses[index] + ' '
                        slide_texts.append(current_segment.strip())
        else:
            slide_texts.append(text)

        return slide_texts


class TimedPreviewUpdate(QRunnable):
    """
    Used to update the preview image in the live widget when a video is playing.
    """
    gui = None
    def __init__(self, gui):
        """
        Used to update the preview image in the live widget when a video is playing.
        :param gui.GUI gui: The current instance of GUI
        """
        super().__init__()
        self.gui = gui
        self.stop = False

    def run(self):
        while not self.stop:
            self.gui.grab_display_signal.emit()
            time.sleep(1.0)
