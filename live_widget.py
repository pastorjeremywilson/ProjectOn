from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtMultimedia import QMediaPlayer
from PyQt5.QtWidgets import QWidget, QLabel, QListWidget, QHBoxLayout, QPushButton, QGridLayout


class LiveWidget(QWidget):
    """
    Provides the 'Live' widget that contains the parts of the current item being shown live.
    """
    web_button_signal = pyqtSignal(str)

    def __init__(self, gui):
        """
        Provides the 'Live' widget that contains the parts of the current item being shown live.
        :param gui.GUI gui: The current instance of GUI
        """
        super().__init__()
        self.gui = gui
        self.web_button_signal.connect(self.web_buttons)
        self.init_components()

    def init_components(self):
        """
        Create the various widgets.py to be contained in this widget.
        """
        self.setObjectName('live_widget')

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

        title_label = QLabel('Live')
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
        container_layout.addWidget(self.slide_list, 1, 0)

        self.preview_label = QLabel()
        #self.preview_label.setStyleSheet('margin-top: 20px;')
        layout.addWidget(self.preview_label, 1, 0, Qt.AlignmentFlag.AlignCenter)

        self.player_controls = QWidget()
        player_layout = QHBoxLayout()
        self.player_controls.setLayout(player_layout)

        to_beginning_button = QPushButton()
        to_beginning_button.setIcon(QIcon('resources/gui_icons/to_beginning.svg'))
        to_beginning_button.setIconSize(QSize(30, 30))
        to_beginning_button.setFixedSize(50, 50)
        to_beginning_button.setObjectName('to_beginning')
        to_beginning_button.clicked.connect(self.video_control)
        player_layout.addStretch()
        player_layout.addWidget(to_beginning_button)

        play_button = QPushButton()
        play_button.setIcon(QIcon('resources/gui_icons/play_pause.svg'))
        play_button.setIconSize(QSize(30, 30))
        play_button.setFixedSize(50, 50)
        play_button.setObjectName('play')
        play_button.clicked.connect(self.video_control)
        player_layout.addWidget(play_button)

        stop_button = QPushButton()
        stop_button.setIcon(QIcon('resources/gui_icons/stop.svg'))
        stop_button.setIconSize(QSize(30, 30))
        stop_button.setFixedSize(50, 50)
        stop_button.setObjectName('stop')
        stop_button.clicked.connect(self.video_control)
        player_layout.addWidget(stop_button)
        player_layout.addStretch()

        layout.addWidget(self.player_controls, 2, 0, Qt.AlignmentFlag.AlignCenter)
        self.player_controls.hide()

    def video_control(self):
        """
        Call the various functions needed depending on which video control buttons are pressed.
        """
        sender = self.gui.main_window.sender()
        if sender.objectName() == 'to_beginning':
            self.gui.media_player.setPosition(0)
        elif sender.objectName() == 'play':
            # pause or play depending on the current mediaStatus
            if self.gui.media_player.state() == QMediaPlayer.State.PlayingState:
                self.gui.media_player.pause()
            else:
                self.gui.media_player.play()
        elif sender.objectName() == 'stop':
            self.gui.media_player.stop()

    def web_buttons(self, button):
        """
        Method to handle input coming from the web remote's buttons.
        :param str button: 'slide_forward', 'slide_back', 'item_forward', or 'item_back'
        """
        current_oos_row = self.gui.oos_widget.oos_list_widget.currentRow()

        if button == 'slide_forward':
            if self.slide_list.currentRow() == self.slide_list.count() - 1:
                if current_oos_row < self.gui.oos_widget.oos_list_widget.count() - 1:
                    self.gui.oos_widget.oos_list_widget.setCurrentRow(current_oos_row + 1)
                    self.gui.preview_widget.slide_list.setCurrentRow(0)
                    self.gui.send_to_live()
            else:
                self.slide_list.setCurrentRow(self.slide_list.currentRow() + 1)

        elif button == 'slide_back':
            if self.slide_list.currentRow() == 0:
                if current_oos_row > 0:
                    self.gui.oos_widget.oos_list_widget.setCurrentRow(current_oos_row - 1)
                    self.gui.preview_widget.slide_list.setCurrentRow(self.gui.preview_widget.slide_list.count() - 1)
                    self.gui.send_to_live()
            else:
                self.slide_list.setCurrentRow(self.slide_list.currentRow() - 1)

        elif button == 'item_forward':
            if current_oos_row < self.gui.oos_widget.oos_list_widget.count() - 1:
                self.gui.oos_widget.oos_list_widget.setCurrentRow(current_oos_row + 1)
                self.gui.preview_widget.slide_list.setCurrentRow(0)
                self.gui.send_to_live()

        elif button == 'item_back':
            if current_oos_row > 0:
                self.gui.oos_widget.oos_list_widget.setCurrentRow(current_oos_row - 1)
                self.gui.preview_widget.slide_list.setCurrentRow(0)
                self.gui.send_to_live()

class CustomListWidget(QListWidget):
    """
    Provides a customized QListWidget that will call changes to the display when items are changed and perform certain
    tasks based on key presses.
    """
    def __init__(self, gui):
        """
        Provides a customized QListWidget that will call changes to the display when items are changed and perform certain
        tasks based on key presses.
        :param gui.GUI gui: The current instance of GUI
        """
        super().__init__()
        self.gui = gui
        self.setObjectName('CustomListWidget')
        self.currentItemChanged.connect(self.change_display)

    def change_display(self):
        """
        Call GUI's change_display function and sync the web remote with the user's input.
        """
        self.gui.change_display('live')

        if self.currentItem():
            self.gui.main.remote_server.socketio.emit('change_current_slide', str(self.currentRow()))

    def keyPressEvent(self, evt):
        """
        Handle arrow key presses as well as standard PowerPoint remote inputs.
        :param QKeyEvent evt: keyPressEvent
        """
        current_oos_row = self.gui.oos_widget.oos_list_widget.currentRow()

        if evt.key() == Qt.Key.Key_Down:
            if self.currentRow() == self.count() - 1:
                if current_oos_row < self.gui.oos_widget.oos_list_widget.count() - 1:
                    self.gui.oos_widget.oos_list_widget.setCurrentRow(current_oos_row + 1)
                    self.gui.preview_widget.slide_list.setCurrentRow(0)
                    self.gui.send_to_live()
            else:
                self.setCurrentRow(self.currentRow() + 1)

        elif evt.key() == Qt.Key.Key_Up:
            if self.currentRow() == 0:
                if current_oos_row > 0:
                    self.gui.oos_widget.oos_list_widget.setCurrentRow(current_oos_row - 1)
                    self.gui.preview_widget.slide_list.setCurrentRow(self.gui.preview_widget.slide_list.count() - 1)
                    self.gui.send_to_live()
            else:
                self.setCurrentRow(self.currentRow() - 1)

        elif evt.key() == Qt.Key.Key_Right:
            if current_oos_row < self.gui.oos_widget.oos_list_widget.count() - 1:
                self.gui.oos_widget.oos_list_widget.setCurrentRow(current_oos_row + 1)
                self.gui.preview_widget.slide_list.setCurrentRow(0)
                self.gui.send_to_live()

        elif evt.key() == Qt.Key.Key_Left:
            if current_oos_row > 0:
                self.gui.oos_widget.oos_list_widget.setCurrentRow(current_oos_row - 1)
                self.gui.preview_widget.slide_list.setCurrentRow(0)
                self.gui.send_to_live()

        # handlers for PowerPoint remote input
        if not self.gui.block_remote_input:
            if evt.key() == 16777239:  # PowerPoint remote 'next' button
                if self.currentRow() == self.count() - 1:
                    if current_oos_row < self.gui.oos_widget.oos_list_widget.count() - 1:
                        self.gui.oos_widget.oos_list_widget.setCurrentRow(current_oos_row + 1)
                        self.gui.preview_widget.slide_list.setCurrentRow(0)
                        self.gui.send_to_live()
                else:
                    self.setCurrentRow(self.currentRow() + 1)
            elif evt.key() == 16777238:  # PowerPoint remote 'previous' button
                if self.currentRow() == 0:
                    if current_oos_row > 0:
                        self.gui.oos_widget.oos_list_widget.setCurrentRow(current_oos_row - 1)
                        self.gui.preview_widget.slide_list.setCurrentRow(self.gui.preview_widget.slide_list.count() - 1)
                        self.gui.send_to_live()
                else:
                    self.setCurrentRow(self.currentRow() - 1)
            elif evt.key() == 46:  # PPT remote 'blank' button
                self.gui.display_black_screen()

            elif evt.key() == 16777268:  # PPT remote 'play' button
                if self.gui.video_widget.isVisible():
                    if self.gui.media_player.isPlaying():
                        self.gui.media_player.pause()
                    else:
                        self.gui.media_player.play()

        else:
            super().keyPressEvent(evt)
