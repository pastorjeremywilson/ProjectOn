import os
import re
import shutil
import sqlite3
import sys

import requests
from PyQt5.QtCore import Qt, QSize, QEvent, QMargins, QPointF, QTimer, pyqtSignal, QRect, QRectF, QPoint, QSizeF, QTime
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor, QPainterPath, QPalette, QBrush, QPen, QPainter, \
    QImage, QFontDatabase, QFontMetrics
from PyQt5.QtMultimedia import QMediaPlayer
from PyQt5.QtPrintSupport import QPrinterInfo, QPrinter
from PyQt5.QtWidgets import QListWidget, QLabel, QListWidgetItem, QComboBox, QListView, QWidget, QVBoxLayout, \
    QGridLayout, QSlider, QMainWindow, QMessageBox, QScrollArea, QLineEdit, QHBoxLayout, \
    QSpinBox, QRadioButton, QButtonGroup, QCheckBox, QColorDialog, QGraphicsRectItem, QDialog, QTextEdit, QPushButton, \
    QApplication, QFontComboBox, QGroupBox, QTabWidget, QTimeEdit, QFileDialog


class AutoSelectLineEdit(QLineEdit):
    """
    Implements QLineEdit to add the ability to select all text when this line edit receives focus.
    """
    def __init__(self):
        super().__init__()

    def focusInEvent(self, evt):
        super().focusInEvent(evt)
        QTimer.singleShot(0, self.selectAll)


class ClickableColorSwatch(QLabel):
    color_changed = pyqtSignal()
    def __init__(self, gui):
        super().__init__()
        self.gui = gui

    def make_color_swatch_pixmap(self, rgb_color):
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

    def mouseReleaseEvent(self, evt):
        super().mouseReleaseEvent(evt)
        image = self.pixmap().toImage()
        current_color = image.pixelColor(10, 10)
        chosen_color = QColorDialog.getColor(current_color, self.gui.main_window, 'Countdown Background Color')
        rgb_color = f'rgba({chosen_color.red()}, {chosen_color.green()}, {chosen_color.blue()}, {chosen_color.alpha()})'
        self.make_color_swatch_pixmap(rgb_color)
        self.color_changed.emit()


class CountdownWidget(QWidget):
    update_label_signal = pyqtSignal(str)
    show_self_signal = pyqtSignal()
    hide_self_signal = pyqtSignal()

    def __init__(self, gui, font, position, bg, fg):
        super().__init__()
        self.gui = gui

        self.update_label_signal.connect(self.update_label)
        self.show_self_signal.connect(self.show_self)
        self.hide_self_signal.connect(self.hide_self)

        #self.setParent(self.gui.display_widget)
        self.setWindowFlag(Qt.WindowType.ToolTip)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

        self.setStyleSheet('background-color: ' + bg)
        self.setAttribute(Qt.WA_StyledBackground, True)
        layout = QGridLayout(self)

        self.label = QLabel()
        self.label.setFont(font)
        self.label.setStyleSheet('color: ' + fg)
        layout.addWidget(self.label, 0, 0, Qt.AlignmentFlag.AlignCenter)

        font_metrics = QFontMetrics(font)
        font_height = font_metrics.height()
        height = font_height + 40

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
        #self.raise_()
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
        :param gui.GUI gui:
        """
        super().__init__()
        self.gui = gui

    def closeEvent(self, evt):
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
            if self.gui.media_player:
                if self.gui.media_player.state() == QMediaPlayer.PlayingState:
                    self.gui.media_player.stop()
                self.gui.media_player.deleteLater()
                if self.gui.video_widget:
                    self.gui.video_widget.deleteLater()
                self.gui.media_player = None
                self.gui.video_widget = None
                self.gui.audio_output = None
                self.gui.video_probe = None

            self.gui.main.server_check_timer.stop()
            if self.gui.countdown_timer:
                self.gui.countdown_timer.stop()
            if self.gui.countdown_widget:
                self.gui.countdown_widget.deleteLater()

            try:
                self.gui.main.server_check.keep_checking = False
            except AttributeError:
                pass
            self.gui.main.save_settings()

            if self.gui.timed_update:
                self.gui.timed_update.keep_running = False
            if self.gui.slide_auto_play:
                self.gui.slide_auto_play.keep_running = False
            evt.accept()
            self.gui.display_widget.deleteLater()


class CustomScrollArea(QScrollArea):
    """
    A simple reimplementation of QScrollArea to ensure that its widget gets resized if the scroll area is resized
    """
    def __init__(self):
        super().__init__()

    def resizeEvent(self, evt):
        self.widget().setFixedWidth(self.width())


class CustomSlider(QSlider):
    def __init__(self):
        super().__init__()
        self.mouse_pressed = False

    def mousePressEvent(self, evt):
        self.mouse_pressed = True
        super().mousePressEvent(evt)

    def mouseReleaseEvent(self, evt):
        self.mouse_pressed = False
        super().mouseReleaseEvent(evt)


class DisplayWidget(QWidget):
    """
    Provides a custom QWidget to be used as the display widget
    """
    def __init__(self, gui, sample=False):
        """
        Provides a custom QWidget to be used as the display widget
        :param gui.GUI gui: The current instance of GUI
        :param bool sample: Whether this is intended to be the sample widget
        """
        super().__init__()
        self.gui = gui
        self.sample = sample
        margins = QMargins(0, 0, 0, 0)

        self.setObjectName('display_widget')
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet('#display_widget { background: blue; }')
        self.setContentsMargins(margins)

        # provide a QLabel for drawing the background image
        self.background_label = QLabel()
        self.background_label.setObjectName('background_label')
        self.background_label.setParent(self)
        self.background_label.setGeometry(self.geometry())
        self.background_label.move(self.x(), self.y())

        self.background_pixmap = None

    def toggle_show_hide(self):
        """
        Convenience method to show/hide this display widget
        """
        if self.isHidden():
            self.showFullScreen()
        else:
            self.hide()

    def paintEvent(self, evt):
        # in the case of a background pixmap, either center it if the pixmap is smaller than the display widget,
        # or scale it down if it is bigger
        super().paintEvent(evt)
        if self.background_pixmap:
            #self.background_label.setStyleSheet('border: 5px solid green')
            p_width = self.background_pixmap.width()
            p_height = self.background_pixmap.height()

            width_diff = self.width() - p_width
            height_diff = self.height() - p_height

            if width_diff > 0 and height_diff > 0:
                if width_diff > height_diff:
                    ratio = self.width() / p_width
                else:
                    ratio = self.height() / p_height
            elif width_diff > 0 and height_diff > 0:
                if width_diff > height_diff:
                    ratio = self.height() / p_height
                else:
                    ratio = self.width() / p_width
            else:
                if width_diff > 0:
                    ratio = self.width() / p_width
                else:
                    ratio = self.height() / p_height

            """if p_width < self.width() or p_height < self.height():
                x = int((self.width() / 2) - (self.background_pixmap.width() / 2))
                y = int((self.height() / 2) - (self.background_pixmap.height() / 2))
            elif p_width > self.width() or p_height > self.height():
                x_ratio = self.width() / p_width
                y_ratio = self.height() / p_height
                if x_ratio < y_ratio:
                    ratio = x_ratio
                else:
                    ratio = y_ratio"""

            """background_pixmap = self.background_pixmap.scaled(
                int(p_width / ratio),
                int(p_height / ratio),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )"""
            background_pixmap = self.background_pixmap.scaled(
                self.width(),
                self.height(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.background_label.setPixmap(background_pixmap)
            return
            """    x = int((self.width() / 2) - (self.background_pixmap.width() / 2))
                y = int((self.height() / 2) - (self.background_pixmap.height() / 2))
            else:"""
            x = 0
            y = 0

            # paint a new pixmap using the new coordinates and/or size
            pixmap = QPixmap(self.width(), self.height())
            brush = QBrush()
            brush.setColor(Qt.GlobalColor.black)
            brush.setStyle(Qt.BrushStyle.SolidPattern)

            painter = QPainter(pixmap)
            painter.setBackground(brush)
            painter.drawPixmap(x, y, self.background_pixmap)
            painter.end()

            self.background_label.setPixmap(pixmap)


class FontFaceListWidget(QListWidget):
    """
    Creates a custom QListWidget that displays all fonts on the system in their own style.
    :param gui.GUI gui: The current instance of GUI
    """
    def __init__(self, gui):
        """
        :param gui.GUI gui: The current instance of GUI
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
    :param gui.GUI gui: The current instance of GUI
    """
    current_font = None

    def __init__(self, gui):
        """
        :param gui.GUI gui: The current instance of GUI
        """
        super().__init__()
        self.setObjectName('FontFaceComboBox')
        self.gui = gui
        self.setEditable(True)
        self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.populate_widget()

    def populate_widget(self):
        try:
            for i in range(len(self.gui.font_pixmaps)):
                if i == len(self.gui.font_pixmaps) - 1:
                    self.setIconSize(QSize(self.gui.font_pixmaps[i][0], self.gui.font_pixmaps[i][1]))
                    self.setMinimumWidth(self.gui.font_pixmaps[i][0])
                else:
                    self.addItem(QIcon(self.gui.font_pixmaps[i][1]), self.gui.font_pixmaps[i][0])
        except Exception:
            self.gui.main.error_log()

        for i in range(self.count()):
            if self.itemText(i) == self.current_font:
                self.setCurrentIndex(i)
                break

    def wheelEvent(self, evt):
        evt.ignore()


class FontSample(QLabel):
    text = ''
    def __init__(self, settings_widget,
                 use_outline=True,
                 outline_color=QColor(0, 0, 0),
                 outline_width=8,
                 fill_color=QColor(255, 255, 255),
                 use_shadow=True,
                 shadow_color=QColor(0, 0, 0),
                 shadow_offset=5,
                 use_shade=False,
                 shade_color=0,
                 shade_opacity=50):
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

        self.sample_background = None

        self.container = self.settings_widget.findChild(QWidget, 'font_sample_container')
        self.widget = self.settings_widget.findChild(QWidget, 'font_sample_widget')
        self.background_label = self.settings_widget.findChild(QLabel, 'font_sample_background_label')

    def paintEvent(self, evt):
        self.paint_font()
        super().paintEvent(evt)

    def paint_font(self):
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

    def make_sample_background(self, rect):
        slide_type = self.settings_widget.slide_type

        if self.settings_widget.applies_to_global:
            sample_background = QImage(
                self.settings_widget.gui.main.background_dir + '/'
                + self.settings_widget.gui.main.settings[f'global_{slide_type}_background'])
        else:
            background = self.settings_widget.parent().parent().findChild(QLineEdit, 'background_line_edit').text()
            if 'rgb(' in background:
                background = background.replace('rgb(', '')
                background = background.replace(')', '')
                background_split = background.split(', ')
                sample_background = QImage(QSize(1920, 1080), QImage.Format.Format_RGB32)
                sample_background.fill(
                    QColor(int(background_split[0]), int(background_split[1]), int(background_split[2])))
            elif 'Song' in background:
                sample_background = QImage(
                    self.settings_widget.gui.main.background_dir + '/'
                    + self.settings_widget.gui.main.settings['global_song_background'])
            elif 'Bible' in background:
                sample_background = QImage(
                    self.settings_widget.gui.main.background_dir + '/'
                    + self.settings_widget.gui.main.settings['global_bible_background'])
            else:
                sample_background = QImage(self.settings_widget.gui.main.background_dir + '/' + background)

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


class FontWidget(QWidget):
    """
    Implements QWidget that contains all of the settings that can be applied to the display font
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

        #self.font_face_combobox = FontFaceComboBox(self.gui)
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

    def blockSignals(self, block):
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

    def change_font(self, value=None):
        """
        applies the currently chosen font settings to gui's global_font_face, global_footer_font_face, and settings
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

            #new_font_face = self.font_list_widget.currentItem().data(20)
            new_font_face = self.font_face_combobox.currentText()
            self.gui.global_font_face = new_font_face
            self.gui.global_footer_font_face = new_font_face

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

    def hideEvent(self, evt):
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
    def __init__(self, gui, type, suppress_autosave=False):
        """
        :param gui.GUI gui: The current instance of GUI
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
            for record in thumbnails:
                if self.gui.main.initial_startup:
                    self.gui.main.update_status_signal.emit('Loading Thumbnails', 'status')
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

    def wheelEvent(self, evt):
        # prevent wheel scrolling, which is undesirable in the settings layout
        evt.ignore()


class LyricDisplayWidget(QWidget):
    """
    Provide a standardized QWidget to be used for showing lyrics on the display and sample widgets.py
    """
    def __init__(
            self,
            gui,
            for_sample=False,
            use_outline=True,
            outline_color=QColor(0, 0, 0),
            outline_width=8,
            fill_color=QColor(255, 255, 255),
            use_shadow=True,
            shadow_color=QColor(0, 0, 0),
            shadow_offset=5,
            use_shade=False,
            shade_color=0,
            shade_opacity=75):
        """
        Provide a standardized QWidget to be used for showing lyrics on the display and sample widgets.py
        :param gui.GUI gui: The current instance of GUI
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
        self.for_sample = for_sample
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
        self.total_height = 0

        margins = QMargins(0, 0, 0, 0)
        self.setContentsMargins(margins)

        layout = QGridLayout()
        layout.setRowStretch(0, 20)
        layout.setRowStretch(1, 1)
        layout.setContentsMargins(margins)
        self.setLayout(layout)
        self.setObjectName('lyric_display_widget')
        self.setAutoFillBackground(False)

        self.footer_label = QLabel()
        self.footer_label.setContentsMargins(margins)
        self.footer_label.setWordWrap(True)
        self.footer_label.setObjectName('footer_label')
        layout.addWidget(self.footer_label, 1, 0)

    def setText(self, text):
        """
        Convenience method to set the text variable
        :param str text: Text to be shown
        """
        self.text = text

    def set_geometry(self):
        """
        Sets the geometry to match its parent widget
        """
        if self.for_sample:
            self.setParent(self.gui.sample_widget)
            self.setGeometry(self.gui.sample_widget.geometry())
            self.move(self.gui.sample_widget.x(), self.gui.sample_widget.y())

    def paintEvent(self, evt):
        """
        Overrides paintEvent to custom paint the text onto the widget
        :param QPaintEvent evt: paintEvent
        """
        palette = self.footer_label.palette()
        palette.setColor(QPalette.ColorRole.WindowText, self.fill_color)
        self.footer_label.setPalette(palette)
        self.paint_text()

    def paint_text(self):
        """
        Method to paint the text onto the widget, using the prescribed outline and shadow values
        """
        self.total_height = 0
        self.text = re.sub('<p.*?>', '', self.text)
        self.text = re.sub('</p>', '', self.text)
        self.text = re.sub('\n', '<br />', self.text)
        self.text = re.sub('<br/>', '<br />', self.text)

        BOLD = 0
        ITALIC = 1
        UNDERLINE = 2

        """text_lines = self.text.split('<br />')
        line_height = self.fontMetrics().boundingRect('Way').height()
        lines = []
        for this_line in text_lines:
            this_line = this_line.strip()

            # split the lines according to their drawn length
            if self.fontMetrics().boundingRect(this_line).width() < self.gui.display_widget.width() - 20:
                lines.append(this_line)
            else:
                this_line_split = this_line.split(' ')
                current_line = ''
                for word in this_line_split:
                    current_line = (current_line + ' ' + word).strip()
                    print(current_line)
                    if self.fontMetrics().boundingRect(current_line).width() > self.gui.display_widget.width() - 20:
                        lines.append(' '.join(current_line.split(' ')[:-1]))
                        current_line = word
                lines.append(current_line)"""

        font = self.font()
        font_size = font.pointSize() + 2
        painter_paths = []
        longest_line = 0
        self.footer_label.adjustSize()

        # build paths for each line, creating a new path whenever the line becomes too long
        footer_height = self.footer_label.height()
        if self.footer_label.isHidden() or len(self.footer_label.text().strip()) == 0:
            footer_height = 0
        usable_rect = QRect(0, 0, self.gui.display_widget.width(), self.gui.display_widget.height() - footer_height - 40)
        self.total_height = -1
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
                #if len(re.sub('<.*?>', '', lines[i]).strip()) > 0:
                x = 0
                y = 0
                line_words = lines[i].split(' ')
                if len(line_words) == 0:
                    line_words = [' ']
                painter_paths.append(QPainterPath())
                path_index += 1
                for word in line_words:
                    #if len(re.sub('<.*?>', '', word).strip()) > 0:
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
                #if path.boundingRect().width() > 0:
                self.total_height += line_height
                if path.boundingRect().width() > longest_line:
                    longest_line = path.boundingRect().width()

            if self.for_sample:
                break

        # start the first path at the midpoint of the usable rect, minus half the total height of the paths, plus
        # the font's ascent (to account for the path's y being the baseline of the text) plus a 20px margin at the top
        path_y = (usable_rect.height() / 2) - (self.total_height / 2) + self.fontMetrics().ascent() + 20
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
            #if path.boundingRect().width() > 0:
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


class NewFontWidget(QWidget):
    """
    Implements QWidget that contains all of the settings that can be applied to the display font
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

        #self.font_face_combobox = FontFaceComboBox(self.gui)
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
        layout.addSpacing(10)

        font_style_widget = QGroupBox()
        font_style_widget.setFont(self.gui.bold_font)
        font_style_widget.setTitle('Font Style')
        layout.addWidget(font_style_widget)
        font_style_layout = QHBoxLayout(font_style_widget)

        font_face_label = QLabel('Font Face')
        font_face_label.setFont(self.gui.bold_font)
        font_style_layout.addWidget(font_face_label)

        self.font_face_combobox.setFont(self.gui.standard_font)
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

    def blockSignals(self, block):
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

    def change_font(self, value=None):
        """
        applies the currently chosen font settings to gui's global_font_face, global_footer_font_face, and settings
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

            #new_font_face = self.font_list_widget.currentItem().data(20)
            new_font_face = self.font_face_combobox.currentText()
            self.gui.global_font_face = new_font_face
            self.gui.global_footer_font_face = new_font_face

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

    def hideEvent(self, evt):
        """
        overrides hideEvent to save settings when the widget is hidden
        """
        self.gui.main.save_settings()
        self.gui.apply_settings(theme_too=False)
        super().hideEvent(evt)


class OffsetSlider(QWidget):
    """
    Creates a widget containing a QSlider and Label which lets the user set the distance of the display's shadow offset
    :param gui.GUI gui: The current instance of GUI
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
        self.offset_slider.setRange(0, 15)
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

    def eventFilter(self, obj, evt):
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
    def __init__(self, document):
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
    :param gui.GUI gui: The current instance of GUI
    """
    def __init__(self, gui):
        """
        Creates a widget containing a QSlider and Label which lets the user set the greyness of the display's shadow
        :param gui.GUI gui: The current instance of GUI
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

    def change_sample(self, value):
        new_pixmap = QPixmap(20, 20)
        new_pixmap.fill(QColor(value, value, value))
        self.color_label.setPixmap(new_pixmap)

    def eventFilter(self, obj, evt):
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

    def __init__(self, gui, text='', subtitle=False, parent=None):
        """
        Provides a simple and standardized popup for showing messages
        :param gui.GUI gui: the current instance of GUI
        :param str text: the text to be displayed
        :param str subtitle: optional: subtitle to be displayed under the text
        :param obj parent: optional: parent widget for SimpleSplash's main widget
        """
        self.gui = gui
        self.text = text

        self.widget = QWidget(parent)
        self.widget.setStyleSheet('background: #6060c0;')
        self.widget.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.widget.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)
        main_layout = QVBoxLayout(self.widget)

        container = QWidget()
        container.setObjectName('container')
        container.setStyleSheet(
            '#container { padding: 30px 20px; border: 3px solid white;}')
        container.setMinimumWidth(300)
        layout = QGridLayout(container)
        main_layout.addWidget(container)

        self.label = QLabel(text)
        self.label.setFont(self.gui.bold_font)
        self.label.setStyleSheet('color: white; padding: 10px 5px;')
        layout.addWidget(self.label, 0, 0, Qt.AlignmentFlag.AlignHCenter)

        if subtitle:
            self.subtitle_label = QLabel(' ')
            self.subtitle_label.setFont(self.gui.list_font)
            self.subtitle_label.setStyleSheet('color: white; padding: 10px 5px;')
            layout.addWidget(self.subtitle_label, 1, 0, Qt.AlignmentFlag.AlignHCenter)

        container.adjustSize()
        self.widget.adjustSize()
        x = int((self.gui.primary_screen.size().width() / 2) - (self.widget.width() / 2))
        y = int((self.gui.primary_screen.size().height() / 2) - (self.widget.height() / 2))
        self.widget.move(x, y)
        self.widget.show()
        QApplication.processEvents()


class StandardDialog(QDialog):
    def __init__(self, gui, message, icon=None, temporary=False, buttons=['yes', 'no', 'cancel']):
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
        self.buttons = buttons

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
            self.icon = self.icon.scaledToHeight(50, Qt.SmoothTransformation)
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
            if this_button == 'ok':
                this_button.pressed.connect(lambda: self.done(self.OK))
            elif this_button == 'yes':
                this_button.pressed.connect(lambda: self.done(self.YES))
            elif this_button == 'no':
                this_button.pressed.connect(lambda: self.done(self.NO))
            elif this_button == 'cancel':
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
    def __init__(self, gui, title, subtitle=None, icon=None, wrap_subtitle=False):
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

    def __init__(self, gui):
        super().__init__()
        self.accept_font_changes = False
        self.setObjectName('settings_container')
        self.gui = gui
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
        #self.gui.main.app.processEvents()
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
        ccli_title_label.setStyleSheet('background: #5555aa; color: white')
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
        display_title_label.setStyleSheet('background: #5555aa; color: white;')
        display_title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(display_title_label, 0, 0, 1, index + 1)

        self.screen_button_group = QButtonGroup()
        id = 0
        for button in widget.findChildren(QRadioButton):
            self.screen_button_group.addButton(button, id)
            id += 1

        stage_display_title_label = QLabel('Stage Display Settings')
        stage_display_title_label.setFont(self.gui.bold_font)
        stage_display_title_label.setStyleSheet('background: #5555aa; color: white;')
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
            rendering_title_label.setStyleSheet('background: #5555aa; color: white;')
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
            software_details.setStyleSheet('border: none; background: rgba(0, 0, 0, 0);')
            software_details.setReadOnly(True)
            software_details.setCursor(Qt.CursorShape.ArrowCursor)
            software_details.setFont(self.gui.list_font)
            layout.addWidget(software_details, 9, 0, 1, index + 1)

        layout.setRowStretch(10, 100)

        return widget

    def font_settings(self):
        widget = QWidget()
        widget.setMinimumWidth(self.min_width)
        widget.setObjectName('settings_container')
        layout = QVBoxLayout()
        widget.setLayout(layout)

        stage_title_label = QLabel('Stage Display Font Settings')
        stage_title_label.setFont(self.gui.bold_font)
        stage_title_label.setStyleSheet('background: #5555aa; color: white')
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
        title_label.setStyleSheet('background: #5555aa; color: white')
        title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(title_label)

        font_widget = QWidget()
        font_layout = QVBoxLayout()
        font_widget.setLayout(font_layout)
        layout.addWidget(font_widget)

        self.song_font_settings_widget = NewFontWidget(self.gui, 'song', draw_border=False)
        #font_layout.addWidget(self.song_font_settings_widget)
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
        from widgets import ImageCombobox

        widget = QWidget()
        widget.setObjectName('settings_container')
        widget.setMinimumWidth(self.min_width)
        layout = QVBoxLayout()
        widget.setLayout(layout)

        title_label = QLabel('Global Background Settings')
        title_label.setFont(self.gui.bold_font)
        title_label.setStyleSheet('background: #5555aa; color: white')
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
        title_label.setStyleSheet('background: #5555aa; color: white')
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

        #self.countdown_font_combobox = FontFaceComboBox(self.gui)
        self.countdown_font_combobox = QFontComboBox()
        self.countdown_font_combobox.setFont(self.gui.standard_font)
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

    def use_countdown_changed(self, options_widget):
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

    def eventFilter(self, obj, evt):
        if evt.type() == QEvent.Type.Wheel:
            return True
        else:
            return super().eventFilter(obj, evt)

    def draw_screen_pixmap(self, name, primary, size):
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
            try:
                file_name_split = result[0].split('/')
                file_name = file_name_split[len(file_name_split) - 1]
                shutil.copy(result[0], self.gui.main.background_dir + '/' + file_name)
            except Exception:
                self.gui.main.error_log()

            from runnables import IndexImages
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

    def delete_background(self, type):
        dialog = QDialog()
        layout = QVBoxLayout()
        dialog.setLayout(layout)

        if type == 'background':
            label = QLabel('Choose a background to remove:')
            current_bible_background = self.bible_background_combobox.currentData(Qt.ItemDataRole.UserRole)
            current_song_background = self.song_background_combobox.currentData(Qt.ItemDataRole.UserRole)
        elif type == 'image':
            label = QLabel('Choose an image item to remove:')
            current_image = self.logo_background_combobox.currentData(Qt.ItemDataRole.UserRole)
        label.setFont(self.gui.standard_font)
        layout.addWidget(label)

        from widgets import ImageCombobox
        if type == 'background':
            combobox = ImageCombobox(self.gui, type='delete_background')
        elif type == 'image':
            combobox = ImageCombobox(self.gui, type='delete_image')
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
            from runnables import IndexImages
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
        
        
class TextLayoutWidget(QWidget):
    def __init__(
            self,
            gui,
            for_sample=False,
            font_face='Sans',
            font_size=72,
            use_outline=True,
            outline_color=QColor(0, 0, 0),
            outline_width=8,
            fill_color=QColor(255, 255, 255),
            use_shadow=True,
            shadow_color=QColor(0, 0, 0),
            shadow_offset=5,
            use_shade=False,
            shade_color=0,
            shade_opacity=75,
            background_pixmap=None,
            sample_text=None,
            footer_text=None):
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
            for_sample=False,
            font_face='Sans',
            font_size=72,
            use_outline=True,
            outline_color=QColor(0, 0, 0),
            outline_width=8,
            fill_color=QColor(255, 255, 255),
            use_shadow=True,
            shadow_color=QColor(0, 0, 0),
            shadow_offset=5,
            use_shade=False,
            shade_color=0,
            shade_opacity=75):
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

    def paintEvent(self, evt):
        self.paint_text()

    def paint_text(self):
        self.total_height = 0
        self.text = re.sub('<p.*?>', '', self.text)
        self.text = re.sub('</p>', '', self.text)
        self.text = re.sub('\n', '<br />', self.text)
        self.text = re.sub('<br/>', '<br />', self.text)

        BOLD = 0
        ITALIC = 1
        UNDERLINE = 2

        font = self.font()
        font_size = font.pointSize() + 2
        painter_paths = []
        longest_line = 0

        # build paths for each line, creating a new path whenever the line becomes too long
        usable_rect = QRect(0, 0, self.width(), self.height())
        self.total_height = -1
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
                #if len(re.sub('<.*?>', '', lines[i]).strip()) > 0:
                x = 0
                y = 0
                line_words = lines[i].split(' ')
                if len(line_words) == 0:
                    line_words = [' ']
                painter_paths.append(QPainterPath())
                path_index += 1
                for word in line_words:
                    #if len(re.sub('<.*?>', '', word).strip()) > 0:
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
                #if path.boundingRect().width() > 0:
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
            #if path.boundingRect().width() > 0:
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
