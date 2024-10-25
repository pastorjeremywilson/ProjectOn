from PyQt5.QtCore import Qt, QSize, QPoint
from PyQt5.QtGui import QCursor, QIcon, QDropEvent
from PyQt5.QtWidgets import QWidget, QListWidget, QVBoxLayout, QLabel, QMenu, QGridLayout, \
    QPushButton, QSizePolicy, QMessageBox, QAction

from edit_widget import EditWidget


class OOSWidget(QWidget):
    """
    Creates a QWidget containing all the necessary components of the program's order of service widget.
    """
    def __init__(self, gui):
        """
        Creates a QWidget containing all the necessary components of the program's order of service widget.
        :param gui.GUI gui: the current instance of GUI
        """
        super().__init__()
        self.gui = gui
        self.init_components()

    def init_components(self):
        """
        Method to create and lay out all of this widget's components.
        """
        self.setObjectName('oos_widget')

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        container = QWidget()
        container.setObjectName('container')
        #container.setStyleSheet('#container { border: 2px solid black; }')
        layout.addWidget(container)

        container_layout = QGridLayout(container)
        container_layout.setSpacing(0)
        container_layout.setContentsMargins(2, 2, 2, 2)
        container_layout.setRowStretch(0, 1)
        container_layout.setRowStretch(1, 20)
        container_layout.setRowStretch(2, 20)

        title_label = QLabel('Order of Service')
        title_label.setObjectName('title_label')
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(self.gui.bold_font)
        #title_label.setStyleSheet(
        #    'background: lightGrey; color: black; padding-top: 5px; padding-bottom: 5px; border-bottom: 2px solid black;')
        container_layout.addWidget(title_label, 0, 0, 1, 2)

        self.oos_list_widget = CustomListWidget(self.gui)
        self.oos_list_widget.setObjectName('oos_list_widget')
        #self.oos_list_widget.setStyleSheet('#oos_list_widget { margin: 0; }')
        self.oos_list_widget.setFont(self.gui.bold_font)
        container_layout.addWidget(self.oos_list_widget, 1, 0, 2, 1)

        move_up_button = QPushButton()
        move_up_button.setIcon(QIcon('resources/gui_icons/item_up.svg'))
        move_up_button.setIconSize(QSize(10, 30))
        move_up_button.setToolTip('Move Item Up')
        move_up_button.setFixedWidth(20)
        '''move_up_button.setStyleSheet(
            'QPushButton { border: square; background: white; margin-top: 1px; border-bottom: 1px solid black; } '
            'QPushButton:hover { background: lightGrey; }'
        )'''
        move_up_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.MinimumExpanding)
        move_up_button.clicked.connect(self.move_item_up)
        container_layout.addWidget(move_up_button, 1, 1)

        move_down_button = QPushButton()
        move_down_button.setIcon(QIcon('resources/gui_icons/item_down.svg'))
        move_down_button.setIconSize(QSize(10, 30))
        move_down_button.setToolTip('Move Item Down')
        move_down_button.setFixedWidth(20)
        '''move_down_button.setStyleSheet(
            'QPushButton { border: square; background: white; margin-bottom: 1px; } '
            'QPushButton:hover { background: lightGrey; }'
        )'''
        move_down_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.MinimumExpanding)
        move_down_button.clicked.connect(self.move_item_down)
        container_layout.addWidget(move_down_button, 2, 1)

    def move_item_up(self):
        """
        Method to move a QListWidgetItem up based on user's button click.
        """
        row = self.oos_list_widget.currentRow()
        if row:
            self.oos_list_widget.blockSignals(True)
            self.oos_list_widget.model().moveRow(self.oos_list_widget.rootIndex(), row, self.oos_list_widget.rootIndex(), row - 1)
            self.oos_list_widget.blockSignals(False)

    def move_item_down(self):
        """
        Method to move a QListWidgetItem down based on user's button click.
        """
        row = self.oos_list_widget.currentRow()
        if row is not None and row < self.oos_list_widget.count() - 1:
            self.oos_list_widget.blockSignals(True)
            self.oos_list_widget.model().moveRow(self.oos_list_widget.rootIndex(), row, self.oos_list_widget.rootIndex(), row + 2)
            self.oos_list_widget.blockSignals(False)


class CustomListWidget(QListWidget):
    """
    Implements QListWidget to add custom functionality.
    """
    def __init__(self, gui):
        """
        Implements QListWidget to add custom functionality.
        :param gui.GUI gui: the current instance of GUI
        """
        super().__init__()
        self.gui = gui
        self.setObjectName('CustomListWidget')
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.source_list_widget = None

        self.setAutoScroll(True)
        self.setMinimumHeight(int(self.gui.primary_screen.size().height() * 2 / 5))
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)
        self.currentItemChanged.connect(self.preview_item)

    def preview_item(self):
        """
        Function that sends the current QListWidgetItem to the preview widget when current item is changed.
        :return:
        """
        if self.currentItem():
            self.gui.send_to_preview(self.currentItem())
            self.gui.main.app.processEvents()

    def keyPressEvent(self, evt):
        """
        Overrides keyPressEvent to send the current item to live when space key is pressed.
        :param QKeyEvent evt: keyEvent
        """
        if evt.key() == Qt.Key.Key_Space:
            self.gui.send_to_live()

    def mouseDoubleClickEvent(self, evt):
        """
        Overrides mouseDoubleClickEvent to send the current item to live on double-click.
        :param evt:
        :return:
        """
        self.gui.send_to_live()

    def dragEnterEvent(self, evt):
        """
        Overrides dragEnterEvent to globalize the event's source widget.
        :param QDragEnterEvent evt: dragEnterEvent
        """
        evt.accept()
        self.source_list_widget = evt.source()

    def dropEvent(self, evt):
        """
        Overrides dropEvent to properly add a QListWidget item to this widget based on the type.
        :param QDropEvent evt: dropEvent
        :return:
        """
        if evt.source() == self:
            super().dropEvent(evt)
            return
        item = evt.source().currentItem().clone()
        item.setText('')
        row = self.row(self.itemAt(QPoint(int(evt.pos().x()), int(evt.pos().y()))))
        if row == -1:
            row = self.count()

        if evt.source().currentItem().data(Qt.ItemDataRole.UserRole)['type'] == 'song':
            self.gui.media_widget.add_song_to_service(item, row)
        elif evt.source().currentItem().data(Qt.ItemDataRole.UserRole)['type'] == 'custom':
            self.gui.media_widget.add_custom_to_service(item, row)
        elif evt.source().currentItem().data(Qt.ItemDataRole.UserRole)['type'] == 'image':
            self.gui.media_widget.add_image_to_service(item, row)
        elif evt.source().currentItem().data(Qt.ItemDataRole.UserRole)['type'] == 'video':
            self.gui.media_widget.add_video_to_service(item, row)
        elif evt.source().currentItem().data(Qt.ItemDataRole.UserRole)['type'] == 'web':
            self.gui.media_widget.add_web_to_service(item, row)

        remote_oos_buttons = ''
        for i in range(self.count()):
            if self.item(i).data(Qt.ItemDataRole.UserRole): # a placeholder item in oos will not have any data
                title = self.item(i).data(Qt.ItemDataRole.UserRole)['title']
                remote_oos_buttons += f"""
                    <button id="{title}" type="submit" name="oos_button" value="{title}">
                        <span class="title">
                            {title}
                        </span>
                    </button>
                    <br />"""
        if self.gui.main.remote_server:
            self.gui.main.remote_server.socketio.emit('update_oos', remote_oos_buttons)

        self.gui.changes = True

    def context_menu(self):
        """
        Method to create a QMenu to be used as a custom context menu.
        """
        self.item_pos = self.mapFromGlobal(self.cursor().pos())
        menu = QMenu()

        edit_text = None
        if self.itemAt(self.item_pos):
            if self.itemAt(self.item_pos).data(Qt.ItemDataRole.UserRole):
                if self.itemAt(self.item_pos).data(Qt.ItemDataRole.UserRole)['type'] == 'song':
                    edit_text = 'Edit Song'
                elif self.itemAt(self.item_pos).data(Qt.ItemDataRole.UserRole)['type'] == 'custom':
                    edit_text = 'Edit Custom Slide'

            if edit_text:
                edit_song_action = QAction('Edit Song')
                edit_song_action.triggered.connect(self.edit_song)
                menu.addAction(edit_song_action)

            delete_song_action = QAction('Remove from Service')
            delete_song_action.triggered.connect(self.delete_song)
            menu.addAction(delete_song_action)

            menu.exec(QCursor.pos())

    def edit_song(self):
        """
        Method to create an EditWidget based on the type of slide being edited.
        :return:
        """
        if self.itemAt(self.item_pos):
            if self.itemAt(self.item_pos).data(Qt.ItemDataRole.UserRole)['type'] == 'song':
                item_text = self.itemAt(self.item_pos).data(Qt.ItemDataRole.UserRole)['title']
                song_info = self.gui.main.get_song_data(item_text)
                song_edit = EditWidget(self.gui, 'song', song_info, item_text)
            elif self.itemAt(self.item_pos).data(Qt.ItemDataRole.UserRole)['type'] == 'custom':
                item_text = self.itemAt(self.item_pos).data(Qt.ItemDataRole.UserRole)['title']
                custom_info = self.gui.main.get_custom_data(item_text)
                song_edit = EditWidget(self.gui, 'custom', custom_info, item_text)

    def delete_song(self):
        """
        Method to remove an item from the order of service.
        """
        if self.currentItem().data(Qt.ItemDataRole.UserRole):
            title = self.currentItem().data(Qt.ItemDataRole.UserRole)['title']
        else:
            title = self.currentItem().text()
        result = QMessageBox.question(
            self.gui.main_window,
            'Really Remove',
            'Remove ' + title + ' from the Order of Service?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if result == QMessageBox.StandardButton.Yes:
            self.takeItem(self.currentRow())

