import os.path

from PyQt5.QtCore import Qt, QRectF, QPointF, QEvent
from PyQt5.QtGui import QPainter, QPixmap, QPen, QBrush, QColor, QFont, QPainterPath, QPalette
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QRadioButton, QButtonGroup, QVBoxLayout, QSpinBox, \
    QScrollArea, QHBoxLayout, QPushButton, QColorDialog, QFileDialog, QMessageBox, QDialog, QLineEdit, \
    QSizePolicy

from simple_splash import SimpleSplash
from widgets import FontWidget


class SettingsWidget(QWidget):
    wait_widget = None

    def __init__(self, gui):
        super().__init__()
        self.accept_font_changes = False
        self.setObjectName('settings_widget')
        self.gui = gui
        self.min_width = 1000

        self.show_wait_widget()
        self.init_components()
        self.gui.main.app.processEvents()

        self.wait_widget.subtitle_label.setText('Applying Settings')
        self.apply_settings()

        self.show()

        self.accept_font_changes = True
        self.wait_widget.subtitle_label.setText('Creating Font Sample')
        self.change_font_sample()
        self.gui.main.app.processEvents()
        self.wait_widget.widget.deleteLater()

    def show_wait_widget(self):
        self.wait_widget = SimpleSplash(self.gui, 'Please wait...', subtitle=True)

    def init_components(self):
        self.setParent(self.gui.main_window)
        self.setWindowTitle('Settings')
        self.setWindowFlag(Qt.WindowType.Window)
        self.setMinimumSize(self.min_width + 60, 800)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.settings_container = QWidget()
        self.settings_container.setObjectName('settings_container')
        settings_container_layout = QVBoxLayout()
        self.settings_container.setLayout(settings_container_layout)

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
        settings_scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        settings_scroll_area.setWidget(self.settings_container)
        layout.addWidget(settings_scroll_area)

        button_widget = QWidget()
        button_layout = QHBoxLayout()
        button_widget.setLayout(button_layout)
        layout.addWidget(button_widget)

        save_button = QPushButton('Save')
        save_button.setFont(self.gui.standard_font)
        save_button.pressed.connect(self.save)
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addSpacing(20)

        cancel_button = QPushButton('Cancel')
        cancel_button.setFont(self.gui.standard_font)
        cancel_button.pressed.connect(self.cancel)
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()

    def change_font_sample(self):
        if self.accept_font_changes:
            self.font_sample.setFont(
                QFont(
                    self.font_settings_widget.font_list_widget.currentItem().data(20),
                    self.font_settings_widget.font_size_spinbox.value(),
                    QFont.Weight.Bold))

            color = self.font_settings_widget.font_color_button_group.checkedButton().objectName()
            if color == 'black':
                self.font_sample.fill_color = QColor(0, 0, 0)
            elif color == 'white':
                self.font_sample.fill_color = QColor(255, 255, 255)
            else:
                fill_color_split = self.font_settings_widget.custom_font_color_radio_button.objectName().split(', ')
                self.font_sample.fill_color = QColor(
                    int(fill_color_split[0]), int(fill_color_split[1]), int(fill_color_split[2]))

            if self.font_settings_widget.shadow_checkbox.isChecked():
                self.font_sample.use_shadow = True
            else:
                self.font_sample.use_shadow = False

            if self.font_settings_widget.outline_checkbox.isChecked():
                self.font_sample.use_outline = True
            else:
                self.font_sample.use_outline = False

            shadow_color = self.font_settings_widget.shadow_color_slider.color_slider.value()
            self.font_sample.shadow_color = QColor(shadow_color, shadow_color, shadow_color)
            self.font_sample.shadow_offset = self.font_settings_widget.shadow_offset_slider.offset_slider.value()

            outline_color = self.font_settings_widget.outline_color_slider.color_slider.value()
            self.font_sample.outline_color = QColor(outline_color, outline_color, outline_color)
            self.font_sample.outline_width = self.font_settings_widget.outline_width_slider.offset_slider.value()

            self.font_sample.paint_font()

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
        widget.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
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

        self.font_sample = FontSample(self)
        self.font_sample.setText('Sample')
        self.font_sample.setObjectName('font_sample')
        font_layout.addWidget(self.font_sample)

        self.font_settings_widget = FontWidget(self.gui, draw_border=False, auto_update=False)
        font_layout.addWidget(self.font_settings_widget)
        self.font_settings_widget.font_list_widget.currentRowChanged.connect(self.change_font_sample)
        self.font_settings_widget.font_size_spinbox.valueChanged.connect(self.change_font_sample)
        self.font_settings_widget.font_color_button_group.buttonClicked.connect(self.change_font_sample)
        self.font_settings_widget.shadow_checkbox.stateChanged.connect(self.change_font_sample)
        self.font_settings_widget.shadow_color_slider.color_slider.valueChanged.connect(self.change_font_sample)
        self.font_settings_widget.shadow_offset_slider.offset_slider.valueChanged.connect(self.change_font_sample)
        self.font_settings_widget.outline_checkbox.stateChanged.connect(self.change_font_sample)
        self.font_settings_widget.outline_color_slider.color_slider.valueChanged.connect(self.change_font_sample)
        self.font_settings_widget.outline_width_slider.offset_slider.valueChanged.connect(self.change_font_sample)

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

        return widget

    def background_settings(self):
        from widgets import ImageCombobox

        widget = QWidget()
        widget.setMinimumWidth(self.min_width)
        widget.setObjectName('background_widget')
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

        add_song_button = QPushButton('Import a Background')
        add_song_button.setFont(self.gui.standard_font)
        add_song_button.pressed.connect(self.gui.tool_bar.import_background)
        song_background_layout.addWidget(add_song_button)
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

        logo_background_button = QPushButton('Add an Image')
        logo_background_button.setFont(self.gui.standard_font)
        logo_background_button.pressed.connect(self.gui.media_widget.add_image)
        logo_background_layout.addWidget(logo_background_button)
        logo_background_layout.addStretch()

        delete_widget = QWidget()
        delete_layout = QHBoxLayout()
        delete_widget.setLayout(delete_layout)
        layout.addWidget(delete_widget)

        delete_background_button = QPushButton('Delete a Background')
        delete_background_button.setFont(self.gui.standard_font)
        delete_background_button.pressed.connect(self.delete_background)
        delete_layout.addWidget(delete_background_button)
        delete_layout.addSpacing(20)

        delete_image_button = QPushButton('Delete an Image')
        delete_image_button.setFont(self.gui.standard_font)
        delete_image_button.pressed.connect(self.gui.media_widget.delete_image)
        delete_layout.addWidget(delete_image_button)
        delete_layout.addStretch()

        spacing_widget = QWidget()
        spacing_widget.setFixedHeight(20)
        layout.addWidget(spacing_widget)

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

    def delete_background(self):
        dialog = QDialog()
        layout = QVBoxLayout()
        dialog.setLayout(layout)

        label = QLabel('Choose a background to remove:')
        label.setFont(self.gui.standard_font)
        layout.addWidget(label)

        from widgets import ImageCombobox
        combobox = ImageCombobox(self.gui, 'background')
        combobox.removeItem(1)
        combobox.removeItem(0)
        layout.addWidget(combobox)

        button_widget = QWidget()
        button_layout = QHBoxLayout()
        button_widget.setLayout(button_layout)
        layout.addWidget(button_widget)

        remove_button = QPushButton('Remove')
        remove_button.setFont(self.gui.standard_font)
        remove_button.pressed.connect(lambda: dialog.done(0))
        button_layout.addWidget(remove_button)

        cancel_button = QPushButton('Cancel')
        cancel_button.setFont(self.gui.standard_font)
        cancel_button.pressed.connect(lambda: dialog.done(1))
        button_layout.addWidget(cancel_button)

        response = dialog.exec()

        if response == 0:
            file_name = combobox.currentData(Qt.ItemDataRole.UserRole)
            try:
                os.remove(self.gui.main.background_dir + '/' + file_name)
            except FileNotFoundError:
                QMessageBox.information(
                    self.gui.main_window, 'Not Found', 'File not found. Reindexing images.', QMessageBox.StandardButton.Ok)

            from main import IndexImages
            ii = IndexImages(self.gui.main, 'backgrounds')
            self.gui.main.thread_pool.start(ii)
            self.gui.main.thread_pool.waitForDone()

            self.song_background_combobox.refresh()
            self.bible_background_combobox.refresh()
            self.gui.tool_bar.song_background_combobox.refresh()
            self.gui.tool_bar.bible_background_combobox.refresh()

            self.song_background_combobox.setCurrentText(self.gui.main.settings['global_song_background'])
            self.bible_background_combobox.setCurrentText(self.gui.main.settings['global_bible_background'])
            self.gui.tool_bar.song_background_combobox.setCurrentText(self.gui.main.settings['global_song_background'])
            self.gui.tool_bar.bible_background_combobox.setCurrentText(self.gui.main.settings['global_bible_background'])

            QMessageBox.information(
                self,
                'Background Removed',
                file_name + ' removed.',
                QMessageBox.StandardButton.Ok
            )

    def apply_settings(self):
        if self.gui.main.settings:
            try:
                if 'ccli_num' in self.gui.main.settings.keys():
                    self.ccli_line_edit.setText(self.gui.main.settings['ccli_num'])
                for button in self.screen_button_group.buttons():
                    if button.objectName() == self.gui.main.settings['selected_screen_name']:
                        button.setChecked(True)

                self.font_settings_widget.apply_settings()

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

    def sync_with_toolbar(self):
        self.gui.tool_bar.font_widget.blockSignals(True)
        self.gui.tool_bar.font_widget.font_list_widget.setCurrentRow(
            self.font_settings_widget.font_list_widget.currentRow())
        self.gui.tool_bar.font_widget.font_size_spinbox.setValue(self.font_settings_widget.font_size_spinbox.value())
        if self.font_settings_widget.font_color_button_group.checkedButton().objectName() == 'white':
            self.gui.tool_bar.font_widget.white_radio_button.setChecked(True)
        elif self.font_settings_widget.font_color_button_group.checkedButton().objectName() == 'black':
            self.gui.tool_bar.font_widget.black_radio_button.setChecked(True)
        else:
            self.gui.tool_bar.font_widget.custom_font_color_radio_button.setChecked(True)
            self.gui.tool_bar.font_widget.custom_font_color_radio_button.setObjectName(
                self.font_settings_widget.custom_font_color_radio_button.objectName()
            )
        self.gui.tool_bar.font_widget.shadow_checkbox.setChecked(self.font_settings_widget.shadow_checkbox.isChecked())
        self.gui.tool_bar.font_widget.shadow_color_slider.color_slider.setValue(
            self.font_settings_widget.shadow_color_slider.color_slider.value())
        self.gui.tool_bar.font_widget.shadow_offset_slider.offset_slider.setValue(
            self.font_settings_widget.shadow_offset_slider.value())
        self.gui.tool_bar.font_widget.outline_checkbox.setChecked(self.font_settings_widget.outline_checkbox.isChecked())
        self.gui.tool_bar.font_widget.outline_color_slider.color_slider.setValue(
            self.font_settings_widget.outline_color_slider.color_slider.value()
        )
        self.gui.tool_bar.font_widget.outline_width_slider.setValue(
            self.font_settings_widget.outline_width_slider.value()
        )

    def save(self):
        self.gui.main.settings['selected_screen_name'] = self.screen_button_group.checkedButton().objectName()
        self.gui.main.settings['font_face'] = self.font_settings_widget.font_list_widget.currentItem().data(20)
        self.gui.main.settings['font_size'] = self.font_settings_widget.font_size_spinbox.value()
        self.gui.main.settings['font_color'] = (
            self.font_settings_widget.font_color_button_group.checkedButton().objectName())
        self.gui.main.settings['use_shadow'] = self.font_settings_widget.shadow_checkbox.isChecked()
        self.gui.main.settings['shadow_color'] = self.font_settings_widget.shadow_color_slider.color_slider.value()
        self.gui.main.settings['shadow_offset'] = self.font_settings_widget.shadow_offset_slider.offset_slider.value()
        self.gui.main.settings['use_outline'] = self.font_settings_widget.outline_checkbox.isChecked()
        self.gui.main.settings['outline_color'] = self.font_settings_widget.outline_color_slider.color_slider.value()
        self.gui.main.settings['outline_width'] = self.font_settings_widget.outline_width_slider.offset_slider.value()
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

        screen_name = self.screen_button_group.checkedButton().objectName()
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

        self.gui.main.save_settings()
        self.gui.apply_settings()
        self.gui.tool_bar.font_widget.apply_settings()
        self.deleteLater()
        self.gui.main.app.processEvents()

    def cancel(self):
        self.deleteLater()
        self.gui.main.app.processEvents()


class FontSample(QLabel):
    def __init__(self, settings_widget,
                 use_outline=True,
                 outline_color=QColor(0, 0, 0),
                 outline_width=8,
                 fill_color=QColor(255, 255, 255),
                 use_shadow=True,
                 shadow_color=QColor(0, 0, 0),
                 shadow_offset=5):
        super().__init__()
        self.settings_widget = settings_widget
        self.use_outline = use_outline
        self.outline_color = outline_color
        self.outline_width = outline_width
        self.fill_color = fill_color
        self.use_shadow = use_shadow
        self.shadow_color = shadow_color
        self.shadow_offset = shadow_offset

    def paintEvent(self, evt):
        self.paint_font()

    def paint_font(self):
        path = QPainterPath()
        shadow_path = QPainterPath()
        metrics = self.fontMetrics()

        y = metrics.ascent() - metrics.descent() + 10
        point = QPointF(0, y)
        shadow_point = QPointF(self.shadow_offset, y + self.shadow_offset)

        if self.use_shadow:
            shadow_path.addText(shadow_point, self.font(), self.text())
        path.addText(point, self.font(), self.text())

        brush = QBrush()
        brush.setColor(self.fill_color)
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        pen = QPen()
        pen.setColor(self.outline_color)
        pen.setWidth(self.outline_width)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(brush)
        painter.setPen(pen)

        if self.use_shadow:
            shadow_brush = QBrush()
            shadow_brush.setColor(self.shadow_color)
            shadow_brush.setStyle(Qt.BrushStyle.SolidPattern)
            painter.fillPath(shadow_path, shadow_brush)

        painter.fillPath(path, brush)
        if self.use_outline:
            painter.strokePath(path, pen)

        widget = self.settings_widget.findChild(QWidget, 'font_widget')
        widget.adjustSize()
        while widget.parent():
            widget = widget.parent()
            widget.update()
        self.settings_widget.settings_container.adjustSize()
