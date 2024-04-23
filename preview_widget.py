from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QHBoxLayout


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
        layout = QVBoxLayout()
        layout.setSpacing(0)
        self.setLayout(layout)

        title_label = QLabel('Preview')
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(self.gui.standard_font)
        title_label.setStyleSheet(
            'background: lightGrey; color: black; padding-top: 5px; padding-bottom: 5px; border: 2px solid black;')
        layout.addWidget(title_label)

        self.slide_list = CustomListWidget(self.gui)
        self.slide_list.setObjectName('slide_list')
        self.slide_list.setStyleSheet('#slide_list { border: 2px solid black; border-top: 0; }')
        self.slide_list.setFont(self.gui.standard_font)
        self.slide_list.itemClicked.connect(self.show_preview)
        self.slide_list.currentItemChanged.connect(self.show_preview)
        layout.addWidget(self.slide_list)
        layout.addSpacing(10)

        preview_container = QWidget()
        preview_container.setStyleSheet('border: 0')
        preview_layout = QHBoxLayout()
        preview_container.setLayout(preview_layout)
        layout.addWidget(preview_container)

        self.preview_label = QLabel()
        preview_layout.addStretch()
        preview_layout.addWidget(self.preview_label)
        preview_layout.addStretch()

    def show_preview(self):
        self.gui.change_display('sample')


class CustomListWidget(QListWidget):
    """
    Implements QListWidget to add send-to-live functionality using the space bar
    """
    def __init__(self, gui):
        super().__init__()
        self.gui = gui

    def keyPressEvent(self, evt):
        if evt.key() == Qt.Key.Key_Space:
            self.gui.send_to_live()
        super().keyPressEvent(evt)
