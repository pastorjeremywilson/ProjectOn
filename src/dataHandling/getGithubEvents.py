import json
from datetime import datetime

import requests
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QScrollArea, QDialog, QMessageBox


def get_release_notes():
    response = requests.get('https://api.github.com/repos/pastorjeremywilson/ProjectOn/events?per_page=100')
    if not response.status_code == 200:
        QMessageBox.information(None, 'HTML Error', 'Service Unavailable', QMessageBox.StandardButton.Ok)
        return

    items = json.loads(response.text)
    events = []
    index = 0
    name = ''
    date = ''
    reformatted_notes = ''
    for item in items:
        if item['type'] == 'ReleaseEvent':
            name = item['payload']['release']['name']
            date = item['payload']['release']['published_at']
            notes = item['payload']['release']['body']

            datetime_date = datetime.fromisoformat(date.replace("Z", "+00:00"))
            date = datetime_date.strftime("%m/%d/%Y %I:%M %p")

            notes_split = notes.split('\n')
            reformatted_notes = '<ul>'
            for note in notes_split:
                if not note.strip().startswith('[!'):
                    note = note.strip()
                    if note.startswith('-'):
                        note = note.replace('-', '').strip()
                    reformatted_notes += f'<li>{note}</li>'
            reformatted_notes += '</ul>'

    html = '<h3>RELEASE NOTES</h3>'
    html += f'<p>{name}</p>'
    html += f'<p>Released: {date}</p>'
    html += f'<p>Notes:{reformatted_notes}</p>'

    return html

def get_commits():
    # first, get the date of the most recent release
    response = requests.get('https://api.github.com/repos/pastorjeremywilson/ProjectOn/events?per_page=100')
    if not response.status_code == 200:
        QMessageBox.information(None, 'HTML Error', 'Service Unavailable', QMessageBox.StandardButton.Ok)
        return

    items = json.loads(response.text)
    release_datetime_date = datetime.now()
    for item in items:
        if item['type'] == 'ReleaseEvent':
            date = item['payload']['release']['published_at']
            release_datetime_date = datetime.fromisoformat(date.replace("Z", "+00:00"))

    params = {
        'sha': 'development',
        'per_page': 50
    }
    response = requests.get('https://api.github.com/repos/pastorjeremywilson/ProjectOn/commits', params=params)
    if not response.status_code == 200:
        QMessageBox.information(None, 'HTML Error', 'Service Unavailable', QMessageBox.StandardButton.Ok)
        return
    items = json.loads(response.text)

    html = '<h3>IN DEVELOPMENT</h3>'
    for item in items:
        date = item['commit']['committer']['date']
        datetime_date = datetime.fromisoformat(date.replace("Z", "+00:00"))
        date = datetime_date.strftime("%m/%d/%Y %I:%M %p")
        notes = item['commit']['message']
        if datetime_date > release_datetime_date:
            html += f'<p>[{date}]</p><p>{notes}</p>'

    return html

def show_notes(release=True, commits=True):
    dialog = QDialog()
    dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
    dialog.setWindowTitle('Release Notes')
    layout = QVBoxLayout(dialog)

    if release and commits:
        html = get_release_notes() + get_commits()
    elif release:
        html = get_release_notes()
    else:
        html = get_commits()

    html = '<body style="font-size: 12pt">' + html + '</body>'

    label = QLabel(html)
    label.setWordWrap(True)

    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setWidget(label)

    layout.addWidget(scroll_area)

    dialog.exec()
