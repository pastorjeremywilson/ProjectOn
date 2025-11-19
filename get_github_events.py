import json

import requests
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QScrollArea, QDialog, QMessageBox


def get_release_notes():
    response = requests.get('https://api.github.com/repos/pastorjeremywilson/ProjectOn/events?per_page=100')
    if not response.status_code == 200:
        QMessageBox.information(None, 'HTML Error', 'Service Unavailable', QMessageBox.StandardButton.Ok)
        return

    items = json.loads(response.text)
    events = []
    index = 0
    for item in items:
        events.append({})
        if item['type'] == 'PushEvent':
            commits = item['payload']['commits']
            for commit in commits:
                events[index]['date'] = item['created_at']
                events[index]['notes'] = commit['message']
        elif item['type'] == 'ReleaseEvent':
            events[index]['release'] = item["payload"]["release"]["name"]
        index += 1

    html = '<body style="font-size: 12pt;"><p style="font-weight: bold; background: lightGrey;">In Development</p>'
    for event in events:
        if 'date' in event.keys():
            if 'Merge pull request' not in event['notes']:
                date = event['date'].split('T')[0]
                notes = event['notes'].replace('\n\n', '\n')
                html += f'<p>{date}</p><p style="margin-left: 10px;">{notes}</p>'
        elif 'release' in event.keys():
            release_name = event['release']
            html += f'<p style="font-weight: bold; background: yellow;">{release_name} Released</p>'
    html += '</body>'

    dialog = QDialog()
    dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
    dialog.setWindowTitle('Release Notes')
    layout = QVBoxLayout(dialog)

    label = QLabel(html)
    label.setWordWrap(True)

    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setWidget(label)

    layout.addWidget(scroll_area)

    dialog.exec()
