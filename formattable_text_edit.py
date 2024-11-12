from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor, QFont, QTextCharFormat, QIcon, QKeyEvent
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit


class FormattableTextEdit(QWidget):
    """
    Provides a QTextEdit whose text is changeable using Bold, Italic, and Underline QPushButtons.
    """
    text_edit = None

    def __init__(self, gui):
        """
        Provides a QTextEdit whose text is changeable using Bold, Italic, and Underline QPushButtons.
        :param gui.GUI gui: The current instance of GUI
        """
        self.gui = gui
        super().__init__()
        self.cursor_position = None
        layout = QVBoxLayout()
        self.setLayout(layout)

        button_widget = QWidget()
        button_layout = QHBoxLayout()
        button_widget.setLayout(button_layout)

        self.bold_button = QPushButton()
        self.bold_button.setIcon(QIcon('resources/gui_icons/boldIcon.png'))
        self.bold_button.setCheckable(True)
        self.bold_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.bold_button.clicked.connect(self.set_bold)
        button_layout.addWidget(self.bold_button)

        self.italic_button = QPushButton()
        self.italic_button.setIcon(QIcon('resources/gui_icons/italicIcon.png'))
        self.italic_button.setCheckable(True)
        self.italic_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.italic_button.clicked.connect(self.set_italic)
        button_layout.addWidget(self.italic_button)

        self.underline_button = QPushButton()
        self.underline_button.setIcon(QIcon('resources/gui_icons/underlineIcon.png'))
        self.underline_button.setCheckable(True)
        self.underline_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.underline_button.clicked.connect(self.set_underline)
        button_layout.addWidget(self.underline_button)
        button_layout.addStretch()

        layout.addWidget(button_widget)

        self.text_edit = CustomTextEdit()
        self.text_edit.setFont(self.gui.standard_font)
        self.text_edit.cursorPositionChanged.connect(self.set_style_buttons)
        layout.addWidget(self.text_edit)

    def set_bold(self):
        """
        Method to set/unset and merge the current selection or cursor's charFormat to bold.
        """
        cursor = self.text_edit.textCursor()
        current_position = cursor.position()
        if cursor.hasSelection():
            selection_start = cursor.selectionStart()
            selection_end = cursor.selectionEnd()
            cursor.setPosition(selection_start, QTextCursor.MoveMode.MoveAnchor)
            cursor.setPosition(selection_end, QTextCursor.MoveMode.KeepAnchor)
            char_format = cursor.charFormat()
            if char_format.font().bold():
                char_format.setFontWeight(QFont.Weight.Normal)
                cursor.mergeCharFormat(char_format)
            else:
                char_format.setFontWeight(QFont.Weight.Bold)
                cursor.mergeCharFormat(char_format)
        else:
            font = cursor.charFormat().font()
            if font.weight() == QFont.Weight.Normal:
                font.setWeight(QFont.Weight.Bold)
                self.text_edit.setCurrentFont(font)
            else:
                font.setWeight(QFont.Weight.Normal)
                self.text_edit.setCurrentFont(font)

        self.text_edit.setFocus()
        self.text_edit.textCursor().setPosition(current_position)

    def set_italic(self):
        """
        Method to set/unset and merge the current selection or cursor's charFormat to italic.
        """
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            font = QTextCharFormat(cursor.charFormat())
            if not font.fontItalic():
                font.setFontItalic(True)
                cursor.setCharFormat(QTextCharFormat(font))
            else:
                font.setFontItalic(False)
                cursor.mergeCharFormat(QTextCharFormat(font))
        else:
            font = cursor.charFormat().font()
            if not font.italic():
                font.setItalic(True)
                self.text_edit.setCurrentFont(font)
            else:
                font.setItalic(False)
                self.text_edit.setCurrentFont(font)

        self.text_edit.setFocus()
        self.text_edit.textCursor().setPosition(self.cursor_position)

    def set_underline(self):
        """
        Method to set/unset and merge the current selection or cursor's charFormat to italic.
        """
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            font = QTextCharFormat(cursor.charFormat())
            if not font.fontUnderline():
                font.setFontUnderline(True)
                cursor.setCharFormat(QTextCharFormat(font))
            else:
                font.setFontUnderline(False)
                cursor.mergeCharFormat(QTextCharFormat(font))
        else:
            font = cursor.charFormat().font()
            if not font.underline():
                font.setUnderline(True)
                self.text_edit.setCurrentFont(font)
            else:
                font.setUnderline(False)
                self.text_edit.setCurrentFont(font)

        self.text_edit.setFocus()
        if self.cursor_position:
            self.text_edit.textCursor().setPosition(self.cursor_position)
            
    def set_style_buttons(self):
        """
        Method to change the state of the QPushButtons based on the character formatting of the current cursor position.
        """
        cursor = self.text_edit.textCursor()
        self.cursor_position = cursor.position()

        font = cursor.charFormat().font()

        if font.weight() == QFont.Weight.Normal:
            self.bold_button.setChecked(False)
        else:
            self.bold_button.setChecked(True)

        if font.italic():
            self.italic_button.setChecked(True)
        else:
            self.italic_button.setChecked(False)

        if font.underline():
            self.underline_button.setChecked(True)
        else:
            self.underline_button.setChecked(False)

    def keyPressEvent(self, event: QKeyEvent):
        """
        Override keyPressEvent to provide the standard CTRL-B, CTRL-I, and CTRL-U for changing formatting.
        :param QKeyEvent event: keyPressEvent
        """
        if event.key() == Qt.Key.Key_B and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.set_bold()
            self.bold_button.blockSignals(True)
            if self.bold_button.isChecked():
                self.bold_button.setChecked(False)
            else:
                self.bold_button.setChecked(True)
            self.bold_button.blockSignals(False)
        elif event.key() == Qt.Key.Key_I and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.set_italic()
            self.italic_button.blockSignals(True)
            if self.italic_button.isChecked():
                self.italic_button.setChecked(False)
            else:
                self.italic_button.setChecked(True)
            self.italic_button.blockSignals(False)
        elif event.key() == Qt.Key.Key_U and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.set_underline()
            self.underline_button.blockSignals(True)
            if self.underline_button.isChecked():
                self.underline_button.setChecked(False)
            else:
                self.underline_button.setChecked(True)
            self.underline_button.blockSignals(False)
        event.accept()


class CustomTextEdit(QTextEdit):
    """
    Provides a QTextEdit that can differentiate between plain text or mime data when inserting.
    """
    def __init__(self):
        super().__init__()

    def insertFromMimeData(self, mime_data):
        # Ensure it is text.
        if (mime_data.hasText()):
            text = mime_data.text()
            self.insertPlainText(text)
        # In case not text.
        else:
            QTextEdit.insertFromMimeData(self, mime_data)
            
    def keyPressEvent(self, evt):
        """
        Override keyPressEvent to provide listeners for certain keystrokes that may indicate that the tag list
        needs to be updated
        """
        super().keyPressEvent(evt)
        if evt.key() == Qt.Key.Key_BracketRight and self.parent().parent().objectName() == 'lyrics_widget':
            parent = self.parent()
            while parent.parent():
                if parent.objectName() == 'edit_widget':
                    parent.populate_tag_list()
                    break
                else:
                    parent = parent.parent()
        elif ((evt.key() == Qt.Key.Key_Delete or evt.key() == Qt.Key.Key_Backspace)
              and self.parent().parent().objectName() == 'lyrics_widget'):
            parent = self.parent()
            while parent.parent():
                if parent.objectName() == 'edit_widget':
                    parent.populate_tag_list()
                    break
                else:
                    parent = parent.parent()
            