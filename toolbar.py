import os
import shutil

from PyQt5.QtCore import QSize, QPoint
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QFileDialog

from openlp_import import OpenLPImport
from settings_widget import SettingsWidget
from widgets import ImageCombobox, FontWidget


class Toolbar(QWidget):
    layout = None
    font_widget = None
    song_background_combobox = None
    bible_background_combobox = None
    sw = None

    def __init__(self, gui):
        super().__init__()
        self.gui = gui

    def init_components(self):
        self.setObjectName('toolbar')
        self.layout = QHBoxLayout(self)
        self.setMaximumHeight(60)

        save_button = QPushButton()
        save_button.setIcon(QIcon('resources/gui_icons/save.svg'))
        save_button.setToolTip('Save this Order of Service')
        save_button.setIconSize(QSize(36, 36))
        save_button.clicked.connect(self.gui.main.save_service)
        self.layout.addWidget(save_button)

        load_button = QPushButton()
        load_button.setIcon(QIcon('resources/gui_icons/open.svg'))
        load_button.setToolTip('Load a Service')
        load_button.setIconSize(QSize(36, 36))
        load_button.clicked.connect(self.gui.main.load_service)
        self.layout.addWidget(load_button)

        new_button = QPushButton()
        new_button.setIcon(QIcon('resources/gui_icons/new.svg'))
        new_button.setToolTip('Create a New Service')
        new_button.setIconSize(QSize(36, 36))
        new_button.clicked.connect(self.gui.new_service)
        self.layout.addWidget(new_button)

        settings_button = QPushButton()
        settings_button.setIcon(QIcon('resources/gui_icons/settings.svg'))
        settings_button.setToolTip('Open Program Settings')
        settings_button.setIconSize(QSize(36, 36))
        settings_button.clicked.connect(self.open_settings)
        self.layout.addWidget(settings_button)

        self.layout.addStretch()

        self.song_font_widget = FontWidget(self.gui, 'song')
        self.song_font_widget.hide()

        song_background_label = QLabel('Global Song Settings:')
        song_background_label.setFont(self.gui.standard_font)
        self.layout.addWidget(song_background_label)

        self.song_font_button = QPushButton()
        self.song_font_button.setObjectName('song_font_button')
        self.song_font_button.setIcon(QIcon('resources/gui_icons/font_settings.svg'))
        self.song_font_button.setIconSize(QSize(36, 36))
        self.song_font_button.setToolTip('Change Font Settings')
        self.song_font_button.setFont(self.gui.standard_font)
        self.song_font_button.clicked.connect(self.song_font_widget.show)
        self.layout.addWidget(self.song_font_button)

        self.song_background_combobox = ImageCombobox(self.gui, 'song')
        self.song_background_combobox.setObjectName('song_background_combobox')
        self.song_background_combobox.setToolTip('Choose a Background for All Songs')
        self.layout.addWidget(self.song_background_combobox)

        self.bible_font_widget = FontWidget(self.gui, 'bible')
        self.bible_font_widget.hide()

        bible_background_label = QLabel('Global Bible Settings:')
        bible_background_label.setFont(self.gui.standard_font)
        self.layout.addWidget(bible_background_label)

        self.bible_font_button = QPushButton()
        self.bible_font_button.setObjectName('bible_font_button')
        self.bible_font_button.setIcon(QIcon('resources/gui_icons/font_settings.svg'))
        self.bible_font_button.setIconSize(QSize(36, 36))
        self.bible_font_button.setToolTip('Change Font Settings')
        self.bible_font_button.setFont(self.gui.standard_font)
        self.bible_font_button.clicked.connect(self.bible_font_widget.show)
        self.layout.addWidget(self.bible_font_button)

        self.bible_background_combobox = ImageCombobox(self.gui, 'bible')
        self.bible_background_combobox.setObjectName('bible_background_combobox')
        self.bible_background_combobox.setToolTip('Choose a Background for Bible Slides')
        self.layout.addWidget(self.bible_background_combobox)

        self.layout.addStretch()

        self.show_display_button = QPushButton()
        self.show_display_button.setIcon(QIcon('resources/gui_icons/no_display.svg'))
        self.show_display_button.setToolTip('Show/Hide the Display Screen')
        self.show_display_button.setIconSize(QSize(36, 36))
        self.show_display_button.setFixedSize(48, 48)
        self.show_display_button.setCheckable(True)
        self.show_display_button.pressed.connect(self.gui.show_hide_display_screen)
        self.layout.addWidget(self.show_display_button)

        self.black_screen_button = QPushButton()
        self.black_screen_button.setIcon(QIcon('resources/gui_icons/black_display.svg'))
        self.black_screen_button.setToolTip('Show a Black Screen')
        self.black_screen_button.setIconSize(QSize(36, 36))
        self.black_screen_button.setFixedSize(48, 48)
        self.black_screen_button.setCheckable(True)
        self.black_screen_button.pressed.connect(self.gui.display_black_screen)
        self.layout.addWidget(self.black_screen_button)

        self.logo_screen_button = QPushButton()
        self.logo_screen_button.setIcon(QIcon('resources/gui_icons/logo_display.svg'))
        self.logo_screen_button.setToolTip('Show the Logo Screen')
        self.logo_screen_button.setIconSize(QSize(36, 36))
        self.logo_screen_button.setFixedSize(48, 48)
        self.logo_screen_button.setCheckable(True)
        self.logo_screen_button.pressed.connect(self.gui.display_logo_screen)
        self.layout.addWidget(self.logo_screen_button)

    def import_songs(self):
       self.olpi = OpenLPImport(self.gui)

    def open_settings(self):
        self.sw = SettingsWidget(self.gui)

    def import_background(self):
        result = QFileDialog.getOpenFileName(
            self.gui.main_window, 'Choose Background Image', os.path.expanduser('~') + '/Pictures')
        if len(result[0]) > 0:
            try:
                file_name_split = result[0].split('/')
                file_name = file_name_split[len(file_name_split) - 1]
                shutil.copy(result[0], self.gui.main.background_dir + '/' + file_name)
            except Exception:
                self.gui.main.error_log()

            from main import IndexImages
            ii = IndexImages(self.gui.main, 'backgrounds')
            ii.add_image_index(self.gui.main.background_dir + '/' + file_name, 'background')
            self.song_background_combobox.blockSignals(True)
            self.song_background_combobox.refresh()
            self.song_background_combobox.update()
            self.bible_background_combobox.refresh()
            self.bible_background_combobox.update()
            self.song_background_combobox.blockSignals(False)
            self.gui.apply_settings()

    def change_background(self):
        sender = self.sender()

        if 'Global' in sender.currentText():
            return
        elif 'Import' in sender.currentText():
            self.import_background()
        else:
            data = sender.itemData(sender.currentIndex())
            if data:
                if 'song' in sender.objectName():
                    self.gui.set_song_background(self.gui.main.background_dir + '/' + data)
                    if self.gui.live_widget.slide_list.currentItem():
                        if self.gui.live_widget.slide_list.currentItem().data(40) == 'song':
                            self.gui.display_widget.background_label.clear()
                            self.gui.display_widget.setStyleSheet('#display_widget { background-color: none } ')
                            self.gui.display_widget.background_label.setPixmap(self.gui.global_song_background_pixmap)

                            self.gui.sample_widget.background_label.clear()
                            self.gui.sample_widget.setStyleSheet('#display_widget { background-color: none } ')
                            self.gui.sample_widget.background_label.setPixmap(self.gui.global_song_background_pixmap)

                elif 'bible' in sender.objectName():
                    self.gui.set_bible_background(self.gui.main.background_dir + '/' + data)
                    if self.gui.live_widget.slide_list.currentItem():
                        if self.gui.live_widget.slide_list.currentItem().data(40) == 'bible':
                            self.gui.display_widget.background_label.clear()
                            self.gui.display_widget.setStyleSheet('#display_widget { background-color: none } ')
                            self.gui.display_widget.background_label.setPixmap(self.gui.global_bible_background_pixmap)

                            self.gui.sample_widget.background_label.clear()
                            self.gui.sample_widget.setStyleSheet('#display_widget { background-color: none } ')
                            self.gui.sample_widget.background_label.setPixmap(self.gui.global_bible_background_pixmap)

                elif 'logo' in sender.objectName():
                    self.gui.set_logo_image(self.gui.main.image_dir + '/' + data)
                    if self.gui.logo_widget.isVisible():
                        self.gui.logo_label.clear()
                        self.gui.logo_label.setPixmap(self.gui.logo_pixmap)

    def paintEvent(self, evt):
        self.song_font_widget.adjustSize()
        self.bible_font_widget.adjustSize()
        self.song_font_widget.move(
            self.mapToGlobal(
                QPoint(self.song_font_button.x(), self.song_font_button.y() + self.song_font_button.height())))
        self.bible_font_widget.move(
            self.mapToGlobal(
                QPoint(self.bible_font_button.x(), self.bible_font_button.y() + self.bible_font_button.height())))
        if self.bible_font_widget.x() + self.bible_font_widget.width() > self.gui.main_window.width():
            self.bible_font_widget.move(
                self.mapToGlobal(
                    QPoint(self.gui.main_window.width() - self.bible_font_widget.width(),
                           self.bible_font_button.y() + self.bible_font_button.height())))
