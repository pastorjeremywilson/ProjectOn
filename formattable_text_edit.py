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
        self.text_edit.selectionChanged.connect(self.set_style_buttons)
        layout.addWidget(self.text_edit)

    def set_bold(self):
        """
        Method to set/unset and merge the current selection or cursor's charFormat to bold.
        """
        cursor = self.text_edit.textCursor()
        char_format = self.get_char_format(cursor)

        if char_format.fontWeight() == QFont.Weight.Bold:
            char_format.setFontWeight(QFont.Weight.Normal)
            cursor.setCharFormat(QTextCharFormat(char_format))
        else:
            char_format.setFontWeight(QFont.Weight.Bold)
            cursor.setCharFormat(QTextCharFormat(char_format))

    def set_italic(self):
        """
        Method to set/unset and merge the current selection or cursor's charFormat to italic.
        """
        cursor = self.text_edit.textCursor()
        char_format = self.get_char_format(cursor)

        if not char_format.fontItalic():
            char_format.setFontItalic(True)
            cursor.setCharFormat(QTextCharFormat(char_format))
        else:
            char_format.setFontItalic(False)
            cursor.setCharFormat(QTextCharFormat(char_format))

    def set_underline(self):
        """
        Method to set/unset and merge the current selection or cursor's charFormat to italic.
        """
        cursor = self.text_edit.textCursor()
        char_format = self.get_char_format(cursor)

        if not char_format.fontUnderline():
            char_format.setFontUnderline(True)
            cursor.setCharFormat(QTextCharFormat(char_format))
        else:
            char_format.setFontUnderline(False)
            cursor.setCharFormat(QTextCharFormat(char_format))
            
    def set_style_buttons(self):
        """
        Method to change the state of the QPushButtons based on the character formatting of the current cursor position.
        """
        cursor = self.text_edit.textCursor()
        self.cursor_position = cursor.position()

        char_format = self.get_char_format(cursor)

        if char_format.fontWeight() == QFont.Weight.Normal:
            self.bold_button.setChecked(False)
        else:
            self.bold_button.setChecked(True)

        if char_format.fontItalic():
            self.italic_button.setChecked(True)
        else:
            self.italic_button.setChecked(False)

        if char_format.fontUnderline():
            self.underline_button.setChecked(True)
        else:
            self.underline_button.setChecked(False)

    def get_char_format(self, cursor):
        if cursor.hasSelection():
            # move the cursor one character to the right or left in case the selection encloses the beginning of a tag
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
            char_format = QTextCharFormat(cursor.charFormat())
            cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter, QTextCursor.MoveMode.KeepAnchor)
        else:
            char_format = QTextCharFormat(cursor.charFormat())

        return char_format

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
                    cursor = self.textCursor()
                    position = cursor.position()
                    self.setHtml(parent.renumber_tags('all', self.toHtml()))
                    cursor.setPosition(position)
                    self.setTextCursor(cursor)
                    parent.populate_tag_list()
                    break
                else:
                    parent = parent.parent()
        elif ((evt.key() == Qt.Key.Key_Delete or evt.key() == Qt.Key.Key_Backspace)
              and self.parent().parent().objectName() == 'lyrics_widget'):
            parent = self.parent()
            while parent.parent():
                if parent.objectName() == 'edit_widget':
                    cursor = self.textCursor()
                    position = cursor.position()
                    self.setHtml(parent.renumber_tags('all', self.toHtml()))
                    cursor.setPosition(position)
                    self.setTextCursor(cursor)
                    if parent.type == 'song':
                        parent.populate_tag_list()
                    break
                else:
                    parent = parent.parent()
            