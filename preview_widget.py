from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QLabel, QListWidget, QGridLayout


class PreviewWidget(QWidget):
    """
    Implements QWidget to create a widget containing all the necessary components for the program's preview widget.
    """
    def __init__(self, gui):
        """
        Implements QWidget to create a widget containing all the necessary components for the program's preview widget.
        :param gui.GUI gui: the current instance of GUI
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
        #container.setStyleSheet('#container { border: 2px solid black; }')
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
        #title_label.setStyleSheet(
        #    'background: lightGrey; color: black; padding-top: 5px; padding-bottom: 5px; border-bottom: 2px solid black;')
        container_layout.addWidget(title_label, 0, 0)

        self.slide_list = CustomListWidget(self.gui)
        self.slide_list.setObjectName('slide_list')
        #self.slide_list.setStyleSheet('#slide_list { border: none; }')
        self.slide_list.setFont(self.gui.standard_font)
        self.slide_list.itemClicked.connect(self.show_preview)
        self.slide_list.currentItemChanged.connect(self.show_preview)
        container_layout.addWidget(self.slide_list, 1, 0)

        self.preview_label = QLabel()
        #self.preview_label.setStyleSheet('margin-top: 20px;')
        layout.addWidget(self.preview_label, 1, 0, Qt.AlignmentFlag.AlignCenter)

    def show_preview(self):
        self.gui.change_display('sample')


class CustomListWidget(QListWidget):
    """
    Implements QListWidget to add send-to-live functionality using the space bar
    """
    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.setObjectName('CustomListWidget')

    def keyPressEvent(self, evt):
        if evt.key() == Qt.Key.Key_Space:
            self.gui.send_to_live()
        super().keyPressEvent(evt)

    def mouseDoubleClickEvent(self, evt):
        if evt.button() == Qt.MouseButton.LeftButton:
            self.gui.send_to_live()
        super().mouseDoubleClickEvent(evt)
