import os.path
import shutil
import sqlite3

from PyQt5.QtCore import Qt, QRectF, QPointF, QEvent
from PyQt5.QtGui import QPainter, QPixmap, QPen, QBrush, QColor, QPainterPath
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QRadioButton, QButtonGroup, QVBoxLayout, QSpinBox, \
    QScrollArea, QHBoxLayout, QPushButton, QColorDialog, QFileDialog, QMessageBox, QDialog, QLineEdit

from simple_splash import SimpleSplash
from widgets import FontWidget


class SettingsWidget(QDialog):
    wait_widget = None

    def __init__(self, gui):
        super().__init__()
        self.accept_font_changes = False
        self.setObjectName('settings_widget')
        self.gui = gui
        self.setParent(self.gui.main_window)
        self.min_width = 1000

        self.show_wait_widget()
        self.init_components()
        self.gui.main.app.processEvents()

        self.wait_widget.subtitle_label.setText('Applying Settings')
        self.apply_settings()
        self.song_font_settings_widget.change_font_sample()
        self.bible_font_settings_widget.change_font_sample()

        self.show()

        self.accept_font_changes = True
        self.wait_widget.subtitle_label.setText('Creating Font Sample')
        self.gui.main.app.processEvents()
        self.wait_widget.widget.deleteLater()

    def show_wait_widget(self):
        self.wait_widget = SimpleSplash(self.gui, 'Please wait...', subtitle=True)

    def init_components(self):
        self.setParent(self.gui.main_window)
        self.setWindowTitle('Settings')
        self.setWindowFlag(Qt.WindowType.Window)
        self.setMinimumSize(self.min_width + 60, 800)
        layout = QGridLayout(self)
        layout.setRowStretch(0, 20)
        layout.setRowStretch(1, 1)

        self.settings_container = QWidget()
        self.settings_container.setObjectName('settings_container')
        settings_container_layout = QVBoxLayout(self.settings_container)

        ccli_container = QWidget()
        ccli_container_layout = QVBoxLayout(ccli_container)
        settings_container_layout.addWidget(ccli_container)

        ccli_title_label = QLabel('CCLI Information')
        ccli_title_label.setFont(self.gui.bold_font)
        ccli_title_label.setStyleSheet('background: #5555aa; color: white')
        ccli_title_label.setContentsMargins(5, 5, 5, 5)
        ccli_container_layout.addWidget(ccli_title_label)

        ccli_widget = QWidget()
        ccli_layout = QHBoxLayout()
        ccli_widget.setLayout(ccli_layout)
        ccli_container_layout.addWidget(ccli_widget)

        ccli_label = QLabel('CCLI License #:')
        ccli_label.setFont(self.gui.standard_font)
        ccli_layout.addWidget(ccli_label)

        self.ccli_line_edit = QLineEdit()
        self.ccli_line_edit.setFont(self.gui.standard_font)
        ccli_layout.addWidget(self.ccli_line_edit)

        self.wait_widget.subtitle_label.setText('Loading Screens')
        self.gui.main.app.processEvents()

        settings_container_layout.addWidget(self.screen_settings())

        self.wait_widget.subtitle_label.setText('Loading Fonts')
        self.gui.main.app.processEvents()

        settings_container_layout.addWidget(self.font_settings())

        self.wait_widget.subtitle_label.setText('Loading Backgrounds')
        self.gui.main.app.processEvents()

        settings_container_layout.addWidget(self.background_settings())
        settings_container_layout.addStretch()

        settings_scroll_area = QScrollArea()
        settings_scroll_area.setWidgetResizable(True)
        #settings_scroll_area.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        #settings_scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.settings_container.adjustSize()
        settings_scroll_area.setWidget(self.settings_container)
        layout.addWidget(settings_scroll_area, 0, 0)

        button_widget = QWidget()
        button_layout = QHBoxLayout()
        button_widget.setLayout(button_layout)
        layout.addWidget(button_widget, 1, 0)

        save_button = QPushButton('Save')
        save_button.setFont(self.gui.standard_font)
        save_button.clicked.connect(self.save)
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addSpacing(20)

        cancel_button = QPushButton('Cancel')
        cancel_button.setFont(self.gui.standard_font)
        cancel_button.clicked.connect(self.cancel)
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()

    def screen_settings(self):
        widget = QWidget()
        widget.setMinimumWidth(self.min_width)
        widget.setObjectName('screen_widget')
        layout = QGridLayout()
        widget.setLayout(layout)

        index = 0
        for screen in self.gui.main.app.screens():
            app_screen_name = screen.name()
            name_split = app_screen_name.split('\\')
            name = name_split[len(name_split) - 1]

            if screen.name() == self.gui.primary_screen.name():
                primary = True
            else:
                primary = False

            screen_pixmap = self.draw_screen_pixmap(name, primary, screen.size())
            screen_icon_label = QLabel()
            screen_icon_label.setPixmap(screen_pixmap)
            layout.addWidget(screen_icon_label, 1, index)

            model_label = QLabel(screen.model())
            layout.addWidget(model_label, 2, index)

            size_label = QLabel('Size: ' + str(screen.size().width()) + 'x' + str(screen.size().height()))
            layout.addWidget(size_label, 3, index)

            set_display_button = QRadioButton('Set as display screen')
            set_display_button.setObjectName(app_screen_name)
            layout.addWidget(set_display_button, 4, index)

            if self.gui.secondary_screen:
                if screen.name() == self.gui.secondary_screen.name():
                    set_display_button.setChecked(True)
            else:
                set_display_button.setChecked(True)

            index += 1

        title_label = QLabel('Display Settings')
        title_label.setFont(self.gui.bold_font)
        title_label.setStyleSheet('background: #5555aa; color: white')
        title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(title_label, 0, 0, 1, index + 1)

        spacing_widget = QWidget()
        spacing_widget.setFixedHeight(20)
        layout.addWidget(spacing_widget, 5, 0, 1, index + 1)

        self.screen_button_group = QButtonGroup()
        id = 0
        for button in widget.findChildren(QRadioButton):
            self.screen_button_group.addButton(button, id)
            id += 1

        return widget

    def font_settings(self):
        widget = QWidget()
        widget.setMinimumWidth(self.min_width)
        #widget.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        widget.setObjectName('font_widget')
        layout = QVBoxLayout()
        widget.setLayout(layout)

        title_label = QLabel('Global Font Settings')
        title_label.setFont(self.gui.bold_font)
        title_label.setStyleSheet('background: #5555aa; color: white')
        title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(title_label)

        font_widget = QWidget()
        font_layout = QVBoxLayout()
        font_widget.setLayout(font_layout)
        layout.addWidget(font_widget)

        self.song_font_settings_widget = FontWidget(self.gui, 'song', draw_border=False)
        font_layout.addWidget(self.song_font_settings_widget)

        self.bible_font_settings_widget = FontWidget(self.gui, 'bible', draw_border=False)
        font_layout.addWidget(self.bible_font_settings_widget)

        stage_font_widget = QWidget()
        stage_font_layout = QHBoxLayout()
        stage_font_widget.setLayout(stage_font_layout)
        layout.addWidget(stage_font_widget)

        stage_font_label = QLabel('Stage Display Font Size:')
        stage_font_label.setFont(self.gui.bold_font)
        stage_font_layout.addWidget(stage_font_label)

        self.stage_font_spinbox = QSpinBox()
        self.stage_font_spinbox.setRange(12, 120)
        self.stage_font_spinbox.setFont(self.gui.standard_font)
        self.stage_font_spinbox.installEventFilter(self)
        stage_font_layout.addWidget(self.stage_font_spinbox)
        stage_font_layout.addStretch()

        return widget

    def background_settings(self):
        from widgets import ImageCombobox

        widget = QWidget()
        widget.setMinimumWidth(self.min_width)
        layout = QVBoxLayout()
        widget.setLayout(layout)

        title_label = QLabel('Global Background Settings')
        title_label.setFont(self.gui.bold_font)
        title_label.setStyleSheet('background: #5555aa; color: white')
        title_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(title_label)

        song_background_label = QLabel('Global Song Background:')
        song_background_label.setFont(self.gui.standard_font)
        layout.addWidget(song_background_label)

        song_background_widget = QWidget()
        song_background_layout = QHBoxLayout(song_background_widget)
        layout.addWidget(song_background_widget)
        layout.addSpacing(20)

        self.song_background_combobox = ImageCombobox(self.gui, 'song', suppress_autosave=True)
        self.song_background_combobox.setMaximumWidth(500)
        song_background_layout.addWidget(self.song_background_combobox)
        song_background_layout.addSpacing(20)

        add_background_button = QPushButton('Import a Background')
        add_background_button.setFont(self.gui.standard_font)
        add_background_button.clicked.connect(self.import_background)
        song_background_layout.addWidget(add_background_button)
        song_background_layout.addSpacing(20)

        delete_background_button = QPushButton('Delete a Background')
        delete_background_button.setFont(self.gui.standard_font)
        delete_background_button.clicked.connect(lambda: self.delete_background('background'))
        song_background_layout.addWidget(delete_background_button)
        song_background_layout.addStretch()

        bible_background_label = QLabel('Global Bible Background:')
        bible_background_label.setFont(self.gui.standard_font)
        layout.addWidget(bible_background_label)

        bible_background_widget = QWidget()
        bible_background_layout = QHBoxLayout(bible_background_widget)
        layout.addWidget(bible_background_widget)
        layout.addSpacing(20)

        self.bible_background_combobox = ImageCombobox(self.gui, 'bible', suppress_autosave=True)
        self.bible_background_combobox.setMaximumWidth(500)
        bible_background_layout.addWidget(self.bible_background_combobox)
        bible_background_layout.addStretch()

        logo_background_label = QLabel('Set Logo Image:')
        logo_background_label.setFont(self.gui.standard_font)
        layout.addWidget(logo_background_label)

        logo_background_widget = QWidget()
        logo_background_layout = QHBoxLayout(logo_background_widget)
        layout.addWidget(logo_background_widget)
        layout.addSpacing(20)

        self.logo_background_combobox = ImageCombobox(self.gui, 'logo', suppress_autosave=True)
        self.logo_background_combobox.setMaximumWidth(500)
        logo_background_layout.addWidget(self.logo_background_combobox)
        logo_background_layout.addSpacing(20)

        logo_background_button = QPushButton('Add an Image')
        logo_background_button.setFont(self.gui.standard_font)
        logo_background_button.clicked.connect(self.gui.media_widget.add_image)
        logo_background_layout.addWidget(logo_background_button)
        logo_background_layout.addSpacing(20)

        delete_image_button = QPushButton('Delete an Image')
        delete_image_button.setFont(self.gui.standard_font)
        delete_image_button.clicked.connect(lambda: self.delete_background('image'))
        logo_background_layout.addWidget(delete_image_button)
        logo_background_layout.addStretch()

        return widget

    def eventFilter(self, obj, evt):
        if evt.type() == QEvent.Type.Wheel:
            return True
        else:
            return super().eventFilter(obj, evt)

    def draw_screen_pixmap(self, name, primary, size):
        ratio = size.width() / size.height()
        height = 100
        width = int(100 * ratio)

        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(pixmap)
        pen = QPen()
        pen.setColor(Qt.GlobalColor.gray)
        pen.setWidth(10)
        brush = QBrush()
        brush.setColor(Qt.GlobalColor.blue)

        painter.setPen(pen)
        painter.setBrush(brush)

        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, width, height), 5, 5)
        painter.fillPath(path, QColor(85, 85, 170))
        painter.drawPath(path)

        text_rect = painter.fontMetrics().boundingRect(name)
        text_pos = QPointF((width / 2) - (text_rect.width() / 2), (height / 2) - (text_rect.height() / 2))
        pen.setColor(Qt.GlobalColor.white)
        painter.setPen(pen)
        painter.drawText(text_pos, name)

        if primary:
            text_pos.setY(text_pos.y() + text_rect.height() + 5)
            painter.drawText(text_pos, '(primary)')

        painter.end()
        return pixmap

    def color_chooser(self):
        sender = self.sender()
        color = QColorDialog.getColor(QColor(Qt.GlobalColor.black), self)
        rgb = color.getRgb()
        color_string = str(rgb[0]) + ', ' + str(rgb[1]) + ', ' + str(rgb[2])
        self.custom_font_color_radio_button.setText('Custom: ' + color_string)
        self.custom_font_color_radio_button.setObjectName(color_string)
        sender.setChecked(True)
        self.change_font_sample()

    def image_chooser(self):
        file = QFileDialog.getOpenFileName(self, 'Choose Image File', os.path.expanduser('~') + '/Pictures')
        if len(file[0]) > 0:
            file_split = file[0].split('/')
            file_name = file_split[len(file_split) - 1]
            self.background_line_edit.setText(file_name)
            self.gui.main.copy_image(file[0])
        self.background_image_radio_button.setChecked(True)

    def import_background(self):
        result = QFileDialog.getOpenFileName(
            self.gui.main_window, 'Choose Background Image', os.path.expanduser('~') + '/Pictures')
        if len(result[0]) > 0:
            try:
                file_name_split = result[0].split('/')
                file_name = file_name_split[len(file_name_split) - 1]
                shutil.copy(result[0], self.gui.main.background_dir + '/' + file_name)
            except Exception:
                self.gui.main.error_log()

            from main import IndexImages
            ii = IndexImages(self.gui.main, 'backgrounds')
            ii.add_image_index(self.gui.main.background_dir + '/' + file_name, 'background')

            self.song_background_combobox.refresh()
            self.bible_background_combobox.refresh()
            self.gui.tool_bar.song_background_combobox.refresh()
            self.gui.tool_bar.bible_background_combobox.refresh()

            self.song_background_combobox.update()
            self.bible_background_combobox.update()
            self.gui.tool_bar.song_background_combobox.update()
            self.gui.tool_bar.bible_background_combobox.update()

            self.song_background_combobox.setCurrentIndex(
                self.song_background_combobox.findData(
                    self.gui.main.settings['global_song_background'])
            )
            self.bible_background_combobox.setCurrentIndex(
                self.bible_background_combobox.findData(
                    self.gui.main.settings['global_bible_background'])
            )
            self.gui.tool_bar.song_background_combobox.setCurrentIndex(
                self.gui.tool_bar.song_background_combobox.findData(
                    self.gui.main.settings['global_song_background'])
            )
            self.gui.tool_bar.bible_background_combobox.setCurrentIndex(
                self.gui.tool_bar.bible_background_combobox.findData(
                    self.gui.main.settings['global_bible_background'])
            )

            self.gui.apply_settings()

    def delete_background(self, type):
        dialog = QDialog()
        layout = QVBoxLayout()
        dialog.setLayout(layout)

        if type == 'background':
            label = QLabel('Choose a background to remove:')
            current_bible_background = self.bible_background_combobox.currentData(Qt.ItemDataRole.UserRole)
            current_song_background = self.song_background_combobox.currentData(Qt.ItemDataRole.UserRole)
        elif type == 'image':
            label = QLabel('Choose an image item to remove:')
            current_image = self.logo_background_combobox.currentData(Qt.ItemDataRole.UserRole)
        label.setFont(self.gui.standard_font)
        layout.addWidget(label)

        from widgets import ImageCombobox
        if type == 'background':
            combobox = ImageCombobox(self.gui, type='delete_background')
        elif type == 'image':
            combobox = ImageCombobox(self.gui, type='delete_image')
        combobox.removeItem(1)
        combobox.removeItem(0)
        layout.addWidget(combobox)

        button_widget = QWidget()
        button_layout = QHBoxLayout()
        button_widget.setLayout(button_layout)
        layout.addWidget(button_widget)

        remove_button = QPushButton('Remove')
        remove_button.setFont(self.gui.standard_font)
        remove_button.clicked.connect(lambda: dialog.done(0))
        button_layout.addWidget(remove_button)

        cancel_button = QPushButton('Cancel')
        cancel_button.setFont(self.gui.standard_font)
        cancel_button.clicked.connect(lambda: dialog.done(1))
        button_layout.addWidget(cancel_button)

        response = dialog.exec()

        if response == 0:
            file_name = combobox.currentData(Qt.ItemDataRole.UserRole)
            try:
                if type == 'background':
                    os.remove(self.gui.main.background_dir + '/' + file_name)
                elif type == 'image':
                    os.remove(self.gui.main.image_dir + '/' + file_name)
            except FileNotFoundError:
                QMessageBox.information(
                    self.gui.main_window, 'Not Found', 'File not found. Reindexing images.', QMessageBox.StandardButton.Ok)

            splash = SimpleSplash(self.gui, 'Reindexing Images. Please Wait...')
            from main import IndexImages
            ii = IndexImages(self.gui.main, 'backgrounds')
            self.gui.main.thread_pool.start(ii)
            self.gui.main.thread_pool.waitForDone()

            self.song_background_combobox.refresh()
            self.bible_background_combobox.refresh()
            self.gui.tool_bar.song_background_combobox.refresh()
            self.gui.tool_bar.bible_background_combobox.refresh()

            self.song_background_combobox.update()
            self.bible_background_combobox.update()
            self.gui.tool_bar.song_background_combobox.update()
            self.gui.tool_bar.bible_background_combobox.update()

            self.song_background_combobox.setCurrentIndex(
                self.song_background_combobox.findData(
                    self.gui.main.settings['global_song_background'])
            )
            self.bible_background_combobox.setCurrentIndex(
                self.bible_background_combobox.findData(
                    self.gui.main.settings['global_bible_background'])
            )
            self.gui.tool_bar.song_background_combobox.setCurrentIndex(
                self.gui.tool_bar.song_background_combobox.findData(
                    self.gui.main.settings['global_song_background'])
            )
            self.gui.tool_bar.bible_background_combobox.setCurrentIndex(
                self.gui.tool_bar.bible_background_combobox.findData(
                    self.gui.main.settings['global_bible_background'])
            )

            splash.widget.deleteLater()

            QMessageBox.information(
                self,
                f'{type.capitalize()} Removed',
                file_name + ' removed.',
                QMessageBox.StandardButton.Ok
            )

            # remove deleted item from the database thumbnails and refresh the appropriate combobox(es)
            if type == 'background':
                connection = sqlite3.connect(self.gui.main.database)
                cursor = connection.cursor()
                cursor.execute('DELETE FROM backgroundThumbnails WHERE fileName="' + file_name + '";')
                connection.commit()
                connection.close()

                self.song_background_combobox.refresh()
                self.bible_background_combobox.refresh()
                self.gui.tool_bar.song_background_combobox.refresh()
                self.gui.tool_bar.bible_background_combobox.refresh()

                current_song_index = self.song_background_combobox.findData(
                    current_song_background, Qt.ItemDataRole.UserRole)
                if current_song_index == -1:
                    self.song_background_combobox.setCurrentIndex(0)
                    self.gui.tool_bar.song_background_combobox.setCurrentIndex(0)
                else:
                    self.song_background_combobox.setCurrentIndex(current_song_index)
                    self.gui.tool_bar.song_background_combobox.setCurrentIndex(current_song_index)

                current_bible_index = self.bible_background_combobox.findData(
                    current_bible_background, Qt.ItemDataRole.UserRole)
                if current_bible_index == -1:
                    self.bible_background_combobox.setCurrentIndex(0)
                    self.gui.tool_bar.bible_background_combobox.setCurrentIndex(0)
                else:
                    self.bible_background_combobox.setCurrentIndex(current_bible_index)
                    self.gui.tool_bar.bible_background_combobox.setCurrentIndex(current_bible_index)

            elif type == 'image':
                connection = sqlite3.connect(self.gui.main.database)
                cursor = connection.cursor()
                cursor.execute('DELETE FROM backgroundThumbnails WHERE fileName="' + file_name + '";')
                connection.commit()
                connection.close()

                self.logo_background_combobox.refresh()
                current_image_index = self.logo_background_combobox.findData(current_image, Qt.ItemDataRole.UserRole)
                if current_image_index == -1:
                    self.logo_background_combobox.setCurrentIndex(0)
                else:
                    self.logo_background_combobox.setCurrentIndex(current_image_index)

    def apply_settings(self):
        if self.gui.main.settings:
            try:
                if 'ccli_num' in self.gui.main.settings.keys():
                    self.ccli_line_edit.setText(self.gui.main.settings['ccli_num'])

                screen_found = False
                for button in self.screen_button_group.buttons():
                    if button.objectName() == self.gui.main.settings['selected_screen_name']:
                        button.setChecked(True)
                        screen_fount = True

                if not screen_found:
                    for button in self.screen_button_group.buttons():
                        if 'primary' not in button.text():
                            button.setChecked(True)

                self.song_font_settings_widget.apply_settings()
                self.bible_font_settings_widget.apply_settings()

                if 'stage_font_size' in self.gui.main.settings.keys():
                    self.stage_font_spinbox.setValue(int(self.gui.main.settings['stage_font_size']))

                self.song_background_combobox.blockSignals(True)
                self.bible_background_combobox.blockSignals(True)
                self.logo_background_combobox.blockSignals(True)

                self.song_background_combobox.setCurrentIndex(
                    self.song_background_combobox.findData(
                        self.gui.main.settings['global_song_background'], Qt.ItemDataRole.UserRole))
                self.bible_background_combobox.setCurrentIndex(
                    self.bible_background_combobox.findData(
                        self.gui.main.settings['global_bible_background'], Qt.ItemDataRole.UserRole))
                self.logo_background_combobox.setCurrentIndex(
                    self.logo_background_combobox.findData(
                        self.gui.main.settings['logo_image'], Qt.ItemDataRole.UserRole))

                self.song_background_combobox.blockSignals(False)
                self.bible_background_combobox.blockSignals(False)
                self.logo_background_combobox.blockSignals(False)
            except Exception:
                self.gui.main.error_log()

    def save(self):
        if not self.screen_button_group.checkedButton().objectName() == self.gui.main.settings['selected_screen_name']:
            screen_name = self.screen_button_group.checkedButton().objectName()

            self.gui.main.settings['selected_screen_name'] = screen_name
            primary_screen = None
            secondary_screen = None

            if len(self.gui.main.app.screens()) == 1:
                primary_screen = self.gui.main.app.screens()[0]
                secondary_screen = self.gui.main.app.screens()[0]
            else:
                for screen in self.gui.main.app.screens():
                    if screen_name in screen.name():
                        secondary_screen = screen
                    else:
                        primary_screen = screen

            self.gui.position_screens(primary_screen, secondary_screen)

        self.gui.main.settings['song_font_face'] = self.song_font_settings_widget.font_list_widget.currentItem().data(20)
        self.gui.main.settings['song_font_size'] = self.song_font_settings_widget.font_size_spinbox.value()
        self.gui.main.settings['song_font_color'] = (
            self.song_font_settings_widget.font_color_button_group.checkedButton().objectName())
        self.gui.main.settings['song_use_shadow'] = self.song_font_settings_widget.shadow_checkbox.isChecked()
        self.gui.main.settings['song_shadow_color'] = self.song_font_settings_widget.shadow_color_slider.color_slider.value()
        self.gui.main.settings['song_shadow_offset'] = self.song_font_settings_widget.shadow_offset_slider.offset_slider.value()
        self.gui.main.settings['song_use_outline'] = self.song_font_settings_widget.outline_checkbox.isChecked()
        self.gui.main.settings['song_outline_color'] = self.song_font_settings_widget.outline_color_slider.color_slider.value()
        self.gui.main.settings['song_outline_width'] = self.song_font_settings_widget.outline_width_slider.offset_slider.value()

        self.gui.main.settings['bible_font_face'] = self.bible_font_settings_widget.font_list_widget.currentItem().data(20)
        self.gui.main.settings['bible_font_size'] = self.bible_font_settings_widget.font_size_spinbox.value()
        self.gui.main.settings['bible_font_color'] = (
            self.bible_font_settings_widget.font_color_button_group.checkedButton().objectName())
        self.gui.main.settings['bible_use_shadow'] = self.bible_font_settings_widget.shadow_checkbox.isChecked()
        self.gui.main.settings['bible_shadow_color'] = self.bible_font_settings_widget.shadow_color_slider.color_slider.value()
        self.gui.main.settings['bible_shadow_offset'] = self.bible_font_settings_widget.shadow_offset_slider.offset_slider.value()
        self.gui.main.settings['bible_use_outline'] = self.bible_font_settings_widget.outline_checkbox.isChecked()
        self.gui.main.settings['bible_outline_color'] = self.bible_font_settings_widget.outline_color_slider.color_slider.value()
        self.gui.main.settings['bible_outline_width'] = self.bible_font_settings_widget.outline_width_slider.offset_slider.value()

        self.gui.main.settings['global_song_background'] = self.song_background_combobox.itemData(
            self.song_background_combobox.currentIndex(), Qt.ItemDataRole.UserRole
        )
        self.gui.main.settings['global_bible_background'] = self.bible_background_combobox.itemData(
            self.bible_background_combobox.currentIndex(), Qt.ItemDataRole.UserRole
        )
        self.gui.main.settings['logo_image'] = self.logo_background_combobox.itemData(
            self.logo_background_combobox.currentIndex(), Qt.ItemDataRole.UserRole
        )
        self.gui.main.settings['ccli_num'] = self.ccli_line_edit.text()
        self.gui.main.settings['stage_font_size'] = self.stage_font_spinbox.value()

        self.gui.main.save_settings()
        self.gui.apply_settings()
        self.done(0)

    def cancel(self):
        self.done(0)
        self.gui.main.app.processEvents()
