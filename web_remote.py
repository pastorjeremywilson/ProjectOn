from gevent import monkey
import geventwebsocket
from engineio.async_drivers import gevent

monkey.patch_all()

import logging
from http.server import BaseHTTPRequestHandler
from flask import Flask, render_template, request

from PyQt6.QtCore import QRunnable
from flask_socketio import SocketIO


class RemoteServer(QRunnable):
    app = None
    socketio = None

    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.html = None

    def run(self):
        try:
            self.app = Flask(__name__, template_folder='resources')
            self.socketio = SocketIO(self.app, async_mode='gevent')
        except Exception:
            self.gui.main.error_log()

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
                    except Exception:
                        self.gui.main.error_log()

                elif 'slide_title' in request.form:
                    try:
                        num = request.form.get("slide_title")
                        if num.isnumeric():
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
            try:
                self.socketio.stop()
                return 'shutting down socketio'
            except Exception:
                self.gui.main.error_log()
                return 'socketio shutdown failed'

        @self.socketio.on('update_stage')
        def update_stage(text):
            self.socketio.emit('update_stage', text)

        @self.socketio.on('update_oos')
        def update_oos(text):
            self.socketio.emit('update_oos', text)

        @self.socketio.on('change_current_oos')
        def change_current_oos(num):
            self.socketio.emit('change_current_oos', str(num))

        @self.socketio.on('update_slides')
        def update_slides(text):
            self.socketio.emit('update_slides', text)

        @self.socketio.on('change_current_slide')
        def change_current_slide(num):
            self.socketio.emit('change_current_slide', str(num))

        try:
            self.socketio.run(self.app, self.gui.main.ip, 15171)
        except Exception:
            self.gui.main.error_log()

    def get_all_gui_data(self):
        class_tag = ''

        remote_oos_buttons = ''
        current_row = self.gui.oos_widget.oos_list_widget.currentRow()
        for i in range(self.gui.oos_widget.oos_list_widget.count()):
            title = self.gui.oos_widget.oos_list_widget.item(i).data(20)

            if i == current_row:
                class_tag = 'class="current" '
            else:
                class_tag = ''

            remote_oos_buttons += f"""
                <button id="{str(i)}" {class_tag}type="submit" name="oos_button" value="{str(i)}">
                    <span class="title">
                        {title}
                    </span>
                </button>
                <br />"""

        slide_buttons = ''
        current_row = self.gui.live_widget.slide_list.currentRow()
        for i in range(self.gui.live_widget.slide_list.count()):
            if self.gui.live_widget.slide_list.item(i).data(30) == 'video':
                title = self.gui.live_widget.slide_list.item(i).data(20)
                text = 'Video'
            else:
                title = self.gui.live_widget.slide_list.item(i).data(31)[1]
                if type(self.gui.live_widget.slide_list.item(i).data(31)[2]) == bytes:
                    text = ''
                else:
                    text = self.gui.live_widget.slide_list.item(i).data(31)[2]

            if i == current_row:
                class_tag = 'class="current" '
            else:
                class_tag = ''

            slide_buttons += f"""
                <button id="{str(i)}" {class_tag}type="submit" name="slide_button" value="{str(i)}">
                    <span class="title">{title}</span>
                    <br>
                    <span class="text">{text}</span>
                </button>
                <br>"""

        return remote_oos_buttons, slide_buttons
    
    def slide_button(self, button):
        self.gui.live_widget.web_button_signal.emit(button)

class RemoteServerHandler(BaseHTTPRequestHandler):
    html = None

    def do_POST(self):
        try:
            referer = self.headers['Referer']
            self.wfile.write(bytes(referer.split('?')[1], 'utf-8'))
        except Exception:
            logging.exception('')

