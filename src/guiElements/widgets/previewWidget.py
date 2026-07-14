import json
import re
from os.path import exists

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QKeyEvent, QMouseEvent, QPixmap, QPainter, QFont, QColor, QImage, QPen, QBrush
from PyQt5.QtWidgets import QWidget, QLabel, QListWidget, QGridLayout, QAbstractItemView

from dataHandling.parsers import parse_song_data
from guiElements import gui


class PreviewWidget(QWidget):
    """
    Implements QWidget to create a widget containing all the necessary components for the program's preview widget.
    """
    def __init__(self, gui):
        """
        Implements QWidget to create a widget containing all the necessary components for the program's preview widget.
        :param guiElements.GUI gui: the current instance of GUI
        """
        super().__init__()
        self.gui = gui
        self.init_components()

    def init_components(self):
        """
        Creates and lays out this widget's components.
        """
        self.setObjectName('preview_widget')

        layout = QGridLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setRowStretch(0, 20)
        layout.setRowStretch(1, 1)

        container = QWidget()
        container.setObjectName('container')
        layout.addWidget(container, 0, 0)

        container_layout = QGridLayout(container)
        container_layout.setSpacing(0)
        container_layout.setContentsMargins(2, 2, 2, 2)
        container_layout.setRowStretch(0, 1)
        container_layout.setRowStretch(1, 20)

        title_label = QLabel('Preview')
        title_label.setObjectName('title_label')
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(self.gui.bold_font)
        container_layout.addWidget(title_label, 0, 0)

        self.slide_list = CustomListWidget(self.gui)
        self.slide_list.setObjectName('slide_list')
        self.slide_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.slide_list.verticalScrollBar().setSingleStep(15)
        self.slide_list.setFont(self.gui.standard_font)
        self.slide_list.currentItemChanged.connect(self.show_preview)
        container_layout.addWidget(self.slide_list, 1, 0)

        self.preview_label = QLabel()
        layout.addWidget(self.preview_label, 1, 0, Qt.AlignmentFlag.AlignCenter)

    def show_preview(self):
        if not self.slide_list.currentItem():
            return

        slide_data = self.slide_list.currentItem().data(Qt.ItemDataRole.UserRole)
        image = QImage(
            self.gui.display_widget.width(),
            self.gui.display_widget.height(),
            QImage.Format_ARGB32_Premultiplied
        )
        image.fill(Qt.GlobalColor.black)
        painter = QPainter()

        if slide_data['type'] == 'song' or slide_data['type'] == 'custom':
            if painter.begin(image):
                try:
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    self.gui.display_widget.lyric_widget.draw_slide(painter, slide_data)
                finally:
                    painter.end()
            self.preview_label.setPixmap(
                QPixmap.fromImage(image).scaled(
                    int(self.gui.display_widget.width() / 5),
                    int(self.gui.display_widget.height() / 5),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
        elif slide_data['type'] == 'bible' or slide_data['type'] == 'custom_bible':
            if painter.begin(image):
                try:
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    self.gui.display_widget.lyric_widget.draw_slide(painter, slide_data)
                finally:
                    painter.end()
            self.preview_label.setPixmap(
                QPixmap.fromImage(image).scaled(
                    int(self.gui.display_widget.width() / 5),
                    int(self.gui.display_widget.height() / 5),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
        elif slide_data['type'] == 'image':
            if exists(self.gui.main.image_dir + '/' + slide_data['title']):
                if painter.begin(image):
                    try:
                        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                        self.gui.display_widget.lyric_widget.draw_slide(painter, slide_data)
                    finally:
                        painter.end()
                self.preview_label.setPixmap(
                    QPixmap.fromImage(image).scaled(
                        int(self.gui.display_widget.width() / 5),
                        int(self.gui.display_widget.height() / 5),
                        Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )
        elif slide_data['type'] == 'video':
            # having switched from storing video icon pixmaps as jpg files in the video directory to storing them
            # in the database, check first for an existing jpg file in case this is an old database entry
            video_jpg = self.gui.main.video_dir + '/' + '.'.join(slide_data['title'].split('.')[:-1]) + '.jpg'
            if exists(video_jpg):
                pixmap = QPixmap(video_jpg).scaled(self.gui.display_widget.width(), self.gui.display_widget.height())
            else:
                pixmap = slide_data['background'].scaled(self.gui.display_widget.width(), self.gui.display_widget.height())

            if painter.begin(image):
                try:
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.drawPixmap(0, 0, pixmap)

                    if len(self.gui.main.settings['song_font_face'].strip()) > 0:
                        font = QFont(self.gui.main.settings['song_font_face'].strip(), 60, QFont.Weight.Bold)
                    else:
                        font = QFont('sans', 60, QFont.Weight.Bold)
                    painter.setFont(font)
                    font_metrics = painter.fontMetrics()
                    bounding_rect = font_metrics.boundingRect(slide_data['title'])
                    painter.setPen(Qt.GlobalColor.black)
                    painter.drawText(
                        QPoint(
                            int(image.width() / 2) - int(bounding_rect.width() / 2),
                            int(image.height() / 2) - int(bounding_rect.height() / 2) + font_metrics.ascent()
                        ),
                        slide_data['title']
                    )
                    painter.setPen(Qt.GlobalColor.white)
                    painter.drawText(
                        QPoint(
                            int(image.width() / 2) - int(bounding_rect.width() / 2) - 6,
                            int(image.height() / 2) - int(bounding_rect.height() / 2) - 6 + font_metrics.ascent()
                        ),
                        slide_data['title']
                    )
                finally:
                    painter.end()

            self.preview_label.setPixmap(
                    QPixmap.fromImage(image).scaled(
                        int(self.gui.display_widget.width() / 5),
                        int(self.gui.display_widget.height() / 5),
                        Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )
        elif slide_data['type'] == 'web':
            if len(self.gui.main.settings['song_font_face'].strip()) > 0:
                font = QFont(self.gui.main.settings['song_font_face'].strip(), 60, QFont.Weight.Bold)
            else:
                font = QFont('sans', 60, QFont.Weight.Bold)

            if painter.begin(image):
                try:
                    pen = QPen(Qt.GlobalColor.white)
                    pen.setWidth(10)
                    pen.setStyle(Qt.PenStyle.SolidLine)
                    painter.setPen(pen)
                    brush = QBrush(Qt.GlobalColor.black)
                    brush.setStyle(Qt.BrushStyle.SolidPattern)
                    painter.setBrush(brush)

                    painter.drawRect(10, 10, image.rect().width() - 20, image.rect().height() - 20)

                    painter.setFont(font)
                    font_metrics = painter.fontMetrics()
                    bounding_rect = font_metrics.boundingRect(slide_data['title'])
                    pen.setWidth(0)
                    painter.setPen(pen)
                    painter.setBrush(Qt.GlobalColor.white)

                    painter.drawText(
                        QPoint(
                            int(image.width() / 2) - int(bounding_rect.width() / 2),
                            int(image.height() / 2) - int(bounding_rect.height() / 2) + font_metrics.ascent()
                        ),
                        slide_data['title']
                    )
                finally:
                    painter.end()

            self.preview_label.setPixmap(
                    QPixmap.fromImage(image).scaled(
                        int(self.gui.display_widget.width() / 5),
                        int(self.gui.display_widget.height() / 5),
                        Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )


class CustomListWidget(QListWidget):
    """
    Implements QListWidget to add send-to-live functionality using the space bar
    """
    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.setObjectName('CustomListWidget')

    def keyPressEvent(self, evt: QKeyEvent):
        if evt.key() == Qt.Key.Key_Space:
            self.gui.send_to_live()
        super().keyPressEvent(evt)

    def mouseDoubleClickEvent(self, evt: QMouseEvent):
        if evt.button() == Qt.MouseButton.LeftButton:
            self.gui.send_to_live()
        super().mouseDoubleClickEvent(evt)
