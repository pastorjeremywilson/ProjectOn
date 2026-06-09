from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QKeyEvent
from PyQt5.QtMultimedia import QMediaPlayer
from PyQt5.QtWidgets import QWidget, QLabel, QListWidget, QHBoxLayout, QPushButton, QGridLayout, QAbstractItemView, \
    QVBoxLayout, QSlider


class LiveWidget(QWidget):
    """
    Provides the 'Live' widget that contains the parts of the current item being shown live.
    """
    web_button_signal = pyqtSignal(str)

    def __init__(self, gui):
        """
        Provides the 'Live' widget that contains the parts of the current item being shown live.
        :param guiElements.GUI gui: The current instance of GUI
        """
        super().__init__()
        self.gui = gui
        self.web_button_signal.connect(self.web_buttons)

        self.slide_list = CustomListWidget(self.gui)
        self.player_controls = QWidget()
        self.seek_slider = QSlider()
        self.video_current_label = QLabel('0:00:00')
        self.video_end_label = QLabel('0:00:00')
        self.web_controls = QWidget()
        self.preview_label = QLabel()

        self.init_components()

    def init_components(self):
        """
        Create the various widgets to be contained in this widget.
        """
        self.setObjectName('live_widget')

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

        title_label = QLabel('Live')
        title_label.setObjectName('title_label')
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(self.gui.bold_font)
        container_layout.addWidget(title_label, 0, 0)

        self.slide_list.setObjectName('slide_list')
        self.slide_list.setFont(self.gui.standard_font)
        self.slide_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.slide_list.verticalScrollBar().setSingleStep(15)
        container_layout.addWidget(self.slide_list, 1, 0)

        preview_container = QWidget()
        layout.addWidget(preview_container, 1, 0)
        preview_container_layout = QVBoxLayout(preview_container)
        preview_container_layout.setContentsMargins(0, 0, 0, 0)
        preview_container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        preview_container_layout.addWidget(self.player_controls)
        player_layout = QVBoxLayout(self.player_controls)

        self.seek_slider.setFont(self.gui.standard_font)
        self.seek_slider.setOrientation(Qt.Orientation.Horizontal)
        def slider_moved():
            if self.gui.display_widget.media_player:
                if self.gui.display_widget.media_player.state() == QMediaPlayer.StoppedState:
                    self.gui.display_widget.media_player.pause()
                    self.gui.display_widget.media_player.play()
                else:
                    self.gui.display_widget.media_player.pause()
                self.gui.display_widget.media_player.setPosition(self.seek_slider.value())
        self.seek_slider.sliderMoved.connect(slider_moved)
        player_layout.addWidget(self.seek_slider)

        slider_label_widget = QWidget()
        player_layout.addWidget(slider_label_widget)
        slider_label_layout = QHBoxLayout(slider_label_widget)

        video_start_label = QLabel('0:00:00')
        video_start_label.setFont(self.gui.standard_font)
        slider_label_layout.addWidget(video_start_label)
        slider_label_layout.addStretch()

        self.video_current_label.setFont(self.gui.bold_font)
        slider_label_layout.addWidget(self.video_current_label)
        slider_label_layout.addStretch()

        self.video_end_label.setFont(self.gui.standard_font)
        slider_label_layout.addWidget(self.video_end_label)

        player_button_widget = QWidget()
        player_layout.addWidget(player_button_widget)
        player_button_layout = QHBoxLayout(player_button_widget)
        player_button_layout.setContentsMargins(0, 0, 0, 0)

        to_beginning_button = QPushButton()
        to_beginning_button.setIcon(QIcon('resources/gui_icons/to_beginning.svg'))
        to_beginning_button.setIconSize(QSize(30, 30))
        to_beginning_button.setFixedSize(50, 50)
        to_beginning_button.setObjectName('to_beginning')
        to_beginning_button.setToolTip('Start Video from Beginning')
        to_beginning_button.released.connect(self.video_control)
        player_button_layout.addStretch()
        player_button_layout.addWidget(to_beginning_button)
        player_button_layout.addSpacing(25)

        play_button = QPushButton()
        play_button.setIcon(QIcon('resources/gui_icons/play_pause.svg'))
        play_button.setIconSize(QSize(30, 30))
        play_button.setFixedSize(50, 50)
        play_button.setObjectName('play')
        play_button.setToolTip('Play/Pause the Video')
        play_button.released.connect(self.video_control)
        player_button_layout.addWidget(play_button)
        player_button_layout.addSpacing(25)

        stop_button = QPushButton()
        stop_button.setIcon(QIcon('resources/gui_icons/stop.svg'))
        stop_button.setIconSize(QSize(30, 30))
        stop_button.setFixedSize(50, 50)
        stop_button.setObjectName('stop')
        stop_button.setToolTip('Stop the Video')
        stop_button.released.connect(self.video_control)
        player_button_layout.addWidget(stop_button)
        player_button_layout.addStretch()

        self.player_controls.hide()

        preview_container_layout.addWidget(self.web_controls)
        web_layout = QHBoxLayout(self.web_controls)

        reload_button = QPushButton()
        reload_button.setIcon(QIcon('resources/gui_icons/reload.svg'))
        reload_button.setIconSize(QSize(30, 30))
        reload_button.setFixedSize(50, 50)
        reload_button.setObjectName('reload')
        reload_button.setToolTip('Reload Web Page')
        reload_button.clicked.connect(self.web_reload)
        web_layout.addStretch()
        web_layout.addWidget(reload_button)
        web_layout.addStretch()

        self.web_controls.hide()

        preview_label_container = QWidget()
        preview_container_layout.addWidget(preview_label_container)
        preview_label_container_layout = QHBoxLayout(preview_label_container)
        preview_label_container_layout.setContentsMargins(0, 0, 0, 0)

        preview_label_container_layout.addStretch()
        preview_label_container_layout.addWidget(self.preview_label)
        preview_label_container_layout.addStretch()

    def video_control(self):
        """
        Call the various functions needed depending on which video control buttons are pressed.
        """
        sender = self.gui.main_window.sender()
        if sender.objectName() == 'to_beginning':
            self.gui.display_widget.media_player.setPosition(0)
        elif sender.objectName() == 'play':
            # pause or play depending on the current mediaStatus
            if self.gui.display_widget.media_player.state() == QMediaPlayer.PlayingState:
                self.gui.media_player.pause()
            else:
                self.gui.display_widget.media_player.play()
        elif sender.objectName() == 'stop':
            self.gui.display_widget.media_player.pause()
            self.gui.display_widget.media_player.setPosition(0)

    def web_reload(self):
        """
        Tell the web view widget to reload the current web page
        :return: None
        """
        self.gui.display_widget.web_view.reload()

    def web_buttons(self, button: str):
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
        :param guiElements.GUI gui: The current instance of GUI
        """
        super().__init__()
        self.gui = gui
        self.setObjectName('CustomListWidget')
        self.currentItemChanged.connect(self.change_display)

    def change_display(self):
        """
        Call GUI's change_display function and sync the web remote with the user's input.
        """

        if self.currentItem():
            self.gui.display_widget.change_display()
            self.gui.main.remote_server.socketio.emit('change_current_slide', str(self.currentRow()))

    def keyPressEvent(self, evt: QKeyEvent):
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
                self.gui.display_widget.show_black_screen()

            elif evt.key() == 16777268:  # PPT remote 'play' button
                if self.gui.video_widget.isVisible():
                    if self.gui.media_player.isPlaying():
                        self.gui.media_player.pause()
                    else:
                        self.gui.media_player.play()

        else:
            super().keyPressEvent(evt)
