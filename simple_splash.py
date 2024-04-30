from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QLabel, QGridLayout, QApplication


class SimpleSplash:
    """
    Provides a simple and standardized popup for showing messages
    """

    def __init__(self, gui, text=''):
        """
        Provides a simple and standardized popup for showing messages
        :param gui.GUI gui: the current instance of GUI
        :param str text: the text to be displayed
        """
        self.gui = gui
        self.text = text

        self.widget = QWidget()
        self.widget.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.widget.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)
        self.widget.setStyleSheet('background: #5555aa;')

        layout = QGridLayout(self.widget)

        self.label = QLabel(text)
        self.label.setFont(gui.bold_font)
        self.label.setStyleSheet('color: white; padding: 30px 20px; border: 2px solid white;')
        layout.addWidget(self.label, 0, 0, Qt.AlignmentFlag.AlignHCenter)

        self.widget.adjustSize()
        x = int((self.gui.primary_screen.size().width() / 2) - (self.widget.width() / 2))
        y = int((self.gui.primary_screen.size().height() / 2) - (self.widget.height() / 2))
        self.widget.move(x, y)
        self.widget.show()
        QApplication.processEvents()
