import os
import re
from asyncio import wait_for
from os.path import exists

from PyQt6 import QtCore
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QLabel, QHBoxLayout, QPushButton, QWidget, QLineEdit, QVBoxLayout, QSizePolicy, \
    QMessageBox, QDialog
from cryptography.fernet import Fernet

from simple_splash import SimpleSplash


class SongselectImport(QDialog):
    BASE_URL = 'https://songselect.ccli.com'
    LOGIN_PAGE = ('https://profile.ccli.com/Account/Signin?'
                  'appContext=SongSelect&returnUrl=https%3A%2F%2Fsongselect.ccli.com%2F')
    LOGIN_URL = 'https://profile.ccli.com'
    LOGOUT_URL = BASE_URL + '/account/logout'
    SEARCH_URL = BASE_URL + '/search/results'
    SONG_PAGE = BASE_URL + '/Songs/'

    def __init__(self, gui, suppress_browser=False):
        super().__init__()
        self.gui = gui

        if not suppress_browser:
            self.init_components()
            self.show()

    def init_components(self):
        primary_screen_width = self.gui.primary_screen.size().width()
        primary_screen_height = self.gui.primary_screen.size().height()
        width = int(primary_screen_width * 2 / 3)
        height = int(primary_screen_height * 2 / 3)
        x = int(width / 2)
        y = int(height / 2)

        self.setParent(self.gui.main_window)
        self.setWindowTitle('SongSelect Import')
        self.setWindowFlag(Qt.WindowType.Window)
        self.setGeometry(x, y, width, height)

        import_layout = QVBoxLayout(self)

        title_label = QLabel('CCLI Songselect Import')
        title_label.setFont(QFont('Helvetica', 16, QFont.Weight.Bold))
        import_layout.addWidget(title_label)

        instruction_label = QLabel('Click "Download" in the Lyrics tab to import the song.')
        instruction_label.setFont(self.gui.standard_font)
        import_layout.addWidget(instruction_label)

        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)
        import_layout.addWidget(nav_widget)

        self.back_button = QPushButton(self)
        self.back_button.setIcon(QIcon('resources/gui_icons/browser_back.svg'))
        nav_layout.addWidget(self.back_button)

        self.url_bar = QLineEdit(self)
        nav_layout.addWidget(self.url_bar)

        self.web_engine_view = QWebEngineView()
        self.web_engine_view.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        CHROME_USER_AGENT = ('Mozilla/5.0 ({os_info}) AppleWebKit/537.36 '
                             '(KHTML, like Gecko) Chrome/{version} Safari/537.36')
        chrome_version = '117.0.5938.48'
        user_agent = CHROME_USER_AGENT.format(os_info='Windows NT 10.0; Win64; x64', version=chrome_version)
        self.web_engine_view.page().profile().setHttpUserAgent(user_agent)
        self.web_engine_view.page().loadFinished.connect(self.page_loaded)
        self.web_engine_view.page().profile().downloadRequested.connect(self.download_requested)
        self.web_engine_view.urlChanged.connect(self.update_url)
        self.web_engine_view.setUrl(QUrl(self.LOGIN_PAGE))
        import_layout.addWidget(self.web_engine_view)

    def get_page_type(self):
        """
        Get the type of page the user is currently ono

        :return: The page the user is on
        """

        current_url_host = self.web_engine_view.page().url().host()
        current_url_path = self.web_engine_view.page().url().path()
        if current_url_host == QtCore.QUrl(self.LOGIN_URL).host() and current_url_path == QtCore.QUrl(self.LOGIN_PAGE).path():
            return 0
        elif current_url_host == QtCore.QUrl(self.BASE_URL).host():
            if current_url_path == '/' or current_url_path == '':
                return 1
            elif current_url_path == QtCore.QUrl(self.SEARCH_URL).path():
                return 2
            elif self.get_song_number_from_url(current_url_path) is not None:
                return 3
        return 4

    def page_loaded(self, successful):
        self.song = None
        page_type = self.get_page_type()
        if page_type == 0:
            self.signin_page_loaded()
        else:
            self.back_button.setEnabled(True)

    def store_credentials(self):
        dialog = QDialog()
        dialog.setObjectName('ccli_credentials_dialog')
        dialog_layout = QVBoxLayout(dialog)
        dialog.setWindowTitle('CCLI Credentials')

        label = QLabel('Store your login info for CCLI SongSelect?')
        label.setFont(self.gui.standard_font)
        dialog_layout.addWidget(label)
        dialog_layout.addSpacing(20)

        ok_button = QPushButton('OK')
        password_line_edit = QLineEdit()

        user_label = QLabel('User Name (Email Address):')
        user_label.setFont(QFont('Helvetica', 10))
        dialog_layout.addWidget(user_label)

        user_line_edit = QLineEdit()
        user_line_edit.setFont(self.gui.standard_font)
        user_line_edit.textEdited.connect(lambda: self.enable_ok(user_line_edit, password_line_edit, ok_button))
        user_line_edit.textChanged.connect(lambda: self.enable_ok(user_line_edit, password_line_edit, ok_button))
        dialog_layout.addWidget(user_line_edit)
        dialog_layout.addSpacing(10)
        user_line_edit.setFocus()

        password_label = QLabel('Password:')
        password_label.setFont(QFont('Helvetica', 10))
        dialog_layout.addWidget(password_label)

        password_line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        password_line_edit.setFont(self.gui.standard_font)
        password_line_edit.textEdited.connect(lambda: self.enable_ok(user_line_edit, password_line_edit, ok_button))
        password_line_edit.textChanged.connect(lambda: self.enable_ok(user_line_edit, password_line_edit, ok_button))
        dialog_layout.addWidget(password_line_edit)
        dialog_layout.addSpacing(20)

        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        dialog_layout.addWidget(button_widget)

        ok_button.setFont(self.gui.standard_font)
        ok_button.clicked.connect(lambda: dialog.done(1))
        ok_button.setEnabled(False)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addSpacing(20)

        cancel_button = QPushButton('Cancel')
        cancel_button.setFont(self.gui.standard_font)
        cancel_button.clicked.connect(lambda: dialog.done(-1))
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()

        result = dialog.exec()
        if result == 1:
            user_name = user_line_edit.text()
            password = password_line_edit.text()

            key = Fernet.generate_key()
            ref_key = Fernet(key)
            enc_user = ref_key.encrypt(user_name.encode('utf-8'))
            enc_pass = ref_key.encrypt(password.encode('utf-8'))

            with open(self.gui.main.data_dir + '/ccli_data.dat', 'w') as file:
                file.writelines([key.decode('utf-8') + '\n', enc_user.decode('utf-8') + '\n', enc_pass.decode('utf-8')])

            QMessageBox.information(
                self.gui.main_window,
                'Credentials Saved',
                'CCLI SongSelect credentials have been encrypted and saved.',
                QMessageBox.StandardButton.Ok
            )

            return user_name, password
        else:
            return -1, -1

    def enable_ok(self, user_line_edit, password_line_edit, ok_button):
        if len(user_line_edit.text()) > 0 and len(password_line_edit.text()) > 0:
            ok_button.setEnabled(True)

    def signin_page_loaded(self):
        if exists(self.gui.main.data_dir + '/ccli_data.dat'):
            with open(self.gui.main.data_dir + '/ccli_data.dat', 'r') as file:
                lines = file.readlines()
            key = lines[0]
            enc_user = lines[1]
            enc_pass = lines[2]

            ref_key = Fernet(key)
            user_name = ref_key.decrypt(enc_user).decode('utf-8')
            password = ref_key.decrypt(enc_pass).decode('utf-8')
        else:
            user_name, password = self.store_credentials()

        if not user_name == -1:
            script_set_login_fields = ('document.getElementById("EmailAddress").value = "{user_name}";'
                                       'document.getElementById("Password").value = "{password}";'
                                       'document.getElementById("sign-in").click();'
                                       ).format(user_name=user_name, password=password)
            self._run_javascript(script_set_login_fields)

    def _run_javascript(self, script):
        """
        Run a script and returns the result

        :param script: The javascript to be run
        :return: The evaluated result
        """
        self.web_stuff = ""
        self.got_web_stuff = False

        def handle_result(result):
            """
            Handle the result from the asynchronous call
            """
            self.got_web_stuff = True
            self.web_stuff = result
        self.web_engine_view.page().runJavaScript(script, handle_result)
        wait_for(lambda: self.got_web_stuff, 5.0)
        return self.web_stuff

    def get_song_number_from_url(self, url):
        """
        Gets the ccli song number for a song from the url

        :return: String containing ccli song number, None is returned if not found
        """
        ccli_number_regex = re.compile(r'.*?Songs\/([0-9]+).*', re.IGNORECASE)
        regex_matches = ccli_number_regex.match(url)
        if regex_matches:
            return regex_matches.group(1)
        return None

    def update_url(self, new_url):
        self.url_bar.setText(new_url.toString())

    def download_requested(self, download_item):
        download_dir = os.path.expanduser('~/AppData/Roaming/ProjectOn')
        if not exists(download_dir):
            os.mkdir(download_dir)
        ccli_number = self.get_song_number_from_url(self.url_bar.text())

        # only import from txt is supported
        if download_item.suggestedFileName().endswith('.txt'):
            self.web_engine_view.setEnabled(False)
            download_item.setDownloadDirectory(download_dir)
            download_item.accept()
            self.current_download_item = download_item
            self.current_download_item.finished.connect(self.download_finished)
        else:
            download_item.cancel()
            QMessageBox.information(
                self.gui.main_window,
                'SongsPlugin.SongSelectForm',
                'Unsupported format',
                'OpenLP can only import simple lyrics or ChordPro'
            )

    def download_finished(self):
        """
        Callback for when download has finished. Parses the downloaded file into song data to be saved to the database.
        """
        if self.current_download_item:
            if self.current_download_item.isFinished():
                song_title = ''
                author = ''
                copyright = ''
                song_number = ''

                song_filename = os.path.join(self.current_download_item.downloadDirectory(),
                                             self.current_download_item.downloadFileName())
                with open(song_filename, 'r', encoding='utf-8') as file:
                    song_text = file.read()

                song_text = re.sub('<br.*?>', '', song_text)

                paragraphs = song_text.split('\n\n')
                song_title = paragraphs[0].strip()

                copyright_info = paragraphs[-1]
                copyright_lines = copyright_info.split('\n')
                author = copyright_lines[0].strip()
                copyright = copyright_lines[2]
                song_number = copyright_lines[1].split('#')[-1]

                song_text = '\n\n'.join(paragraphs[1:-1])

                song_text_split = song_text.split('\n')
                segment_markers = [
                    'intro',
                    'verse',
                    'pre-chorus',
                    'chorus',
                    'bridge',
                    'tag',
                    'ending'
                ]
                segment_marker_indices = []
                for i in range(len(song_text_split)):
                    for marker in segment_markers:
                        if marker in song_text_split[i].lower() and len(song_text_split[i]) < len(marker) + 3:
                            segment_marker_indices.append(i)
                            break

                index = 0
                formatted_song_text = ''
                order = []
                while index < len(song_text_split):
                    if index in segment_marker_indices:
                        marker = song_text_split[index].strip()
                        formatted_marker = f'[{marker}]\n'
                        marker_split = marker.split(' ')
                        if len(marker_split) < 2:
                            marker_split.append('1')
                            formatted_marker = f'[{marker} 1]\n'
                        formatted_song_text += formatted_marker
                        marker_split[0] = marker_split[0].lower().strip()[0]
                        marker = ''.join(marker_split)
                        order.append(marker)
                    else:
                        formatted_song_text += song_text_split[index] + '\n'
                    index += 1
                order = ' '.join(order)

                song_data = [
                    song_title,
                    author,
                    copyright,
                    song_number,
                    formatted_song_text,
                    order,
                    'true',
                    'global',
                    'global',
                    'global_song',
                    'global',
                    'False',
                    0,
                    0,
                    'False',
                    0,
                    0,
                    'False',
                    'False',
                    100,
                    100
                ]

                if song_title in self.gui.main.get_song_titles():
                    dialog = QDialog(self.gui.main_window)
                    dialog.setLayout(QVBoxLayout())
                    dialog.setWindowTitle('Song Title Exists')

                    label = QLabel('Unable to save song because this title already exists\n'
                                   'in the database. Please provide a different title:')
                    label.setFont(self.gui.standard_font)
                    dialog.layout().addWidget(label)

                    line_edit = QLineEdit(song_title + '(1)', dialog)
                    line_edit.setFont(self.gui.standard_font)
                    dialog.layout().addWidget(line_edit)

                    button_widget = QWidget()
                    button_widget.setLayout(QHBoxLayout())
                    dialog.layout().addWidget(button_widget)

                    ok_button = QPushButton('OK')
                    ok_button.setFont(self.gui.standard_font)
                    ok_button.clicked.connect(lambda: dialog.done(1))
                    button_widget.layout().addStretch()
                    button_widget.layout().addWidget(ok_button)
                    button_widget.layout().addStretch()

                    cancel_button = QPushButton('Cancel')
                    cancel_button.setFont(self.gui.standard_font)
                    cancel_button.clicked.connect(lambda: dialog.done(-1))
                    button_widget.layout().addWidget(cancel_button)
                    button_widget.layout().addStretch()

                    result = dialog.exec()

                    if result == 1:
                        song_data[0] = line_edit.text()
                    else:
                        return

                save_widget = SimpleSplash(self.gui, 'Saving...')

                self.gui.main.save_song(song_data)
                self.gui.media_widget.populate_song_list()

                self.gui.media_widget.song_list.setCurrentItem(
                    self.gui.media_widget.song_list.findItems(song_title, Qt.MatchFlag.MatchExactly)[0])

                save_widget.widget.deleteLater()
                os.remove(song_filename)
                self.done(0)
