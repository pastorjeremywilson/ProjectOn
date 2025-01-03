from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QLabel, QGridLayout, QApplication, QVBoxLayout


class SimpleSplash:
    """
    Provides a simple and standardized popup for showing messages
    """

    def __init__(self, gui, text='', subtitle=False):
        """
        Provides a simple and standardized popup for showing messages
        :param gui.GUI gui: the current instance of GUI
        :param str text: the text to be displayed
        """
        self.gui = gui
        self.text = text

        self.widget = QWidget()
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
