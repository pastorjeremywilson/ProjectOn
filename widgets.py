import re
import sqlite3

import requests
from PyQt5.QtCore import Qt, QSize, QEvent, QMargins, QPointF, QTimer, pyqtSignal, QRect, QRectF, QPoint
from PyQt5.QtGui import QFontDatabase, QFont, QPixmap, QIcon, QColor, QPainterPath, QPalette, QBrush, QPen, QPainter, \
    QImage
from PyQt5.QtMultimedia import QMediaPlayer
from PyQt5.QtWidgets import QListWidget, QLabel, QListWidgetItem, QComboBox, QListView, QWidget, QVBoxLayout, \
    QGridLayout, QSlider, QMainWindow, QMessageBox, QScrollArea, QLineEdit, QHBoxLayout, \
    QSpinBox, QRadioButton, QButtonGroup, QCheckBox, QColorDialog, QSizePolicy, QGraphicsScene, QGraphicsRectItem, \
    QGraphicsWidget, QGraphicsPixmapItem, QGraphicsView


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
            font_database = QFontDatabase()
            for font in font_database.families():
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
    def __init__(self, gui):
        """
        :param gui.GUI gui: The current instance of GUI
        """
        super().__init__()
        self.gui = gui
        self.populate_widget()

    def populate_widget(self):
        try:
            row = 0
            model = self.model()
            font_database = QFontDatabase()
            for font in font_database.families():
                if self.gui.main.initial_startup:
                    self.gui.main.update_status_signal.emit('Processing Fonts', 'status')
                    self.gui.main.update_status_signal.emit(font, 'info')
                self.addItem(font)
                model.setData(model.index(row, 0), QFont(font, 14), Qt.ItemDataRole.FontRole)
                row += 1

        except Exception:
            self.gui.main.error_log()

    def wheelEvent(self, evt):
        evt.ignore()


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
        if self.type == 'logo':
            self.gui.main.settings['logo_image'] = file_name
        elif self.type == 'song':
            self.gui.main.settings['global_song_background'] = file_name
            self.gui.global_song_background_pixmap = QPixmap(self.gui.main.image_dir + '/' + file_name)

            for i in range(self.gui.oos_widget.oos_list_widget.count()):
                item = self.gui.oos_widget.oos_list_widget.item(i)
                if item.data(29) == 'global_song' or item.data(40) == 'song':
                    item = self.gui.oos_widget.oos_list_widget.item(i)
                    widget = self.gui.oos_widget.oos_list_widget.itemWidget(item)
                    pixmap = QPixmap(self.gui.main.background_dir + '/' + file_name)
                    pixmap = pixmap.scaled(
                        50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    widget.icon.setPixmap(pixmap)
        elif self.type == 'bible':
            self.gui.main.settings['global_bible_background'] = file_name
            self.gui.global_bible_background_pixmap = QPixmap(self.gui.main.image_dir + '/' + file_name)

            for i in range(self.gui.oos_widget.oos_list_widget.count()):
                item = self.gui.oos_widget.oos_list_widget.item(i)
                if item.data(29) == 'global_bible' or item.data(40) == 'bible':
                    item = self.gui.oos_widget.oos_list_widget.item(i)
                    widget = self.gui.oos_widget.oos_list_widget.itemWidget(item)
                    pixmap = QPixmap(self.gui.main.background_dir + '/' + file_name)
                    pixmap = pixmap.scaled(
                        50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    widget.icon.setPixmap(pixmap)

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
            image_list = self.gui.main.logo_items
        elif self.type == 'edit':
            self.addItem('Choose Custom Background', userData='choose_global')
            self.table = 'backgroundThumbnails'
            image_list = self.gui.main.image_items
        else:
            self.addItem('Choose Global ' + self.type + ' Background', userData='choose_global')
            self.addItem('Import a Background Image', userData='import_global')
            self.table = 'backgroundThumbnails'
            image_list = self.gui.main.image_items
        connection = None

        try:
            # check if items for this combo box have already been created
            if not image_list:
                image_list = []
                connection = sqlite3.connect(self.gui.main.database)
                cursor = connection.cursor()
                thumbnails = cursor.execute('SELECT * FROM ' + self.table).fetchall()
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
            else:
                for image in image_list:
                    self.addItem(image[0], image[1], userData=image[2])

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
                if self.gui.media_player.state() == QMediaPlayer.State.PlayingState:
                    self.gui.media_player.stop()
                self.gui.media_player.deleteLater()
                self.gui.video_widget.deleteLater()
                self.gui.media_player = None
                self.gui.video_widget = None
                self.gui.audio_output = None
                self.gui.video_probe = None

            try:
                self.gui.main.server_check.keep_checking = False
            except AttributeError:
                pass
            self.gui.main.save_settings()
            self.gui.display_widget.deleteLater()
            # shutdown the remote server
            try:
                requests.get('http://' + self.gui.main.ip + ':15171/shutdown')
            except requests.exceptions.ConnectionError as e:
                print("Shutdown with Connection Error " + e.__str__())
            except BaseException as e:
                print("Shutdown Error " + e.__str__())

            if self.gui.timed_update:
                self.gui.timed_update.stop = True
            evt.accept()


class CustomScrollArea(QScrollArea):
    """
    A simple reimplementation of QScrollArea to ensure that its widget gets resized if the scroll area is resized
    """
    def __init__(self):
        super().__init__()

    def resizeEvent(self, evt):
        self.widget().setFixedWidth(self.width())


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

    def toggle_show_hide(self):
        """
        Convenience method to show/hide this display widget
        """
        if self.isHidden():
            self.showFullScreen()
        else:
            self.hide()


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
        self.path = QPainterPath()
        self.shadow_path = QPainterPath()

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
        self.path.clear()
        self.shadow_path.clear()
        self.text = re.sub('<p.*?>', '', self.text)
        self.text = re.sub('</p>', '', self.text)
        self.text = re.sub('\n', '<br />', self.text)
        self.text = re.sub('<br/>', '<br />', self.text)

        text_lines = self.text.split('<br />')
        metrics = self.fontMetrics()
        line_height = metrics.boundingRect('Way').height()
        space_width = metrics.boundingRect('m m').width() - metrics.boundingRect('mm').width()
        lines = []
        for this_line in text_lines:
            this_line = this_line.strip()

            # split the lines according to their drawn length
            if (metrics.boundingRect(this_line).adjusted(
                    0, 0, self.outline_width, self.outline_width).width()
                    < self.gui.display_widget.width() - 20):
                lines.append(this_line)
            else:
                split_more = True
                splitted_lines = [this_line]
                iterations = 0
                while split_more:
                    new_splits = []
                    for line in splitted_lines:
                        if (metrics.boundingRect(line).adjusted(
                                0, 0, self.outline_width, self.outline_width).width()
                                > self.gui.display_widget.width() - 20):
                            line_split = line.split(' ')
                            center_index = int(len(line_split) / 2)
                            new_lines = [' '.join(line_split[:center_index]), ' '.join(line_split[center_index:len(line_split)])]
                            for i in range(len(new_lines)):
                                if '</b>' in new_lines[i] and '<b>' not in new_lines[i]:
                                    new_lines[i] = '<b>' + new_lines[i]
                                if '</i>' in new_lines[i] and '<i>' not in new_lines[i]:
                                    new_lines[i] = '<i>' + new_lines[i]
                                if '</u>' in new_lines[i] and '<u>' not in new_lines[i]:
                                    new_lines[i] = '<u>' + new_lines[i]

                                if '<b>' in new_lines[i] and '</b>' not in new_lines[i]:
                                    new_lines[i] = new_lines[i] + '</b>'
                                if '<i>' in new_lines[i] and '</i>' not in new_lines[i]:
                                    new_lines[i] = new_lines[i] + '</i>'
                                if '<u>' in new_lines[i] and '</u>' not in new_lines[i]:
                                    new_lines[i] = new_lines[i] + '</u>'
                            new_splits.append(new_lines[0])
                            new_splits.append(new_lines[1])
                        else:
                            new_splits.append(line)

                    split_more = False
                    splitted_lines = new_splits
                    for line in splitted_lines:
                        if (metrics.boundingRect(line).adjusted(
                                0, 0, self.outline_width, self.outline_width).width()
                                > self.gui.display_widget.width() - 20):
                            split_more = True
                    iterations += 1
                    if iterations > 10:
                        break

                for line in splitted_lines:
                    lines.append(line)

        for i in range(len(lines)):
            this_line = lines[i]

            # check for any html formatting in this line
            formatted_line = []
            if '<i>' in this_line or '<b>' in this_line or '<u>' in this_line:
                index = 0
                line_parts = ['']
                j = 0
                while j < len(this_line):
                    if this_line[j] == '<':
                        index += 1
                        line_parts.append('')
                        while this_line[j] != '/':
                            line_parts[index] += this_line[j]
                            j += 1

                        if len(this_line) == j + 3 or this_line[j + 3] != '<':
                            line_parts[index] += this_line[j:j + 3]
                            j += 3
                        elif len(this_line) == j + 7 or this_line[j + 7] != '<':
                            line_parts[index] += this_line[j:j + 7]
                            j += 7
                        elif len(this_line) == j + 11 or this_line[j + 11] != '<':
                            line_parts[index] += this_line[j:j + 11]
                            j += 11

                        index += 1
                        line_parts.append('')
                    else:
                        line_parts[index] += this_line[j]
                        j += 1

                line_split = re.split('<i>|<b>|<u>', this_line)
                for item in line_split:
                    formatting_markers = ''
                    if '/i' in item:
                        formatting_markers += 'i'
                    if '/b' in item:
                        formatting_markers += 'b'
                    if '/u' in item:
                        formatting_markers += 'u'
                    formatted_line.append([formatting_markers, re.sub('<.*?>', '', item)])
            else:
                formatted_line.append(['', this_line])
                line_parts = [this_line]

            this_line = re.sub('<.*?>', '', this_line)
            line_width = metrics.boundingRect(this_line).adjusted(
                0, 0, self.outline_width, self.outline_width).width()
            x = (self.width() - line_width) / 2
            y = (self.gui.display_widget.height() / 2) - (line_height * len(lines) / 2) + (line_height / 1.5) + (i * line_height)

            for part in line_parts:
                font = self.font()
                if '<b>' in part:
                    font.setWeight(1000)
                if '<i>' in part:
                    font.setItalic(True)
                if '<u>' in part:
                    font.setUnderline(True)

                part = re.sub('<.*?>', '', part)
                if self.use_shadow:
                    self.shadow_path.addText(QPointF(x + self.shadow_offset, y + self.shadow_offset), font, part)
                self.path.addText(QPointF(x, y), font, part)
                x += metrics.boundingRect(part).width()
                if part.endswith(' '):
                    x += space_width

        painter = QPainter(self)
        brush = QBrush()
        painter.setBrush(brush)
        pen = QPen()
        painter.setPen(pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        opacity = self.shade_opacity
        if not self.use_shade:
            opacity = 0
        path_rect = self.path.boundingRect()
        shade_rect = QRectF(path_rect.x() - 20, path_rect.y() - 20, path_rect.width() + 40, path_rect.height() + 40)
        painter.fillRect(shade_rect, QColor(self.shade_color, self.shade_color, self.shade_color, opacity))

        brush.setColor(self.fill_color)
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        pen.setColor(self.outline_color)
        pen.setWidth(self.outline_width)
        painter.setPen(pen)

        if self.use_shadow:
            shadow_brush = QBrush()
            shadow_brush.setColor(self.shadow_color)
            shadow_brush.setStyle(Qt.BrushStyle.SolidPattern)
            painter.fillPath(self.shadow_path, shadow_brush)

        painter.fillPath(self.path, brush)
        if self.use_outline:
            painter.strokePath(self.path, pen)


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


class AutoSelectLineEdit(QLineEdit):
    """
    Implements QLineEdit to add the ability to select all text when this line edit receives focus.
    """
    def __init__(self):
        super().__init__()

    def focusInEvent(self, evt):
        super().focusInEvent(evt)
        QTimer.singleShot(0, self.selectAll)


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
        self.font_widget = None
        self.font_combo_box = None
        self.font_size_spinbox = None
        self.white_radio_button = None
        self.black_radio_button = None
        self.font_color_button_group = None
        self.custom_font_color_radio_button = None
        self.shadow_color_slider = None
        self.shadow_offset_slider = None
        self.shadow_checkbox = None
        self.outline_checkbox = None
        self.outline_color_slider = None
        self.outline_width_slider = None
        self.gui = gui
        self.slide_type = slide_type
        self.draw_border = draw_border
        self.applies_to_global = applies_to_global

        self.mouse_release_signal.connect(lambda value: self.change_font(value))

        self.setParent(self.gui.main_window)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)
        self.setWindowFlag(Qt.WindowType.Popup)
        self.init_components()

    def init_components(self):
        self.setFixedWidth(950)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        """self.font_sample_container = QWidget()
        self.font_sample_container.setObjectName('font_sample_container')
        font_sample_container_layout = QVBoxLayout(self.font_sample_container)
        font_sample_container_layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(self.font_sample_container)

        self.font_sample_background_label = QLabel(self.font_sample_container)
        self.font_sample_background_label.setObjectName('font_sample_background_label')

        self.font_sample_widget = QWidget()
        self.font_sample_widget.setObjectName('font_sample_widget')
        self.font_sample_widget.setAutoFillBackground(True)
        font_sample_layout = QVBoxLayout(self.font_sample_widget)
        font_sample_layout.setContentsMargins(20, 20, 20, 20)
        font_sample_container_layout.addWidget(self.font_sample_widget)"""

        sample_text = self.slide_type.capitalize() + ' Font Sample'
        self.font_sample = FontSample(self)
        self.font_sample.text = sample_text
        self.font_sample.setObjectName('font_sample')
        layout.addWidget(self.font_sample)

        self.font_widget = QWidget()
        self.setObjectName('font_widget')
        layout.addWidget(self.font_widget)
        font_widget_layout = QGridLayout(self.font_widget)

        font_face_widget = QWidget()
        font_face_layout = QVBoxLayout(font_face_widget)
        font_face_layout.setContentsMargins(0, 0, 0, 0)
        font_widget_layout.addWidget(font_face_widget, 0, 0, 8, 1)

        global_font_label = QLabel('Font Face:')
        global_font_label.setFont(self.gui.bold_font)
        font_face_layout.addWidget(global_font_label)

        self.font_list_widget = FontFaceListWidget(self.gui)
        self.font_list_widget.setToolTip('Set the font style')
        self.font_list_widget.currentRowChanged.connect(self.change_font)
        font_face_layout.addWidget(self.font_list_widget)

        font_size_widget = QWidget()
        font_size_widget.setObjectName('font_size_widget')
        font_size_layout = QHBoxLayout(font_size_widget)
        font_size_layout.setContentsMargins(0, 0, 0, 20)
        font_widget_layout.addWidget(font_size_widget, 0, 1)

        font_size_label = QLabel('Font Size:')
        font_size_label.setFont(self.gui.bold_font)
        font_size_layout.addWidget(font_size_label)

        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setMaximumWidth(100)
        self.font_size_spinbox.setFont(self.gui.standard_font)
        self.font_size_spinbox.setRange(10, 240)
        self.font_size_spinbox.valueChanged.connect(self.change_font)
        self.font_size_spinbox.installEventFilter(self)
        font_size_layout.addWidget(self.font_size_spinbox)
        font_size_layout.addSpacing(20)

        font_color_widget = QWidget()
        font_color_layout = QHBoxLayout()
        font_color_layout.setContentsMargins(0, 0, 0, 20)
        font_color_widget.setLayout(font_color_layout)
        font_widget_layout.addWidget(font_color_widget, 1, 1)
        font_size_layout.addStretch()

        font_color_label = QLabel('Font Color:')
        font_color_label.setFont(self.gui.bold_font)
        font_color_layout.addWidget(font_color_label)

        self.white_radio_button = QRadioButton('White')
        self.white_radio_button.setObjectName('white')
        self.white_radio_button.setFont(self.gui.standard_font)
        font_color_layout.addWidget(self.white_radio_button)

        self.black_radio_button = QRadioButton('Black')
        self.black_radio_button.setObjectName('black')
        self.black_radio_button.setFont(self.gui.standard_font)
        font_color_layout.addWidget(self.black_radio_button)

        self.custom_font_color_radio_button = QRadioButton('Custom')
        self.custom_font_color_radio_button.setObjectName('custom')
        self.custom_font_color_radio_button.setFont(self.gui.standard_font)
        self.custom_font_color_radio_button.setObjectName('custom_font_color_radio_button')
        self.custom_font_color_radio_button.clicked.connect(self.color_chooser)
        font_color_layout.addWidget(self.custom_font_color_radio_button)
        font_color_layout.addStretch()

        self.font_color_button_group = QButtonGroup()
        self.font_color_button_group.addButton(self.white_radio_button)
        self.font_color_button_group.addButton(self.black_radio_button)
        self.font_color_button_group.addButton(self.custom_font_color_radio_button)
        self.font_color_button_group.buttonClicked.connect(self.change_font)

        self.shadow_checkbox = QCheckBox('Use Shadow')
        self.shadow_checkbox.setFont(self.gui.bold_font)
        self.shadow_checkbox.clicked.connect(self.change_font)
        font_widget_layout.addWidget(self.shadow_checkbox, 2, 1)

        shadow_widget = QWidget()
        shadow_widget.setObjectName('shadow_widget')
        shadow_layout = QHBoxLayout()
        shadow_layout.setContentsMargins(0, 0, 0, 20)
        shadow_widget.setLayout(shadow_layout)
        font_widget_layout.addWidget(shadow_widget, 3, 1)

        self.shadow_color_slider = ShadowSlider(self.gui)
        self.shadow_color_slider.setObjectName('shadow_color_slider')
        shadow_layout.addWidget(self.shadow_color_slider)
        shadow_layout.addSpacing(20)

        self.shadow_offset_slider = OffsetSlider(self.gui)
        self.shadow_offset_slider.setObjectName('shadow_offset_slider')
        shadow_layout.addWidget(self.shadow_offset_slider)
        shadow_layout.addStretch()

        self.outline_checkbox = QCheckBox('Use Outline')
        self.outline_checkbox.setFont(self.gui.bold_font)
        self.outline_checkbox.clicked.connect(self.change_font)
        font_widget_layout.addWidget(self.outline_checkbox, 4, 1)

        outline_widget = QWidget()
        outline_widget.setObjectName('outline_widget')
        outline_layout = QHBoxLayout()
        outline_layout.setContentsMargins(0, 0, 0, 20)
        outline_widget.setLayout(outline_layout)
        font_widget_layout.addWidget(outline_widget, 5, 1)

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

        self.shade_behind_text_checkbox = QCheckBox('Shade Behind Text')
        self.shade_behind_text_checkbox.setFont(self.gui.bold_font)
        self.shade_behind_text_checkbox.clicked.connect(self.change_font)
        font_widget_layout.addWidget(self.shade_behind_text_checkbox, 6, 1)

        shade_widget = QWidget()
        shade_widget.setObjectName('shade_widget')
        shade_layout = QHBoxLayout(shade_widget)
        shade_layout.setContentsMargins(0, 0, 0, 20)
        font_widget_layout.addWidget(shade_widget, 7, 1)

        self.shade_color_slider = ShadowSlider(self.gui)
        self.shade_color_slider.setObjectName('shade_color_slider')
        shade_layout.addWidget(self.shade_color_slider)

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
        self.font_list_widget.blockSignals(block)
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
        font_face_found = False
        if not len(font_face) > 0:
            font_face = 'Arial Black'
        for i in range(self.font_list_widget.count()):
            if self.font_list_widget.item(i).data(20) == font_face:
                self.font_list_widget.setCurrentRow(i)
                font_face_found = True
                break

        if not font_face_found:
            self.font_list_widget.setCurrentRow(0)

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

            new_font_face = self.font_list_widget.currentItem().data(20)
            self.gui.global_font_face = new_font_face
            self.gui.global_footer_font_face = new_font_face

            self.gui.main.settings[f'{self.slide_type}_font_face'] = self.font_list_widget.currentItem().data(20)
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
        if self.font_list_widget.currentItem():
            font_name = self.font_list_widget.currentItem().data(20)
        else:
            font_name = self.font_list_widget.item(0).data(20)

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
        color = QColorDialog.getColor(QColor(Qt.GlobalColor.black), self)
        rgb = color.getRgb()
        color_string = str(rgb[0]) + ', ' + str(rgb[1]) + ', ' + str(rgb[2])
        self.custom_font_color_radio_button.setText('Custom: ' + color_string)
        self.custom_font_color_radio_button.setObjectName(color_string)
        sender.setChecked(True)
        self.show()
        self.change_font()

    def hideEvent(self, evt):
        """
        overrides hideEvent to save settings when the widget is hidden
        """
        self.gui.main.save_settings()
        self.gui.apply_settings(theme_too=False)
        super().hideEvent(evt)


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
        painter.begin(image)

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

