import re
import os

import logging
import engineio.async_drivers.threading
from http.server import BaseHTTPRequestHandler

from PyQt5.QtCore import Qt
from flask import Flask, render_template, request
from flask_socketio import SocketIO


class RemoteServer:
    app = None
    socketio = None

    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.html = None

    def start_server(self):
        try:
            self.app = Flask(
                __name__,
                template_folder=os.path.abspath('.') + '/resources',
                static_folder=os.path.abspath('.') + '/core/static'
            )
            self.socketio = SocketIO(self.app, async_mode='threading')
        except Exception:
            self.gui.main.error_log()

        @self.app.route('/', methods=['GET'])
        def root():
            return render_template('index.html')

        @self.app.route('/remote', methods=['GET', 'POST'])
        def remote():
            if self.gui.block_remote_input:
                oos, slides = self.get_all_gui_data()
                return render_template(
                    'web_remote.html',
                    oos=oos,
                    slides=slides
                )

            oos = ''
            slides = ''
            if request.method == "POST":
                if 'oos_title' in request.form:
                    try:
                        num = request.form.get('oos_title')
                        if num.isnumeric():
                            self.gui.live_from_remote_signal.emit(int(num))
                            return '', 200
                    except Exception:
                        self.gui.main.error_log()

                elif 'slide_title' in request.form:
                    try:
                        num = request.form.get("slide_title")
                        if num.isnumeric():
                            self.gui.live_slide_from_remote_signal.emit(int(num))
                            return '', 200
                    except Exception:
                        self.gui.main.error_log()

                elif b'black_screen' in request.data:
                    self.gui.display_black_screen_signal.emit()
                    return '', 200

                elif b'logo_screen' in request.data:
                    self.gui.display_logo_screen_signal.emit()

                    
                elif b'item_back' in request.data:
                    self.slide_button('item_back')
                
                elif b'slide_back' in request.data:
                    self.slide_button('slide_back')
                
                elif b'slide_forward' in request.data:
                    self.slide_button('slide_forward')
                
                elif b'item_forward' in request.data:
                    self.slide_button('item_forward')

            if request.method == "GET":
                oos, slides = self.get_all_gui_data()

            return render_template(
                'web_remote.html',
                oos=oos,
                slides=slides
            )

        @self.app.route('/mremote', methods=['GET', 'POST'])
        def mremote():
            if self.gui.block_remote_input:
                oos, slides = self.get_all_gui_data()
                return render_template(
                    'mobile_web_remote.html',
                    oos=oos,
                    slides=slides
                )

            oos = ''
            slides = ''
            if request.method == "POST":
                if 'oos_title' in request.form:
                    try:
                        num = request.form.get("oos_title")
                        self.gui.live_from_remote_signal.emit(int(num))
                    except Exception as ex:
                        self.gui.main.error_log()

                elif 'slide_title' in request.form:
                    try:
                        num = request.form.get("slide_title")
                        self.gui.live_slide_from_remote_signal.emit(int(num))
                    except Exception:
                        self.gui.main.error_log()

                elif b'black_screen' in request.data:
                    self.gui.display_black_screen_signal.emit()

                elif b'logo_screen' in request.data:
                    self.gui.display_logo_screen_signal.emit()

                elif b'item_back' in request.data:
                    self.slide_button('item_back')

                elif b'slide_back' in request.data:
                    self.slide_button('slide_back')

                elif b'slide_forward' in request.data:
                    self.slide_button('slide_forward')

                elif b'item_forward' in request.data:
                    self.slide_button('item_forward')

            if request.method == "GET":
                oos, slides = self.get_all_gui_data()

            return render_template(
                'mobile_web_remote.html',
                oos=oos,
                slides=slides
            )

        @self.app.route('/stage', methods=['POST', 'GET'])
        def stage(text=None):
            return render_template(
                'stage_view.html',
                text=text
            )

        @self.app.route('/shutdown', methods=['GET'])
        def shutdown():
            print('Shutting down the server via request is no '
                  'longer necessary as the server is running on a daemonized thread.')
            self.gui.main.error_log('Shutting down the server via request is no '
                  'longer necessary as the server is running on a daemonized thread.')

        try:
            self.socketio.run(
                self.app,
                host=self.gui.main.ip,
                port=self.gui.main.port,
                debug=False,
                use_reloader=False,
                allow_unsafe_werkzeug=True
            )
        except Exception:
            self.gui.main.error_log()

    def update_stage_text(self, stage_html, font_size, slide_info):
        with self.app.app_context():
            self.socketio.emit('update_stage', [stage_html, font_size, slide_info])

    def update_stage_image(self, jpg_bytes, slide_info):
        with self.app.app_context():
            self.socketio.emit('update_display', [jpg_bytes, slide_info])

    def get_all_gui_data(self):
        class_tag = ''

        remote_oos_buttons = ''
        current_row = self.gui.oos_widget.oos_list_widget.currentRow()
        for i in range(self.gui.oos_widget.oos_list_widget.count()):
            title = self.gui.oos_widget.oos_list_widget.item(i).data(Qt.ItemDataRole.UserRole)['title']

            if i == current_row:
                class_tag = 'class="current" '
            else:
                class_tag = ''

            remote_oos_buttons += f"""
                <button id="oos{str(i)}" {class_tag}type="button" name="oos_button" value="{str(i)}" onclick="oosClick(event)">
                    <span class="title">
                        {title}
                    </span>
                </button>
                <br />"""

        slide_buttons = ''
        current_row = self.gui.live_widget.slide_list.currentRow()

        for i in range(self.gui.live_widget.slide_list.count()):
            slide_data = self.gui.live_widget.slide_list.item(i).data(Qt.ItemDataRole.UserRole)
            if slide_data['type'] == 'video':
                title = slide_data['title']
                text = 'Video'
            else:
                title = slide_data['title']
                if 'parsed_text' in slide_data.keys() and type(slide_data['parsed_text']) == dict:
                    text = re.sub('<p.*?>', '', slide_data['parsed_text']['text'])
                elif 'parsed_text' in slide_data.keys():
                    text = re.sub('<p.*?>', '', slide_data['parsed_text'])
                else:
                    text = re.sub('<p.*?>', '', slide_data['text'])
                text = text.replace('</p>', '')

            if i == current_row:
                class_tag = 'class="current" '
            else:
                class_tag = ''

            slide_buttons += f"""
                <button id="slide{str(i)}" {class_tag}type="button" name="slide_button" value="{str(i)}" onClick="slideClick(event)">
                    <span class="title">{title}</span>
                    <br>
                    <span class="text">{text}</span>
                </button>
                <br>"""

        return remote_oos_buttons, slide_buttons
    
    def slide_button(self, button):
        self.gui.live_widget.web_button_signal.emit(button)
        return '', 200


class RemoteServerHandler(BaseHTTPRequestHandler):
    html = None

    def do_POST(self):
        try:
            referer = self.headers['Referer']
            self.wfile.write(bytes(referer.split('?')[1], 'utf-8'))
        except Exception:
            logging.exception('')

