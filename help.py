import os
from os.path import exists

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QMainWindow, QApplication


class Help(QMainWindow):
    """
    Implements a QMainWindow containing all of the help topics.
    """

    def __init__(self, gui):
        """
        Implements a QMainWindow containing all of the help topics.
        :param gui.GUI gui: the current instance of GUI
        """
        super().__init__()
        self.gui = gui
        self.title_font = QFont('Helvetica', 16, QFont.Weight.Bold)
        self.base_url = QUrl.fromLocalFile(os.getcwd() + os.path.sep)
        self.init_components()
        self.show()

    def init_components(self):
        self.setParent(self.gui.main_window)
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle('Help Contents')

        tab_widget = QTabWidget()
        tab_widget.currentChanged.connect(lambda: self.refresh_html(tab_widget))
        tab_widget.setFont(QFont('Helvetica', 12, QFont.Weight.Bold))
        self.setCentralWidget(tab_widget)

        tab_widget.addTab(self.intro_widget(), 'Introduction')
        tab_widget.addTab(self.main_screen_widget(), 'Main Screen')
        tab_widget.addTab(self.menu_widget(), 'Menu Bar')
        tab_widget.addTab(self.media_widget(), 'Media Box')
        tab_widget.addTab(self.edit_widget(), 'Edit Window')
        tab_widget.addTab(self.settings_widget(), 'Settings Window')
        tab_widget.addTab(self.remote_widget(), 'Remote Server')
        tab_widget.addTab(self.import_widget(), 'Importing Songs')
        tab_widget.addTab(self.file_widget(), 'File Locations')

    def refresh_html(self, tab_widget):
        QApplication.processEvents()

    def intro_widget(self):
        widget = QWidget()
        widget.setLayout(QVBoxLayout())
        widget.layout().setContentsMargins(40, 20, 40, 20)

        web_view = QWebEngineView()
        web_view.setObjectName('web_view')
        widget.layout().addWidget(web_view)
        intro_file = 'resources/help/intro.html'
        if exists(intro_file):
            with open(intro_file, 'r') as file:
                web_view.setHtml(file.read(), self.base_url)

        return widget

    def main_screen_widget(self):
        widget = QWidget()
        widget.setLayout(QVBoxLayout())
        widget.layout().setContentsMargins(40, 20, 40, 20)

        web_view = QWebEngineView()
        web_view.setObjectName('web_view')
        widget.layout().addWidget(web_view)
        main_screen_file = 'resources/help/main_screen.html'
        if exists(main_screen_file):
            with open(main_screen_file, 'r') as file:
                web_view.setHtml(file.read(), self.base_url)

        return widget

    def media_widget(self):
        widget = QWidget()
        widget.setLayout(QVBoxLayout())
        widget.layout().setContentsMargins(40, 20, 40, 20)

        web_view = QWebEngineView()
        web_view.setObjectName('web_view')
        widget.layout().addWidget(web_view)
        media_file = 'resources/help/media_box.html'
        if exists(media_file):
            with open(media_file, 'r') as file:
                web_view.setHtml(file.read(), self.base_url)

        return widget

    def edit_widget(self):
        widget = QWidget()
        widget.setLayout(QVBoxLayout())
        widget.layout().setContentsMargins(40, 20, 40, 20)

        web_view = QWebEngineView()
        web_view.setObjectName('web_view')
        widget.layout().addWidget(web_view)
        edit_file = 'resources/help/edit.html'
        if exists(edit_file):
            with open(edit_file, 'r') as file:
                web_view.setHtml(file.read(), self.base_url)

        return widget

    def settings_widget(self):
        widget = QWidget()
        widget.setLayout(QVBoxLayout())
        widget.layout().setContentsMargins(40, 20, 40, 20)

        web_view = QWebEngineView()
        web_view.setObjectName('web_view')
        widget.layout().addWidget(web_view)
        settings_file = 'resources/help/settings.html'
        if exists(settings_file):
            with open(settings_file, 'r') as file:
                web_view.setHtml(file.read(), self.base_url)

        return widget

    def remote_widget(self):
        widget = QWidget()
        widget.setLayout(QVBoxLayout())
        widget.layout().setContentsMargins(40, 20, 40, 20)

        web_view = QWebEngineView()
        web_view.setObjectName('web_view')
        widget.layout().addWidget(web_view)
        remote_file = 'resources/help/remote.html'
        if exists(remote_file):
            with open(remote_file, 'r') as file:
                web_view.setHtml(file.read(), self.base_url)

        return widget

    def import_widget(self):
        widget = QWidget()
        widget.setLayout(QVBoxLayout())
        widget.layout().setContentsMargins(40, 20, 40, 20)

        web_view = QWebEngineView()
        web_view.setObjectName('web_view')
        widget.layout().addWidget(web_view)
        import_file = 'resources/help/import.html'
        if exists(import_file):
            with open(import_file, 'r') as file:
                web_view.setHtml(file.read(), self.base_url)

        return widget

    def menu_widget(self):
        widget = QWidget()
        widget.setLayout(QVBoxLayout())
        widget.layout().setContentsMargins(40, 20, 40, 20)

        web_view = QWebEngineView()
        web_view.setObjectName('web_view')
        widget.layout().addWidget(web_view)
        menu_file = 'resources/help/menu_bar.html'
        if exists(menu_file):
            with open(menu_file, 'r') as file:
                web_view.setHtml(file.read(), self.base_url)

        return widget

    def file_widget(self):
        widget = QWidget()
        widget.setLayout(QVBoxLayout())
        widget.layout().setContentsMargins(40, 20, 40, 20)

        web_view = QWebEngineView()
        web_view.setObjectName('web_view')
        widget.layout().addWidget(web_view)
        file_file = 'resources/help/file_locations.html'
        if exists(file_file):
            with open(file_file, 'r') as file:
                web_view.setHtml(file.read(), self.base_url)

        return widget
