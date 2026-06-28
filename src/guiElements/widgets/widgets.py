import os
import re
import shutil
import sqlite3
import sys
from os.path import exists

import requests
from PyQt5 import sip
from PyQt5.QtCore import Qt, QSize, QEvent, QMargins, QPointF, QTimer, pyqtSignal, QRect, QRectF, QPoint, QSizeF, QTime, \
    QModelIndex, QObject, QByteArray, QBuffer, QIODevice, QUrl
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor, QPainterPath, QBrush, QPen, QPainter, \
    QImage, QFontDatabase, QFontMetrics, QFocusEvent, QMouseEvent, QResizeEvent, \
    QPaintEvent, QWheelEvent, QHideEvent, QTextDocument, QDropEvent, QKeyEvent, QMoveEvent, QShowEvent
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QGraphicsVideoItem, QVideoWidget
from PyQt5.QtPrintSupport import QPrinterInfo, QPrinter
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtWidgets import QListWidget, QLabel, QListWidgetItem, QComboBox, QListView, QWidget, QVBoxLayout, \
    QGridLayout, QSlider, QMainWindow, QMessageBox, QScrollArea, QLineEdit, QHBoxLayout, \
    QSpinBox, QRadioButton, QButtonGroup, QCheckBox, QColorDialog, QGraphicsRectItem, QDialog, QTextEdit, QPushButton, \
    QApplication, QFontComboBox, QGroupBox, QTabWidget, QTimeEdit, QFileDialog, QStyledItemDelegate, QTreeWidget, \
    QTreeWidgetItem, QMenu, QAction, QStyleOptionViewItem, QProgressBar, QGraphicsView, \
    QGraphicsScene, QStackedWidget, QSizePolicy

from core.runnables import SlideAutoPlay, TimedPreviewUpdate
from dataHandling.parsers import get_qcolor_from_str
from importExport.openlpImport import OpenLPImport


class AutoSelectLineEdit(QLineEdit):
    """
    Implements QLineEdit to add the ability to select all text when this line edit receives focus.
    """
    def __init__(self):
        super().__init__()

    def focusInEvent(self, evt: QFocusEvent):
        super().focusInEvent(evt)
        QTimer.singleShot(0, self.selectAll)


class ClickableColorSwatch(QLabel):
    color_changed = pyqtSignal()
    def __init__(self, gui, settings_widget: QWidget = None):
        super().__init__()
        self.gui = gui
        self.settings_widget = settings_widget

    def make_color_swatch_pixmap(self, rgb_color: str):
        if 'rgba' in rgb_color:
            bg_color = rgb_color.replace('rgba(', '').replace(')', '')
        else:
            bg_color = rgb_color.replace('rgb(', '').replace(')', '')
        bg_color_split = bg_color.split(', ')

        if len(bg_color_split) == 4:
            brush = QBrush(
                QColor(int(bg_color_split[0]), int(bg_color_split[1]), int(bg_color_split[2]), int(bg_color_split[3])))
        else:
            brush = QBrush(
                QColor(int(bg_color_split[0]), int(bg_color_split[1]), int(bg_color_split[2])))
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        pen = QPen(Qt.GlobalColor.black)
        pen.setWidth(2)

        pixmap = QPixmap(48, 48)
        painter = QPainter(pixmap)
        painter.setBrush(brush)
        painter.setPen(pen)
        painter.setPen(Qt.GlobalColor.black)

        painter.fillRect(0, 0, 48, 48, brush)
        painter.drawRect(QRect(0, 0, 48, 48))
        painter.end()

        self.setPixmap(pixmap)
        self.repaint()

    def mouseReleaseEvent(self, evt: QMouseEvent):
        super().mouseReleaseEvent(evt)
        image = self.pixmap().toImage()
        current_color = image.pixelColor(10, 10)
        chosen_color = QColorDialog.getColor(current_color, self.gui.main_window, 'Countdown Background Color')
        rgb_color = f'rgba({chosen_color.red()}, {chosen_color.green()}, {chosen_color.blue()}, {chosen_color.alpha()})'
        self.make_color_swatch_pixmap(rgb_color)
        self.color_changed.emit()
        if self.settings_widget:
            self.settings_widget.raise_()
            self.settings_widget.activateWindow()


class CountdownWidget(QWidget):
    update_label_signal = pyqtSignal(str)
    show_self_signal = pyqtSignal()
    hide_self_signal = pyqtSignal()

    def __init__(self, gui, font: QFont, position: str, bg: str, fg: str):
        super().__init__()
        self.gui = gui

        self.update_label_signal.connect(self.update_label)
        self.show_self_signal.connect(self.show_self)
        self.hide_self_signal.connect(self.hide_self)

        self.setWindowFlag(Qt.WindowType.ToolTip)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

        self.setStyleSheet('background-color: ' + bg)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QGridLayout(self)

        self.label = QLabel()
        self.label.setFont(font)
        self.label.setStyleSheet('color: ' + fg)
        layout.addWidget(self.label, 0, 0, Qt.AlignmentFlag.AlignCenter)

        font_metrics = QFontMetrics(font)
        font_height = font_metrics.height()
        height = font_height + 40

        x = 0
        y = 0
        width = 0
        if position == 'top_full':
            x = gui.display_widget.x()
            y = gui.display_widget.y()
            width = gui.display_widget.width()
        elif position == 'bottom_full':
            x = gui.display_widget.x()
            y = gui.display_widget.y() + gui.display_widget.height() - height
            width = gui.display_widget.width()

        self.setGeometry(QRect(x, y, width, height))

    def update_label(self, text):
        self.label.setText(text)

    def show_self(self):
        self.show()
        self.gui.main.app.processEvents()

    def hide_self(self):
        self.hide()
        self.gui.main.app.processEvents()


class CustomMainWindow(QMainWindow):
    """
    Provides added functionality to QMainWindow, such as save on close
    """
    def __init__(self, gui):
        """
        Provides added functionality to QMainWindow, such as save on close and key bindings
        :param guiElements.GUI gui:
        """
        super().__init__()
        self.gui = gui

    def closeEvent(self, evt: QEvent):
        """
        Checks for unsaved changes and prompts the user to save
        :param QEvent evt: closeEvent
        :return:
        """
        continue_close = False
        if self.gui.oos_widget.oos_list_widget.count() > 0 and self.gui.changes:
            response = QMessageBox.question(
                self.gui.main_window,
                'Save Changes',
                'Changes have been made. Save changes?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )

            if response == QMessageBox.StandardButton.Yes:
                result = self.gui.main.save_service()
                if result == 1:
                    continue_close = True
                else:
                    continue_close = False
                    evt.ignore()
            elif response == QMessageBox.StandardButton.No:
                continue_close = True
            else:
                evt.ignore()
        else:
            continue_close = True

        if continue_close:
            # shutdown the media player
            if self.gui.display_widget.media_player and not sip.isdeleted(self.gui.display_widget.media_player):
                if self.gui.display_widget.media_player.state() == QMediaPlayer.PlayingState:
                    self.gui.display_widget.media_player.stop()

            # shut down the server check timer
            if self.gui.main.server_check_timer:
                self.gui.main.server_check_timer.keep_checking = False
                self.gui.main.server_check_timer.stop()

            # shut down the countdown timer and remove the countdown widget
            if self.gui.countdown_timer:
                self.gui.countdown_timer.stop()
            if self.gui.countdown_widget:
                self.gui.countdown_widget.deleteLater()

            # shut down the timed_update
            if self.gui.timed_update:
                self.gui.timed_update.keep_running = False

            # shut down the slide auto-play
            if self.gui.display_widget.slide_auto_play:
                self.gui.display_widget.slide_auto_play.keep_running = False

            self.gui.main.save_settings()
            self.gui.display_widget.deleteLater()
            evt.accept()


class CustomScrollArea(QScrollArea):
    """
    A simple reimplementation of QScrollArea to ensure that its widget gets resized if the scroll area is resized
    """
    def __init__(self):
        super().__init__()

    def resizeEvent(self, evt: QResizeEvent):
        self.widget().setFixedWidth(self.width())


class CustomSlider(QSlider):
    def __init__(self):
        super().__init__()
        self.mouse_pressed = False

    def mousePressEvent(self, evt: QMouseEvent):
        self.mouse_pressed = True
        super().mousePressEvent(evt)

    def mouseReleaseEvent(self, evt: QMouseEvent):
        self.mouse_pressed = False
        super().mouseReleaseEvent(evt)


class DisplayWidget(QStackedWidget):
    """
    Provides a custom QWidget to be used as the display widget
    """
    def __init__(self, gui):
        """
        Provides a custom QWidget to be used as the display widget
        :param guiElements.GUI gui: The current instance of GUI
        :param bool sample: Whether this is intended to be the sample widget
        """
        super().__init__()
        self.gui = gui

        self.background_label = QLabel()
        self.lyric_widget = LyricDisplayWidget(self.gui)
        self.blackout_widget = QWidget()
        self.logo_label = QLabel()
        self.web_view = QWebEngineView()
        from guiElements.gui import CustomWebEnginePage
        self.web_engine_page = CustomWebEnginePage()
        self.video_widget, self.media_player = self.make_video_widget()
        self.slide_auto_play = None
        self.last_current_widget = None
        self.slide_auto_play = None

        self.init_components()

    def init_components(self):
        self.setObjectName('display_widget')
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet('#display_widget { background: black; }')

        self.addWidget(self.lyric_widget)

        self.blackout_widget.setStyleSheet('background-color: #000000;')
        self.blackout_widget.setParent(self)
        self.addWidget(self.blackout_widget)

        self.addWidget(self.logo_label)

        self.web_view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.web_view.setStyleSheet("background: transparent;")
        self.web_view.setParent(self)
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)  # rarely needed for video
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        self.web_engine_page.setParent(self.web_view)
        self.web_view.setPage(self.web_engine_page)
        self.addWidget(self.web_view)

        self.addWidget(self.video_widget)

    def make_lyric_widget(self):
        widget = QWidget()
        widget.setParent(self)

        self.background_label.setObjectName('background_label')
        self.background_label.setParent(widget)

        self.lyric_widget.setObjectName('lyric_widget')
        self.lyric_widget.setParent(widget)
        self.lyric_widget.setStyleSheet('border: 3px solid darkGreen;')

        return widget

    def make_video_widget(self) -> tuple[QGraphicsView, QMediaPlayer]:
        video_widget = QVideoWidget()

        media_player = QMediaPlayer()
        media_player.setVideoOutput(video_widget)

        def media_error(err):
            QMessageBox.information(self.gui.main_window, f'Media Error', 'Unable to play video:\n{err}',
                                    QMessageBox.StandardButton.Ok)
        media_player.error.connect(media_error)

        def duration_changed(duration):
            self.gui.live_widget.seek_slider.setMaximum(duration)
            self.gui.live_widget.seek_slider.setEnabled(True)
            total_seconds = duration // 1000
            hours = total_seconds // 3600
            minutes = (total_seconds // 60) % 60
            seconds = total_seconds % 60
            self.gui.live_widget.video_end_label.setText(f'{hours:01d}:{minutes:02d}:{seconds:02d}')
        media_player.durationChanged.connect(duration_changed)

        def position_changed(position):
            if media_player.state() == QMediaPlayer.StoppedState and position > 0:
                position = 0
            self.gui.live_widget.seek_slider.setValue(position)
            total_seconds = position // 1000
            hours = total_seconds // 3600
            minutes = (total_seconds // 60) % 60
            seconds = total_seconds % 60
            self.gui.live_widget.video_current_label.setText(f'{hours:01d}:{minutes:02d}:{seconds:02d}')
        media_player.positionChanged.connect(position_changed)

        def media_status_changed(status):
            if status == QMediaPlayer.EndOfMedia:
                media_player.pause()
                media_player.setPosition(0)
        media_player.mediaStatusChanged.connect(media_status_changed)

        return video_widget, media_player

    def show_hide(self):
        if self.gui.tool_bar.hide_display_button.isChecked():
            self.hide()
        else:
            self.show()

    def show_logo(self, checked: bool | None = None):
        if checked is not None:
            if checked:
                self.setCurrentWidget(self.logo_label)
                self.gui.tool_bar.black_screen_button.setChecked(False)
            elif self.last_current_widget is not None:
                self.setCurrentWidget(self.last_current_widget)
        else:
            self.setCurrentWidget(self.logo_label)

    def show_black_screen(self, checked: bool | None = None):
        if checked is not None:
            if checked:
                self.setCurrentWidget(self.blackout_widget)
                self.gui.tool_bar.logo_screen_button.setChecked(False)
            elif self.last_current_widget is not None:
                self.setCurrentWidget(self.last_current_widget)
        else:
            self.setCurrentWidget(self.blackout_widget)

    def show_lyric_widget(self):
        self.setCurrentWidget(self.lyric_widget)

    def show_web_view(self):
        self.setCurrentWidget(self.web_view)

    def show_video_widget(self):
        self.setCurrentWidget(self.graphics_view)

    def change_display(self):
        """
        Method to change what it being displayed in the display widget or the hidden sample widget.
        :param str widget: 'live' or 'sample' widget that is being changed
        """
        # we don't need things being futzed with while the program is still starting up
        if self.gui.main.initial_startup:
            return

        auto_play_text = ''

        # stop timed update if it's running
        if self.gui.timed_update:
            self.gui.timed_update.keep_running = False
            self.gui.timed_update = None

        # handle stopping the media player carefully to avoid an Access Violation
        if self.media_player:
            if self.media_player.state == QMediaPlayer.PlayingState:
                self.media_player.pause()
                self.media_player.setPosition(0)

            # return statusChanged to its default function in case loop audio has been used
            def media_status_changed(status):
                if status == QMediaPlayer.EndOfMedia:
                    self.media_player.pause()
                    self.media_player.setPosition(0)
            self.media_player.mediaStatusChanged.connect(media_status_changed)

        item_data = self.gui.live_widget.slide_list.currentItem().data(Qt.ItemDataRole.UserRole).copy()

        # stop slide auto-play if it's running and this slide isn't auto play
        if self.slide_auto_play and not item_data['auto_play']:
            self.slide_auto_play.keep_running = False
            self.slide_auto_play = None

        # show the appropriate widget and start any media, but not if this isn't being done live
        if (item_data['type'] == 'song'
                or item_data['type'] == 'bible'
                or item_data['type'] == 'custom'
                or item_data['type'] == 'image'):
            self.setCurrentWidget(self.lyric_widget)

            # start playing audio if this is a custom slide with audio, but only if audio isn't already playing
            if (item_data['type'] == 'custom'
                    and item_data['audio_file']
                    and len(item_data['audio_file']) > 0
                    and not self.media_player):
                audio_data = self.gui.main.get_audio_data(item_data['audio_file'])
                if audio_data == -2:
                    QMessageBox.critical(
                        self.gui.main_window,
                        'Missing Audio File',
                        f'The audio named {item_data["audio_file"]} is missing. Unable to play sound.',
                        QMessageBox.StandardButton.Ok
                    )
                    return
                elif audio_data == -1:
                    QMessageBox.critical(
                        self.gui.main_window,
                        'Audio Data Error',
                        'Error loading the audio. Unable to play sound.',
                        QMessageBox.StandardButton.Ok
                    )
                else:
                    byte_array = QByteArray(audio_data[0])
                    audio_buffer = QBuffer()
                    audio_buffer.setData(byte_array)
                    audio_buffer.open(QIODevice.ReadOnly)
                    self.media_player.setMedia(QMediaContent(), self.audio_buffer)

                    if item_data['loop_audio'] is True:
                        def repeat_media():
                            if self.media_player.mediaStatus() == QMediaPlayer.EndOfMedia:
                                self.media_player.play()

                        self.media_player.mediaStatusChanged.connect(repeat_media)
                    else:
                        self.media_player.stateChanged.connect(self.media_playing_change)

                    self.media_player.play()

            # cycle through text paragraphs if auto-play is enabled for this custom slide
            if item_data['auto_play'] and not self.slide_auto_play:
                # if we're moving from one auto-play slide to another, the interval may be different
                self.slide_auto_play = SlideAutoPlay(self.gui,  item_data['slide_delay'])
                self.gui.main.thread_pool.start(self.slide_auto_play)
            elif item_data['auto_play'] and self.slide_auto_play:
                # if we're moving from one auto-play slide to another, the interval may be different
                self.slide_auto_play.interval = item_data['slide_delay']
        elif item_data['type'] == 'video':
            self.setCurrentWidget(self.video_widget)
            media = QMediaContent(QUrl.fromLocalFile(self.gui.main.video_dir + '/' + item_data['file_name']))
            self.media_player.setMedia(media)
            self.media_player.play()
            # start the timed update so that the live preview and stage view is updated at regular intervals
            self.gui.timed_update = TimedPreviewUpdate(self.gui)
            self.gui.main.thread_pool.start(self.gui.timed_update)
        elif item_data['type'] == 'web':
            self.setCurrentWidget(self.web_view)
            self.web_engine_page.load(QUrl(item_data['url']))
            # start the timed update so that the live preview and stage view is updated at regular intervals
            self.gui.timed_update = TimedPreviewUpdate(self.gui)
            self.gui.main.thread_pool.start(self.gui.timed_update)

        # change the preview image
        full_size_pixmap = self.grab(self.rect())
        pixmap = full_size_pixmap.scaled(
            int(self.width() / 5),
            int(self.height() / 5),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        stage_html = re.sub('<p.*?>', '', self.lyric_widget.text)
        stage_html = stage_html.replace('</p>', '')
        stage_html = f'<p style="align-text: center;">{stage_html}</p>'

        slide_number = self.gui.live_widget.slide_list.currentRow() + 1
        num_slides = self.gui.live_widget.slide_list.count()
        slide_info = f'Slide {slide_number} of {num_slides}'

        if not item_data['type'] == 'web' and not item_data['type'] == 'video' and not auto_play_text:
            self.gui.live_widget.preview_label.setPixmap(pixmap)

            if 'mirror_stage_display' in self.gui.main.settings.keys() and self.gui.main.settings['mirror_stage_display']:
                buffer = QBuffer()
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)

                success = full_size_pixmap.save(buffer, 'JPEG', 70)

                if success:
                    jpg_bytes = buffer.data().data()
                    self.gui.main.remote_server.socketio.emit('update_display', [jpg_bytes, slide_info])
                else:
                    print("Failed to save pixmap as JPEG!")

                buffer.close()
            else:
                self.gui.main.remote_server.update_stage_text(
                    stage_html, self.gui.main.settings['stage_font_size'], slide_info)
        elif auto_play_text:
            self.gui.live_widget.preview_label.setPixmap(pixmap)
            if 'mirror_stage_display' in self.gui.main.settings.keys() and self.gui.main.settings['mirror_stage_display']:
                buffer = QBuffer()
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)

                success = full_size_pixmap.save(buffer, 'JPEG', 70)

                if success:
                    jpg_bytes = buffer.data().data()
                    self.gui.main.remote_server.socketio.emit('update_display', [jpg_bytes, slide_info])
                else:
                    print("Failed to save pixmap as JPEG!")

                buffer.close()
            else:
                self.gui.main.remote_server.update_stage_text(
                    stage_html, self.gui.main.settings['stage_font_size'], slide_info)
        else:
            if 'mirror_stage_display' in self.gui.main.settings.keys() and self.gui.main.settings[
                    'mirror_stage_display']:
                buffer = QBuffer()
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)

                success = full_size_pixmap.save(buffer, 'JPEG', 70)

                if success:
                    jpg_bytes = buffer.data().data()
                    self.gui.main.remote_server.socketio.emit('update_display', [jpg_bytes, ''])
                else:
                    print("Failed to save pixmap as JPEG!")

                buffer.close()
            else:
                self.gui.main.remote_server.update_stage_text(
                    stage_html, self.gui.main.settings['stage_font_size'], '')

        if not self.currentWidget == self.video_widget:
            self.currentWidget().update()

    def setCurrentWidget(self, widget):
        self.last_current_widget = widget
        super().setCurrentWidget(widget)


class FontFaceListWidget(QListWidget):
    """
    Creates a custom QListWidget that displays all fonts on the system in their own style.
    :param guiElements.GUI gui: The current instance of GUI
    """
    def __init__(self, gui):
        """
        :param guiElements.GUI gui: The current instance of GUI
        """
        super().__init__()
        self.gui = gui
        self.setObjectName('FontFaceListWidget')
        self.setMinimumHeight(60)
        self.blockSignals(True)
        self.populate_widget()
        self.blockSignals(False)

    def populate_widget(self):
        try:
            families = QFontDatabase().families()
            for font in families:
                if self.gui.main.initial_startup:
                    self.gui.main.update_status_signal.emit('Processing Fonts', 'status')
                    self.gui.main.update_status_signal.emit(font, 'info')
                list_label = QLabel(font)
                list_label.setFont(QFont(font, 12))
                item = QListWidgetItem()
                item.setData(20, font)
                self.addItem(item)
                self.setItemWidget(item, list_label)

            if self.gui.main.initial_startup:
                self.gui.main.update_status_signal.emit('', 'info')
        except Exception:
            self.gui.main.error_log()


class FontFaceComboBox(QComboBox):
    """
    Creates a custom QComboBox that displays all fonts on the system in their own style.
    :param guiElements.GUI gui: The current instance of GUI
    """
    current_font = None

    def __init__(self, gui):
        """
        :param guiElements.GUI gui: The current instance of GUI
        """
        super().__init__()
        self.setObjectName('FontFaceComboBox')
        self.gui = gui
        self.setEditable(True)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.populate_widget()

    def populate_widget(self):
        try:
            for i in range(len(self.gui.font_pixmaps)):
                if i == len(self.gui.font_pixmaps) - 1:
                    self.setIconSize(QSize(self.gui.font_pixmaps[i][0], self.gui.font_pixmaps[i][1]))
                    #self.setMinimumWidth(self.guiElements.font_pixmaps[i][0])
                else:
                    self.addItem(QIcon(self.gui.font_pixmaps[i][1]), self.gui.font_pixmaps[i][0])
        except Exception:
            self.gui.main.error_log()

        for i in range(self.count()):
            if self.itemText(i) == self.current_font:
                self.setCurrentIndex(i)
                break

    def wheelEvent(self, evt: QWheelEvent):
        evt.ignore()


class FontSample(QLabel):
    text = ''
    def __init__(self, settings_widget: QWidget,
                 use_outline: bool | None = True,
                 outline_color: QColor | None = QColor(0, 0, 0),
                 outline_width: int | None = 8,
                 fill_color: QColor | None = QColor(255, 255, 255),
                 use_shadow: bool | None = True,
                 shadow_color: QColor | None = QColor(0, 0, 0),
                 shadow_offset: int | None = 5,
                 use_shade: bool | None = False,
                 shade_color: int | None = 0,
                 shade_opacity: int | None = 50,
                 edit_widget: QWidget | None = None):
        super().__init__()
        self.settings_widget = settings_widget
        self.use_outline = use_outline
        self.outline_color = outline_color
        self.outline_width = outline_width
        self.fill_color = fill_color
        self.use_shadow = use_shadow
        self.shadow_color = shadow_color
        self.shadow_offset = shadow_offset
        self.use_shade = use_shade
        self.shade_color = shade_color
        self.shade_opacity = shade_opacity
        self.edit_widget = edit_widget

        self.sample_background = None

        self.container = self.settings_widget.findChild(QWidget, 'font_sample_container')
        self.widget = self.settings_widget.findChild(QWidget, 'font_sample_widget')
        self.background_label = self.settings_widget.findChild(QLabel, 'font_sample_background_label')

    def paintEvent(self, evt: QPaintEvent):
        brush = QBrush()
        pen = QPen()

        path = QPainterPath()
        shadow_path = QPainterPath()
        metrics = self.fontMetrics()

        y = metrics.ascent() - metrics.descent() + 20
        point = QPointF(20, y)
        shadow_point = QPointF(point.x() + self.shadow_offset, point.y() + self.shadow_offset)

        if self.use_shadow:
            shadow_path.addText(shadow_point, self.font(), self.text)
        path.addText(point, self.font(), self.text)
        path_rect = path.boundingRect()

        image_rect = QRectF(0, 0, path_rect.width() + 40, path_rect.height() + 40)
        image = QPixmap(int(image_rect.width()), int(image_rect.height()))

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        background_image = self.make_sample_background(image_rect)
        if background_image:
            painter.drawImage(QPoint(0, 0), background_image)

        opacity = self.shade_opacity
        if not self.use_shade:
            opacity = 0
        brush.setColor(QColor(self.shade_color, self.shade_color, self.shade_color, opacity))
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        shade_rect = QRectF(10, 10, path_rect.width() + 20, path_rect.height() + 20)
        rect_item = QGraphicsRectItem(shade_rect)
        rect_item.setBrush(brush)
        painter.fillRect(shade_rect, brush)

        if self.use_shadow:
            brush.setColor(self.shadow_color)
            pen.setWidth(0)
            painter.fillPath(shadow_path, brush)

        brush.setColor(self.fill_color)
        pen.setColor(self.outline_color)
        pen.setWidth(self.outline_width)
        painter.fillPath(path, brush)

        if self.use_outline:
            painter.setPen(pen)
            painter.drawPath(path)
        painter.end()

        self.setPixmap(image)

        super().paintEvent(evt)

    def make_sample_background(self, rect: QRect):
        slide_type = self.settings_widget.slide_type

        if self.settings_widget.applies_to_global:
            sample_background = QImage(
                self.settings_widget.gui.main.background_dir + '/'
                + self.settings_widget.gui.main.settings[f'global_{slide_type}_background'])
            return sample_background
        elif self.edit_widget:
            background_button_text = self.edit_widget.background_button_group.checkedButton().text()
            if 'global song' in background_button_text.lower():
                sample_background = QImage(
                    self.edit_widget.gui.main.background_dir + '/'
                    + self.edit_widget.gui.main.settings['global_song_background'])
            elif 'global bible' in background_button_text.lower():
                sample_background = QImage(
                    self.edit_widget.gui.main.background_dir + '/'
                    + self.edit_widget.gui.main.settings['global_bible_background'])
            elif 'solid color' in background_button_text.lower():
                background = self.edit_widget.background_button_group.button(2).objectName()
                if not 'rgb' in background:
                    return
                background = background.replace('rgb(', '')
                background = background.replace(')', '')
                background_split = background.split(', ')
                sample_background = QImage(QSize(1920, 1080), QImage.Format.Format_RGB32)
                sample_background.fill(
                    QColor(int(background_split[0]), int(background_split[1]), int(background_split[2])))
            else:
                sample_background = QImage(
                    self.edit_widget.gui.main.background_dir + '/' + self.edit_widget.background_combobox.currentText())

            ratio = sample_background.width() / rect.width()
            # if there was no background yet chosen, ration will be 0
            if ratio > 0:
                sample_background = sample_background.scaled(
                    int(rect.width()),
                    int(sample_background.height() / ratio),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

                piece_rect = QRect(
                    0,
                    int(sample_background.height() / 2) - int(rect.height() / 2),
                    int(rect.width()),
                    int(rect.height())
                )
                sample_background = sample_background.copy(piece_rect)
            else:
                sample_background = QImage(QSize(int(rect.width()), int(rect.height())), QImage.Format_RGB32)
                sample_background.fill(Qt.GlobalColor.black)

            return sample_background

        return -1


class FontWidget(QWidget):
    """
    Implements QWidget that contains all the settings that can be applied to the display font
    """
    mouse_release_signal = pyqtSignal(int)

    def __init__(self, gui, slide_type, draw_border=True, applies_to_global=True):
        """
        Implements QWidget that contains all of the settings that can be applied to the display font
        :param GUI gui: the current instance of GUI
        :param bool draw_border: apply a border to the widgets
        """
        super().__init__()
        self.gui = gui
        self.slide_type = slide_type
        self.draw_border = draw_border
        self.applies_to_global = applies_to_global

        #self.font_face_combobox = FontFaceComboBox(self.guiElements)
        self.font_face_combobox = QFontComboBox()
        self.font_size_spinbox = QSpinBox()
        self.white_radio_button = QRadioButton('White')
        self.black_radio_button = QRadioButton('Black')
        self.custom_font_color_radio_button = QRadioButton('Custom')
        self.font_color_button_group = QButtonGroup()
        self.shadow_color_slider = ShadowSlider(self.gui)
        self.shadow_offset_slider = OffsetSlider(self.gui)
        self.shadow_checkbox = QCheckBox('Use Shadow')
        self.outline_checkbox = QCheckBox('Use Outline')
        self.outline_color_slider = ShadowSlider(self.gui)
        self.outline_width_slider = OffsetSlider(self.gui)
        self.shade_behind_text_checkbox = QCheckBox('Shade Behind Text')

        self.mouse_release_signal.connect(lambda value: self.change_font(value))

        self.setParent(self.gui.main_window)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)
        self.setWindowFlag(Qt.WindowType.Popup)
        self.init_components()

    def init_components(self):
        self.setFixedWidth(950)
        self.setObjectName('font_widget')
        layout = QVBoxLayout(self)

        sample_text = self.slide_type.capitalize() + ' Font Sample'
        self.font_sample = FontSample(self)
        self.font_sample.text = sample_text
        self.font_sample.setObjectName('font_sample')
        layout.addWidget(self.font_sample)

        face_size_widget = QWidget()
        layout.addWidget(face_size_widget)
        face_size_layout = QHBoxLayout(face_size_widget)
        face_size_layout.setContentsMargins(0, 0, 0, 0)

        font_face_widget = QWidget()
        face_size_layout.addWidget(font_face_widget)
        font_face_layout = QVBoxLayout(font_face_widget)
        font_face_layout.setContentsMargins(0, 0, 0, 0)

        font_face_label = QLabel('Font Face')
        font_face_label.setFont(self.gui.bold_font)
        font_face_layout.addWidget(font_face_label)

        self.font_face_combobox.setIconSize(QSize(1, 36))
        self.font_face_combobox.setFont(self.gui.standard_font)
        self.font_face_combobox.currentIndexChanged.connect(self.change_font)
        font_face_layout.addWidget(self.font_face_combobox)

        font_size_widget = QWidget()
        face_size_layout.addWidget(font_size_widget)
        font_size_layout = QVBoxLayout(font_size_widget)
        font_size_layout.setContentsMargins(0, 0, 0, 0)

        font_size_label = QLabel('Font Size:')
        font_size_label.setFont(self.gui.bold_font)
        font_size_layout.addWidget(font_size_label)

        self.font_size_spinbox.setMaximumWidth(100)
        self.font_size_spinbox.setMinimumHeight(40)
        self.font_size_spinbox.setFont(self.gui.standard_font)
        self.font_size_spinbox.setRange(10, 240)
        self.font_size_spinbox.valueChanged.connect(self.change_font)
        self.font_size_spinbox.installEventFilter(self)
        font_size_layout.addWidget(self.font_size_spinbox)

        font_color_widget = QWidget()
        layout.addWidget(font_color_widget)
        font_color_layout = QVBoxLayout(font_color_widget)
        font_color_layout.setContentsMargins(0, 0, 0, 0)

        font_color_label = QLabel('Font Color:')
        font_color_label.setFont(self.gui.bold_font)
        font_color_layout.addWidget(font_color_label)

        color_button_widget = QWidget()
        font_color_layout.addWidget(color_button_widget)
        color_button_layout = QHBoxLayout(color_button_widget)
        color_button_layout.setContentsMargins(0, 0, 0, 0)

        self.white_radio_button.setObjectName('white')
        self.white_radio_button.setFont(self.gui.standard_font)
        color_button_layout.addWidget(self.white_radio_button)

        self.black_radio_button.setObjectName('black')
        self.black_radio_button.setFont(self.gui.standard_font)
        color_button_layout.addWidget(self.black_radio_button)

        self.custom_font_color_radio_button.setObjectName('custom')
        self.custom_font_color_radio_button.setFont(self.gui.standard_font)
        self.custom_font_color_radio_button.setObjectName('custom_font_color_radio_button')
        self.custom_font_color_radio_button.clicked.connect(self.color_chooser)
        color_button_layout.addWidget(self.custom_font_color_radio_button)
        color_button_layout.addStretch()

        self.font_color_button_group.addButton(self.white_radio_button)
        self.font_color_button_group.addButton(self.black_radio_button)
        self.font_color_button_group.addButton(self.custom_font_color_radio_button)
        self.font_color_button_group.buttonClicked.connect(self.change_font)

        shadow_widget = QWidget()
        layout.addSpacing(10)
        layout.addWidget(shadow_widget)
        shadow_layout = QHBoxLayout(shadow_widget)
        shadow_layout.setContentsMargins(0, 0, 0, 0)

        self.shadow_checkbox.setFont(self.gui.bold_font)
        self.shadow_checkbox.clicked.connect(self.change_font)
        shadow_layout.addWidget(self.shadow_checkbox)
        shadow_layout.addStretch()

        self.shadow_color_slider = ShadowSlider(self.gui)
        self.shadow_color_slider.setObjectName('shadow_color_slider')
        shadow_layout.addWidget(self.shadow_color_slider)
        shadow_layout.addSpacing(20)

        self.shadow_offset_slider = OffsetSlider(self.gui)
        self.shadow_offset_slider.setObjectName('shadow_offset_slider')
        shadow_layout.addWidget(self.shadow_offset_slider)

        outline_widget = QWidget()
        layout.addSpacing(10)
        layout.addWidget(outline_widget)
        outline_layout = QHBoxLayout(outline_widget)
        outline_layout.setContentsMargins(0, 0, 0, 0)

        self.outline_checkbox.setFont(self.gui.bold_font)
        self.outline_checkbox.clicked.connect(self.change_font)
        outline_layout.addWidget(self.outline_checkbox)
        outline_layout.addStretch()

        self.outline_color_slider = ShadowSlider(self.gui)
        self.outline_color_slider.setObjectName('outline_color_slider')
        self.outline_color_slider.color_title.setText('Outline Shade:')
        outline_layout.addWidget(self.outline_color_slider)
        outline_layout.addSpacing(20)

        self.outline_width_slider = OffsetSlider(self.gui)
        self.outline_width_slider.setObjectName('outline_width_slider')
        self.outline_width_slider.offset_slider.setRange(1, 10)
        self.outline_width_slider.max_label.setText('10px')
        self.outline_width_slider.offset_title.setText('Outline Width:')
        outline_layout.addWidget(self.outline_width_slider)

        shade_widget = QWidget()
        layout.addSpacing(10)
        layout.addWidget(shade_widget)
        shade_layout = QHBoxLayout(shade_widget)
        shade_layout.setContentsMargins(0, 0, 0, 0)

        self.shade_behind_text_checkbox.setFont(self.gui.bold_font)
        self.shade_behind_text_checkbox.clicked.connect(self.change_font)
        shade_layout.addWidget(self.shade_behind_text_checkbox)
        shade_layout.addStretch()

        self.shade_color_slider = ShadowSlider(self.gui)
        self.shade_color_slider.setObjectName('shade_color_slider')
        shade_layout.addWidget(self.shade_color_slider)
        shade_layout.addSpacing(20)

        self.shade_opacity_slider = ShadowSlider(self.gui)
        self.shade_opacity_slider.setObjectName('shade_opacity_slider')
        self.shade_opacity_slider.color_title.setText('Shade Opacity:')
        self.shade_opacity_slider.color_label.hide()
        self.shade_opacity_slider.min_label.setText('Transparent')
        self.shade_opacity_slider.max_label.setText('Opaque')
        shade_layout.addWidget(self.shade_opacity_slider)

    def blockSignals(self, block: bool):
        """
        method to block the signals of all widgets that would be updated during apply_settings
        """
        super().blockSignals(block)

        # also block all children widgets connected to functions
        self.font_face_combobox.blockSignals(block)
        self.font_size_spinbox.blockSignals(block)
        self.white_radio_button.blockSignals(block)
        self.black_radio_button.blockSignals(block)
        self.custom_font_color_radio_button.blockSignals(block)
        self.font_color_button_group.blockSignals(block)
        self.shadow_checkbox.blockSignals(block)
        self.shadow_color_slider.color_slider.blockSignals(block)
        self.shadow_offset_slider.offset_slider.blockSignals(block)
        self.outline_checkbox.blockSignals(block)
        self.outline_color_slider.color_slider.blockSignals(block)
        self.outline_width_slider.offset_slider.blockSignals(block)

    def apply_settings(self):
        """
        updates the various widgets to match the current settings
        """
        self.blockSignals(True)

        font_face = self.gui.main.settings[f'{self.slide_type}_font_face']
        self.font_face_combobox.setCurrentIndex(self.font_face_combobox.findText(font_face))

        self.font_size_spinbox.setValue(self.gui.main.settings[f'{self.slide_type}_font_size'])

        font_color = self.gui.main.settings[f'{self.slide_type}_font_color']
        if font_color == 'white':
            self.white_radio_button.setChecked(True)
        elif font_color == 'black':
            self.black_radio_button.setChecked(True)
        else:
            self.custom_font_color_radio_button.setChecked(True)
            self.custom_font_color_radio_button.setText('Custom: ' + font_color)
            self.custom_font_color_radio_button.setObjectName(font_color)

        use_shadow = self.gui.main.settings[f'{self.slide_type}_use_shadow']
        shadow_color = self.gui.main.settings[f'{self.slide_type}_shadow_color']
        shadow_offset = self.gui.main.settings[f'{self.slide_type}_shadow_offset']

        if use_shadow:
            self.shadow_checkbox.setChecked(True)
        self.shadow_color_slider.color_slider.setValue(shadow_color)
        self.shadow_color_slider.change_sample(shadow_color)
        self.shadow_offset_slider.offset_slider.setValue(shadow_offset)
        self.shadow_offset_slider.current_label.setText(str(shadow_offset) + 'px')

        use_outline = self.gui.main.settings[f'{self.slide_type}_use_outline']
        outline_color = self.gui.main.settings[f'{self.slide_type}_outline_color']
        outline_width = self.gui.main.settings[f'{self.slide_type}_outline_width']

        self.outline_checkbox.setChecked(use_outline)
        self.outline_color_slider.color_slider.setValue(outline_color)
        self.outline_color_slider.change_sample(outline_color)
        self.outline_width_slider.offset_slider.setValue(outline_width)
        self.outline_width_slider.current_label.setText(str(outline_width) + 'px')
        self.blockSignals(False)

        if f'{self.slide_type}_use_shade' in self.gui.main.settings.keys():
            self.shade_behind_text_checkbox.setChecked(self.gui.main.settings[f'{self.slide_type}_use_shade'])
        if f'{self.slide_type}_shade_color' in self.gui.main.settings.keys():
            self.shade_color_slider.color_slider.setValue(self.gui.main.settings[f'{self.slide_type}_shade_color'])
        if f'{self.slide_type}_shade_opacity' in self.gui.main.settings.keys():
            self.shade_opacity_slider.color_slider.setValue(self.gui.main.settings[f'{self.slide_type}_shade_opacity'])

        self.change_font_sample()

    def change_font(self, value: int | None = None):
        """
        updates ProjectOn.settings to the user's selected font settings
        """

        shadow_color = None
        shadow_offset = None
        outline_color = None
        outline_width = None
        if not self.signalsBlocked() and self.applies_to_global:
            if value:
                if self.sender().objectName() == 'shadow_color_slider':
                    shadow_color = value
                elif self.sender().objectName() == 'shadow_offset_slider':
                    shadow_offset = value
                elif self.sender().objectName() == 'outline_color_slider':
                    outline_color = value
                elif self.sender().objectName() == 'outline_width_slider':
                    outline_width = value

            new_font_face = self.font_face_combobox.currentText()

            self.gui.main.settings[f'{self.slide_type}_font_face'] = self.font_face_combobox.currentText()
            self.gui.main.settings[f'{self.slide_type}_font_size'] = self.font_size_spinbox.value()
            if self.font_color_button_group.checkedButton():
                self.gui.main.settings[f'{self.slide_type}_font_color'] = self.font_color_button_group.checkedButton().objectName()

            self.gui.main.settings[f'{self.slide_type}_use_shadow'] = self.shadow_checkbox.isChecked()
            if shadow_color:
                self.gui.main.settings[f'{self.slide_type}_shadow_color'] = shadow_color
            else:
                self.gui.main.settings[f'{self.slide_type}_shadow_color'] = self.shadow_color_slider.color_slider.value()
            if shadow_offset:
                self.gui.main.settings[f'{self.slide_type}_shadow_offset'] = shadow_offset
            else:
                self.gui.main.settings[f'{self.slide_type}_shadow_offset'] = self.shadow_offset_slider.offset_slider.value()

            self.gui.main.settings[f'{self.slide_type}_use_outline'] = self.outline_checkbox.isChecked()
            if outline_color:
                self.gui.main.settings[f'{self.slide_type}_outline_color'] = outline_color
            else:
                self.gui.main.settings[f'{self.slide_type}_outline_color'] = self.outline_color_slider.color_slider.value()
            if outline_width:
                self.gui.main.settings[f'{self.slide_type}_outline_width'] = outline_width
            else:
                self.gui.main.settings[f'{self.slide_type}_outline_width'] = self.outline_width_slider.offset_slider.value()

            self.gui.main.settings[f'{self.slide_type}_use_shade'] = self.shade_behind_text_checkbox.isChecked()
            self.gui.main.settings[f'{self.slide_type}_shade_color'] = self.shade_color_slider.color_slider.value()
            self.gui.main.settings[f'{self.slide_type}_shade_opacity'] = self.shade_opacity_slider.color_slider.value()

        self.change_font_sample()
        self.font_sample.repaint()

    def change_font_sample(self):
        if self.font_face_combobox.currentText():
            font_name = self.font_face_combobox.currentText()
        else:
            font_name = self.font_face_combobox.itemText(0)

        self.font_sample.setFont(
            QFont(
                font_name,
                self.font_size_spinbox.value(),
                QFont.Weight.Bold))

        if self.font_color_button_group.checkedButton():
            color = self.font_color_button_group.checkedButton().objectName()
        else:
            color = 'black'
            self.black_radio_button.blockSignals(True)
            self.black_radio_button.setChecked(True)
            self.black_radio_button.blockSignals(False)

        if color == 'black':
            self.font_sample.fill_color = QColor(0, 0, 0)
        elif color == 'white':
            self.font_sample.fill_color = QColor(255, 255, 255)
        else:
            fill_color = self.custom_font_color_radio_button.objectName()
            fill_color = fill_color.replace('rgb(', '')
            fill_color = fill_color.replace(')', '')
            fill_color_split = fill_color.split(', ')
            self.font_sample.fill_color = QColor(
                int(fill_color_split[0]), int(fill_color_split[1]), int(fill_color_split[2]))

        if self.shadow_checkbox.isChecked():
            self.font_sample.use_shadow = True
        else:
            self.font_sample.use_shadow = False

        if self.outline_checkbox.isChecked():
            self.font_sample.use_outline = True
        else:
            self.font_sample.use_outline = False

        shadow_color = self.shadow_color_slider.color_slider.value()
        self.font_sample.shadow_color = QColor(shadow_color, shadow_color, shadow_color)
        self.font_sample.shadow_offset = self.shadow_offset_slider.offset_slider.value()

        outline_color = self.outline_color_slider.color_slider.value()
        self.font_sample.outline_color = QColor(outline_color, outline_color, outline_color)
        self.font_sample.outline_width = self.outline_width_slider.offset_slider.value()

        self.font_sample.use_shade = self.shade_behind_text_checkbox.isChecked()
        self.font_sample.shade_color = self.shade_color_slider.color_slider.value()
        self.font_sample.shade_opacity = self.shade_opacity_slider.color_slider.value()

        self.font_sample.repaint()

    def color_chooser(self):
        """
        creates a color dialog for the user to select a custom font color
        """
        sender = self.sender()
        current_color = self.gui.main.settings[f'{self.slide_type}_font_color']
        if current_color == 'white':
            r, g, b = 255, 255, 255
        elif current_color == 'black':
            r, g, b = 0, 0, 0
        else:
            color_split = current_color.split(', ')
            r, g, b = int(color_split[0]), int(color_split[1]), int(color_split[2])

        color = QColorDialog.getColor(QColor(r, g, b), self)
        rgb = color.getRgb()
        if color.isValid():
            color_string = str(rgb[0]) + ', ' + str(rgb[1]) + ', ' + str(rgb[2])
            self.custom_font_color_radio_button.setText('Custom: ' + color_string)
            self.custom_font_color_radio_button.setObjectName(color_string)
            sender.setChecked(True)
            self.change_font()

        self.show()

    def hideEvent(self, evt: QHideEvent):
        """
        overrides hideEvent to save settings when the widget is hidden
        """
        self.gui.main.save_settings()
        self.gui.apply_settings(theme_too=False)
        super().hideEvent(evt)


class ImageCombobox(QComboBox):
    """
    Creates a custom QComboBox that displays a thumbnail of an image to be used.
    """
    def __init__(self, gui, type: str, suppress_autosave: bool | None = False):
        """
        :param guiElements.GUI gui: The current instance of GUI
        :param str type: Whether this is creating a combobox of 'logo', 'song', or 'bible' images
        """
        super().__init__()
        self.gui = gui
        self.type = type
        self.table = None
        self.suppress_autosave = suppress_autosave
        self.setView(QListView())
        self.setObjectName(type)

        self.setIconSize(QSize(96, 54))
        self.setMaximumWidth(240)
        self.setFont(self.gui.standard_font)

        self.currentIndexChanged.connect(self.index_changed)

        if type == 'edit_background':
            self.removeItem(0)
        else:
            self.currentIndexChanged.connect(self.gui.tool_bar.change_background)
        self.refresh()

    def index_changed(self):
        file_name = self.itemData(self.currentIndex(), Qt.ItemDataRole.UserRole)
        if not file_name:
            return
        if self.type == 'logo':
            self.gui.main.settings['logo_image'] = file_name
        elif self.type == 'song':
            self.gui.main.settings['global_song_background'] = file_name
            self.gui.global_song_background_pixmap = QPixmap(self.gui.main.image_dir + '/' + file_name)
        elif self.type == 'bible':
            self.gui.main.settings['global_bible_background'] = file_name
            self.gui.global_bible_background_pixmap = QPixmap(self.gui.main.image_dir + '/' + file_name)

        for i in range(self.gui.oos_widget.oos_list_widget.count()):
            item = self.gui.oos_widget.oos_list_widget.item(i)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            pixmap = None

            if item_data['type'] == 'song' or item_data['type'] == 'bible' or item_data['type'] == 'custom':
                if not item_data['override_global'] or item_data['override_global'] == 'False':
                    if item_data['type'] == self.type:
                        pixmap = self.itemIcon(self.currentIndex()).pixmap(QSize(50, 27))
                    elif item_data['type'] == 'custom' and self.type == 'bible':
                        pixmap = self.itemIcon(self.currentIndex()).pixmap(QSize(50, 27))
                else:
                    if item_data['background'] == 'global_song' and self.type == 'song':
                        pixmap = self.itemIcon(self.currentIndex()).pixmap(QSize(50, 27))
                    elif item_data['background'] == 'global_bible' and self.type == 'bible':
                        pixmap = self.itemIcon(self.currentIndex()).pixmap(QSize(50, 27))

            if pixmap:
                widget = self.gui.oos_widget.oos_list_widget.itemWidget(item)
                widget.icon.setPixmap(pixmap)
                widget.adjustSize()
                item.setSizeHint(widget.sizeHint())

        if not self.suppress_autosave:
            self.gui.main.save_settings()

    def refresh(self):
        """
        Method to refresh the combo box after changes to the image indices
        """
        self.blockSignals(True)
        self.clear()

        if self.type == 'logo':
            self.addItem('Choose Logo Image', userData='choose_logo')
            self.addItem('Import a Logo Image', userData='import_logo')
            self.table = 'imageThumbnails'
        elif self.type == 'edit':
            self.addItem('Choose Custom Background', userData='choose_global')
            self.table = 'backgroundThumbnails'
        elif self.type == 'delete_background':
            self.addItem('Choose Background to Remove')
            self.table = 'backgroundThumbnails'
        elif self.type == 'delete_image':
            self.addItem('Choose Image Item to Remove')
            self.table = 'imageThumbnails'
        else:
            self.addItem('Choose Global ' + self.type + ' Background', userData='choose_global')
            self.addItem('Import a Background Image', userData='import_global')
            self.table = 'backgroundThumbnails'
        connection = None

        try:
            image_list = []
            connection = sqlite3.connect(self.gui.main.database)
            cursor = connection.cursor()
            thumbnails = cursor.execute(
                'SELECT * FROM ' + self.table + ' ORDER BY fileName COLLATE NOCASE ASC;').fetchall()
            self.gui.main.update_status_signal.emit('Loading Thumbnails', 'status')
            for record in thumbnails:
                if self.gui.main.initial_startup:
                    self.gui.main.update_status_signal.emit(record[0], 'info')
                pixmap = QPixmap()
                pixmap.loadFromData(record[1], 'JPG')
                icon = QIcon(pixmap)
                self.addItem(icon, record[0].split('.')[0], userData=record[0])
                image_list.append([icon, record[0].split('.')[0], record[0]])
            connection.close()

            if self.gui.main.initial_startup:
                self.gui.main.update_status_signal.emit('', 'info')

            self.blockSignals(False)
        except Exception:
            self.gui.main.error_log()
            if connection:
                connection.close()
            self.blockSignals(False)

    def wheelEvent(self, evt: QWheelEvent):
        # prevent wheel scrolling, which is undesirable in the settings layout
        evt.ignore()


class LyricDisplayWidget(QWidget):
    """
    Provide a standardized QWidget to be used for showing lyrics on the display and sample widgets.py
    """

    footer_label = None
    def __init__(self, gui):
        """
        Provide a standardized QWidget to be used for showing lyrics on the display and sample widgets.py
        :param guiElements.GUI gui: The current instance of GUI
        :param bool for_sample: Whether this widget is intended for the sample widget or not
        :param bool use_outline: Whether the font is to be outlined
        :param int outline_color: The shade of the font outline (QColor(x, x, x))
        :param int outline_width: The width, in px, of the font outline
        :param fill_color: The fill color of the font
        :param use_shadow: Whether the font is to be shadowed
        :param shadow_color: The shade of the font shadow (QColor(x, x, x))
        :param shadow_offset: The offset, in px, of the shadow
        """
        super().__init__()
        self.gui = gui
        self.text = ''

        self.setObjectName('lyric_display_widget')
        self.setContentsMargins(0, 0, 0, 0)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    def set_font(self, slide_data):
        if 'override_global' in slide_data.keys() and slide_data['override_global']:
            # use all of the relevent font data stored in slide_data
            font = QFont(slide_data['font_family'], slide_data['font_size'])
            fill_color = get_qcolor_from_str(self.gui.main, slide_data['font_color'], slide_data['type'])
            use_shadow = slide_data['use_shadow']
            shadow_color = QColor(
                slide_data['shadow_color'], slide_data['shadow_color'], slide_data['shadow_color'])
            shadow_offset = slide_data['shadow_offset']
            use_outline = slide_data['use_outline']
            outline_color = QColor(
                slide_data['outline_color'], slide_data['outline_color'], slide_data['outline_color'])
            outline_width = slide_data['outline_width']
            use_shade = slide_data['use_shade']
            # needs to be sent as an integer so opacity can be set by the lyric widget
            shade_color = slide_data['shade_color']
            shade_opacity = slide_data['shade_opacity']
        else:
            # use the relevent font settings stored in ProjectOn.settings
            slide_type = slide_data['type']
            if not slide_type == 'song':
                slide_type = 'bible'

            # Set the main font face, size, and color
            font = QFont(
                self.gui.main.settings[f'{slide_type}_font_face'],
                self.gui.main.settings[f'{slide_type}_font_size']
            )

            fill_color = get_qcolor_from_str(
                self.gui.main, self.gui.main.settings[f'{slide_type}_font_color'], slide_type)

            # Set the font shadow
            use_shadow = self.gui.main.settings[f'{slide_type}_use_shadow']
            shadow_color = QColor(
                self.gui.main.settings[f'{slide_type}_shadow_color'],
                self.gui.main.settings[f'{slide_type}_shadow_color'],
                self.gui.main.settings[f'{slide_type}_shadow_color']
            )
            shadow_offset = self.gui.main.settings[
                f'{slide_type}_shadow_offset']

            # Set the font outline
            use_outline = self.gui.main.settings[f'{slide_type}_use_outline']
            outline_color = QColor(
                self.gui.main.settings[f'{slide_type}_outline_color'],
                self.gui.main.settings[f'{slide_type}_outline_color'],
                self.gui.main.settings[f'{slide_type}_outline_color']
            )
            outline_width = self.gui.main.settings[
                f'{slide_type}_outline_width']

            # Set the shading behind the text
            use_shade = self.gui.main.settings[f'{slide_type}_use_shade']
            shade_color = self.gui.main.settings[
                f'{slide_type}_shade_color']  # needs to be sent as an integer so opacity can be set by the lyric widget
            shade_opacity = self.gui.main.settings[
                f'{slide_type}_shade_opacity']

        return (font, fill_color, use_shadow, shadow_color, shadow_offset, use_outline, outline_color,
                outline_width, use_shade, shade_color, shade_opacity)

    def test_url(self, url: str):
        response = None
        try:
            response = requests.get(url)
        except requests.exceptions.MissingSchema:
            pass
        except requests.exceptions.ConnectionError:
            pass
        except requests.exceptions.InvalidSchema:
            new_url = 'http://' + url.split('//')[1]
            try:
                response = requests.get(new_url)
            except requests.exceptions.ConnectionError:
                pass
            if response and response.ok:
                return True, new_url
        if response and response.ok:
            return True, url
        else:
            if not '//' in url:
                new_url = 'http://' + url
                try:
                    response = requests.get(new_url)
                except requests.exceptions.ConnectionError:
                    pass
                if response and response.ok:
                    return True, new_url
                else:
                    new_url = 'https://' + url
                    try:
                        response = requests.get(new_url)
                    except requests.exceptions.ConnectionError:
                        pass
                    if response and response.ok:
                        return True, new_url
            else:
                new_url = '//www.'.join(url.split('//'))
                try:
                    response = requests.get(new_url)
                except requests.exceptions.ConnectionError:
                    pass
                if response and response.ok:
                    return True, new_url

        return False, url

    def setText(self, text: str):
        """
        Convenience method to set the text variable
        :param str text: Text to be shown
        """
        self.text = text

    def paintEvent(self, evt: QPaintEvent):
        """
        Overrides paintEvent to custom paint the text onto the widget
        :param QPaintEvent evt: paintEvent
        """
        super().paintEvent(evt)
        painter = QPainter()
        if painter.begin(self):
            try:
                if self.gui.live_widget.slide_list.currentItem():
                    self.draw_slide(
                        painter,
                        self.gui.live_widget.slide_list.currentItem().data(Qt.ItemDataRole.UserRole).copy()
                    )
            finally:
                painter.end()

    def draw_slide(self, painter: QPainter, slide_data: dict, auto_fit: bool | None = True):
        """
        Provides a method for performing all the drawing operations for the text that will be shown on the slide,
        but it does so outside of the paintEvent. If the text is actually to be drawn, the widget's painter is to be
        passed to this method and the text will be painted on to it. If not, a painter from a like-sized QImage can be
        used and will return the size of the text background rect in order to give feedback on the final size of the
        text + background. If auto_fit is true, it will reduce the font size in the case the height of the text is
        larger than the usable area of the slide.
        :param painter: QPainter
        :param slide_data: dict
        :param auto_fit: bool
        :return: QRectF
        """
        background_pixmap = None
        if slide_data['type'] == 'song' or slide_data['type'] == 'custom':
            # set the background
            if slide_data['override_global']:
                if slide_data['background'] == 'global_song':
                    background_pixmap = self.gui.global_song_background_pixmap
                elif slide_data['background'] == 'global_bible':
                    background_pixmap = self.gui.global_bible_background_pixmap
                elif 'rgb(' in slide_data['background']:
                    background_pixmap = QPixmap(self.gui.display_widget.width(), self.gui.display_widget.height())
                    background_color = get_qcolor_from_str(
                        self.gui.main, slide_data['background'], slide_data['type'])
                    background_pixmap.fill(background_color)
                elif exists(self.gui.main.background_dir + '/' + slide_data['background']):
                    background_pixmap = QPixmap(self.gui.main.background_dir + '/' + slide_data['background'])
                else:
                    background_pixmap = self.gui.global_song_background_pixmap
            elif slide_data['type'] == 'song':
                background_pixmap = self.gui.global_song_background_pixmap
            else:
                background_pixmap = self.gui.global_bible_background_pixmap

            # set the lyric text
            if slide_data['type'] == 'song':
                text = slide_data['parsed_text']['text']
                # store the text so that it can be accessed by the display widget for changing the stage text
                self.text = text
            else:
                text = slide_data['parsed_text']
                # store the text so that it can be accessed by the display widget for changing the stage text
                self.text = text

            # set the footer text
            footer_text = []
            if slide_data['type'] == 'song':
                if len(slide_data['author'].strip()) > 0:
                    footer_text.append(slide_data['author'])
                if len(slide_data['copyright'].strip()) > 0:
                    footer_text.append('\n\u00A9' + slide_data['copyright'].replace('\n', ' '))
                if len(slide_data['ccli_song_number'].strip()) > 0:
                    footer_text.append('\nCCLI Song #: ' + slide_data['ccli_song_number'])
                if len(self.gui.main.settings['ccli_num'].strip()) > 0:
                    footer_text.append('\nCCLI License #: ' + self.gui.main.settings['ccli_num'])
            footer_text = footer_text
        elif 'bible' in slide_data['type']:
            # set the background
            background_pixmap = self.gui.global_bible_background_pixmap

            # set the lyrics
            text = slide_data['parsed_text']
            # store the text so that it can be accessed by the display widget for changing the stage text
            self.text = text

            # set the footer text
            footer_text = [f'{slide_data['title']}({slide_data['author']})']
        elif slide_data['type'] == 'image':
            if exists(self.gui.main.image_dir + '/' + slide_data['title']):
                background_pixmap = QPixmap(self.gui.main.image_dir + '/' + slide_data['title'])
            text = ''
            # store the text so that it can be accessed by the display widget for changing the stage text
            self.text = slide_data['title']
            footer_text = []
        elif slide_data['type'] == 'video':
            # provie a black background behind the video
            background_pixmap = QPixmap(self.gui.display_widget.width(), self.gui.display_widget.height())
            background_pixmap.fill(Qt.GlobalColor.black)
            text = ''
            # store the text so that it can be accessed by the display widget for changing the stage text
            self.text = slide_data['title']
            footer_text = []
        elif slide_data['type'] == 'web':
            text = ''
            # store the text so that it can be accessed by the display widget for changing the stage text
            self.text = slide_data['text']
            url_ok, url = self.test_url(slide_data['url'])
            if not url_ok:
                text = '<p style="align-text: center;">Unable to load webpage: invalid URL</p>'
            footer_text = []
        else:
            return

        # set the font
        (font, fill_color, use_shadow, shadow_color, shadow_offset, use_outline, outline_color,
         outline_width, use_shade, shade_color, shade_opacity) = self.set_font(slide_data)

        # paint the background pixmap if it is set
        if background_pixmap:
            # check to see if the pixmap is wider or taller than the display widget; shrink if so
            if 'background_fit' in self.gui.main.settings.keys():
                mode = self.gui.main.settings['background_fit']
            else:
                mode = 'fill'
            screen_size = self.gui.display_widget.size()  # Your widget's current dimensions

            if mode == 'stretch':
                # Force it to fit the rect exactly (Option 1)
                scaled_pixmap = background_pixmap.scaled(
                    screen_size,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                x = 0
                y = 0

            elif mode == 'fit':
                # Scale to bounds, leaving black bars (Option 2)
                scaled_pixmap = background_pixmap.scaled(
                    screen_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                # Center the image on the screen
                x = (screen_size.width() - scaled_pixmap.width()) // 2
                y = (screen_size.height() - scaled_pixmap.height()) // 2

            else:
                # Scale to completely fill the screen, cropping edges (Option 3)
                scaled_pixmap = background_pixmap.scaled(
                    screen_size,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                # Center the image so the cropping happens equally on both sides/top/bottom
                x = (screen_size.width() - scaled_pixmap.width()) // 2
                y = (screen_size.height() - scaled_pixmap.height()) // 2

            painter.drawPixmap(x, y, scaled_pixmap)

        text = re.sub('<p.*?>', '', text)
        text = re.sub('</p>', '', text)
        text = re.sub('\n', '<br />', text)
        text = re.sub('<br/>', '<br />', text)

        # draw the footer first so it's height can be used to determine the usable space for the text
        brush = QBrush()
        painter.setBrush(brush)
        pen = QPen(fill_color)
        painter.setPen(pen)
        painter.setFont(QFont(font.family(), self.gui.main.settings['footer_font_size']))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font_metrics = painter.fontMetrics()
        line_height = font_metrics.height()
        footer_height = line_height * len(footer_text)
        y = self.gui.display_widget.height() - footer_height
        for line in footer_text:
            painter.drawText(
                QPoint(20, y),
                line
            )
            y += line_height

        # build painter paths according to how many words will fit within the width of the screen, creating a new
        # path whenever the line becomes too long
        if len(footer_text) == 0:
            footer_height = 0
        usable_rect = QRect(
            0,
            0,
            self.gui.display_widget.width(),
            self.gui.display_widget.height() - footer_height - font_metrics.height()
        )

        longest_line = 0
        painter_paths = []

        lines = text.split('<br />')
        while True:
            longest_line = 0
            painter.setFont(font)
            font_metrics = painter.fontMetrics()
            space_width = font_metrics.horizontalAdvance(' ')
            line_height = font_metrics.boundingRect('Wy').height()
            painter_paths.clear()

            for i in range(len(lines)):
                line_words = lines[i].split(' ')
                if len(line_words) == 0:
                    line_words = [' ']

                # get the full length of this line to check if it is longer than the usable rect's width
                full_line_path = QPainterPath()
                full_line_x = 0
                full_line_y = 0
                for word in line_words:
                    if '<b>' in word:
                        font.setWeight(1000)
                    if '<i>' in word:
                        font.setItalic(True)
                    if '<u>' in word:
                        font.setUnderline(True)

                    full_line_path.addText(QPointF(full_line_x, full_line_y), font, re.sub('<.*?>', '', word))
                    full_line_x = full_line_path.boundingRect().width() + space_width

                    if '</b>' in word:
                        font.setWeight(QFont.Weight.Normal)
                    if '</i>' in word:
                        font.setItalic(False)
                    if '</u>' in word:
                        font.setUnderline(False)

                line_segments = [line_words]
                # split the line in two if the line overflows usable_rect
                if full_line_path.boundingRect().width() > usable_rect.width() - 40:
                    half_index = int(len(line_words) / 2)
                    line_segments = [line_words[:half_index], line_words[half_index:]]

                # draw the path(s) for this line
                painter_path_x = 0
                painter_path_y = 0
                for segment in line_segments:
                    painter_path = QPainterPath()
                    for word in segment:
                        if '<b>' in word:
                            font.setWeight(1000)
                        if '<i>' in word:
                            font.setItalic(True)
                        if '<u>' in word:
                            font.setUnderline(True)

                        painter_path.addText(
                            QPointF(painter_path_x, painter_path_y),
                            font,
                            re.sub('<.*?>', '', word)
                        )

                        if '</b>' in word:
                            font.setWeight(QFont.Weight.Normal)
                        if '</i>' in word:
                            font.setItalic(False)
                        if '</u>' in word:
                            font.setUnderline(False)

                        painter_path_x = painter_path.boundingRect().width() + space_width

                    painter_paths.append(painter_path)
                    painter_path_x = 0

            # get the total size of the paths that will be drawn for creating the shading rectangle
            total_height = 0
            for path in painter_paths:
                total_height += line_height
                if path.boundingRect().width() > longest_line:
                    longest_line = path.boundingRect().width()

            # Calculate what the total size including the margins of the shadeing rectangle will be. If it
            # overflows the usable rect, shrink the font by 2 points and allow loop.
            if ((total_height + font_metrics.descent() + 40 > usable_rect.height()
                    or longest_line + 80 > usable_rect.width())
                    and font.pointSize() > 24 and auto_fit):
                font.setPointSize(font.pointSize() - 2)
            else:
                break

        # Set the opacity of the shading rectangle behind the text. If use_shade is false or there is no text, set the
        # opacity to zero.
        opacity = shade_opacity
        if not use_shade or len(text.strip()) == 0:
            opacity = 0

        # Calculate the size of the shade_rect based on the longest line and the height of the text. Account for
        # margins.
        shade_rect = QRectF(
            0,
            0,
            longest_line + 80,
            total_height + font_metrics.descent() + 40
        )
        # Center the shade rectangle within the usable rect
        shade_rect.translate(
            (usable_rect.width() / 2) - (shade_rect.width() / 2),
            (usable_rect.height() / 2) - (shade_rect.height() / 2)
        )
        painter.fillRect(
            shade_rect,
            QColor(shade_color, shade_color, shade_color, opacity)
        )

        path_y = shade_rect.y() + line_height
        for path in painter_paths:
            path_x = (usable_rect.width() / 2) - (path.boundingRect().width() / 2)
            path.translate(path_x, path_y)

            if use_shadow:
                path.translate(shadow_offset, shadow_offset)
                shadow_brush = QBrush()
                shadow_brush.setColor(shadow_color)
                shadow_brush.setStyle(Qt.BrushStyle.SolidPattern)
                painter.fillPath(path, shadow_brush)
                path.translate(-shadow_offset, -shadow_offset)

            brush.setColor(fill_color)
            brush.setStyle(Qt.BrushStyle.SolidPattern)
            pen.setColor(outline_color)
            pen.setWidth(outline_width)
            painter.setPen(pen)

            painter.fillPath(path, brush)
            if use_outline:
                painter.strokePath(path, pen)

            path_y += line_height

        return shade_rect, footer_height


class NewFontWidget(QWidget):
    """
    Implements QWidget that contains all of the settings that can be applied to the display font
    """
    mouse_release_signal = pyqtSignal(int)

    def __init__(self,
                 gui,
                 slide_type: str,
                 draw_border: bool | None = True,
                 applies_to_global: bool | None = True,
                 edit_widget: QWidget | None = None):
        """
        Implements QWidget that contains all of the settings that can be applied to the display font
        :param GUI gui: the current instance of GUI
        :param bool draw_border: apply a border to the widgets
        """
        super().__init__()
        self.gui = gui
        self.slide_type = slide_type
        self.draw_border = draw_border
        self.applies_to_global = applies_to_global
        self.edit_widget = edit_widget

        self.font_face_combobox = QFontComboBox()
        self.font_size_spinbox = QSpinBox()
        self.white_radio_button = QRadioButton('White')
        self.black_radio_button = QRadioButton('Black')
        self.custom_font_color_radio_button = QRadioButton('Custom')
        self.font_color_button_group = QButtonGroup()
        self.shadow_color_slider = ShadowSlider(self.gui)
        self.shadow_offset_slider = OffsetSlider(self.gui)
        self.shadow_checkbox = QCheckBox('Use Shadow')
        self.outline_checkbox = QCheckBox('Use Outline')
        self.outline_color_slider = ShadowSlider(self.gui)
        self.outline_width_slider = OffsetSlider(self.gui)
        self.shade_behind_text_checkbox = QCheckBox('Shade Behind Text')

        self.mouse_release_signal.connect(lambda value: self.change_font(value))

        self.setParent(self.gui.main_window)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)
        self.setWindowFlag(Qt.WindowType.Popup)
        self.init_components()

    def init_components(self):
        self.setFixedWidth(950)
        self.setObjectName('font_widget')
        layout = QVBoxLayout(self)

        sample_text = self.slide_type.capitalize() + ' Font Sample'
        self.font_sample = FontSample(self, edit_widget=self.edit_widget)
        self.font_sample.text = sample_text
        self.font_sample.setObjectName('font_sample')
        layout.addWidget(self.font_sample)
        layout.addSpacing(10)

        font_style_widget = QGroupBox()
        font_style_widget.setFont(self.gui.bold_font)
        font_style_widget.setTitle('Font Style')
        layout.addWidget(font_style_widget)
        font_style_layout = QHBoxLayout(font_style_widget)

        font_face_label = QLabel('Font Face')
        font_face_label.setFont(self.gui.bold_font)
        font_style_layout.addWidget(font_face_label)

        delegate = FontComboboxDelegate(row_height=36, font_size=16)
        self.font_face_combobox.setItemDelegate(delegate)
        self.font_face_combobox.setMinimumHeight(30)
        self.font_face_combobox.currentIndexChanged.connect(self.change_font)
        font_style_layout.addWidget(self.font_face_combobox)

        font_size_label = QLabel('Font Size:')
        font_size_label.setFont(self.gui.bold_font)
        font_style_layout.addWidget(font_size_label)

        self.font_size_spinbox.setMaximumWidth(100)
        self.font_size_spinbox.setMinimumHeight(30)
        self.font_size_spinbox.setFont(self.gui.standard_font)
        self.font_size_spinbox.setRange(10, 240)
        self.font_size_spinbox.valueChanged.connect(self.change_font)
        self.font_size_spinbox.installEventFilter(self)
        font_style_layout.addWidget(self.font_size_spinbox)
        font_style_layout.addSpacing(10)

        font_color_label = QLabel('Font Color:')
        font_color_label.setFont(self.gui.bold_font)
        font_style_layout.addWidget(font_color_label)

        self.white_radio_button.setObjectName('white')
        self.white_radio_button.setFont(self.gui.standard_font)
        font_style_layout.addWidget(self.white_radio_button)

        self.black_radio_button.setObjectName('black')
        self.black_radio_button.setFont(self.gui.standard_font)
        font_style_layout.addWidget(self.black_radio_button)

        self.custom_font_color_radio_button.setObjectName('custom')
        self.custom_font_color_radio_button.setFont(self.gui.standard_font)
        self.custom_font_color_radio_button.setObjectName('custom_font_color_radio_button')
        self.custom_font_color_radio_button.clicked.connect(self.color_chooser)
        font_style_layout.addWidget(self.custom_font_color_radio_button)

        self.font_color_button_group.addButton(self.white_radio_button)
        self.font_color_button_group.addButton(self.black_radio_button)
        self.font_color_button_group.addButton(self.custom_font_color_radio_button)
        self.font_color_button_group.buttonClicked.connect(self.change_font)

        shadow_widget = QGroupBox()
        shadow_widget.setFont(self.gui.bold_font)
        shadow_widget.setTitle('Text Shadow')
        layout.addWidget(shadow_widget)
        shadow_layout = QHBoxLayout(shadow_widget)

        self.shadow_checkbox.setFont(self.gui.bold_font)
        self.shadow_checkbox.clicked.connect(self.change_font)
        shadow_layout.addWidget(self.shadow_checkbox)
        shadow_layout.addStretch()

        self.shadow_color_slider = ShadowSlider(self.gui)
        self.shadow_color_slider.setObjectName('shadow_color_slider')
        shadow_layout.addWidget(self.shadow_color_slider)
        shadow_layout.addSpacing(20)

        self.shadow_offset_slider = OffsetSlider(self.gui)
        self.shadow_offset_slider.setObjectName('shadow_offset_slider')
        shadow_layout.addWidget(self.shadow_offset_slider)

        outline_widget = QGroupBox()
        outline_widget.setFont(self.gui.bold_font)
        outline_widget.setTitle('Text Outline')
        layout.addWidget(outline_widget)
        outline_layout = QHBoxLayout(outline_widget)

        self.outline_checkbox.setFont(self.gui.bold_font)
        self.outline_checkbox.clicked.connect(self.change_font)
        outline_layout.addWidget(self.outline_checkbox)
        outline_layout.addStretch()

        self.outline_color_slider = ShadowSlider(self.gui)
        self.outline_color_slider.setObjectName('outline_color_slider')
        self.outline_color_slider.color_title.setText('Outline Shade:')
        outline_layout.addWidget(self.outline_color_slider)
        outline_layout.addSpacing(20)

        self.outline_width_slider = OffsetSlider(self.gui)
        self.outline_width_slider.setObjectName('outline_width_slider')
        self.outline_width_slider.offset_slider.setRange(1, 10)
        self.outline_width_slider.max_label.setText('10px')
        self.outline_width_slider.offset_title.setText('Outline Width:')
        outline_layout.addWidget(self.outline_width_slider)

        shade_widget = QGroupBox()
        shade_widget.setFont(self.gui.bold_font)
        shade_widget.setTitle('Shade Behind Text')
        layout.addWidget(shade_widget)
        shade_layout = QHBoxLayout(shade_widget)

        self.shade_behind_text_checkbox.setFont(self.gui.bold_font)
        self.shade_behind_text_checkbox.clicked.connect(self.change_font)
        shade_layout.addWidget(self.shade_behind_text_checkbox)
        shade_layout.addStretch()

        self.shade_color_slider = ShadowSlider(self.gui)
        self.shade_color_slider.setObjectName('shade_color_slider')
        shade_layout.addWidget(self.shade_color_slider)
        shade_layout.addSpacing(20)

        self.shade_opacity_slider = ShadowSlider(self.gui)
        self.shade_opacity_slider.setObjectName('shade_opacity_slider')
        self.shade_opacity_slider.color_title.setText('Shade Opacity:')
        self.shade_opacity_slider.color_label.hide()
        self.shade_opacity_slider.min_label.setText('Transparent')
        self.shade_opacity_slider.max_label.setText('Opaque')
        shade_layout.addWidget(self.shade_opacity_slider)

    def blockSignals(self, block: bool):
        """
        method to block the signals of all widgets that would be updated during apply_settings
        """
        super().blockSignals(block)

        # also block all children widgets connected to functions
        self.font_face_combobox.blockSignals(block)
        self.font_size_spinbox.blockSignals(block)
        self.white_radio_button.blockSignals(block)
        self.black_radio_button.blockSignals(block)
        self.custom_font_color_radio_button.blockSignals(block)
        self.font_color_button_group.blockSignals(block)
        self.shadow_checkbox.blockSignals(block)
        self.shadow_color_slider.color_slider.blockSignals(block)
        self.shadow_offset_slider.offset_slider.blockSignals(block)
        self.outline_checkbox.blockSignals(block)
        self.outline_color_slider.color_slider.blockSignals(block)
        self.outline_width_slider.offset_slider.blockSignals(block)

    def apply_settings(self):
        """
        updates the various widgets to match the current settings
        """
        self.blockSignals(True)

        font_face = self.gui.main.settings[f'{self.slide_type}_font_face']
        if len(font_face.strip()) > 0:
            self.font_face_combobox.setCurrentIndex(
                self.font_face_combobox.findText(font_face, Qt.MatchFlag.MatchFixedString))
        else:
            self.font_face_combobox.setCurrentIndex(0)
            self.gui.main.settings[f'{self.slide_type}_font_face'] = self.font_face_combobox.currentText()

        self.font_size_spinbox.setValue(self.gui.main.settings[f'{self.slide_type}_font_size'])

        font_color = self.gui.main.settings[f'{self.slide_type}_font_color']
        if font_color == 'white':
            self.white_radio_button.setChecked(True)
        elif font_color == 'black':
            self.black_radio_button.setChecked(True)
        else:
            self.custom_font_color_radio_button.setChecked(True)
            self.custom_font_color_radio_button.setText('Custom: ' + font_color)
            self.custom_font_color_radio_button.setObjectName(font_color)

        use_shadow = self.gui.main.settings[f'{self.slide_type}_use_shadow']
        shadow_color = self.gui.main.settings[f'{self.slide_type}_shadow_color']
        shadow_offset = self.gui.main.settings[f'{self.slide_type}_shadow_offset']

        if use_shadow:
            self.shadow_checkbox.setChecked(True)
        self.shadow_color_slider.color_slider.setValue(shadow_color)
        self.shadow_color_slider.change_sample(shadow_color)
        self.shadow_offset_slider.offset_slider.setValue(shadow_offset)
        self.shadow_offset_slider.current_label.setText(str(shadow_offset) + 'px')

        use_outline = self.gui.main.settings[f'{self.slide_type}_use_outline']
        outline_color = self.gui.main.settings[f'{self.slide_type}_outline_color']
        outline_width = self.gui.main.settings[f'{self.slide_type}_outline_width']

        self.outline_checkbox.setChecked(use_outline)
        self.outline_color_slider.color_slider.setValue(outline_color)
        self.outline_color_slider.change_sample(outline_color)
        self.outline_width_slider.offset_slider.setValue(outline_width)
        self.outline_width_slider.current_label.setText(str(outline_width) + 'px')
        self.blockSignals(False)

        if f'{self.slide_type}_use_shade' in self.gui.main.settings.keys():
            self.shade_behind_text_checkbox.setChecked(self.gui.main.settings[f'{self.slide_type}_use_shade'])
        if f'{self.slide_type}_shade_color' in self.gui.main.settings.keys():
            self.shade_color_slider.color_slider.setValue(self.gui.main.settings[f'{self.slide_type}_shade_color'])
        if f'{self.slide_type}_shade_opacity' in self.gui.main.settings.keys():
            self.shade_opacity_slider.color_slider.setValue(self.gui.main.settings[f'{self.slide_type}_shade_opacity'])

        self.change_font_sample()

    def change_font(self, value: int | None = None):
        """
        updates ProjectOn.settings to the user's selected font settings
        """

        shadow_color = None
        shadow_offset = None
        outline_color = None
        outline_width = None
        if not self.signalsBlocked() and self.applies_to_global:
            if value:
                if self.sender().objectName() == 'shadow_color_slider':
                    shadow_color = value
                elif self.sender().objectName() == 'shadow_offset_slider':
                    shadow_offset = value
                elif self.sender().objectName() == 'outline_color_slider':
                    outline_color = value
                elif self.sender().objectName() == 'outline_width_slider':
                    outline_width = value

            new_font_face = self.font_face_combobox.currentText()

            self.gui.main.settings[f'{self.slide_type}_font_face'] = self.font_face_combobox.currentText()
            self.gui.main.settings[f'{self.slide_type}_font_size'] = self.font_size_spinbox.value()
            if self.font_color_button_group.checkedButton():
                self.gui.main.settings[f'{self.slide_type}_font_color'] = self.font_color_button_group.checkedButton().objectName()

            self.gui.main.settings[f'{self.slide_type}_use_shadow'] = self.shadow_checkbox.isChecked()
            if shadow_color:
                self.gui.main.settings[f'{self.slide_type}_shadow_color'] = shadow_color
            else:
                self.gui.main.settings[f'{self.slide_type}_shadow_color'] = self.shadow_color_slider.color_slider.value()
            if shadow_offset:
                self.gui.main.settings[f'{self.slide_type}_shadow_offset'] = shadow_offset
            else:
                self.gui.main.settings[f'{self.slide_type}_shadow_offset'] = self.shadow_offset_slider.offset_slider.value()

            self.gui.main.settings[f'{self.slide_type}_use_outline'] = self.outline_checkbox.isChecked()
            if outline_color:
                self.gui.main.settings[f'{self.slide_type}_outline_color'] = outline_color
            else:
                self.gui.main.settings[f'{self.slide_type}_outline_color'] = self.outline_color_slider.color_slider.value()
            if outline_width:
                self.gui.main.settings[f'{self.slide_type}_outline_width'] = outline_width
            else:
                self.gui.main.settings[f'{self.slide_type}_outline_width'] = self.outline_width_slider.offset_slider.value()

            self.gui.main.settings[f'{self.slide_type}_use_shade'] = self.shade_behind_text_checkbox.isChecked()
            self.gui.main.settings[f'{self.slide_type}_shade_color'] = self.shade_color_slider.color_slider.value()
            self.gui.main.settings[f'{self.slide_type}_shade_opacity'] = self.shade_opacity_slider.color_slider.value()

        self.change_font_sample()
        self.font_sample.repaint()

    def change_font_sample(self):
        if self.font_face_combobox.currentText():
            font_name = self.font_face_combobox.currentText()
        else:
            font_name = self.font_face_combobox.itemText(0)

        self.font_sample.setFont(
            QFont(
                font_name,
                self.font_size_spinbox.value(),
                QFont.Weight.Bold))

        if self.font_color_button_group.checkedButton():
            color = self.font_color_button_group.checkedButton().objectName()
        else:
            color = 'black'
            self.black_radio_button.blockSignals(True)
            self.black_radio_button.setChecked(True)
            self.black_radio_button.blockSignals(False)

        if color == 'black':
            self.font_sample.fill_color = QColor(0, 0, 0)
        elif color == 'white':
            self.font_sample.fill_color = QColor(255, 255, 255)
        else:
            fill_color = self.custom_font_color_radio_button.objectName()
            fill_color = fill_color.replace('rgb(', '')
            fill_color = fill_color.replace(')', '')
            fill_color_split = fill_color.split(', ')
            try:
                self.font_sample.fill_color = QColor(
                    int(fill_color_split[0]), int(fill_color_split[1]), int(fill_color_split[2]))
            except Exception:
                pass

        if self.shadow_checkbox.isChecked():
            self.font_sample.use_shadow = True
        else:
            self.font_sample.use_shadow = False

        if self.outline_checkbox.isChecked():
            self.font_sample.use_outline = True
        else:
            self.font_sample.use_outline = False

        shadow_color = self.shadow_color_slider.color_slider.value()
        self.font_sample.shadow_color = QColor(shadow_color, shadow_color, shadow_color)
        self.font_sample.shadow_offset = self.shadow_offset_slider.offset_slider.value()

        outline_color = self.outline_color_slider.color_slider.value()
        self.font_sample.outline_color = QColor(outline_color, outline_color, outline_color)
        self.font_sample.outline_width = self.outline_width_slider.offset_slider.value()

        self.font_sample.use_shade = self.shade_behind_text_checkbox.isChecked()
        self.font_sample.shade_color = self.shade_color_slider.color_slider.value()
        self.font_sample.shade_opacity = self.shade_opacity_slider.color_slider.value()

        self.font_sample.repaint()

    def color_chooser(self):
        """
        creates a color dialog for the user to select a custom font color
        """
        sender = self.sender()
        current_color = self.gui.main.settings[f'{self.slide_type}_font_color']
        if current_color == 'white':
            r, g, b = 255, 255, 255
        elif current_color == 'black':
            r, g, b = 0, 0, 0
        else:
            color_split = current_color.split(', ')
            r, g, b = int(color_split[0]), int(color_split[1]), int(color_split[2])

        color = QColorDialog.getColor(QColor(r, g, b), self)
        rgb = color.getRgb()
        if color.isValid():
            color_string = str(rgb[0]) + ', ' + str(rgb[1]) + ', ' + str(rgb[2])
            self.custom_font_color_radio_button.setText('Custom: ' + color_string)
            self.custom_font_color_radio_button.setObjectName(color_string)
            sender.setChecked(True)
            self.change_font()

        self.show()

    def hideEvent(self, evt: QHideEvent):
        """
        overrides hideEvent to save settings when the widget is hidden
        """
        self.gui.main.save_settings()
        self.gui.apply_settings(theme_too=False)
        super().hideEvent(evt)


class FontComboboxDelegate(QStyledItemDelegate):
    def __init__(self, parent: QWidget | None = None, row_height: int | None = 40, font_size: int | None = 12):
        super().__init__(parent)
        self.row_height = row_height
        self.font_size = font_size

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex):
        size = super().sizeHint(option, index)
        size.setHeight(40)
        return size

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        font_name = index.data(Qt.DisplayRole)
        font = QFont(font_name)
        font.setPointSize(self.font_size)
        option.font = font
        super().paint(painter, option, index)


class OffsetSlider(QWidget):
    """
    Creates a widget containing a QSlider and Label which lets the user set the distance of the display's shadow offset
    :param guiElements.GUI gui: The current instance of GUI
    """
    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        self.offset_title = QLabel('Shadow Offset:')
        self.offset_title.setFont(self.gui.list_font)
        layout.addWidget(self.offset_title)

        slider_widget = QWidget()
        slider_widget.setFixedWidth(300)
        slider_layout = QGridLayout()
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setVerticalSpacing(0)
        slider_widget.setLayout(slider_layout)
        layout.addWidget(slider_widget)

        self.offset_slider = CustomSlider()
        self.offset_slider.setOrientation(Qt.Orientation.Horizontal)
        self.offset_slider.setFont(self.gui.list_font)
        self.offset_slider.setRange(1, 15)
        self.offset_slider.setValue(self.gui.shadow_offset)
        self.offset_slider.installEventFilter(self)
        slider_layout.addWidget(self.offset_slider, 0, 0, 1, 3)

        self.min_label = QLabel(str(self.offset_slider.minimum()) + 'px')
        self.min_label.setFont(self.gui.list_font)
        slider_layout.addWidget(self.min_label, 1, 0, Qt.AlignmentFlag.AlignLeft)

        self.current_label = QLabel(str(self.offset_slider.value()) + 'px')
        self.current_label.setFont(self.gui.list_title_font)
        slider_layout.addWidget(self.current_label, 1, 1, Qt.AlignmentFlag.AlignCenter)
        self.offset_slider.sliderMoved.connect(lambda value: self.current_label.setText(str(value) + 'px'))

        self.max_label = QLabel(str(self.offset_slider.maximum()) + 'px')
        self.max_label.setFont(self.gui.list_font)
        slider_layout.addWidget(self.max_label, 1, 2, Qt.AlignmentFlag.AlignRight)

    def eventFilter(self, obj: QObject, evt: QEvent):
        if obj == self.offset_slider and evt.type() == QEvent.Type.Wheel:
            return True
        elif obj == self.offset_slider and evt.type() == QEvent.Type.MouseButtonRelease:
            parent = self.parent()
            while parent.parent():
                if hasattr(parent, 'mouse_release_signal'):
                    parent.mouse_release_signal.emit(self.offset_slider.value())
                    break
                else:
                    parent = parent.parent()
            return super().eventFilter(obj, evt)
        else:
            return super().eventFilter(obj, evt)


class PrintDialog(QDialog):
    def __init__(self, document: QTextDocument):
        super().__init__()

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        resolution = printer.resolution()
        document_size = QSizeF(8.5 * resolution, 11 * resolution)
        document.setPageSize(document_size)

        print_dialog = QDialog()
        print_layout = QHBoxLayout(print_dialog)

        document_viewer = QTextEdit()
        document_viewer.setReadOnly(True)
        print_layout.addWidget(document_viewer)
        document_viewer.setDocument(document)
        document_viewer.setFixedSize(QSize(int(850 * 0.75), int(1100 * 0.75)))

        options_widget = QWidget()
        options_layout = QVBoxLayout(options_widget)
        print_layout.addWidget(options_widget)

        printer_combobox = QComboBox()
        options_layout.addWidget(printer_combobox)

        printers = QPrinterInfo.availablePrinters()
        default_printer = QPrinterInfo.defaultPrinter()

        for this_printer in printers:
            printer_combobox.addItem(this_printer.printerName())
        printer_combobox.setCurrentText(default_printer.printerName())

        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        options_layout.addWidget(button_widget)
        options_layout.addStretch()

        print_button = QPushButton('Print')
        print_button.pressed.connect(lambda: print_dialog.done(1))
        button_layout.addWidget(print_button)

        cancel_button = QPushButton('Cancel')
        cancel_button.pressed.connect(lambda: print_dialog.done(-1))
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()

        result = print_dialog.exec()

        if result == 1:
            printer.setPrinterName(printer_combobox.currentText())
            document.print(printer)


class ShadowSlider(QWidget):
    """
    Creates a widget containing a QSlider and Label which lets the user set the greyness of the display's shadow
    :param guiElements.GUI gui: The current instance of GUI
    """
    def __init__(self, gui):
        """
        Creates a widget containing a QSlider and Label which lets the user set the greyness of the display's shadow
        :param guiElements.GUI gui: The current instance of GUI
        """
        super().__init__()
        self.gui = gui
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        self.color_title = QLabel('Shadow Shade:')
        self.color_title.setFont(self.gui.list_font)
        layout.addWidget(self.color_title)

        slider_widget = QWidget()
        slider_widget.setFixedWidth(300)
        slider_layout = QGridLayout()
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setVerticalSpacing(0)
        slider_widget.setLayout(slider_layout)
        layout.addWidget(slider_widget)

        self.color_slider = CustomSlider()
        self.color_slider.setObjectName('color_slider')
        self.color_slider.setOrientation(Qt.Orientation.Horizontal)
        self.color_slider.setFont(self.gui.list_font)
        self.color_slider.setRange(0, 255)
        self.color_slider.installEventFilter(self)
        slider_layout.addWidget(self.color_slider, 0, 0, 1, 3)

        self.min_label = QLabel('Black')
        self.min_label.setFont(self.gui.list_font)
        slider_layout.addWidget(self.min_label, 1, 0, Qt.AlignmentFlag.AlignLeft)

        self.color_label = QLabel()
        color_pixmap = QPixmap(20, 20)
        color_pixmap.fill(QColor(self.color_slider.value(), self.color_slider.value(), self.color_slider.value()))
        self.color_label.setPixmap(color_pixmap)
        self.color_slider.sliderMoved.connect(lambda value: self.change_sample(value))
        slider_layout.addWidget(self.color_label, 1, 1, Qt.AlignmentFlag.AlignCenter)

        self.max_label = QLabel('White')
        self.max_label.setFont(self.gui.list_font)
        slider_layout.addWidget(self.max_label, 1, 2, Qt.AlignmentFlag.AlignRight)

    def change_sample(self, value: int):
        new_pixmap = QPixmap(20, 20)
        new_pixmap.fill(QColor(value, value, value))
        self.color_label.setPixmap(new_pixmap)

    def eventFilter(self, obj: QObject, evt: QEvent):
        if obj == self.color_slider and evt.type() == QEvent.Type.Wheel:
            return True
        elif obj == self.color_slider and evt.type() == QEvent.Type.MouseButtonRelease:
            parent = self.parent()
            while parent.parent():
                if hasattr(parent, 'mouse_release_signal'):
                    parent.mouse_release_signal.emit(self.color_slider.value())
                    break
                else:
                    parent = parent.parent()
            return super().eventFilter(obj, evt)
        else:
            return super().eventFilter(obj, evt)


class SimpleSplash:
    """
    Provides a simple and standardized popup for showing messages
    """

    def __init__(self, gui, text: str | None = '', subtitle: bool | None = False, progress: bool = False, parent: QWidget | None = None):
        """
        Provides a simple and standardized popup for showing messages
        :param guiElements.GUI gui: the current instance of GUI
        :param str text: the text to be displayed
        :param bool subtitle: optional: Whether a subtitle will be used
        :param bool progress: optional: Whether a progress bar will be used
        :param obj parent: optional: parent widget for SimpleSplash's main widget
        """
        self.gui = gui
        self.text = text

        self.widget = QWidget(parent)
        self.widget.setObjectName('simple_splash')
        self.widget.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.widget.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)
        main_layout = QVBoxLayout(self.widget)

        container = QWidget()
        container.setObjectName('simple_splash_container')
        container.setMinimumWidth(300)
        layout = QGridLayout(container)
        main_layout.addWidget(container)

        self.label = QLabel(text)
        self.label.setObjectName('simple_splash_label')
        self.label.setFont(self.gui.bold_font)
        layout.addWidget(self.label, 0, 0, Qt.AlignmentFlag.AlignHCenter)

        if subtitle:
            self.subtitle_label = QLabel(' ')
            self.subtitle_label.setObjectName('simple_splash_subtitle_label')
            self.subtitle_label.setFont(self.gui.list_font)
            layout.addWidget(self.subtitle_label, 1, 0, Qt.AlignmentFlag.AlignHCenter)

        if progress:
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setFont(self.gui.bold_font)
            self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.progress_bar)

        container.adjustSize()
        self.widget.adjustSize()
        x = int((self.gui.primary_screen.size().width() / 2) - (self.widget.width() / 2))
        y = int((self.gui.primary_screen.size().height() / 2) - (self.widget.height() / 2))
        self.widget.move(x, y)
        self.widget.show()
        QApplication.processEvents()


class StandardDialog(QDialog):
    def __init__(self,
                 gui,
                 message: str,
                 icon: QPixmap | None = None,
                 temporary: bool | None = False,
                 buttons: list[str] | None = None):
        """
        Custom QDialog to standardize dialogs across the program.
        :param str message: Message to display
        :param QPixmap icon: Icon to use
        :param bool temporary: 'True' will show the dialog for a fixed number of seconds,
        specified by setting this class's 'temp_time' attribute
        :param list of str buttons: Buttons to use on this dialog: ok | yes | no | cancel
        """
        super().__init__()
        self.init_components()
        self.gui = gui
        self.message = message
        self.icon = icon
        self.temporary = temporary
        self.buttons = buttons if buttons is not None else ['yes', 'no', 'cancel']

        self.OK = 1
        self.YES = 2
        self.NO = -1
        self.CANCEL = -2

    def init_components(self):
        layout = QVBoxLayout(self)
        if self.icon:
            message_widget = QWidget()
            layout.addWidget(message_widget)
            message_layout = QHBoxLayout(message_widget)

            icon_label = QLabel()
            self.icon = self.icon.scaledToHeight(50, Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(self.icon)
            message_layout.addWidget(icon_label)
            message_layout.addSpacing(10)

            message_label = QLabel(self.message)
            message_label.setFont(self.gui.standard_font)
            message_layout.addWidget(message_label)
        else:
            message_label = QLabel(self.message)
            message_label.setFont(self.gui.standard_font)
            layout.addWidget(message_label)

        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.addStretch()

        for i in range(len(self.buttons)):
            this_button = QPushButton(self.buttons[i].capitalize())
            this_button.setFont(self.gui.standard_font)
            if self.buttons[i].lower() == 'ok':
                this_button.pressed.connect(lambda: self.done(self.OK))
            elif self.buttons[i].lower() == 'yes':
                this_button.pressed.connect(lambda: self.done(self.YES))
            elif self.buttons[i].lower() == 'no':
                this_button.pressed.connect(lambda: self.done(self.NO))
            elif self.buttons[i].lower() == 'cancel':
                this_button.pressed.connect(lambda: self.done(self.CANCEL))

            button_layout.addWidget(this_button)

            if i < len(self.buttons) - 1:
                button_layout.addSpacing(20)

    def exec(self):
        return self.exec()


class StandardItemWidget(QWidget):
    """
    Provides a standardized QWidget to be used as a QListWidget ItemWidget
    """
    def __init__(self,
                 gui,
                 title: str,
                 subtitle: str | None = None,
                 icon: QPixmap | None = None,
                 wrap_subtitle: bool | None = False):
        super().__init__()
        self.gui = gui
        self.setObjectName('item_widget')
        layout = QHBoxLayout(self)

        self.subtitle = None
        self.icon = None

        if icon:
            self.icon = QLabel()
            self.icon.setAutoFillBackground(False)
            self.icon.setPixmap(icon)
            self.icon.adjustSize()
            layout.addWidget(self.icon)

        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        layout.addWidget(text_container)

        self.title = QLabel(title)
        self.title.setAutoFillBackground(False)
        self.title.setObjectName('lyric_item_widget_title')
        self.title.setFont(self.gui.list_title_font)
        self.title.adjustSize()
        text_layout.addWidget(self.title)

        if subtitle:
            subtitle = re.sub('<br.*?>', '\n', subtitle)
            subtitle = re.sub('<.*?>', '', subtitle)

            self.subtitle = QLabel(subtitle)
            self.subtitle.setAutoFillBackground(False)
            self.title.setObjectName('lyric_item_widget_text')
            if wrap_subtitle:
                self.subtitle.setWordWrap(True)
            self.subtitle.setFont(self.gui.list_font)
            self.subtitle.adjustSize()
            text_layout.addWidget(self.subtitle)

        if not wrap_subtitle:
            layout.addStretch()

        self.adjustSize()


class SettingsWidget(QWidget):
    wait_widget = None
    song_background_combobox: ImageCombobox = None

    def __init__(self, gui):
        super().__init__()
        self.gui = gui

        self.accept_font_changes = False
        self.setObjectName('settings_container')
        self.setParent(self.gui.main_window)
        self.min_width = 1000

        #self.show_wait_widget()
        self.init_components()
        self.gui.main.app.processEvents()

        #self.wait_widget.subtitle_label.setText('Applying Settings')
        self.apply_settings()
        self.song_font_settings_widget.change_font_sample()
        self.bible_font_settings_widget.change_font_sample()

        #self.show()

        self.accept_font_changes = True
        #self.wait_widget.subtitle_label.setText('Creating Font Sample')
        #self.guiElements.main.app.processEvents()
        #self.wait_widget.widget.deleteLater()

    def show_wait_widget(self):
        self.wait_widget = SimpleSplash(self.gui, 'Please wait...', subtitle=True)

    def init_components(self):
        self.setParent(self.gui.main_window)
        self.setWindowTitle('Settings')
        self.setWindowFlag(Qt.WindowType.Window)
        self.setMinimumSize(self.min_width + 60, 800)
        layout = QGridLayout(self)
        layout.setRowStretch(0, 20)
        layout.setRowStretch(1, 1)

        self.settings_container = QTabWidget()
        self.settings_container.setFont(self.gui.standard_font)
        self.settings_container.setIconSize(QSize(36, 36))
        self.settings_container.setStyleSheet('QTabBar::tab { height: 42px; }')
        self.settings_container.setObjectName('tab_widget')

        self.settings_container.addTab(self.ccli_settings(), 'CCLI Info')
        self.settings_container.addTab(self.screen_settings(), 'Screen Settings')
        self.settings_container.addTab(self.font_settings(), 'Font Settings')
        self.settings_container.addTab(self.background_settings(), 'Background Settings')
        self.settings_container.addTab(self.countdown_settings(), 'Countdown Settings')

        self.settings_container.setTabIcon(0, QIcon('resources/gui_icons/ccli_settings.svg'))
        self.settings_container.setTabIcon(1, QIcon('resources/gui_icons/screen_settings.svg'))
        self.settings_container.setTabIcon(2, QIcon('resources/gui_icons/font_settings_settings.svg'))
        self.settings_container.setTabIcon(3, QIcon('resources/gui_icons/background_settings.svg'))
        self.settings_container.setTabIcon(4, QIcon('resources/gui_icons/countdown_settings.svg'))
        layout.addWidget(self.settings_container)

        button_widget = QWidget()
        button_widget.setObjectName('button_widget')
        button_layout = QHBoxLayout()
        button_widget.setLayout(button_layout)
        layout.addWidget(button_widget, 1, 0)

        save_button = QPushButton('Save')
        save_button.setFont(self.gui.standard_font)
        save_button.clicked.connect(self.save)
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addSpacing(20)

        cancel_button = QPushButton('Cancel')
        cancel_button.setFont(self.gui.standard_font)
        cancel_button.clicked.connect(self.cancel)
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()

    def ccli_settings(self):
        widget = QWidget()
        widget.setObjectName('settings_container')
        layout = QVBoxLayout(widget)

        ccli_title_label = QLabel('CCLI Information')
        ccli_title_label.setFont(self.gui.bold_font)
        ccli_title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(ccli_title_label)

        ccli_widget = QWidget()
        ccli_layout = QHBoxLayout()
        ccli_widget.setLayout(ccli_layout)
        layout.addWidget(ccli_widget)

        ccli_label = QLabel('CCLI License #:')
        ccli_label.setFont(self.gui.standard_font)
        ccli_layout.addWidget(ccli_label)

        self.ccli_line_edit = QLineEdit()
        self.ccli_line_edit.setFont(self.gui.standard_font)
        ccli_layout.addWidget(self.ccli_line_edit)
        layout.addStretch()

        return widget

    def screen_settings(self):
        widget = QWidget()
        widget.setObjectName('settings_container')
        widget.setMinimumWidth(self.min_width)
        layout = QGridLayout()
        layout.setSpacing(20)
        widget.setLayout(layout)

        index = 0
        for screen in self.gui.main.app.screens():
            app_screen_name = screen.name()
            name_split = app_screen_name.split('\\')
            name = name_split[len(name_split) - 1]

            if screen.name() == self.gui.primary_screen.name():
                primary = True
            else:
                primary = False

            screen_pixmap = self.draw_screen_pixmap(name, primary, screen.size())
            screen_icon_label = QLabel()
            screen_icon_label.setPixmap(screen_pixmap)
            layout.addWidget(screen_icon_label, 1, index)

            model_label = QLabel(screen.model())
            layout.addWidget(model_label, 2, index)

            size_label = QLabel('Size: ' + str(screen.size().width()) + 'x' + str(screen.size().height()))
            layout.addWidget(size_label, 3, index)

            set_display_button = QRadioButton('Set as display screen')
            set_display_button.setObjectName(app_screen_name)
            layout.addWidget(set_display_button, 4, index)

            if self.gui.secondary_screen:
                if screen.name() == self.gui.secondary_screen.name():
                    set_display_button.setChecked(True)
            else:
                set_display_button.setChecked(True)

            index += 1

        display_title_label = QLabel('Display Settings')
        display_title_label.setFont(self.gui.bold_font)
        display_title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(display_title_label, 0, 0, 1, index + 1)

        self.screen_button_group = QButtonGroup()
        id = 0
        for button in widget.findChildren(QRadioButton):
            self.screen_button_group.addButton(button, id)
            id += 1

        stage_display_title_label = QLabel('Stage Display Settings')
        stage_display_title_label.setFont(self.gui.bold_font)
        stage_display_title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(stage_display_title_label, 5, 0, 1, index + 1)

        stage_display_widget = QWidget()
        stage_display_layout = QHBoxLayout(stage_display_widget)
        layout.addWidget(stage_display_widget, 6, 0, 1, index + 1)

        text_only_radio_button = QRadioButton('Text Only')
        text_only_radio_button.setFont(self.gui.standard_font)
        text_only_radio_button.setToolTip('Display only the text of slides on the stage display. '
                                          'Best for slower networks.')
        stage_display_layout.addWidget(text_only_radio_button)

        mirror_radio_button = QRadioButton('Mirror Display')
        mirror_radio_button.setFont(self.gui.standard_font)
        mirror_radio_button.setToolTip('The stage display will show exactly what appears on the display screen.')
        stage_display_layout.addWidget(mirror_radio_button)
        stage_display_layout.addStretch()

        self.stage_display_button_group = QButtonGroup()
        self.stage_display_button_group.addButton(text_only_radio_button, 0)
        self.stage_display_button_group.addButton(mirror_radio_button, 1)

        if 'mirror_stage_display' in self.gui.main.settings.keys() and self.gui.main.settings['mirror_stage_display']:
            mirror_radio_button.setChecked(True)
        else:
            text_only_radio_button.setChecked(True)

        if sys.platform == 'win32':
            rendering_title_label = QLabel('Rendering')
            rendering_title_label.setFont(self.gui.bold_font)
            rendering_title_label.setContentsMargins(5, 5, 5, 5)
            layout.addWidget(rendering_title_label, 7, 0, 1, index + 1)

            self.software_checkbox = QCheckBox('Force Software Rendering')
            self.software_checkbox.setFont(self.gui.standard_font)
            self.software_checkbox.stateChanged.connect(self.rendering_restart)
            layout.addWidget(self.software_checkbox, 8, 0, 1, index + 1)

            software_details = QTextEdit(
                'Rending web pages on some AMD radeon graphics cards may cause ProjectOn to quit unexpectedly. If you '
                'are experiencing this behavior check this box, save your settings, and restart the program.'
            )
            software_details.setReadOnly(True)
            software_details.setCursor(Qt.CursorShape.ArrowCursor)
            software_details.setFont(self.gui.list_font)
            layout.addWidget(software_details, 9, 0, 1, index + 1)

        layout.setRowStretch(10, 100)

        return widget

    def update_settings(self):
        widget = QWidget()
        widget.setObjectName('settings_container')
        widget.setMinimumWidth(self.min_width)
        layout = QVBoxLayout()
        widget.setLayout(layout)

        display_title_label = QLabel('Preview Update Settings')
        display_title_label.setFont(self.gui.bold_font)
        display_title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(display_title_label)

        explanation_label = QLabel(
            'The rate at which the ProjectOn preview image and the stage view updates when a website or video is '
            'being displayed (in Frames Per Second). Higher gives smoother updates but higher CPU usage.'
        )
        explanation_label.setFont(self.gui.standard_font)
        layout.addWidget(explanation_label)

        button_widget = QWidget()
        layout.addWidget(button_widget)
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)

        fps_1_radio_button = QRadioButton('1 FPS')
        fps_1_radio_button.setFont(self.gui.standard_font)
        button_layout.addWidget(fps_1_radio_button)

        fps_5_radio_button = QRadioButton('5 FPS')
        fps_5_radio_button.setFont(self.gui.standard_font)
        button_layout.addWidget(fps_5_radio_button)

        fps_10_radio_button = QRadioButton('10 FPS')
        fps_10_radio_button.setFont(self.gui.standard_font)
        button_layout.addWidget(fps_10_radio_button)

        fps_24_radio_button = QRadioButton('24 FPS')
        fps_24_radio_button.setFont(self.gui.standard_font)
        button_layout.addWidget(fps_24_radio_button)
        button_layout.addStretch()

        self.fps_button_group = QButtonGroup()
        self.fps_button_group.addButton(fps_1_radio_button, 1)
        self.fps_button_group.addButton(fps_5_radio_button, 5)
        self.fps_button_group.addButton(fps_10_radio_button, 10)
        self.fps_button_group.addButton(fps_24_radio_button, 24)

        return widget

    def font_settings(self):
        widget = QWidget()
        widget.setMinimumWidth(self.min_width)
        widget.setObjectName('settings_container')
        layout = QVBoxLayout()
        widget.setLayout(layout)

        stage_title_label = QLabel('Stage Display Font Settings')
        stage_title_label.setFont(self.gui.bold_font)
        stage_title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(stage_title_label)

        stage_font_widget = QWidget()
        stage_font_layout = QHBoxLayout()
        stage_font_widget.setLayout(stage_font_layout)
        layout.addWidget(stage_font_widget)

        stage_font_label = QLabel('Stage Display Font Size:')
        stage_font_label.setFont(self.gui.bold_font)
        stage_font_layout.addWidget(stage_font_label)

        self.stage_font_spinbox = QSpinBox()
        self.stage_font_spinbox.setRange(12, 120)
        self.stage_font_spinbox.setMinimumSize(60, 30)
        self.stage_font_spinbox.setFont(self.gui.standard_font)
        self.stage_font_spinbox.installEventFilter(self)
        stage_font_layout.addWidget(self.stage_font_spinbox)
        stage_font_layout.addStretch()

        title_label = QLabel('Global Font Settings')
        title_label.setFont(self.gui.bold_font)
        title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(title_label)

        font_widget = QWidget()
        font_layout = QVBoxLayout()
        font_widget.setLayout(font_layout)
        layout.addWidget(font_widget)

        self.song_font_settings_widget = NewFontWidget(self.gui, 'song', draw_border=False)
        font_layout.addWidget(self.song_font_settings_widget)
        song_font_group_box = QGroupBox()
        song_font_group_box.setTitle('Song Font Settings')
        song_font_group_box.setFont(self.gui.standard_font)
        song_font_group_box_layout = QVBoxLayout(song_font_group_box)
        song_font_group_box_layout.addWidget(self.song_font_settings_widget)
        font_layout.addWidget(song_font_group_box)
        font_layout.addSpacing(20)

        self.bible_font_settings_widget = NewFontWidget(self.gui, 'bible', draw_border=False)
        #font_layout.addWidget(self.bible_font_settings_widget)
        bible_font_group_box = QGroupBox()
        bible_font_group_box.setTitle('Bible Font Settings')
        bible_font_group_box.setFont(self.gui.standard_font)
        bible_font_group_box_layout = QVBoxLayout(bible_font_group_box)
        bible_font_group_box_layout.addWidget(self.bible_font_settings_widget)
        font_layout.addWidget(bible_font_group_box)
        layout.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        widget.adjustSize()
        scroll_area.setWidget(widget)

        return scroll_area

    def background_settings(self):
        widget = QWidget()
        widget.setObjectName('settings_container')
        widget.setMinimumWidth(self.min_width)
        layout = QVBoxLayout()
        widget.setLayout(layout)

        title_label = QLabel('Global Background Settings')
        title_label.setFont(self.gui.bold_font)
        title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(title_label)

        song_background_label = QLabel('Global Song Background:')
        song_background_label.setFont(self.gui.standard_font)
        layout.addWidget(song_background_label)

        song_background_widget = QWidget()
        song_background_layout = QHBoxLayout(song_background_widget)
        layout.addWidget(song_background_widget)
        layout.addSpacing(20)

        self.song_background_combobox = ImageCombobox(self.gui, 'song', suppress_autosave=True)
        self.song_background_combobox.setMaximumWidth(500)
        song_background_layout.addWidget(self.song_background_combobox)
        song_background_layout.addSpacing(20)

        add_background_button = QPushButton('Import a Background')
        add_background_button.setFont(self.gui.standard_font)
        add_background_button.clicked.connect(self.import_background)
        song_background_layout.addWidget(add_background_button)
        song_background_layout.addSpacing(20)

        delete_background_button = QPushButton('Delete a Background')
        delete_background_button.setFont(self.gui.standard_font)
        delete_background_button.clicked.connect(lambda: self.delete_background('background'))
        song_background_layout.addWidget(delete_background_button)
        song_background_layout.addStretch()

        bible_background_label = QLabel('Global Bible Background:')
        bible_background_label.setFont(self.gui.standard_font)
        layout.addWidget(bible_background_label)

        bible_background_widget = QWidget()
        bible_background_layout = QHBoxLayout(bible_background_widget)
        layout.addWidget(bible_background_widget)
        layout.addSpacing(20)

        self.bible_background_combobox = ImageCombobox(self.gui, 'bible', suppress_autosave=True)
        self.bible_background_combobox.setMaximumWidth(500)
        bible_background_layout.addWidget(self.bible_background_combobox)
        bible_background_layout.addStretch()

        logo_background_label = QLabel('Set Logo Image:')
        logo_background_label.setFont(self.gui.standard_font)
        layout.addWidget(logo_background_label)

        logo_background_widget = QWidget()
        logo_background_layout = QHBoxLayout(logo_background_widget)
        layout.addWidget(logo_background_widget)
        layout.addSpacing(20)

        self.logo_background_combobox = ImageCombobox(self.gui, 'logo', suppress_autosave=True)
        self.logo_background_combobox.setMaximumWidth(500)
        logo_background_layout.addWidget(self.logo_background_combobox)
        logo_background_layout.addSpacing(20)

        logo_background_button = QPushButton('Add an Image')
        logo_background_button.setFont(self.gui.standard_font)
        logo_background_button.clicked.connect(self.gui.media_widget.add_image)
        logo_background_layout.addWidget(logo_background_button)
        logo_background_layout.addSpacing(20)

        delete_image_button = QPushButton('Delete an Image')
        delete_image_button.setFont(self.gui.standard_font)
        delete_image_button.clicked.connect(lambda: self.delete_background('image'))
        logo_background_layout.addWidget(delete_image_button)
        logo_background_layout.addStretch()
        layout.addStretch()

        return widget

    def countdown_settings(self):
        widget = QWidget()
        widget.setObjectName('settings_container')
        layout = QVBoxLayout(widget)

        title_label = QLabel('Service Countdown')
        title_label.setFont(self.gui.bold_font)
        title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(title_label)

        options_widget = QWidget()

        self.use_countdown_checkbox = QCheckBox('Use Countdown')
        self.use_countdown_checkbox.setToolTip('Show a timer that counts down the time until the service starts')
        self.use_countdown_checkbox.stateChanged.connect(lambda: self.use_countdown_changed(options_widget))
        self.use_countdown_checkbox.setChecked(self.gui.main.settings['countdown_settings']['use_countdown'])
        self.use_countdown_changed(options_widget)
        layout.addWidget(self.use_countdown_checkbox)

        layout.addWidget(options_widget)
        options_layout = QGridLayout(options_widget)

        self.countdown_sample_label = QLabel('Service starts in 3:21')
        options_layout.addWidget(self.countdown_sample_label, 0, 0, 1, 2)
        font = QFont(
            self.gui.main.settings['countdown_settings']['font_face'],
            self.gui.main.settings['countdown_settings']['font_size']
        )
        if self.gui.main.settings['countdown_settings']['font_bold']:
            font.setBold(True)
        self.countdown_sample_label.setFont(font)
        self.countdown_sample_label.setStyleSheet(
            f'background-color: {self.gui.main.settings["countdown_settings"]["bg_color"]}; '
            f'color: {self.gui.main.settings["countdown_settings"]["fg_color"]};'
        )

        font_face_label = QLabel('Font')
        font_face_label.setFont(self.gui.standard_font)
        options_layout.addWidget(font_face_label, 1, 0)

        self.countdown_font_combobox = QFontComboBox()
        delegate = FontComboboxDelegate(parent=self.countdown_font_combobox, row_height=36, font_size=16)
        self.countdown_font_combobox.setItemDelegate(delegate)
        self.countdown_font_combobox.setMinimumHeight(30)
        self.countdown_font_combobox.setCurrentIndex(
            self.countdown_font_combobox.findText(self.gui.main.settings['countdown_settings']['font_face']))
        self.countdown_font_combobox.currentIndexChanged.connect(self.countdown_changed)
        options_layout.addWidget(self.countdown_font_combobox, 2, 0)

        font_size_label = QLabel('Font Size')
        font_size_label.setFont(self.gui.standard_font)
        options_layout.addWidget(font_size_label, 1, 1)

        self.countdown_size_combobox = QComboBox()
        self.countdown_size_combobox.setFont(self.gui.standard_font)
        self.countdown_size_combobox.setMinimumHeight(40)
        for i in range(10, 161, 2):
            self.countdown_size_combobox.addItem(str(i))
        for i in range(self.countdown_size_combobox.count()):
            if self.countdown_size_combobox.itemText(i) == str(self.gui.main.settings['countdown_settings']['font_size']):
                self.countdown_size_combobox.setCurrentIndex(i)
                break
        self.countdown_size_combobox.currentIndexChanged.connect(self.countdown_changed)

        options_layout.addWidget(self.countdown_size_combobox, 2, 1)

        self.countdown_bold_checkbox = QCheckBox('Bold')
        self.countdown_bold_checkbox.setFont(self.gui.standard_font)
        self.countdown_bold_checkbox.setChecked(self.gui.main.settings['countdown_settings']['font_bold'])
        self.countdown_bold_checkbox.stateChanged.connect(self.countdown_changed)
        options_layout.addWidget(self.countdown_bold_checkbox, 2, 2)

        location_label = QLabel('Position')
        location_label.setFont(self.gui.standard_font)
        options_layout.addWidget(location_label, 1, 3)

        self.countdown_position_combobox = QComboBox()
        self.countdown_position_combobox.setFont(self.gui.standard_font)
        self.countdown_position_combobox.addItem('Top', 'top_full')
        self.countdown_position_combobox.addItem('Bottom', 'bottom_full')
        if 'top' in self.gui.main.settings['countdown_settings']['position']:
            self.countdown_position_combobox.setCurrentIndex(0)
        elif 'bottom' in self.gui.main.settings['countdown_settings']['position']:
            self.countdown_position_combobox.setCurrentIndex(1)
        options_layout.addWidget(self.countdown_position_combobox, 2, 3)

        start_time_label = QLabel('Service Start Time')
        start_time_label.setFont(self.gui.standard_font)
        options_layout.addWidget(start_time_label, 3, 0)

        self.countdown_start_time_widget = QTimeEdit()
        self.countdown_start_time_widget.setMinimumHeight(40)
        self.countdown_start_time_widget.setFont(self.gui.standard_font)
        self.countdown_start_time_widget.setTime(
            QTime(
                self.gui.main.settings['countdown_settings']['start_time'][0],
                self.gui.main.settings['countdown_settings']['start_time'][1],
                0,
                0
            )
        )
        options_layout.addWidget(self.countdown_start_time_widget, 4, 0)

        show_time_label = QLabel('Time to Begin Countdown')
        show_time_label.setFont(self.gui.standard_font)
        options_layout.addWidget(show_time_label, 3, 1)

        self.countdown_display_time_widget = QTimeEdit()
        self.countdown_display_time_widget.setMinimumHeight(40)
        self.countdown_display_time_widget.setFont(self.gui.standard_font)
        self.countdown_display_time_widget.setTime(
            QTime(
                self.gui.main.settings['countdown_settings']['display_time'][0],
                self.gui.main.settings['countdown_settings']['display_time'][1],
                0,
                0
            )
        )
        options_layout.addWidget(self.countdown_display_time_widget, 4, 1)

        background_color_label = QLabel('Countdown Background Color')
        background_color_label.setFont(self.gui.standard_font)
        options_layout.addWidget(background_color_label, 5, 0)

        self.bg_color_swatch = ClickableColorSwatch(self.gui)
        self.bg_color_swatch.make_color_swatch_pixmap(self.gui.main.settings['countdown_settings']['bg_color'])
        self.bg_color_swatch.color_changed.connect(self.countdown_changed)
        options_layout.addWidget(self.bg_color_swatch, 6, 0)

        foreground_color_label = QLabel('Countdown Font Color')
        foreground_color_label.setFont(self.gui.standard_font)
        options_layout.addWidget(foreground_color_label, 5, 1)

        self.fg_color_swatch = ClickableColorSwatch(self.gui)
        self.fg_color_swatch.make_color_swatch_pixmap(self.gui.main.settings['countdown_settings']['fg_color'])
        self.fg_color_swatch.color_changed.connect(self.countdown_changed)
        options_layout.addWidget(self.fg_color_swatch, 6, 1)
        layout.addStretch()

        return widget

    def use_countdown_changed(self, options_widget: QWidget):
        if self.use_countdown_checkbox.isChecked():
            options_widget.show()
        else:
            options_widget.hide()

    def countdown_changed(self):
        font = QFont(self.countdown_font_combobox.currentText(), int(self.countdown_size_combobox.currentText()))
        if self.countdown_bold_checkbox.isChecked():
            font.setBold(True)
        self.countdown_sample_label.setFont(font)

        bg_image = self.bg_color_swatch.pixmap().toImage()
        pixel_color = bg_image.pixelColor(10, 10)
        bg_color = f'rgba({pixel_color.red()}, {pixel_color.green()}, {pixel_color.blue()}, {pixel_color.alpha()})'

        fg_image = self.fg_color_swatch.pixmap().toImage()
        pixel_color = fg_image.pixelColor(10, 10)
        fg_color = f'rgb({pixel_color.red()}, {pixel_color.green()}, {pixel_color.blue()})'

        self.countdown_sample_label.setStyleSheet(f'background-color: {bg_color}; color: {fg_color};')
        self.countdown_sample_label.repaint()

    def rendering_restart(self):
        QMessageBox.warning(
            self,
            'Restart Required',
            'The program needs to be restarted in order for rendering changes\nto take effect. Please restart after saving your changes.',
            QMessageBox.StandardButton.Ok
        )

    def eventFilter(self, obj: QObject, evt: QEvent):
        if evt.type() == QEvent.Type.Wheel:
            return True
        else:
            return super().eventFilter(obj, evt)

    def draw_screen_pixmap(self, name: str, primary: bool, size: QSize):
        ratio = size.width() / size.height()
        height = 100
        width = int(100 * ratio)

        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(pixmap)
        pen = QPen()
        pen.setColor(Qt.GlobalColor.gray)
        pen.setWidth(10)
        brush = QBrush()
        brush.setColor(Qt.GlobalColor.blue)

        painter.setPen(pen)
        painter.setBrush(brush)

        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, width, height), 5, 5)
        painter.fillPath(path, QColor(85, 85, 170))
        painter.drawPath(path)

        text_rect = painter.fontMetrics().boundingRect(name)
        text_pos = QPointF((width / 2) - (text_rect.width() / 2), (height / 2) - (text_rect.height() / 2))
        pen.setColor(Qt.GlobalColor.white)
        painter.setPen(pen)
        painter.drawText(text_pos, name)

        if primary:
            text_pos.setY(text_pos.y() + text_rect.height() + 5)
            painter.drawText(text_pos, '(primary)')

        painter.end()
        return pixmap

    def color_chooser(self):
        sender = self.sender()
        color = QColorDialog.getColor(QColor(Qt.GlobalColor.black), self)
        rgb = color.getRgb()
        color_string = str(rgb[0]) + ', ' + str(rgb[1]) + ', ' + str(rgb[2])
        self.custom_font_color_radio_button.setText('Custom: ' + color_string)
        self.custom_font_color_radio_button.setObjectName(color_string)
        sender.setChecked(True)
        self.change_font_sample()

    def image_chooser(self):
        file = QFileDialog.getOpenFileName(self, 'Choose Image File', os.path.expanduser('~') + '/Pictures')
        if len(file[0]) > 0:
            file_split = file[0].split('/')
            file_name = file_split[len(file_split) - 1]
            self.background_line_edit.setText(file_name)
            self.gui.main.copy_image(file[0])
        self.background_image_radio_button.setChecked(True)

    def import_background(self):
        result = QFileDialog.getOpenFileName(
            self.gui.main_window, 'Choose Background Image', os.path.expanduser('~') + '/Pictures')
        if len(result[0]) > 0:
            file_name = ''
            try:
                file_name_split = result[0].split('/')
                file_name = file_name_split[len(file_name_split) - 1]
                shutil.copy(result[0], self.gui.main.background_dir + '/' + file_name)
            except Exception:
                self.gui.main.error_log()

            from core.runnables import IndexImages
            ii = IndexImages(self.gui.main, 'backgrounds')
            ii.add_image_index(self.gui.main.background_dir + '/' + file_name, 'background')

            self.song_background_combobox.refresh()
            self.bible_background_combobox.refresh()
            self.gui.tool_bar.song_background_combobox.refresh()
            self.gui.tool_bar.bible_background_combobox.refresh()

            self.song_background_combobox.update()
            self.bible_background_combobox.update()
            self.gui.tool_bar.song_background_combobox.update()
            self.gui.tool_bar.bible_background_combobox.update()

            self.song_background_combobox.setCurrentIndex(
                self.song_background_combobox.findData(
                    self.gui.main.settings['global_song_background'])
            )
            self.bible_background_combobox.setCurrentIndex(
                self.bible_background_combobox.findData(
                    self.gui.main.settings['global_bible_background'])
            )
            self.gui.tool_bar.song_background_combobox.setCurrentIndex(
                self.gui.tool_bar.song_background_combobox.findData(
                    self.gui.main.settings['global_song_background'])
            )
            self.gui.tool_bar.bible_background_combobox.setCurrentIndex(
                self.gui.tool_bar.bible_background_combobox.findData(
                    self.gui.main.settings['global_bible_background'])
            )

            self.gui.apply_settings()

    def delete_background(self, type: str):
        dialog = QDialog()
        layout = QVBoxLayout()
        dialog.setLayout(layout)

        label = QLabel()
        current_song_background = ''
        current_bible_background = ''
        current_image = ''
        if type == 'background':
            label.setText('Choose a background to remove:')
            current_bible_background = self.bible_background_combobox.currentData(Qt.ItemDataRole.UserRole)
            current_song_background = self.song_background_combobox.currentData(Qt.ItemDataRole.UserRole)
        elif type == 'image':
            label.setText('Choose an image item to remove:')
            current_image = self.logo_background_combobox.currentData(Qt.ItemDataRole.UserRole)
        label.setFont(self.gui.standard_font)
        layout.addWidget(label)

        combobox = None
        if type == 'background':
            combobox = ImageCombobox(self.gui, type='delete_background')
        elif type == 'image':
            combobox = ImageCombobox(self.gui, type='delete_image')
        if combobox:
            combobox.removeItem(1)
            combobox.removeItem(0)
            layout.addWidget(combobox)

        button_widget = QWidget()
        button_layout = QHBoxLayout()
        button_widget.setLayout(button_layout)
        layout.addWidget(button_widget)

        remove_button = QPushButton('Remove')
        remove_button.setFont(self.gui.standard_font)
        remove_button.clicked.connect(lambda: dialog.done(0))
        button_layout.addWidget(remove_button)

        cancel_button = QPushButton('Cancel')
        cancel_button.setFont(self.gui.standard_font)
        cancel_button.clicked.connect(lambda: dialog.done(1))
        button_layout.addWidget(cancel_button)

        response = dialog.exec()

        if response == 0:
            file_name = combobox.currentData(Qt.ItemDataRole.UserRole)
            try:
                if type == 'background':
                    os.remove(self.gui.main.background_dir + '/' + file_name)
                elif type == 'image':
                    os.remove(self.gui.main.image_dir + '/' + file_name)
            except FileNotFoundError:
                QMessageBox.information(
                    self.gui.main_window, 'Not Found', 'File not found. Reindexing images.', QMessageBox.StandardButton.Ok)

            splash = SimpleSplash(self.gui, 'Reindexing Images. Please Wait...')
            from core.runnables import IndexImages
            ii = IndexImages(self.gui.main, 'backgrounds')
            self.gui.main.thread_pool.start(ii)
            self.gui.main.thread_pool.waitForDone()

            self.song_background_combobox.refresh()
            self.bible_background_combobox.refresh()
            self.gui.tool_bar.song_background_combobox.refresh()
            self.gui.tool_bar.bible_background_combobox.refresh()

            self.song_background_combobox.update()
            self.bible_background_combobox.update()
            self.gui.tool_bar.song_background_combobox.update()
            self.gui.tool_bar.bible_background_combobox.update()

            self.song_background_combobox.setCurrentIndex(
                self.song_background_combobox.findData(
                    self.gui.main.settings['global_song_background'])
            )
            self.bible_background_combobox.setCurrentIndex(
                self.bible_background_combobox.findData(
                    self.gui.main.settings['global_bible_background'])
            )
            self.gui.tool_bar.song_background_combobox.setCurrentIndex(
                self.gui.tool_bar.song_background_combobox.findData(
                    self.gui.main.settings['global_song_background'])
            )
            self.gui.tool_bar.bible_background_combobox.setCurrentIndex(
                self.gui.tool_bar.bible_background_combobox.findData(
                    self.gui.main.settings['global_bible_background'])
            )

            splash.widget.deleteLater()

            QMessageBox.information(
                self,
                f'{type.capitalize()} Removed',
                file_name + ' removed.',
                QMessageBox.StandardButton.Ok
            )

            # remove deleted item from the database thumbnails and refresh the appropriate combobox(es)
            if type == 'background':
                connection = sqlite3.connect(self.gui.main.database)
                cursor = connection.cursor()
                cursor.execute('DELETE FROM backgroundThumbnails WHERE fileName="' + file_name + '";')
                connection.commit()
                connection.close()

                self.song_background_combobox.refresh()
                self.bible_background_combobox.refresh()
                self.gui.tool_bar.song_background_combobox.refresh()
                self.gui.tool_bar.bible_background_combobox.refresh()

                current_song_index = self.song_background_combobox.findData(
                    current_song_background, Qt.ItemDataRole.UserRole)
                if current_song_index == -1:
                    self.song_background_combobox.setCurrentIndex(0)
                    self.gui.tool_bar.song_background_combobox.setCurrentIndex(0)
                else:
                    self.song_background_combobox.setCurrentIndex(current_song_index)
                    self.gui.tool_bar.song_background_combobox.setCurrentIndex(current_song_index)

                current_bible_index = self.bible_background_combobox.findData(
                    current_bible_background, Qt.ItemDataRole.UserRole)
                if current_bible_index == -1:
                    self.bible_background_combobox.setCurrentIndex(0)
                    self.gui.tool_bar.bible_background_combobox.setCurrentIndex(0)
                else:
                    self.bible_background_combobox.setCurrentIndex(current_bible_index)
                    self.gui.tool_bar.bible_background_combobox.setCurrentIndex(current_bible_index)

            elif type == 'image':
                connection = sqlite3.connect(self.gui.main.database)
                cursor = connection.cursor()
                cursor.execute('DELETE FROM backgroundThumbnails WHERE fileName="' + file_name + '";')
                connection.commit()
                connection.close()

                self.logo_background_combobox.refresh()
                current_image_index = self.logo_background_combobox.findData(current_image, Qt.ItemDataRole.UserRole)
                if current_image_index == -1:
                    self.logo_background_combobox.setCurrentIndex(0)
                else:
                    self.logo_background_combobox.setCurrentIndex(current_image_index)

    def apply_settings(self):
        if self.gui.main.settings:
            try:
                if 'ccli_num' in self.gui.main.settings.keys():
                    self.ccli_line_edit.setText(self.gui.main.settings['ccli_num'])

                screen_found = False
                for button in self.screen_button_group.buttons():
                    if button.objectName() == self.gui.main.settings['selected_screen_name']:
                        button.setChecked(True)
                        screen_found = True

                if not screen_found:
                    for button in self.screen_button_group.buttons():
                        if 'primary' not in button.text():
                            button.setChecked(True)

                if 'force_software_rendering' in self.gui.main.settings.keys() and sys.platform == 'win32':
                    self.software_checkbox.blockSignals(True)
                    self.software_checkbox.setChecked(self.gui.main.settings['force_software_rendering'])
                    self.software_checkbox.blockSignals(False)

                self.song_font_settings_widget.apply_settings()
                self.bible_font_settings_widget.apply_settings()

                if 'stage_font_size' in self.gui.main.settings.keys():
                    self.stage_font_spinbox.setValue(int(self.gui.main.settings['stage_font_size']))

                self.song_background_combobox.blockSignals(True)
                self.bible_background_combobox.blockSignals(True)
                self.logo_background_combobox.blockSignals(True)

                self.song_background_combobox.setCurrentIndex(
                    self.song_background_combobox.findData(
                        self.gui.main.settings['global_song_background'], Qt.ItemDataRole.UserRole))
                self.bible_background_combobox.setCurrentIndex(
                    self.bible_background_combobox.findData(
                        self.gui.main.settings['global_bible_background'], Qt.ItemDataRole.UserRole))
                self.logo_background_combobox.setCurrentIndex(
                    self.logo_background_combobox.findData(
                        self.gui.main.settings['logo_image'], Qt.ItemDataRole.UserRole))

                self.song_background_combobox.blockSignals(False)
                self.bible_background_combobox.blockSignals(False)
                self.logo_background_combobox.blockSignals(False)
            except Exception:
                self.gui.main.error_log()

    def save(self):
        if not self.screen_button_group.checkedButton().objectName() == self.gui.main.settings['selected_screen_name']:
            screen_name = self.screen_button_group.checkedButton().objectName()

            self.gui.main.settings['selected_screen_name'] = screen_name
            primary_screen = None
            secondary_screen = None

            if len(self.gui.main.app.screens()) == 1:
                primary_screen = self.gui.main.app.screens()[0]
                secondary_screen = self.gui.main.app.screens()[0]
            else:
                for screen in self.gui.main.app.screens():
                    if screen_name in screen.name():
                        secondary_screen = screen
                    else:
                        primary_screen = screen

            self.gui.position_screens(primary_screen, secondary_screen)

        if sys.platform == 'win32':
            self.gui.main.settings['force_software_rendering'] = self.software_checkbox.isChecked()

        self.gui.main.settings['song_font_face'] = self.song_font_settings_widget.font_face_combobox.currentText()
        self.gui.main.settings['song_font_size'] = self.song_font_settings_widget.font_size_spinbox.value()
        self.gui.main.settings['song_font_color'] = (
            self.song_font_settings_widget.font_color_button_group.checkedButton().objectName())
        self.gui.main.settings['song_use_shadow'] = self.song_font_settings_widget.shadow_checkbox.isChecked()
        self.gui.main.settings['song_shadow_color'] = self.song_font_settings_widget.shadow_color_slider.color_slider.value()
        self.gui.main.settings['song_shadow_offset'] = self.song_font_settings_widget.shadow_offset_slider.offset_slider.value()
        self.gui.main.settings['song_use_outline'] = self.song_font_settings_widget.outline_checkbox.isChecked()
        self.gui.main.settings['song_outline_color'] = self.song_font_settings_widget.outline_color_slider.color_slider.value()
        self.gui.main.settings['song_outline_width'] = self.song_font_settings_widget.outline_width_slider.offset_slider.value()

        self.gui.main.settings['bible_font_face'] = self.bible_font_settings_widget.font_face_combobox.currentText()
        self.gui.main.settings['bible_font_size'] = self.bible_font_settings_widget.font_size_spinbox.value()
        self.gui.main.settings['bible_font_color'] = (
            self.bible_font_settings_widget.font_color_button_group.checkedButton().objectName())
        self.gui.main.settings['bible_use_shadow'] = self.bible_font_settings_widget.shadow_checkbox.isChecked()
        self.gui.main.settings['bible_shadow_color'] = self.bible_font_settings_widget.shadow_color_slider.color_slider.value()
        self.gui.main.settings['bible_shadow_offset'] = self.bible_font_settings_widget.shadow_offset_slider.offset_slider.value()
        self.gui.main.settings['bible_use_outline'] = self.bible_font_settings_widget.outline_checkbox.isChecked()
        self.gui.main.settings['bible_outline_color'] = self.bible_font_settings_widget.outline_color_slider.color_slider.value()
        self.gui.main.settings['bible_outline_width'] = self.bible_font_settings_widget.outline_width_slider.offset_slider.value()

        self.gui.main.settings['global_song_background'] = self.song_background_combobox.itemData(
            self.song_background_combobox.currentIndex(), Qt.ItemDataRole.UserRole
        )
        self.gui.main.settings['global_bible_background'] = self.bible_background_combobox.itemData(
            self.bible_background_combobox.currentIndex(), Qt.ItemDataRole.UserRole
        )
        self.gui.main.settings['logo_image'] = self.logo_background_combobox.itemData(
            self.logo_background_combobox.currentIndex(), Qt.ItemDataRole.UserRole
        )
        self.gui.main.settings['ccli_num'] = self.ccli_line_edit.text()
        self.gui.main.settings['stage_font_size'] = self.stage_font_spinbox.value()

        self.gui.main.settings['update_fps'] = self.fps_button_group.id(self.fps_button_group.checkedButton())

        if self.stage_display_button_group.checkedId() == 0:
            self.gui.main.settings['mirror_stage_display'] = False
        else:
            self.gui.main.settings['mirror_stage_display'] = True

        self.gui.main.settings['countdown_settings']['use_countdown'] = self.use_countdown_checkbox.isChecked()
        self.gui.main.settings['countdown_settings']['font_face'] = self.countdown_font_combobox.currentText()
        self.gui.main.settings['countdown_settings']['font_size'] = int(self.countdown_size_combobox.currentText())
        self.gui.main.settings['countdown_settings']['font_bold'] = self.countdown_bold_checkbox.isChecked()
        self.gui.main.settings['countdown_settings']['position'] = self.countdown_position_combobox.currentData(Qt.ItemDataRole.UserRole)
        bg_qcolor = self.bg_color_swatch.pixmap().toImage().pixelColor(10, 10)
        bg_color = f'rgba({bg_qcolor.red()}, {bg_qcolor.green()}, {bg_qcolor.blue()}, {bg_qcolor.alpha()})'
        self.gui.main.settings['countdown_settings']['bg_color'] = bg_color
        fg_qcolor = self.fg_color_swatch.pixmap().toImage().pixelColor(10, 10)
        fg_color = f'rgb({fg_qcolor.red()}, {fg_qcolor.green()}, {fg_qcolor.blue()})'
        self.gui.main.settings['countdown_settings']['fg_color'] = fg_color
        self.gui.main.settings['countdown_settings']['start_time'] = [
            self.countdown_start_time_widget.time().hour(),
            self.countdown_start_time_widget.time().minute()
        ]
        self.gui.main.settings['countdown_settings']['display_time'] = [
            self.countdown_display_time_widget.time().hour(),
            self.countdown_display_time_widget.time().minute()
        ]

        self.gui.main.save_settings()
        self.gui.apply_settings(theme_too=False)
        self.hide()

    def cancel(self):
        self.hide()


class IndexedSettingsWidget(QWidget):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.widget_positions = []

        self.accept_font_changes = False
        self.setObjectName('settings_container')
        self.setParent(self.gui.main_window)
        self.setWindowFlag(Qt.WindowType.Window)
        self.setWindowTitle('ProjectOn Settings')
        self.setMinimumWidth(1400)
        self.setMinimumHeight(700)

        self.init_components()
        self.gui.main.app.processEvents()

        self.apply_settings()
        self.song_font_settings_widget.change_font_sample()
        self.bible_font_settings_widget.change_font_sample()

        self.accept_font_changes = True

    def paintEvent(self, evt: QPaintEvent):
        super().paintEvent(evt)
        self.widget_positions = []
        for widget in self.settings_container.findChildren(QWidget, 'settings_container'):
            self.widget_positions.append(widget.y())

    def init_components(self):
        main_layout = QGridLayout(self)
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 10)
        main_layout.setRowStretch(0, 50)
        main_layout.setRowStretch(1, 1)

        self.headings_list = QListWidget()
        self.headings_list.currentRowChanged.connect(self.scroll_to_setting)
        main_layout.addWidget(self.headings_list, 0, 0, 2, 1)
        settings_headings = [
            'CCLI',
            'Screens',
            'Preview Update',
            'Fonts',
            'Backgrounds',
            'Countdown'
        ]
        for heading in settings_headings:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, heading)

            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)

            heading_label = QLabel(heading)
            heading_label.setFont(self.gui.standard_font)
            heading_label.setContentsMargins(5, 10, 5, 10)
            layout.addWidget(heading_label)
            
            item.setSizeHint(widget.sizeHint())
            self.headings_list.addItem(item)
            self.headings_list.setItemWidget(item, widget)

        self.settings_container = QWidget()
        self.settings_container.setObjectName('settings_container')
        self.settings_scroll_area = QScrollArea()
        self.settings_scroll_area.setAutoFillBackground(False)
        self.settings_scroll_area.setWidget(self.settings_container)
        self.settings_scroll_area.setWidgetResizable(True)
        self.settings_scroll_area.verticalScrollBar().valueChanged.connect(self.match_list_to_scroll)
        main_layout.addWidget(self.settings_scroll_area, 0, 1)

        settings_container_layout = QVBoxLayout(self.settings_container)
        settings_container_layout.addWidget(self.ccli_settings())
        settings_container_layout.addSpacing(40)
        settings_container_layout.addWidget(self.screen_settings())
        settings_container_layout.addSpacing(40)
        settings_container_layout.addWidget(self.update_settings())
        settings_container_layout.addSpacing(40)
        settings_container_layout.addWidget(self.font_settings())
        settings_container_layout.addSpacing(40)
        settings_container_layout.addWidget(self.background_settings())
        settings_container_layout.addSpacing(40)
        settings_container_layout.addWidget(self.countdown_settings())
        settings_container_layout.addSpacing(40)

        button_widget = QWidget()
        main_layout.addWidget(button_widget, 1, 1)
        button_layout = QHBoxLayout(button_widget)

        save_button = QPushButton('Save')
        save_button.setFont(self.gui.standard_font)
        save_button.clicked.connect(self.save)
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addSpacing(20)

        cancel_button = QPushButton('Cancel')
        cancel_button.setFont(self.gui.standard_font)
        cancel_button.clicked.connect(self.cancel)
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()

    def ccli_settings(self):
        widget = QWidget()
        widget.setObjectName('settings_container')
        layout = QVBoxLayout(widget)

        ccli_title_label = QLabel('CCLI Information')
        ccli_title_label.setObjectName('settings_title_label')
        ccli_title_label.setFont(self.gui.bold_font)
        ccli_title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(ccli_title_label)

        ccli_widget = QWidget()
        ccli_layout = QHBoxLayout()
        ccli_widget.setLayout(ccli_layout)
        layout.addWidget(ccli_widget)

        ccli_label = QLabel('CCLI License #:')
        ccli_label.setFont(self.gui.standard_font)
        ccli_layout.addWidget(ccli_label)

        self.ccli_line_edit = QLineEdit()
        self.ccli_line_edit.setFont(self.gui.standard_font)
        self.ccli_line_edit.setAutoFillBackground(True)
        ccli_layout.addWidget(self.ccli_line_edit)
        layout.addStretch()

        return widget

    def screen_settings(self):
        widget = QWidget()
        widget.setObjectName('settings_container')
        layout = QGridLayout()
        layout.setSpacing(20)
        widget.setLayout(layout)

        index = 0
        for screen in self.gui.main.app.screens():
            app_screen_name = screen.name()
            name_split = app_screen_name.split('\\')
            name = name_split[len(name_split) - 1]

            if screen.name() == self.gui.primary_screen.name():
                primary = True
            else:
                primary = False

            screen_pixmap = self.draw_screen_pixmap(name, primary, screen.size())
            screen_icon_label = QLabel()
            screen_icon_label.setPixmap(screen_pixmap)
            layout.addWidget(screen_icon_label, 1, index)

            model_label = QLabel(screen.model())
            layout.addWidget(model_label, 2, index)

            size_label = QLabel('Size: ' + str(screen.size().width()) + 'x' + str(screen.size().height()))
            layout.addWidget(size_label, 3, index)

            set_display_button = QRadioButton('Set as display screen')
            set_display_button.setObjectName(app_screen_name)
            layout.addWidget(set_display_button, 4, index)

            if self.gui.secondary_screen:
                if screen.name() == self.gui.secondary_screen.name():
                    set_display_button.setChecked(True)
            else:
                set_display_button.setChecked(True)

            index += 1

        display_title_label = QLabel('Display Settings')
        display_title_label.setObjectName('settings_title_label')
        display_title_label.setFont(self.gui.bold_font)
        display_title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(display_title_label, 0, 0, 1, index + 1)

        self.screen_button_group = QButtonGroup()
        id = 0
        for button in widget.findChildren(QRadioButton):
            self.screen_button_group.addButton(button, id)
            id += 1

        stage_display_title_label = QLabel('Stage Display Settings')
        stage_display_title_label.setObjectName('settings_title_label')
        stage_display_title_label.setFont(self.gui.bold_font)
        stage_display_title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(stage_display_title_label, 5, 0, 1, index + 1)

        stage_display_widget = QWidget()
        stage_display_layout = QHBoxLayout(stage_display_widget)
        layout.addWidget(stage_display_widget, 6, 0, 1, index + 1)

        text_only_radio_button = QRadioButton('Text Only')
        text_only_radio_button.setFont(self.gui.standard_font)
        text_only_radio_button.setToolTip('Display only the text of slides on the stage display. '
                                          'Best for slower networks.')
        stage_display_layout.addWidget(text_only_radio_button)

        mirror_radio_button = QRadioButton('Mirror Display')
        mirror_radio_button.setFont(self.gui.standard_font)
        mirror_radio_button.setToolTip('The stage display will show exactly what appears on the display screen.')
        stage_display_layout.addWidget(mirror_radio_button)
        stage_display_layout.addStretch()

        self.stage_display_button_group = QButtonGroup()
        self.stage_display_button_group.addButton(text_only_radio_button, 0)
        self.stage_display_button_group.addButton(mirror_radio_button, 1)

        if sys.platform == 'win32':
            rendering_title_label = QLabel('Rendering')
            rendering_title_label.setObjectName('settings_title_label')
            rendering_title_label.setFont(self.gui.bold_font)
            rendering_title_label.setContentsMargins(5, 5, 5, 5)
            layout.addWidget(rendering_title_label, 7, 0, 1, index + 1)

            software_details = QLabel(
                'Rending web pages on some AMD radeon graphics cards may cause ProjectOn to quit unexpectedly. If you '
                'are experiencing this behavior check this box, save your settings, and restart the program.'
            )
            software_details.setObjectName('help_label')
            software_details.setWordWrap(True)
            software_details.setFont(self.gui.standard_font)
            layout.addWidget(software_details, 8, 0, 1, index + 1)

            self.software_checkbox = QCheckBox('Force Software Rendering')
            self.software_checkbox.setFont(self.gui.standard_font)
            self.software_checkbox.stateChanged.connect(self.rendering_restart)
            layout.addWidget(self.software_checkbox, 9, 0, 1, index + 1)

        if 'mirror_stage_display' in self.gui.main.settings.keys() and self.gui.main.settings['mirror_stage_display']:
            mirror_radio_button.setChecked(True)
        else:
            text_only_radio_button.setChecked(True)

        layout.setRowStretch(10, 100)

        return widget

    def update_settings(self):
        widget = QWidget()
        widget.setObjectName('settings_container')
        layout = QVBoxLayout()
        layout.setSpacing(20)
        widget.setLayout(layout)

        display_title_label = QLabel('Preview Update Settings')
        display_title_label.setObjectName('settings_title_label')
        display_title_label.setFont(self.gui.bold_font)
        display_title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(display_title_label)

        explanation_label = QLabel(
            'The rate at which the ProjectOn preview image and the stage view updates when a website or video is '
            'being displayed (in Frames Per Second).\nHigher gives smoother updates but higher CPU usage.'
        )
        explanation_label.setObjectName('help_label')
        explanation_label.setFont(self.gui.standard_font)
        layout.addWidget(explanation_label)

        button_widget = QWidget()
        layout.addWidget(button_widget)
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)

        fps_1_radio_button = QRadioButton('1 FPS')
        fps_1_radio_button.setFont(self.gui.standard_font)
        button_layout.addWidget(fps_1_radio_button)
        button_layout.addSpacing(10)

        fps_5_radio_button = QRadioButton('5 FPS')
        fps_5_radio_button.setFont(self.gui.standard_font)
        button_layout.addWidget(fps_5_radio_button)
        button_layout.addSpacing(10)

        fps_10_radio_button = QRadioButton('10 FPS')
        fps_10_radio_button.setFont(self.gui.standard_font)
        button_layout.addWidget(fps_10_radio_button)
        button_layout.addSpacing(10)

        fps_24_radio_button = QRadioButton('24 FPS')
        fps_24_radio_button.setFont(self.gui.standard_font)
        button_layout.addWidget(fps_24_radio_button)
        button_layout.addStretch()

        self.fps_button_group = QButtonGroup()
        self.fps_button_group.addButton(fps_1_radio_button, 1)
        self.fps_button_group.addButton(fps_5_radio_button, 5)
        self.fps_button_group.addButton(fps_10_radio_button, 10)
        self.fps_button_group.addButton(fps_24_radio_button, 24)

        return widget

    def font_settings(self):
        widget = QWidget()
        widget.setObjectName('settings_container')
        layout = QVBoxLayout()
        widget.setLayout(layout)

        title_label = QLabel('Font Settings')
        title_label.setObjectName('settings_title_label')
        title_label.setFont(self.gui.bold_font)
        title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(title_label)

        stage_font_group_box = QGroupBox()
        stage_font_group_box.setTitle('Stage Font Settings')
        stage_font_group_box.setFont(self.gui.standard_font)
        stage_font_layout = QHBoxLayout(stage_font_group_box)
        layout.addWidget(stage_font_group_box)
        layout.addSpacing(20)

        stage_font_label = QLabel('Stage Display Font Size:')
        stage_font_label.setFont(self.gui.bold_font)
        stage_font_layout.addWidget(stage_font_label)

        self.stage_font_spinbox = QSpinBox()
        self.stage_font_spinbox.setRange(12, 120)
        self.stage_font_spinbox.setMinimumSize(60, 30)
        self.stage_font_spinbox.setFont(self.gui.standard_font)
        self.stage_font_spinbox.installEventFilter(self)
        stage_font_layout.addWidget(self.stage_font_spinbox)
        stage_font_layout.addStretch()

        footer_font_group_box = QGroupBox()
        footer_font_group_box.setTitle('Footer Font Settings')
        footer_font_group_box.setFont(self.gui.standard_font)
        footer_font_layout = QHBoxLayout(footer_font_group_box)
        layout.addWidget(footer_font_group_box)
        layout.addSpacing(20)

        footer_font_label = QLabel('Footer Font Size:')
        footer_font_label.setFont(self.gui.bold_font)
        footer_font_layout.addWidget(footer_font_label)

        self.footer_font_spinbox = QSpinBox()
        self.footer_font_spinbox.setRange(8, 60)
        self.footer_font_spinbox.setMinimumSize(60, 30)
        self.footer_font_spinbox.setFont(self.gui.standard_font)
        self.footer_font_spinbox.installEventFilter(self)
        self.footer_font_spinbox.setValue(24)
        footer_font_layout.addWidget(self.footer_font_spinbox)
        footer_font_layout.addStretch()

        self.song_font_settings_widget = NewFontWidget(self.gui, 'song', draw_border=False)
        song_font_group_box = QGroupBox()
        song_font_group_box.setTitle('Song Font Settings')
        song_font_group_box.setFont(self.gui.standard_font)
        song_font_group_box_layout = QVBoxLayout(song_font_group_box)
        song_font_group_box_layout.addWidget(self.song_font_settings_widget)
        layout.addWidget(song_font_group_box)
        layout.addSpacing(20)

        self.bible_font_settings_widget = NewFontWidget(self.gui, 'bible', draw_border=False)
        bible_font_group_box = QGroupBox()
        bible_font_group_box.setTitle('Bible Font Settings')
        bible_font_group_box.setFont(self.gui.standard_font)
        bible_font_group_box_layout = QVBoxLayout(bible_font_group_box)
        bible_font_group_box_layout.addWidget(self.bible_font_settings_widget)
        layout.addWidget(bible_font_group_box)
        layout.addStretch()

        return widget

    def background_settings(self):
        widget = QWidget()
        widget.setObjectName('settings_container')
        layout = QVBoxLayout()
        widget.setLayout(layout)

        title_label = QLabel('Global Background Settings')
        title_label.setObjectName('settings_title_label')
        title_label.setFont(self.gui.bold_font)
        title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(title_label)

        fit_group_box = QGroupBox('Background Image Fit')
        fit_group_box.setFont(self.gui.standard_font)
        layout.addWidget(fit_group_box)
        fit_layout = QVBoxLayout(fit_group_box)

        fit_label = QLabel()
        fit_label.setObjectName('help_label')
        fit_label.setTextFormat(Qt.TextFormat.MarkdownText)
        fit_label.setWordWrap(True)
        fit_label.setText('Specifies how a background image will be fit to the screen if it\'s a different size.\n'
                          '- Fill (default): Resize the image to fill the screen without changing the aspect ratio. '
                          'Top/bottom or sides may be cut off.\n'
                          '- Fit: Resize the image to fit within the screen without changing the aspect ratio. '
                          'Top/bottom or sides may have blank space around the image.\n'
                          '- Stretch: Resize the image to fill the screen by stretching it to the screen\'s dimensions. '
                          'Image may be noticeably distorted.')
        fit_label.setFont(self.gui.standard_font)
        fit_layout.addWidget(fit_label)

        self.fit_combobox = QComboBox()
        self.fit_combobox.setFont(self.gui.standard_font)
        self.fit_combobox.setMinimumHeight(30)
        self.fit_combobox.setMaximumWidth(200)
        self.fit_combobox.addItem('Fill', 'fill')
        self.fit_combobox.addItem('Fit', 'fit')
        self.fit_combobox.addItem('Stretch', 'stretch')
        if 'background_fit' in self.gui.main.settings.keys():
            self.fit_combobox.setCurrentIndex(
                self.fit_combobox.findData(self.gui.main.settings['background_fit'], Qt.ItemDataRole.UserRole))
        else:
            self.fit_combobox.setCurrentIndex(0)
        fit_layout.addWidget(self.fit_combobox)
        fit_layout.addStretch()

        song_background_group_box = QGroupBox()
        song_background_group_box.setFont(self.gui.standard_font)
        song_background_group_box.setTitle('Global Song Background')
        layout.addWidget(song_background_group_box)
        layout.addSpacing(20)
        song_background_layout = QHBoxLayout(song_background_group_box)

        self.song_background_combobox = ImageCombobox(self.gui, 'song', suppress_autosave=True)
        self.song_background_combobox.setMaximumWidth(500)
        song_background_layout.addWidget(self.song_background_combobox)
        song_background_layout.addSpacing(20)

        add_background_button = QPushButton('Import a Background')
        add_background_button.setFont(self.gui.standard_font)
        add_background_button.clicked.connect(self.import_background)
        song_background_layout.addWidget(add_background_button)
        song_background_layout.addSpacing(20)

        delete_background_button = QPushButton('Delete a Background')
        delete_background_button.setFont(self.gui.standard_font)
        delete_background_button.clicked.connect(lambda: self.delete_background('background'))
        song_background_layout.addWidget(delete_background_button)
        song_background_layout.addStretch()

        bible_background_group_box = QGroupBox()
        bible_background_group_box.setFont(self.gui.standard_font)
        bible_background_group_box.setTitle('Global Bible Background')
        layout.addWidget(bible_background_group_box)
        layout.addSpacing(20)
        bible_background_layout = QHBoxLayout(bible_background_group_box)

        self.bible_background_combobox = ImageCombobox(self.gui, 'bible', suppress_autosave=True)
        self.bible_background_combobox.setMaximumWidth(500)
        bible_background_layout.addWidget(self.bible_background_combobox)
        bible_background_layout.addStretch()

        logo_background_group_box = QGroupBox()
        logo_background_group_box.setFont(self.gui.standard_font)
        logo_background_group_box.setTitle('Logo Image')
        layout.addWidget(logo_background_group_box)
        layout.addSpacing(20)
        logo_background_layout = QHBoxLayout(logo_background_group_box)

        self.logo_background_combobox = ImageCombobox(self.gui, 'logo', suppress_autosave=True)
        self.logo_background_combobox.setMaximumWidth(500)
        logo_background_layout.addWidget(self.logo_background_combobox)
        logo_background_layout.addSpacing(20)

        logo_background_button = QPushButton('Add an Image')
        logo_background_button.setFont(self.gui.standard_font)
        logo_background_button.clicked.connect(self.gui.media_widget.add_image)
        logo_background_layout.addWidget(logo_background_button)
        logo_background_layout.addSpacing(20)

        delete_image_button = QPushButton('Delete an Image')
        delete_image_button.setFont(self.gui.standard_font)
        delete_image_button.clicked.connect(lambda: self.delete_background('image'))
        logo_background_layout.addWidget(delete_image_button)
        logo_background_layout.addStretch()
        layout.addStretch()

        return widget

    def countdown_settings(self):
        widget = QWidget()
        widget.setObjectName('settings_container')
        layout = QVBoxLayout(widget)

        title_label = QLabel('Service Countdown')
        title_label.setObjectName('settings_title_label')
        title_label.setFont(self.gui.bold_font)
        title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(title_label)

        options_widget = QWidget()

        self.use_countdown_checkbox = QCheckBox('Use Countdown')
        self.use_countdown_checkbox.setToolTip('Show a timer that counts down the time until the service starts')
        self.use_countdown_checkbox.stateChanged.connect(lambda: self.use_countdown_changed(options_widget))
        self.use_countdown_checkbox.setChecked(self.gui.main.settings['countdown_settings']['use_countdown'])
        self.use_countdown_changed(options_widget)
        layout.addWidget(self.use_countdown_checkbox)

        layout.addWidget(options_widget)
        options_layout = QGridLayout(options_widget)
        for i in range(4):
            options_layout.setColumnStretch(i, 1)
        options_layout.setColumnStretch(4, 5)

        self.countdown_sample_label = QLabel('Service starts in 3:21')
        options_layout.addWidget(self.countdown_sample_label, 0, 0, 1, 2)
        font = QFont(
            self.gui.main.settings['countdown_settings']['font_face'],
            self.gui.main.settings['countdown_settings']['font_size']
        )
        if self.gui.main.settings['countdown_settings']['font_bold']:
            font.setBold(True)
        self.countdown_sample_label.setFont(font)
        self.countdown_sample_label.setStyleSheet(
            f'background-color: {self.gui.main.settings["countdown_settings"]["bg_color"]}; '
            f'color: {self.gui.main.settings["countdown_settings"]["fg_color"]};'
        )

        font_face_label = QLabel('Font')
        font_face_label.setFont(self.gui.standard_font)
        options_layout.addWidget(font_face_label, 1, 0)

        self.countdown_font_combobox = QFontComboBox()
        delegate = FontComboboxDelegate(row_height=36, font_size=16)
        self.countdown_font_combobox.setItemDelegate(delegate)
        self.countdown_font_combobox.setFont(self.gui.standard_font)
        self.countdown_font_combobox.setMinimumHeight(40)
        self.countdown_font_combobox.setCurrentIndex(
            self.countdown_font_combobox.findText(self.gui.main.settings['countdown_settings']['font_face']))
        self.countdown_font_combobox.currentIndexChanged.connect(self.countdown_changed)
        options_layout.addWidget(self.countdown_font_combobox, 2, 0)

        font_size_label = QLabel('Font Size')
        font_size_label.setFont(self.gui.standard_font)
        options_layout.addWidget(font_size_label, 1, 1)

        self.countdown_size_combobox = QComboBox()
        self.countdown_size_combobox.setFont(self.gui.standard_font)
        self.countdown_size_combobox.setMinimumHeight(40)
        for i in range(10, 161, 2):
            self.countdown_size_combobox.addItem(str(i))
        for i in range(self.countdown_size_combobox.count()):
            if self.countdown_size_combobox.itemText(i) == str(self.gui.main.settings['countdown_settings']['font_size']):
                self.countdown_size_combobox.setCurrentIndex(i)
                break
        self.countdown_size_combobox.currentIndexChanged.connect(self.countdown_changed)

        options_layout.addWidget(self.countdown_size_combobox, 2, 1)

        self.countdown_bold_checkbox = QCheckBox('Bold')
        self.countdown_bold_checkbox.setFont(self.gui.standard_font)
        self.countdown_bold_checkbox.setChecked(self.gui.main.settings['countdown_settings']['font_bold'])
        self.countdown_bold_checkbox.stateChanged.connect(self.countdown_changed)
        options_layout.addWidget(self.countdown_bold_checkbox, 2, 2)

        location_label = QLabel('Position')
        location_label.setFont(self.gui.standard_font)
        options_layout.addWidget(location_label, 1, 3)

        self.countdown_position_combobox = QComboBox()
        self.countdown_position_combobox.setFont(self.gui.standard_font)
        self.countdown_position_combobox.setMinimumHeight(40)
        self.countdown_position_combobox.addItem('Top', 'top_full')
        self.countdown_position_combobox.addItem('Bottom', 'bottom_full')
        if 'top' in self.gui.main.settings['countdown_settings']['position']:
            self.countdown_position_combobox.setCurrentIndex(0)
        elif 'bottom' in self.gui.main.settings['countdown_settings']['position']:
            self.countdown_position_combobox.setCurrentIndex(1)
        options_layout.addWidget(self.countdown_position_combobox, 2, 3)

        start_time_label = QLabel('Service Start Time')
        start_time_label.setFont(self.gui.standard_font)
        options_layout.addWidget(start_time_label, 3, 0)

        self.countdown_start_time_widget = QTimeEdit()
        self.countdown_start_time_widget.setMinimumHeight(40)
        self.countdown_start_time_widget.setFont(self.gui.standard_font)
        self.countdown_start_time_widget.setTime(
            QTime(
                self.gui.main.settings['countdown_settings']['start_time'][0],
                self.gui.main.settings['countdown_settings']['start_time'][1],
                0,
                0
            )
        )
        options_layout.addWidget(self.countdown_start_time_widget, 4, 0)

        show_time_label = QLabel('Time to Begin Countdown')
        show_time_label.setFont(self.gui.standard_font)
        options_layout.addWidget(show_time_label, 3, 1)

        self.countdown_display_time_widget = QTimeEdit()
        self.countdown_display_time_widget.setMinimumHeight(40)
        self.countdown_display_time_widget.setFont(self.gui.standard_font)
        self.countdown_display_time_widget.setTime(
            QTime(
                self.gui.main.settings['countdown_settings']['display_time'][0],
                self.gui.main.settings['countdown_settings']['display_time'][1],
                0,
                0
            )
        )
        options_layout.addWidget(self.countdown_display_time_widget, 4, 1)

        background_color_label = QLabel('Countdown Background Color')
        background_color_label.setFont(self.gui.standard_font)
        options_layout.addWidget(background_color_label, 5, 0)

        self.bg_color_swatch = ClickableColorSwatch(self.gui, self)
        self.bg_color_swatch.make_color_swatch_pixmap(self.gui.main.settings['countdown_settings']['bg_color'])
        self.bg_color_swatch.color_changed.connect(self.countdown_changed)
        options_layout.addWidget(self.bg_color_swatch, 6, 0)

        foreground_color_label = QLabel('Countdown Font Color')
        foreground_color_label.setFont(self.gui.standard_font)
        options_layout.addWidget(foreground_color_label, 5, 1)

        self.fg_color_swatch = ClickableColorSwatch(self.gui, self)
        self.fg_color_swatch.make_color_swatch_pixmap(self.gui.main.settings['countdown_settings']['fg_color'])
        self.fg_color_swatch.color_changed.connect(self.countdown_changed)
        options_layout.addWidget(self.fg_color_swatch, 6, 1)
        layout.addStretch()

        return widget

    def scroll_to_setting(self):
        if not len(self.widget_positions) > 0:
            return

        index = self.sender().currentRow()
        self.settings_scroll_area.verticalScrollBar().setValue(self.widget_positions[index])

    def match_list_to_scroll(self):
        if len(self.widget_positions) == 0:
            return

        item_number = None
        for index in range(len(self.widget_positions)):
            if self.sender().value() >= self.widget_positions[index]:
                item_number = index

        if item_number and item_number < self.headings_list.count():
            self.headings_list.blockSignals(True)
            self.headings_list.setCurrentRow(item_number)
            self.headings_list.blockSignals(False)

    def use_countdown_changed(self, options_widget: QWidget):
        if self.use_countdown_checkbox.isChecked():
            options_widget.show()
        else:
            options_widget.hide()

    def countdown_changed(self):
        font = QFont(self.countdown_font_combobox.currentText(), int(self.countdown_size_combobox.currentText()))
        if self.countdown_bold_checkbox.isChecked():
            font.setBold(True)
        self.countdown_sample_label.setFont(font)

        bg_image = self.bg_color_swatch.pixmap().toImage()
        pixel_color = bg_image.pixelColor(10, 10)
        bg_color = f'rgba({pixel_color.red()}, {pixel_color.green()}, {pixel_color.blue()}, {pixel_color.alpha()})'

        fg_image = self.fg_color_swatch.pixmap().toImage()
        pixel_color = fg_image.pixelColor(10, 10)
        fg_color = f'rgb({pixel_color.red()}, {pixel_color.green()}, {pixel_color.blue()})'

        self.countdown_sample_label.setStyleSheet(f'background-color: {bg_color}; color: {fg_color};')
        self.countdown_sample_label.repaint()

    def rendering_restart(self):
        QMessageBox.warning(
            self,
            'Restart Required',
            'The program needs to be restarted in order for rendering changes\nto take effect. Please restart after saving your changes.',
            QMessageBox.StandardButton.Ok
        )

    def eventFilter(self, obj: QObject, evt: QEvent):
        if evt.type() == QEvent.Type.Wheel:
            return True
        else:
            return super().eventFilter(obj, evt)

    def draw_screen_pixmap(self, name: str, primary: bool, size: QSize):
        ratio = size.width() / size.height()
        height = 100
        width = int(100 * ratio)

        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(pixmap)
        pen = QPen()
        pen.setColor(Qt.GlobalColor.gray)
        pen.setWidth(10)
        brush = QBrush()
        brush.setColor(Qt.GlobalColor.blue)

        painter.setPen(pen)
        painter.setBrush(brush)

        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, width, height), 5, 5)
        painter.fillPath(path, QColor(85, 85, 170))
        painter.drawPath(path)

        text_rect = painter.fontMetrics().boundingRect(name)
        text_pos = QPointF((width / 2) - (text_rect.width() / 2), (height / 2) - (text_rect.height() / 2))
        pen.setColor(Qt.GlobalColor.white)
        painter.setPen(pen)
        painter.drawText(text_pos, name)

        if primary:
            text_pos.setY(text_pos.y() + text_rect.height() + 5)
            painter.drawText(text_pos, '(primary)')

        painter.end()
        return pixmap

    def color_chooser(self):
        sender = self.sender()
        color = QColorDialog.getColor(QColor(Qt.GlobalColor.black), self)
        rgb = color.getRgb()
        color_string = str(rgb[0]) + ', ' + str(rgb[1]) + ', ' + str(rgb[2])
        self.custom_font_color_radio_button.setText('Custom: ' + color_string)
        self.custom_font_color_radio_button.setObjectName(color_string)
        sender.setChecked(True)
        self.change_font_sample()

    def image_chooser(self):
        file = QFileDialog.getOpenFileName(self, 'Choose Image File', os.path.expanduser('~') + '/Pictures')
        if len(file[0]) > 0:
            file_split = file[0].split('/')
            file_name = file_split[len(file_split) - 1]
            self.background_line_edit.setText(file_name)
            self.gui.main.copy_image(file[0])
        self.background_image_radio_button.setChecked(True)

    def import_background(self):
        result = QFileDialog.getOpenFileName(
            self.gui.main_window, 'Choose Background Image', os.path.expanduser('~') + '/Pictures')
        if len(result[0]) > 0:
            file_name = ''
            try:
                file_name_split = result[0].split('/')
                file_name = file_name_split[len(file_name_split) - 1]
                shutil.copy(result[0], self.gui.main.background_dir + '/' + file_name)
            except Exception:
                self.gui.main.error_log()

            from core.runnables import IndexImages
            ii = IndexImages(self.gui.main, 'backgrounds')
            ii.add_image_index(self.gui.main.background_dir + '/' + file_name, 'background')

            self.song_background_combobox.refresh()
            self.bible_background_combobox.refresh()
            self.gui.tool_bar.song_background_combobox.refresh()
            self.gui.tool_bar.bible_background_combobox.refresh()

            self.song_background_combobox.update()
            self.bible_background_combobox.update()
            self.gui.tool_bar.song_background_combobox.update()
            self.gui.tool_bar.bible_background_combobox.update()

            self.song_background_combobox.setCurrentIndex(
                self.song_background_combobox.findData(
                    self.gui.main.settings['global_song_background'])
            )
            self.bible_background_combobox.setCurrentIndex(
                self.bible_background_combobox.findData(
                    self.gui.main.settings['global_bible_background'])
            )
            self.gui.tool_bar.song_background_combobox.setCurrentIndex(
                self.gui.tool_bar.song_background_combobox.findData(
                    self.gui.main.settings['global_song_background'])
            )
            self.gui.tool_bar.bible_background_combobox.setCurrentIndex(
                self.gui.tool_bar.bible_background_combobox.findData(
                    self.gui.main.settings['global_bible_background'])
            )

            self.gui.apply_settings()

    def delete_background(self, type: str):
        dialog = QDialog()
        layout = QVBoxLayout()
        dialog.setLayout(layout)

        label = QLabel()
        current_song_background = ''
        current_bible_background = ''
        current_image = ''
        if type == 'background':
            label.setText('Choose a background to remove:')
            current_bible_background = self.bible_background_combobox.currentData(Qt.ItemDataRole.UserRole)
            current_song_background = self.song_background_combobox.currentData(Qt.ItemDataRole.UserRole)
        elif type == 'image':
            label.setText('Choose an image item to remove:')
            current_image = self.logo_background_combobox.currentData(Qt.ItemDataRole.UserRole)
        label.setFont(self.gui.standard_font)
        layout.addWidget(label)

        combobox = None
        if type == 'background':
            combobox = ImageCombobox(self.gui, type='delete_background')
        elif type == 'image':
            combobox = ImageCombobox(self.gui, type='delete_image')
        if combobox:
            combobox.removeItem(1)
            combobox.removeItem(0)
            layout.addWidget(combobox)

        button_widget = QWidget()
        button_layout = QHBoxLayout()
        button_widget.setLayout(button_layout)
        layout.addWidget(button_widget)

        remove_button = QPushButton('Remove')
        remove_button.setFont(self.gui.standard_font)
        remove_button.clicked.connect(lambda: dialog.done(0))
        button_layout.addWidget(remove_button)

        cancel_button = QPushButton('Cancel')
        cancel_button.setFont(self.gui.standard_font)
        cancel_button.clicked.connect(lambda: dialog.done(1))
        button_layout.addWidget(cancel_button)

        response = dialog.exec()

        if response == 0:
            file_name = combobox.currentData(Qt.ItemDataRole.UserRole)
            try:
                if type == 'background':
                    os.remove(self.gui.main.background_dir + '/' + file_name)
                elif type == 'image':
                    os.remove(self.gui.main.image_dir + '/' + file_name)
            except FileNotFoundError:
                QMessageBox.information(
                    self.gui.main_window, 'Not Found', 'File not found. Reindexing images.', QMessageBox.StandardButton.Ok)

            splash = SimpleSplash(self.gui, 'Reindexing Images. Please Wait...')
            from core.runnables import IndexImages
            ii = IndexImages(self.gui.main, 'backgrounds')
            self.gui.main.thread_pool.start(ii)
            self.gui.main.thread_pool.waitForDone()

            self.song_background_combobox.refresh()
            self.bible_background_combobox.refresh()
            self.gui.tool_bar.song_background_combobox.refresh()
            self.gui.tool_bar.bible_background_combobox.refresh()

            self.song_background_combobox.update()
            self.bible_background_combobox.update()
            self.gui.tool_bar.song_background_combobox.update()
            self.gui.tool_bar.bible_background_combobox.update()

            self.song_background_combobox.setCurrentIndex(
                self.song_background_combobox.findData(
                    self.gui.main.settings['global_song_background'])
            )
            self.bible_background_combobox.setCurrentIndex(
                self.bible_background_combobox.findData(
                    self.gui.main.settings['global_bible_background'])
            )
            self.gui.tool_bar.song_background_combobox.setCurrentIndex(
                self.gui.tool_bar.song_background_combobox.findData(
                    self.gui.main.settings['global_song_background'])
            )
            self.gui.tool_bar.bible_background_combobox.setCurrentIndex(
                self.gui.tool_bar.bible_background_combobox.findData(
                    self.gui.main.settings['global_bible_background'])
            )

            splash.widget.deleteLater()

            QMessageBox.information(
                self,
                f'{type.capitalize()} Removed',
                file_name + ' removed.',
                QMessageBox.StandardButton.Ok
            )

            # remove deleted item from the database thumbnails and refresh the appropriate combobox(es)
            if type == 'background':
                connection = sqlite3.connect(self.gui.main.database)
                cursor = connection.cursor()
                cursor.execute('DELETE FROM backgroundThumbnails WHERE fileName="' + file_name + '";')
                connection.commit()
                connection.close()

                self.song_background_combobox.refresh()
                self.bible_background_combobox.refresh()
                self.gui.tool_bar.song_background_combobox.refresh()
                self.gui.tool_bar.bible_background_combobox.refresh()

                current_song_index = self.song_background_combobox.findData(
                    current_song_background, Qt.ItemDataRole.UserRole)
                if current_song_index == -1:
                    self.song_background_combobox.setCurrentIndex(0)
                    self.gui.tool_bar.song_background_combobox.setCurrentIndex(0)
                else:
                    self.song_background_combobox.setCurrentIndex(current_song_index)
                    self.gui.tool_bar.song_background_combobox.setCurrentIndex(current_song_index)

                current_bible_index = self.bible_background_combobox.findData(
                    current_bible_background, Qt.ItemDataRole.UserRole)
                if current_bible_index == -1:
                    self.bible_background_combobox.setCurrentIndex(0)
                    self.gui.tool_bar.bible_background_combobox.setCurrentIndex(0)
                else:
                    self.bible_background_combobox.setCurrentIndex(current_bible_index)
                    self.gui.tool_bar.bible_background_combobox.setCurrentIndex(current_bible_index)

            elif type == 'image':
                connection = sqlite3.connect(self.gui.main.database)
                cursor = connection.cursor()
                cursor.execute('DELETE FROM backgroundThumbnails WHERE fileName="' + file_name + '";')
                connection.commit()
                connection.close()

                self.logo_background_combobox.refresh()
                current_image_index = self.logo_background_combobox.findData(current_image, Qt.ItemDataRole.UserRole)
                if current_image_index == -1:
                    self.logo_background_combobox.setCurrentIndex(0)
                else:
                    self.logo_background_combobox.setCurrentIndex(current_image_index)

    def apply_settings(self):
        if self.gui.main.settings:
            try:
                if 'ccli_num' in self.gui.main.settings.keys():
                    self.ccli_line_edit.setText(self.gui.main.settings['ccli_num'])

                screen_found = False
                for button in self.screen_button_group.buttons():
                    if button.objectName() == self.gui.main.settings['selected_screen_name']:
                        button.setChecked(True)
                        screen_found = True

                if not screen_found:
                    for button in self.screen_button_group.buttons():
                        if 'primary' not in button.text():
                            button.setChecked(True)

                button_found = False
                if 'update_fps' in self.gui.main.settings.keys():
                    for button in self.fps_button_group.buttons():
                        if self.fps_button_group.id(button) == self.gui.main.settings['update_fps']:
                            button.setChecked(True)
                            button_found = True
                if not button_found:
                    self.fps_button_group.button(10).setChecked(True)

                if 'force_software_rendering' in self.gui.main.settings.keys() and sys.platform == 'win32':
                    self.software_checkbox.blockSignals(True)
                    self.software_checkbox.setChecked(self.gui.main.settings['force_software_rendering'])
                    self.software_checkbox.blockSignals(False)

                self.song_font_settings_widget.apply_settings()
                self.bible_font_settings_widget.apply_settings()

                if 'stage_font_size' in self.gui.main.settings.keys():
                    self.stage_font_spinbox.setValue(int(self.gui.main.settings['stage_font_size']))

                if 'footer_font_size' in self.gui.main.settings.keys():
                    self.footer_font_spinbox.setValue(int(self.gui.main.settings['footer_font_size']))

                self.song_background_combobox.blockSignals(True)
                self.bible_background_combobox.blockSignals(True)
                self.logo_background_combobox.blockSignals(True)

                self.song_background_combobox.setCurrentIndex(
                    self.song_background_combobox.findData(
                        self.gui.main.settings['global_song_background'], Qt.ItemDataRole.UserRole))
                self.bible_background_combobox.setCurrentIndex(
                    self.bible_background_combobox.findData(
                        self.gui.main.settings['global_bible_background'], Qt.ItemDataRole.UserRole))
                self.logo_background_combobox.setCurrentIndex(
                    self.logo_background_combobox.findData(
                        self.gui.main.settings['logo_image'], Qt.ItemDataRole.UserRole))

                self.song_background_combobox.blockSignals(False)
                self.bible_background_combobox.blockSignals(False)
                self.logo_background_combobox.blockSignals(False)
            except Exception:
                self.gui.main.error_log()

    def save(self):
        reposition_screens = False
        primary_screen = None
        secondary_screen = None
        if not self.screen_button_group.checkedButton().objectName() == self.gui.main.settings['selected_screen_name']:
            reposition_screens = True
            screen_name = self.screen_button_group.checkedButton().objectName()

            self.gui.main.settings['selected_screen_name'] = screen_name
            primary_screen = None
            secondary_screen = None

            screens = self.gui.main.app.screens()

            if len(self.gui.main.app.screens()) == 1:
                primary_screen = screens[0]
                secondary_screen = screens[0]
            else:
                for screen in screens:
                    if screen_name == screen.name():
                        secondary_screen = screen
                    else:
                        primary_screen = screen

        if sys.platform == 'win32':
            self.gui.main.settings['force_software_rendering'] = self.software_checkbox.isChecked()

        self.gui.main.settings['song_font_face'] = self.song_font_settings_widget.font_face_combobox.currentText()
        self.gui.main.settings['song_font_size'] = self.song_font_settings_widget.font_size_spinbox.value()
        self.gui.main.settings['song_font_color'] = (
            self.song_font_settings_widget.font_color_button_group.checkedButton().objectName())
        self.gui.main.settings['song_use_shadow'] = self.song_font_settings_widget.shadow_checkbox.isChecked()
        self.gui.main.settings['song_shadow_color'] = self.song_font_settings_widget.shadow_color_slider.color_slider.value()
        self.gui.main.settings['song_shadow_offset'] = self.song_font_settings_widget.shadow_offset_slider.offset_slider.value()
        self.gui.main.settings['song_use_outline'] = self.song_font_settings_widget.outline_checkbox.isChecked()
        self.gui.main.settings['song_outline_color'] = self.song_font_settings_widget.outline_color_slider.color_slider.value()
        self.gui.main.settings['song_outline_width'] = self.song_font_settings_widget.outline_width_slider.offset_slider.value()

        self.gui.main.settings['bible_font_face'] = self.bible_font_settings_widget.font_face_combobox.currentText()
        self.gui.main.settings['bible_font_size'] = self.bible_font_settings_widget.font_size_spinbox.value()
        self.gui.main.settings['bible_font_color'] = (
            self.bible_font_settings_widget.font_color_button_group.checkedButton().objectName())
        self.gui.main.settings['bible_use_shadow'] = self.bible_font_settings_widget.shadow_checkbox.isChecked()
        self.gui.main.settings['bible_shadow_color'] = self.bible_font_settings_widget.shadow_color_slider.color_slider.value()
        self.gui.main.settings['bible_shadow_offset'] = self.bible_font_settings_widget.shadow_offset_slider.offset_slider.value()
        self.gui.main.settings['bible_use_outline'] = self.bible_font_settings_widget.outline_checkbox.isChecked()
        self.gui.main.settings['bible_outline_color'] = self.bible_font_settings_widget.outline_color_slider.color_slider.value()
        self.gui.main.settings['bible_outline_width'] = self.bible_font_settings_widget.outline_width_slider.offset_slider.value()

        self.gui.main.settings['background_fit'] = self.fit_combobox.currentData(Qt.ItemDataRole.UserRole)
        self.gui.main.settings['global_song_background'] = self.song_background_combobox.itemData(
            self.song_background_combobox.currentIndex(), Qt.ItemDataRole.UserRole
        )
        self.gui.main.settings['global_bible_background'] = self.bible_background_combobox.itemData(
            self.bible_background_combobox.currentIndex(), Qt.ItemDataRole.UserRole
        )
        self.gui.main.settings['logo_image'] = self.logo_background_combobox.itemData(
            self.logo_background_combobox.currentIndex(), Qt.ItemDataRole.UserRole
        )
        self.gui.main.settings['ccli_num'] = self.ccli_line_edit.text()
        self.gui.main.settings['stage_font_size'] = self.stage_font_spinbox.value()
        self.gui.main.settings['footer_font_size'] = self.footer_font_spinbox.value()
        self.gui.main.settings['update_fps'] = self.fps_button_group.id(self.fps_button_group.checkedButton())

        if self.stage_display_button_group.checkedId() == 0:
            self.gui.main.settings['mirror_stage_display'] = False
        else:
            self.gui.main.settings['mirror_stage_display'] = True

        self.gui.main.settings['countdown_settings']['use_countdown'] = self.use_countdown_checkbox.isChecked()
        self.gui.main.settings['countdown_settings']['font_face'] = self.countdown_font_combobox.currentText()
        self.gui.main.settings['countdown_settings']['font_size'] = int(self.countdown_size_combobox.currentText())
        self.gui.main.settings['countdown_settings']['font_bold'] = self.countdown_bold_checkbox.isChecked()
        self.gui.main.settings['countdown_settings']['position'] = self.countdown_position_combobox.currentData(Qt.ItemDataRole.UserRole)
        bg_qcolor = self.bg_color_swatch.pixmap().toImage().pixelColor(10, 10)
        bg_color = f'rgba({bg_qcolor.red()}, {bg_qcolor.green()}, {bg_qcolor.blue()}, {bg_qcolor.alpha()})'
        self.gui.main.settings['countdown_settings']['bg_color'] = bg_color
        fg_qcolor = self.fg_color_swatch.pixmap().toImage().pixelColor(10, 10)
        fg_color = f'rgb({fg_qcolor.red()}, {fg_qcolor.green()}, {fg_qcolor.blue()})'
        self.gui.main.settings['countdown_settings']['fg_color'] = fg_color
        self.gui.main.settings['countdown_settings']['start_time'] = [
            self.countdown_start_time_widget.time().hour(),
            self.countdown_start_time_widget.time().minute()
        ]
        self.gui.main.settings['countdown_settings']['display_time'] = [
            self.countdown_display_time_widget.time().hour(),
            self.countdown_display_time_widget.time().minute()
        ]

        self.gui.main.save_settings()
        self.gui.apply_settings(theme_too=False)
        self.hide()

        if reposition_screens:
            self.gui.position_screens(primary_screen, secondary_screen)

    def cancel(self):
        self.hide()


class TextLayoutWidget(QWidget):
    def __init__(
            self,
            gui,
            for_sample: bool | None = False,
            font_face: str | None = 'Sans',
            font_size: int | None = 72,
            use_outline: bool | None = True,
            outline_color: QColor | None = QColor(0, 0, 0),
            outline_width: int | None = 8,
            fill_color: QColor | None = QColor(255, 255, 255),
            use_shadow: bool | None = True,
            shadow_color: QColor | None = QColor(0, 0, 0),
            shadow_offset: int | None = 5,
            use_shade: bool | None = False,
            shade_color: int | None = 0,
            shade_opacity: int | None = 75,
            background_pixmap: bool | None = None,
            sample_text: bool | None = None,
            footer_text: bool | None = None):
        super().__init__()
        self.gui = gui
        self.for_sample = for_sample
        self.font_face = font_face
        self.font_size = int(font_size)
        self.use_outline = use_outline
        self.outline_color = outline_color
        self.outline_width = outline_width
        self.fill_color = fill_color
        self.use_shadow = use_shadow
        self.shadow_color = shadow_color
        self.shadow_offset = shadow_offset
        self.use_shade = use_shade
        self.shade_color = shade_color
        self.shade_opacity = shade_opacity
        self.sample_text = sample_text
        self.background_pixmap = background_pixmap
        if not self.background_pixmap:
            self.background_pixmap = QPixmap(1920, 1080)
            painter = QPainter(self.background_pixmap)
            painter.setBackground(Qt.GlobalColor.blue)

        if not self.sample_text:
            self.sample_text = ('A mighty fortress is our God;\n'
                                'A bulwark never failing.\n'
                                'Our helper He amid the flood,\n'
                                'Of mortal ills prevailing.')
        self.footer_text = footer_text
        if not self.footer_text:
            self.footer_text = 'Sample Song\nSample Composer\nSample Copyright Information\nSample CCLI Number'

        self.parent = self.gui
        self.init_components()
        
    def init_components(self):
        """
        current, default text/footer ratio is 20:1
        :return:
        """
        layout = QVBoxLayout(self)
        sample_display_width = int(self.gui.secondary_screen.size().width() / 2)
        sample_display_height = int(self.gui.secondary_screen.size().height() / 2)
        self.font_size = int(self.font_size / 2)
        h_margin = 5
        v_margin = 5
        lyric_height = int(sample_display_height / 21 * 20)
        footer_height = int(sample_display_height / 21)

        sample_widget = QWidget()
        sample_widget.setFixedSize(sample_display_width, sample_display_height)
        layout.addWidget(sample_widget)

        background_label = QLabel()
        background_label.setParent(sample_widget)
        background_label.setFixedSize(sample_display_width, sample_display_height)
        background_label.move(0, 0)
        self.background_pixmap = self.background_pixmap.scaled(
            sample_display_width,
            sample_display_height,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        background_label.setPixmap(self.background_pixmap)

        lyric_widget = TextLayoutLyricWidget(
            self.gui,
            self.for_sample,
            self.use_outline ,
            self.outline_color,
            self.outline_width,
            self.fill_color,
            self.use_shadow,
            self.shadow_color,
            self.shadow_offset,
            self.use_shade,
            self.shade_color,
            self.shade_opacity
        )
        lyric_widget.setFixedSize(sample_display_width - (h_margin * 2), lyric_height - v_margin)
        lyric_widget.move(h_margin, v_margin)
        lyric_widget.setText(self.sample_text)

        footer_widget = QLabel(self.footer_text)
        footer_widget.setFixedSize(sample_display_width - (h_margin * 2), footer_height - v_margin)


class TextLayoutLyricWidget(QWidget):
    def __init__(
            self,
            gui,
            for_sample: bool | None = False,
            font_face: str | None = 'Sans',
            font_size: int | None = 72,
            use_outline: bool | None = True,
            outline_color: QColor | None = QColor(0, 0, 0),
            outline_width: int | None = 8,
            fill_color: QColor | None = QColor(255, 255, 255),
            use_shadow: bool | None = True,
            shadow_color: QColor | None = QColor(0, 0, 0),
            shadow_offset: int | None = 5,
            use_shade: bool | None = False,
            shade_color: int | None = 0,
            shade_opacity: int | None = 75):
        super().__init__()
        self.gui = gui
        self.for_sample = for_sample
        self.font_face = font_face
        self.font_size = int(font_size)
        self.font = QFont(self.font_face, self.font_size, QFont.Weight.Bold)
        self.use_outline = use_outline
        self.outline_color = outline_color
        self.outline_width = outline_width
        self.fill_color = fill_color
        self.use_shadow = use_shadow
        self.shadow_color = shadow_color
        self.shadow_offset = shadow_offset
        self.use_shade = use_shade
        self.shade_color = shade_color
        self.shade_opacity = shade_opacity
        self.text = ''

    def setText(self, text):
        self.text = text

    def paintEvent(self, evt: QPaintEvent):
        self.total_height = 0
        self.text = re.sub('<p.*?>', '', self.text)
        self.text = re.sub('</p>', '', self.text)
        self.text = re.sub('\n', '<br />', self.text)
        self.text = re.sub('<br/>', '<br />', self.text)

        BOLD = 0
        ITALIC = 1
        UNDERLINE = 2

        font = self.font
        font_size = font.pointSize() + 2
        painter_paths = []
        longest_line = 0

        # build paths for each line, creating a new path whenever the line becomes too long
        usable_rect = QRect(0, 0, self.width(), self.height())
        self.total_height = -1
        line_height = 0
        while self.total_height == -1 or self.total_height > usable_rect.height():
            longest_line = 0
            painter_paths = []
            word_path = QPainterPath()
            path_index = -1

            font_size -= 2
            font = QFont(font.family(), font_size)
            self.setFont(font)
            line_height = self.fontMetrics().boundingRect('Way').height()
            space_width = self.fontMetrics().boundingRect('w w').width() - self.fontMetrics().boundingRect('ww').width()

            lines = self.text.split('<br />')
            for i in range(len(lines)):
                # if len(re.sub('<.*?>', '', lines[i]).strip()) > 0:
                x = 0
                y = 0
                line_words = lines[i].split(' ')
                if len(line_words) == 0:
                    line_words = [' ']
                painter_paths.append(QPainterPath())
                path_index += 1
                for word in line_words:
                    # if len(re.sub('<.*?>', '', word).strip()) > 0:
                    word_path.clear()
                    if '<b>' in word:
                        font.setWeight(1000)
                    if '<i>' in word:
                        font.setItalic(True)
                    if '<u>' in word:
                        font.setUnderline(True)

                    word_path.addText(QPointF(x, y), font, re.sub('<.*?>', '', word))
                    if (painter_paths[path_index].boundingRect().width() + word_path.boundingRect().width()
                            > self.gui.display_widget.width() - 40):
                        painter_paths.append(QPainterPath())
                        x = 0
                        y = 0
                        path_index += 1
                    painter_paths[path_index].addText(QPointF(x, y), font, re.sub('<.*?>', '', word))
                    x = painter_paths[path_index].boundingRect().width() + space_width

                    if '</b>' in word:
                        font.setWeight(QFont.Weight.Normal)
                    if '</i>' in word:
                        font.setItalic(False)
                    if '</u>' in word:
                        font.setUnderline(False)

            # get the total size of the paths that will be drawn for creating the shading rectangle
            self.total_height = 0
            for path in painter_paths:
                # if path.boundingRect().width() > 0:
                self.total_height += line_height
                if path.boundingRect().width() > longest_line:
                    longest_line = path.boundingRect().width()

        # start the first path at the midpoint of the usable rect, minus half the total height of the paths, plus
        # the font's ascent (to account for the path's y being the baseline of the text)
        path_y = (usable_rect.height() / 2) - (self.total_height / 2) + self.fontMetrics().ascent()
        starting_y = path_y
        painter = QPainter(self)
        brush = QBrush()
        painter.setBrush(brush)
        pen = QPen()
        painter.setPen(pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        opacity = self.shade_opacity
        if not self.use_shade:
            opacity = 0
        shade_rect = QRectF(
            int((self.gui.display_widget.width() / 2) - (longest_line / 2)) - 20,
            starting_y - self.fontMetrics().ascent() - 20,
            longest_line + 40,
            self.total_height + 40
        )
        painter.fillRect(shade_rect, QColor(self.shade_color, self.shade_color, self.shade_color, opacity))

        for path in painter_paths:
            path_x = (self.gui.display_widget.width() / 2) - (path.boundingRect().width() / 2)
            path.translate(path_x, path_y)

            if self.use_shadow:
                path.translate(self.shadow_offset, self.shadow_offset)
                shadow_brush = QBrush()
                shadow_brush.setColor(self.shadow_color)
                shadow_brush.setStyle(Qt.BrushStyle.SolidPattern)
                painter.fillPath(path, shadow_brush)
                path.translate(-self.shadow_offset, -self.shadow_offset)

            brush.setColor(self.fill_color)
            brush.setStyle(Qt.BrushStyle.SolidPattern)
            pen.setColor(self.outline_color)
            pen.setWidth(self.outline_width)
            painter.setPen(pen)

            painter.fillPath(path, brush)
            if self.use_outline:
                painter.strokePath(path, pen)

            path_y += line_height
        super().paintEvent(evt)


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
        save_button.setIconSize(self.gui.toolbar_icon_size)
        save_button.clicked.connect(self.gui.main.save_service)
        self.layout.addWidget(save_button)

        load_button = QPushButton()
        load_button.setIcon(QIcon('resources/gui_icons/open.svg'))
        load_button.setToolTip('Load a Service')
        load_button.setIconSize(self.gui.toolbar_icon_size)
        load_button.clicked.connect(self.gui.main.load_service)
        self.layout.addWidget(load_button)

        new_button = QPushButton()
        new_button.setIcon(QIcon('resources/gui_icons/new.svg'))
        new_button.setToolTip('Create a New Service')
        new_button.setIconSize(self.gui.toolbar_icon_size)
        new_button.clicked.connect(self.gui.new_service)
        self.layout.addWidget(new_button)

        settings_button = QPushButton()
        settings_button.setIcon(QIcon('resources/gui_icons/settings.svg'))
        settings_button.setToolTip('Open Program Settings')
        settings_button.setIconSize(self.gui.toolbar_icon_size)
        settings_button.clicked.connect(self.open_settings)
        self.layout.addWidget(settings_button)

        self.layout.addStretch()

        self.song_font_widget = NewFontWidget(self.gui, 'song')
        self.song_font_widget.hide()

        song_background_label = QLabel('Global Song Settings:')
        song_background_label.setFont(self.gui.standard_font)
        self.layout.addWidget(song_background_label)

        self.song_font_button = QPushButton()
        self.song_font_button.setObjectName('song_font_button')
        self.song_font_button.setIcon(QIcon('resources/gui_icons/font_settings.svg'))
        self.song_font_button.setIconSize(self.gui.toolbar_icon_size)
        self.song_font_button.setToolTip('Change Font Settings')
        self.song_font_button.setFont(self.gui.standard_font)
        self.song_font_button.clicked.connect(lambda: self.show_font_widget('song'))
        self.layout.addWidget(self.song_font_button)

        self.song_background_combobox = ImageCombobox(self.gui, 'song')
        self.song_background_combobox.setObjectName('song_background_combobox')
        self.song_background_combobox.setToolTip('Choose a Background for All Songs')
        self.layout.addWidget(self.song_background_combobox)

        self.bible_font_widget = NewFontWidget(self.gui, 'bible')
        self.bible_font_widget.hide()

        bible_background_label = QLabel('Global Bible Settings:')
        bible_background_label.setFont(self.gui.standard_font)
        self.layout.addWidget(bible_background_label)

        self.bible_font_button = QPushButton()
        self.bible_font_button.setObjectName('bible_font_button')
        self.bible_font_button.setIcon(QIcon('resources/gui_icons/font_settings.svg'))
        self.bible_font_button.setIconSize(self.gui.toolbar_icon_size)
        self.bible_font_button.setToolTip('Change Font Settings')
        self.bible_font_button.setFont(self.gui.standard_font)
        self.bible_font_button.clicked.connect(lambda: self.show_font_widget('bible'))
        self.layout.addWidget(self.bible_font_button)

        self.bible_background_combobox = ImageCombobox(self.gui, 'bible')
        self.bible_background_combobox.setObjectName('bible_background_combobox')
        self.bible_background_combobox.setToolTip('Choose a Background for Bible Slides')
        self.layout.addWidget(self.bible_background_combobox)

        self.layout.addStretch()

        self.hide_display_button = QPushButton()
        self.hide_display_button.setIcon(QIcon('resources/gui_icons/no_display.svg'))
        self.hide_display_button.setToolTip('Show/Hide the Display Screen')
        self.hide_display_button.setIconSize(self.gui.toolbar_icon_size)
        self.hide_display_button.setCheckable(True)
        self.hide_display_button.released.connect(self.gui.display_widget.show_hide)
        self.layout.addWidget(self.hide_display_button)

        self.black_screen_button = QPushButton()
        self.black_screen_button.setIcon(QIcon('resources/gui_icons/black_display.svg'))
        self.black_screen_button.setToolTip('Show a Black Screen')
        self.black_screen_button.setIconSize(self.gui.toolbar_icon_size)
        self.black_screen_button.setCheckable(True)
        self.black_screen_button.released.connect(
            lambda: self.gui.display_widget.show_black_screen(self.black_screen_button.isChecked()))
        self.layout.addWidget(self.black_screen_button)

        self.logo_screen_button = QPushButton()
        self.logo_screen_button.setIcon(QIcon('resources/gui_icons/logo_display.svg'))
        self.logo_screen_button.setToolTip('Show the Logo Screen')
        self.logo_screen_button.setIconSize(self.gui.toolbar_icon_size)
        self.logo_screen_button.setCheckable(True)
        self.logo_screen_button.released.connect(
            lambda: self.gui.display_widget.show_logo(self.logo_screen_button.isChecked()))
        self.layout.addWidget(self.logo_screen_button)

    def show_font_widget(self, slide_type: str):
        if slide_type == 'song':
            font_widget = self.song_font_widget
            font_button = self.song_font_button
        else:
            font_widget = self.bible_font_widget
            font_button = self.bible_font_button

        font_widget.adjustSize()
        font_widget.move(
            self.mapToGlobal(
                QPoint(font_button.x(), font_button.y() + font_button.height())))
        if font_widget.x() + font_widget.width() > self.gui.main_window.width():
            font_widget.move(
                self.mapToGlobal(
                    QPoint(self.gui.main_window.width() - font_widget.width(),
                           font_button.y() + font_button.height())))
            font_widget.change_font()

        font_widget.show()

    def import_songs(self):
       self.olpi = OpenLPImport(self.gui)

    def open_settings(self):
        self.sw.show()
        self.sw.setFocus()

    def import_background(self):
        result = QFileDialog.getOpenFileName(
            self.gui.main_window, 'Choose Background Image', os.path.expanduser('~') + '/Pictures')
        if len(result[0]) > 0:
            file_name = ''
            try:
                file_name_split = result[0].split('/')
                file_name = file_name_split[len(file_name_split) - 1]
                shutil.copy(result[0], self.gui.main.background_dir + '/' + file_name)
            except Exception:
                self.gui.main.error_log()

            from core.runnables import IndexImages
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

                elif 'bible' in sender.objectName():
                    self.gui.set_bible_background(self.gui.main.background_dir + '/' + data)
                    if self.gui.live_widget.slide_list.currentItem():
                        if self.gui.live_widget.slide_list.currentItem().data(40) == 'bible':
                            self.gui.display_widget.background_label.clear()
                            self.gui.display_widget.setStyleSheet('#display_widget { background-color: none } ')
                            self.gui.display_widget.background_label.setPixmap(self.gui.global_bible_background_pixmap)

                elif 'logo' in sender.objectName():
                    self.gui.set_logo_image(self.gui.main.image_dir + '/' + data)
                    if self.gui.display_widget.currentWidget() == self.gui.display_widget.logo_widget:
                        self.gui.display_widget.logo_label.clear()
                        self.gui.display_widget.logo_label.setPixmap(self.gui.logo_pixmap)


class CustomTreeWidget(QTreeWidget):
    def __init__(self, gui, parent: QWidget = None):
        super().__init__(parent)
        self.gui = gui
        self.sorting = False
        self.available_folders = []

        self.header().hide()

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.currentItemChanged.connect(self.current_item_changed)
        self.setSelectionMode(self.SelectionMode.ExtendedSelection)

    def add_item(self, item_text: str, item_data: dict, item_pixmap: QPixmap = None, item_parent: QTreeWidgetItem = None):
        widget = QWidget()
        layout = QHBoxLayout(widget)

        if item_pixmap:
            pixmap_label = QLabel()
            pixmap_label.setPixmap(item_pixmap)
            layout.addWidget(pixmap_label)

        label = QLabel(item_text)
        label.setFont(self.gui.standard_font)
        layout.addWidget(label)
        layout.addStretch()

        item = QTreeWidgetItem((item_text,), 0)
        item.setData(0, Qt.ItemDataRole.UserRole, item_data)

        if item_parent:
            item_parent.addChild(item)
        else:
            self.addTopLevelItem(item)
        self.setItemWidget(item, 0, widget)
        self.custom_sort()

        return item

    def add_folder(self, name: str = None, from_populate: bool = False):
        if not name:
            result = self.get_folder_name()
            if result == -1:
                return
            name = result

        if len(name.strip()) == 0:
            return

        # check that name isn't a duplicate of existing top level items
        for i in range(self.topLevelItemCount()):
            if self.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole)['title'] == name:
                name = f'{name} (1)'
                break

        widget = QWidget()
        layout = QHBoxLayout(widget)

        icon_label = QLabel()
        pixmap = QPixmap('resources/gui_icons/folder.svg').scaled(
            20,
            20,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        icon_label.setPixmap(pixmap)
        layout.addWidget(icon_label)

        title_label = QLabel(name)
        title_label.setObjectName('title_label')
        title_label.setFont(self.gui.bold_font)
        layout.addWidget(title_label)
        layout.addStretch()

        item = QTreeWidgetItem((name,), 0)
        item.setForeground(0, QBrush(Qt.GlobalColor.transparent))
        item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder', 'title': name})
        item.setSizeHint(0, widget.sizeHint())
        self.addTopLevelItem(item)
        self.setItemWidget(item, 0, widget)

        if not from_populate:
            self.custom_sort()
            self.scrollToItem(item)

        self.available_folders.append(name)
        self.available_folders.sort()

        return item

    def show_context_menu(self):
        click_pos = self.cursor().pos()
        item = self.currentItem()
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        menu = QMenu()
        menu.setToolTipsVisible(True)

        if not item_data['type'] == 'folder':
            move_menu = menu.addMenu('Move to folder...')
            for folder in self.available_folders:
                action = move_menu.addAction(folder)
                action.setObjectName(folder)
                action.triggered.connect(self.move_items)

        if type(item.parent()) == QTreeWidgetItem:
            action = menu.addAction('Move out of folder')
            action.setToolTip('Removes this item from its folder and moves it back into the main list')
            action.triggered.connect(lambda: self.complete_move(self.selectedItems()))

        menu.addSeparator()

        if not item_data['type'] == 'folder':
            add_to_service_action = QAction('Add to Order of Service')
            if item_data['type'] == 'song':
                add_to_service_action.triggered.connect(self.gui.media_widget.add_song_to_service)
            elif item_data['type'] == 'custom':
                add_to_service_action.triggered.connect(self.gui.media_widget.add_custom_to_service)
            elif item_data['type'] == 'image':
                add_to_service_action.triggered.connect(self.gui.media_widget.add_image_to_service)
            elif item_data['type'] == 'video':
                add_to_service_action.triggered.connect(self.gui.media_widget.add_video_to_service)
            elif item_data['type'] == 'web':
                add_to_service_action.triggered.connect(self.gui.media_widget.add_web_to_service)
            menu.addAction(add_to_service_action)

            edit_action = None
            if item_data['type'] == 'song':
                edit_action = QAction('Edit Song')
            elif item_data['type'] == 'custom':
                edit_action = QAction('Edit Slide')
            elif item_data['type'] == 'web':
                edit_action = QAction('Edit Web Item')

            if edit_action:
                if item_data['type'] == 'web':
                    edit_action.triggered.connect(self.edit_web)
                else:
                    edit_action.triggered.connect(self.edit_song)
            menu.addAction(edit_action)
        else:
            rename_action = menu.addAction('Rename Folder')
            rename_action.triggered.connect(self.rename_folder)

            empty_action = menu.addAction('Empty Folder')
            empty_action.setToolTip('Move all items in this folder to the main list')
            empty_action.triggered.connect(self.empty_folder)

        delete_action = None
        if item_data['type'] == 'image':
            delete_action = QAction('Remove Image')
            delete_action.triggered.connect(self.delete_item)
        elif item_data['type'] == 'custom':
            delete_action = QAction('Delete Slide')
            delete_action.triggered.connect(self.delete_item)
        elif item_data['type'] == 'song':
            delete_action = QAction('Delete Song')
            delete_action.triggered.connect(self.delete_item)
        elif item_data['type'] == 'video':
            delete_action = QAction('Remove Video')
            delete_action.triggered.connect(self.delete_item)
        elif item_data['type'] == 'web':
            delete_action = QAction('Remove Web Item')
            delete_action.triggered.connect(self.delete_item)
        elif item_data['type'] == 'folder':
            delete_action = QAction('Delete Folder')
            delete_action.triggered.connect(self.delete_item)

        if delete_action:
            menu.addAction(delete_action)

        menu.exec(click_pos)

    def current_item_changed(self):
        """
        Method to send the current item to the preview widget upon the current item being changed.
        """
        if self.currentItem():
            self.gui.send_to_preview(self.currentItem())

    def move_items(self):
        if len(self.selectedItems()) == 0:
            return
        folder_name = self.sender().objectName()

        target_items = self.findItems(folder_name, Qt.MatchFlag.MatchFixedString | Qt.MatchFlag.MatchRecursive, 0)
        if len(target_items) == 0:
            return
        self.complete_move(self.selectedItems(), target_items[0])
        self.custom_sort()

    def complete_move(self, items: list[QTreeWidgetItem], target_item: QTreeWidgetItem = None):
        if not items:
            return

        simple_splash = None
        if len(items) > 5:
            simple_splash = SimpleSplash(self.gui, 'Moving items...', True)

        for item in items:
            if (target_item
                    and item.data(0, Qt.ItemDataRole.UserRole)['type'] == 'folder'
                    and target_item.data(0, Qt.ItemDataRole.UserRole)['type'] == 'folder'):
                # we don't want folders nested into folders
                QMessageBox(
                    self.gui.main_window,
                    'Unsupported Action',
                    'Placing folders inside other folders is not currently supported.'
                )
                return

        if not target_item:
            for item in items:
                if simple_splash:
                    simple_splash.subtitle_label.setText(item.data(0, Qt.ItemDataRole.UserRole)['title'])
                    QApplication.processEvents()
                dragged_widget = self.itemWidget(item, 0)
                new_item = item.clone()
                self.addTopLevelItem(new_item)
                self.setItemWidget(new_item, 0, dragged_widget)

                data = new_item.data(0, Qt.ItemDataRole.UserRole)
                data['folder'] = ''
                item.setData(0, Qt.ItemDataRole.UserRole, data)
                if data['type'] == 'song':
                    self.gui.main.save_song(data, old_title=data['title'])
                elif data['type'] == 'custom':
                    self.gui.main.save_custom(data, old_title=data['title'])
                elif data['type'] == 'image':
                    self.gui.main.save_image(data, old_title=data['title'])
                elif data['type'] == 'video':
                    self.gui.main.save_video(data, old_title=data['title'])
                elif data['type'] == 'web':
                    self.gui.main.save_web_item(data, old_title=data['title'])
        else:
            for item in items:
                if simple_splash:
                    simple_splash.subtitle_label.setText(item.data(0, Qt.ItemDataRole.UserRole)['title'])
                    QApplication.processEvents()
                dragged_widget = self.itemWidget(item, 0)
                new_item = item.clone()
                target_item.addChild(new_item)
                target_item.setExpanded(True)
                self.setItemWidget(new_item, 0, dragged_widget)

                data = new_item.data(0, Qt.ItemDataRole.UserRole)
                data['folder'] = target_item.data(0, Qt.ItemDataRole.UserRole)['title']
                item.setData(0, Qt.ItemDataRole.UserRole, data)
                if data['type'] == 'song':
                    self.gui.main.save_song(data, old_title=data['title'])
                elif data['type'] == 'custom':
                    self.gui.main.save_custom(data, old_title=data['title'])
                elif data['type'] == 'image':
                    self.gui.main.save_image(data, old_title=data['title'])
                elif data['type'] == 'video':
                    self.gui.main.save_video(data, old_title=data['title'])
                elif data['type'] == 'web':
                    self.gui.main.save_web_item(data, old_title=data['title'])

        for item in items:
            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                self.takeTopLevelItem(self.indexOfTopLevelItem(item))

        self.custom_sort()
        self.scrollToItem(target_item)

    def custom_sort(self):
        if self.sorting:
            return
        self.sorting = True

        folder_items = []
        other_items = []

        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)

            if data and data.get('type') == 'folder':
                folder_items.append((data.get('title', '').lower(), item))
            else:
                title = data.get('title', '') if data else item.text(0)
                other_items.append((title.lower(), item))

        # Sort alphabetically in memory
        folder_items.sort(key=lambda x: x[0])
        other_items.sort(key=lambda x: x[0])

        # 2. Apply a strict sequential "Sort Text" or "Sort Weight" to column 0.
        # To make Qt sort them exactly in this order without breaking widgets,
        # we can temporarily inject a hidden sort key into the item's display role,
        # sort it, and then put the original widgets/text right back.

        # Combine them: Folders first, then others
        master_list = folder_items + other_items

        # Store original text values so we can restore them if needed
        # (Though if you are using setItemWidget, the text is hidden behind the widget anyway!)
        original_texts = []

        for index, (title, item) in enumerate(master_list):
            original_texts.append((item, title))
            # Pad the index with zeros (e.g., "00001", "00002") so string sorting matches numerical sorting
            item.setText(0, f"{index:05d}")

        super().sortItems(0, Qt.SortOrder.AscendingOrder)

        # 4. Restore the original text values.
        # Because we aren't changing their positions anymore, the widgets stay perfectly intact!
        for item, item_text in original_texts:
            item.setText(0, item_text)
        self.sorting = False

    def edit_song(self):
        """
        Method to create a EditWidget for a song or custom slide.
        """

        from guiElements.widgets.editWidget import EditWidget
        if self.currentItem():
            data = self.currentItem().data(0, Qt.ItemDataRole.UserRole)
            if data['type'] == 'song':
                self.gui.edit_widget = EditWidget(self.gui, data, 'song')
            elif data['type'] == 'custom':
                self.gui.edit_widget = EditWidget(self.gui, data, 'custom')

        self.custom_sort()

    def edit_web(self):
        if not self.currentItem():
            return

        data = self.currentItem().data(0, Qt.ItemDataRole.UserRole)
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
            self.gui.media_widget.save_web(title_line_edit.text(), url_line_edit.text(), old_title=data['title'])
            self.gui.media_widget.populate_web_list()
            self.custom_sort()

    def rename_folder(self):
        result = self.get_folder_name()

        if result == -1:
            return

        item = self.currentItem()
        data = item.data(0, Qt.ItemDataRole.UserRole)
        old_name = data['title']
        data['title'] = result
        item.setData(0, Qt.ItemDataRole.DisplayRole, data)
        widget = self.itemWidget(item, 0)
        widget.findChild(QLabel, 'title_label').setText(result)

        self.available_folders.remove(old_name)
        self.available_folders.append(result)
        self.available_folders.sort()

        self.custom_sort()

    def empty_folder(self):
        children = []
        for i in range(self.currentItem().childCount()):
            children.append(self.currentItem().child(i))
        self.complete_move(children)

    def get_folder_name(self):
        dialog = QDialog(self.gui.main_window)
        dialog_layout = QVBoxLayout(dialog)

        dialog_label = QLabel('Please enter your new folder name:')
        dialog_label.setFont(self.gui.standard_font)
        dialog_layout.addWidget(dialog_label)

        dialog_line_edit = QLineEdit('Folder Name')
        dialog_line_edit.setFont(self.gui.standard_font)
        dialog_line_edit.setFocus()
        dialog_line_edit.selectAll()
        dialog_layout.addWidget(dialog_line_edit)

        dialog_button_widget = QWidget()
        dialog_layout.addWidget(dialog_button_widget)
        dialog_button_layout = QHBoxLayout(dialog_button_widget)
        dialog_button_layout.setContentsMargins(0, 0, 0, 0)

        ok_button = QPushButton('Ok')
        ok_button.setFont(self.gui.standard_font)
        ok_button.pressed.connect(lambda: dialog.done(1))
        dialog_button_layout.addStretch()
        dialog_button_layout.addWidget(ok_button)

        cancel_button = QPushButton('Cancel')
        cancel_button.setFont(self.gui.standard_font)
        cancel_button.pressed.connect(lambda: dialog.done(-1))
        dialog_button_layout.addWidget(cancel_button)
        dialog_button_layout.addStretch()

        result = dialog.exec()
        if not result == 1:
            return -1
        return dialog_line_edit.text()

    def delete_item(self):
        """
        Method to remove an item from this widget. Creates a QMessageBox to confirm removal.
        """
        if len(self.selectedItems()) == 0:
            return

        items = self.selectedItems()

        titles = []
        has_folder = False
        for item in items:
            titles.append(item.data(0, Qt.ItemDataRole.UserRole)['title'])
            if item.data(0, Qt.ItemDataRole.UserRole)['type'] == 'folder':
                has_folder = True
        title_count = len(titles)

        if title_count == 0:
            return
        elif title_count == 1:
            titles = titles[0]
        elif title_count == 2:
            titles = ' and '.join(titles)
        else:
            if title_count > 3:
                truncated_titles = titles[:3]
                remaining_count = title_count - 3
                if remaining_count == 1:
                    titles = f'{", ".join(truncated_titles)}, and {remaining_count} more item'
                else:
                    titles = f'{", ".join(truncated_titles)}, and {remaining_count} more items'
            else:
                titles = f'{", ".join(titles[:-1])}, and {titles[-1]}'

        if has_folder:
            message = (f'Really delete {titles}? All items contained in selected folders will also be deleted. '
                       f'This action cannot be undone')
        else:
            message = f'Really delete {titles}? This action cannot be undone.'

        response = QMessageBox.question(
            self.gui.main_window,
            'Really Delete',
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if not response == QMessageBox.StandardButton.Yes:
            return

        # remove the selected items from the database
        items_to_delete_from_db = set()
        for item in items:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data['type'] == 'folder':
                for i in range(item.childCount()):
                    child_data = item.child(i).data(0, Qt.ItemDataRole.UserRole)
                    if child_data['type'] == 'video':
                        items_to_delete_from_db.add((child_data['type'], child_data['file_name']))
                    else:
                        items_to_delete_from_db.add((child_data['type'], child_data['title']))
            elif data['type'] == 'video':
                items_to_delete_from_db.add((data['type'], data['file_name']))
            else:
                items_to_delete_from_db.add((data['type'], data['title']))
        self.gui.main.delete_items_from_db(items_to_delete_from_db)

        # remove each selected item from the tree
        for item in items:
            if item.data(0, Qt.ItemDataRole.UserRole)['type'] == 'folder':
                children = item.takeChildren()
                children.clear()

            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                index = self.indexOfTopLevelItem(item)
                if index != -1:
                    detached = self.takeTopLevelItem(index)
                    del detached

        if len(titles) == 1:
            message = f'{titles} has been removed.'
        else:
            message = f'{titles} have been removed.'
        QMessageBox.information(
            self.gui.main_window,
            'Removed',
            message,
            QMessageBox.StandardButton.Ok
        )

        self.gui.preview_widget.slide_list.clear()
        self.gui.preview_widget.preview_label.clear()

        self.custom_sort()

    def dropEvent(self, evt: QDropEvent):
        target_item = self.itemAt(evt.pos())
        target_item_data = None
        if target_item:
            target_item_data = target_item.data(0, Qt.ItemDataRole.UserRole)

        if (not target_item_data or not target_item_data['type'] == 'folder') and evt.pos() in self.rect():
            self.complete_move(self.selectedItems())
        elif target_item_data and target_item_data['type'] == 'folder':
            self.complete_move(self.selectedItems(), target_item)

    def mouseDoubleClickEvent(self, evt: QMouseEvent):
        """
        Overrides mouseDoubleClickEvent to provide the ability to add an item to the order of service upon double-click.
        :param QMouseEvent evt: mouseEvent
        """
        if not self.currentItem():
            return

        data = self.currentItem().data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data['type'] == 'song':
            self.gui.media_widget.add_song_to_service()
        elif data['type'] == 'custom':
            self.gui.media_widget.add_custom_to_service()
        elif data['type'] == 'web':
            self.gui.media_widget.add_web_to_service()
        elif data['type'] == 'image':
            self.gui.media_widget.add_image_to_service()
        elif data['type'] == 'video':
            self.gui.media_widget.add_video_to_service()
        elif data['type'] == 'folder':
            if self.currentItem().isExpanded():
                self.currentItem().setExpanded(False)
            else:
                self.currentItem().setExpanded(True)

        self.gui.oos_widget.oos_list_widget.setCurrentRow(self.gui.oos_widget.oos_list_widget.count() - 1)
        self.gui.oos_widget.oos_list_widget.setFocus()

    def keyPressEvent(self, evt: QKeyEvent):
        if evt.key() == Qt.Key.Key_Delete:
            self.delete_item()
        else:
            super().keyPressEvent(evt)

    def mouseReleaseEvent(self, evt):
        super().mouseReleaseEvent(evt)
        # since send_to_preview is called on currentItemChanged, provide send to preview on mouse release as well
        # in case this widget only has one item
        if self.currentItem():
            self.gui.send_to_preview(self.currentItem())