import re
import sqlite3

import requests
from PyQt6.QtCore import Qt, QSize, QEvent, QMargins, QPointF, QTimer
from PyQt6.QtGui import QFontDatabase, QFont, QPixmap, QIcon, QColor, QPainterPath, QPalette, QBrush, QPen, QPainter
from PyQt6.QtWidgets import QListWidget, QLabel, QListWidgetItem, QComboBox, QListView, QWidget, QVBoxLayout, \
    QGridLayout, QSlider, QMainWindow, QMessageBox, QScrollArea, QLineEdit


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
        self.setMinimumHeight(60)
        self.gui = gui

        try:
            for font in QFontDatabase.families():
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

        try:
            row = 0
            for font in QFontDatabase.families():
                if self.gui.main.initial_startup:
                    self.gui.main.update_status_signal.emit('Processing Fonts', 'status')
                    self.gui.main.update_status_signal.emit(font, 'info')
                model = self.model()
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

            for i in range(self.gui.oos_widget.oos_list_widget.count()):
                if self.gui.oos_widget.oos_list_widget.item(i).data(30) == 'song':
                    item = self.gui.oos_widget.oos_list_widget.item(i)
                    widget = self.gui.oos_widget.oos_list_widget.itemWidget(item)
                    pixmap = QPixmap(self.gui.main.background_dir + '/' + file_name)
                    pixmap = pixmap.scaled(
                        50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    widget.picture_label.setPixmap(pixmap)
        elif self.type == 'bible':
            self.gui.main.settings['global_bible_background'] = file_name

            for i in range(self.gui.oos_widget.oos_list_widget.count()):
                if self.gui.oos_widget.oos_list_widget.item(i).data(30) == 'bible':
                    item = self.gui.oos_widget.oos_list_widget.item(i)
                    widget = self.gui.oos_widget.oos_list_widget.itemWidget(item)
                    pixmap = QPixmap(self.gui.main.background_dir + '/' + file_name)
                    pixmap = pixmap.scaled(
                        50, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    widget.picture_label.setPixmap(pixmap)

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
        else:
            self.addItem('Choose Global ' + self.type + ' Background', userData='choose_global')
            self.addItem('Import a Background Image', userData='import_global')
            self.table = 'backgroundThumbnails'
        connection = None

        try:
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

            if self.gui.main.initial_startup:
                self.gui.main.update_status_signal.emit('', 'info')

            connection.close()
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

        self.color_title = QLabel('Shadow Color:')
        self.color_title.setStyleSheet('padding-bottom: 10px')
        self.color_title.setFont(self.gui.list_font)
        layout.addWidget(self.color_title)

        slider_widget = QWidget()
        slider_widget.setFixedWidth(300)
        slider_layout = QGridLayout()
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setVerticalSpacing(0)
        slider_widget.setLayout(slider_layout)
        layout.addWidget(slider_widget)

        self.color_slider = QSlider()
        self.color_slider.setObjectName('color_slider')
        self.color_slider.setOrientation(Qt.Orientation.Horizontal)
        self.color_slider.setFont(self.gui.list_font)
        self.color_slider.setRange(0, 255)
        self.color_slider.installEventFilter(self)
        slider_layout.addWidget(self.color_slider, 0, 0, 1, 2)

        min_label = QLabel('Black')
        min_label.setFont(self.gui.list_font)
        slider_layout.addWidget(min_label, 1, 0, Qt.AlignmentFlag.AlignLeft)

        max_label = QLabel('White')
        max_label.setFont(self.gui.list_font)
        slider_layout.addWidget(max_label, 1, 1, Qt.AlignmentFlag.AlignRight)

    def eventFilter(self, obj, evt):
        if obj == self.color_slider and evt.type() == QEvent.Type.Wheel:
            return True
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
        self.offset_title.setStyleSheet('padding-bottom: 10px')
        self.offset_title.setFont(self.gui.list_font)
        layout.addWidget(self.offset_title)

        slider_widget = QWidget()
        slider_widget.setFixedWidth(300)
        slider_layout = QGridLayout()
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setVerticalSpacing(0)
        slider_widget.setLayout(slider_layout)
        layout.addWidget(slider_widget)

        self.offset_slider = QSlider()
        self.offset_slider.setOrientation(Qt.Orientation.Horizontal)
        self.offset_slider.setFont(self.gui.list_font)
        self.offset_slider.setRange(0, 15)
        self.offset_slider.setValue(self.gui.shadow_offset)
        self.offset_slider.installEventFilter(self)
        slider_layout.addWidget(self.offset_slider, 0, 0, 1, 2)

        self.min_label = QLabel(str(self.offset_slider.minimum()) + 'px')
        self.min_label.setFont(self.gui.list_font)
        slider_layout.addWidget(self.min_label, 1, 0, Qt.AlignmentFlag.AlignLeft)

        self.max_label = QLabel(str(self.offset_slider.maximum()) + 'px')
        self.max_label.setFont(self.gui.list_font)
        slider_layout.addWidget(self.max_label, 1, 1, Qt.AlignmentFlag.AlignRight)

    def eventFilter(self, obj, evt):
        if obj == self.offset_slider and evt.type() == QEvent.Type.Wheel:
            return True
        else:
            return super().eventFilter(obj, evt)


class CustomMainWindow(QMainWindow):
    """
    Provides added functionality to QMainWindow, such as save on close and key bindings
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
            self.gui.main.server_check.keep_checking = False
            self.gui.main.save_settings()
            self.gui.display_widget.deleteLater()
            # shutdown the remote server
            try:
                requests.get('http://' + self.gui.main.ip + ':15171/shutdown')
            except requests.exceptions.ConnectionError as e:
                print("Shutdown with Connection Error" + e.__str__())
            except BaseException as e:
                print("Shutdown Error " + e.__str__())

            if self.gui.timed_update:
                self.gui.timed_update.stop = True
            evt.accept()

    def keyPressEvent(self, evt):
        """
        Provide keystrokes for hiding/showing the display screen and (for troubleshooting) the sample widget
        :param evt:
        :return:
        """
        if evt.key() == Qt.Key.Key_D and evt.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.gui.show_hide_display_screen()
        if evt.key() == Qt.Key.Key_H and evt.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if self.gui.sample_widget.isHidden():
                self.gui.sample_widget.show()
            else:
                self.gui.sample_widget.hide()


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

    def keyPressEvent(self, evt):
        """
        Mirror the main window's keystrokes in the event this widget has focus
        :param QKeyEvent evt: keyPressEvent
        """
        if evt.key() == Qt.Key.Key_D and evt.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if not self.sample:
                self.gui.show_hide_display_screen()
            else:
                if self.gui.sample_widget.isHidden():
                    self.gui.sample_widget.show()
                else:
                    self.gui.sample_widget.hide()


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
            shadow_offset=5):
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

            this_line = re.sub('<.*?>', '', this_line)
            line_width = metrics.boundingRect(this_line).adjusted(
                0, 0, self.outline_width, self.outline_width).width()
            x = (self.width() - line_width) / 2
            y = (self.gui.display_widget.height() / 2) - (line_height * len(lines) / 2) + (line_height / 1.5) + (i * line_height)

            for item in formatted_line:
                font = self.font()
                if 'i' in item[0]:
                    font.setItalic(True)
                if 'b' in item[0]:
                    font.setWeight(1000)
                if 'u' in item[0]:
                    font.setUnderline(True)

                if self.use_shadow:
                    self.shadow_path.addText(QPointF(x + self.shadow_offset, y + self.shadow_offset), font, item[1])
                self.path.addText(QPointF(x, y), font, item[1])

                item_width = metrics.boundingRect(item[1]).adjusted(
                    0, 0, self.outline_width, self.outline_width).width()
                x += item_width + metrics.horizontalAdvance(' ')

        brush = QBrush()
        brush.setColor(self.fill_color)
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        pen = QPen()
        pen.setColor(self.outline_color)
        pen.setWidth(3)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(brush)
        painter.setPen(pen)

        if self.use_shadow:
            shadow_brush = QBrush()
            shadow_brush.setColor(self.shadow_color)
            shadow_brush.setStyle(Qt.BrushStyle.SolidPattern)
            painter.fillPath(self.shadow_path, shadow_brush)

        painter.fillPath(self.path, brush)
        if self.use_outline:
            painter.strokePath(self.path, pen)


class LyricItemWidget(QWidget):
    """
    Provides a standardized QWidget to be used as a QListWidget ItemWidget
    """
    def __init__(self, gui, title, segment_text):
        super().__init__()
        segment_text = re.sub('<br.*?>', '\n', segment_text)
        segment_text = re.sub('<.*?>', '', segment_text)

        self.segment_title = QLabel(title)
        self.segment_title.setFont(gui.list_title_font)

        self.segment_text = QLabel(segment_text)
        self.segment_text.setWordWrap(True)
        self.segment_text.setFont(gui.list_font)

        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.segment_title)
        layout.addWidget(self.segment_text)


class AutoSelectLineEdit(QLineEdit):
    """
    Implements QLineEdit to add the ability to select all text when this line edit receives focus.
    """
    def __init__(self):
        super().__init__()

    def focusInEvent(self, evt):
        super().focusInEvent(evt)
        QTimer.singleShot(0, self.selectAll)
