import os
import shutil
import sqlite3
import sys
import time
import traceback
from os.path import exists

from PyQt5.QtCore import Qt, QByteArray, QBuffer, QIODevice
from PyQt5.QtGui import QPixmap
from PyQt5.QtMultimedia import QMediaPlayer
from PyQt5.QtWidgets import QMessageBox

from dataHandling.declarations import SLIDE_DATA_DEFAULTS, SQL_COLUMN_TO_DICTIONARY_SONG, SLIDE_DATA_DATA_TYPES, \
    SQL_COLUMN_TO_DICTIONARY_CUSTOM, SLIDE_DICTIONARY_TO_SONG_SQL_COLUMN, SLIDE_DICTIONARY_TO_CUSTOM_SQL_COLUMN


def get_connection(database: str) -> tuple[sqlite3.Connection, sqlite3.Cursor] | int:
    """
    Creates a sqlite3 connection to the given database file
    :param str database: string path to the database
    :return: tuple[Connection, Cursor] | int: -1 on exception
    """
    try:
        connection = sqlite3.connect(database)
        cursor = connection.cursor()

        return connection, cursor
    except Exception:
        return -1


def get_song_data(database: str, title: str) -> dict | int:
    """
    Gets the song data for a particular song where the 'title' column matches 'title'
    :param str database: string path to the database
    :param str title: the song title
    :return: list[str]: all columns for this song | int: -1 on exception
    """
    connection = None
    try:
        connection, cursor = get_connection(database)
        result = cursor.execute('SELECT * FROM songs WHERE title="' + title + '"').fetchone()
        connection.close()
        data = SLIDE_DATA_DEFAULTS.copy()
        data['type'] = 'song'
        for i in range(len(result)):
            if 'global' in str(result[i]):
                data[SQL_COLUMN_TO_DICTIONARY_SONG[i]] = result[i]
            elif result[i] is not None and type(result[i]) is not int and result[i].lower() == 'true':
                data[SQL_COLUMN_TO_DICTIONARY_SONG[i]] = True
            elif result[i] is not None and type(result[i]) is not int and result[i].lower() == 'false':
                data[SQL_COLUMN_TO_DICTIONARY_SONG[i]] = False
            elif result[i] is not None:
                data[SQL_COLUMN_TO_DICTIONARY_SONG[i]] = SLIDE_DATA_DATA_TYPES[SQL_COLUMN_TO_DICTIONARY_SONG[i]](
                    result[i])
        return data
    except Exception:
        error_log()
        if connection:
            connection.close()
        return -1


def get_all_songs(database: str) -> list[str] | int:
    """
    Retrieves all song data from the ProjectOn database's 'songs' table
    :param str database: string path to the database
    :return: list[str]: all songs and their data | int: -1 on exception
    """
    connection = None
    try:
        connection, cursor = get_connection(database)
        result = cursor.execute('SELECT * FROM songs ORDER BY title').fetchall()

        # there's been enough variation in how data is stored across versions that we're going to
        # convert the stored sql data to the standardized slide data, including making sure the
        # data types are standardized in each dictionary
        all_songs = []
        for song in result:
            data = SLIDE_DATA_DEFAULTS.copy()
            data['type'] = 'song'
            for i in range(len(song)):
                if 'global' in str(song[i]):
                    data[SQL_COLUMN_TO_DICTIONARY_SONG[i]] = song[i]
                elif song[i] is not None and type(song[i]) is not int and song[i].lower() == 'true':
                    data[SQL_COLUMN_TO_DICTIONARY_SONG[i]] = True
                elif song[i] is not None and type(song[i]) is not int and song[i].lower() == 'false':
                    data[SQL_COLUMN_TO_DICTIONARY_SONG[i]] = False
                elif song[i] is not None:
                    data[SQL_COLUMN_TO_DICTIONARY_SONG[i]] = SLIDE_DATA_DATA_TYPES[SQL_COLUMN_TO_DICTIONARY_SONG[i]](
                        song[i])
            all_songs.append(data)

        return all_songs
    except Exception:
        error_log()
        if connection:
            connection.close()
        return -1


def get_all_custom_slides(database: str) -> list[str] | int:
    """
    Retrieves all custom slide data from the ProjectOn database's 'customSlides' table
    :param str database: string path to the database
    :return: list[str]: all custom slides and their data | int: -1 on exception
    """
    connection = None
    try:
        connection, cursor = get_connection(database)
        result = cursor.execute('SELECT * FROM customSlides ORDER BY title').fetchall()

        # there's been enough variation in how data is stored across versions that we're going to
        # convert the stored sql data to the standardized slide data, including making sure the
        # data types are standardized in each dictionary
        all_custom = []
        for custom in result:
            data = SLIDE_DATA_DEFAULTS.copy()
            data['type'] = 'custom'
            for i in range(len(custom)):
                if 'global' in str(custom[i]):
                    data[SQL_COLUMN_TO_DICTIONARY_CUSTOM[i]] = custom[i]
                elif custom[i] is not None and type(custom[i]) is not int and custom[i].lower() == 'true':
                    data[SQL_COLUMN_TO_DICTIONARY_CUSTOM[i]] = True
                elif custom[i] is not None and type(custom[i]) is not int and custom[i].lower() == 'false':
                    data[SQL_COLUMN_TO_DICTIONARY_CUSTOM[i]] = False
                elif custom[i] is not None:
                    data[SQL_COLUMN_TO_DICTIONARY_CUSTOM[i]] = SLIDE_DATA_DATA_TYPES[
                        SQL_COLUMN_TO_DICTIONARY_CUSTOM[i]](custom[i])
            all_custom.append(data)
        connection.close()
        return all_custom
    except Exception:
        error_log()
        if connection:
            connection.close()
        return -1


def get_all_images(database) -> list | int:
    """
    Retrieves all image data from the ProjectOn database's 'images' table
    :param str database: string path to the database
    :return: list: all images and their data | int: -1 on exception
    """
    connection = None
    try:
        connection, cursor = get_connection(database)
        result = cursor.execute('SELECT * FROM imageThumbnails ORDER BY fileName COLLATE NOCASE ASC').fetchall()

        all_images = []
        for image in result:
            data = SLIDE_DATA_DEFAULTS.copy()
            data['type'] = 'image'
            data['title'] = image[0]
            pixmap = QPixmap()
            pixmap.loadFromData(image[1], 'jpg')
            data['background'] = pixmap
            data['folder'] = image[2]
            all_images.append(data)
        connection.close()
        return all_images
    except Exception:
        error_log()
        if connection:
            connection.close()
        return -1


def get_all_videos(database) -> list | int:
    """
    Retrieves all video data from the ProjectOn database's 'videos' table
    :param str database: string path to the database
    :return: list: all videos and their data | int: -1 on exception
    """
    connection = None
    try:
        connection, cursor = get_connection(database)
        result = cursor.execute('SELECT * FROM videos').fetchall()
        all_videos = []
        for video in result:
            data = SLIDE_DATA_DEFAULTS.copy()
            data['type'] = 'video'
            data['title'] = video[0]
            data['file_name'] = video[0]
            data['folder'] = video[2]
            data['use_footer'] = False

            pixmap = QPixmap()
            pixmap.loadFromData(video[1], 'jpg')
            data['background'] = pixmap

            all_videos.append(data)
        return all_videos
    except Exception:
        error_log()
        if connection:
            connection.close()
        return -1


def get_all_web(database) -> list | int:
    """
    Retrieves all web page data from the ProjectOn database's 'web' table
    :param str database: string path to the database
    :return: list: all web pages and their data | int: -1 on exception
    """
    connection = None
    all_web = []
    try:
        connection, cursor = get_connection(database)
        results = cursor.execute('SELECT * FROM web').fetchall()
        connection.close()

        for record in results:
            data = SLIDE_DATA_DEFAULTS.copy()
            data['type'] = 'web'
            data['title'] = record[0]
            data['url'] = record[1]
            data['folder'] = record[2]
            data['use_footer'] = False
            all_web.append(data)

        return all_web
    except Exception:
        error_log()
        if connection:
            connection.close()
        return -1


def get_custom_data(database: str, title: str) -> list[str] | int: # unused
    """
    Gets the song data for a particular custom slide where the 'title' column matches 'title'
    :param str database: string path to the database
    :param str title: the title (name) of the custom slide
    :return: list[str]: all columns for this custom slide | int: -1 on exception
    """
    connection = None
    try:
        connection, cursor = get_connection(database)
        result = cursor.execute('SELECT * FROM customSlides WHERE title="' + title + '"').fetchone()
        connection.close()
        return result
    except Exception:
        error_log()
        if connection:
            connection.close()
        return -1 #


def get_folders(database, slide_type: str) -> list[str] | int:
    """
    Retrieves all the folders associated with items for this slide type
    :param str database: string path to the database
    :param str slide_type: The type of slide
    :return: list[str]: all folders | int: -1 on exception, 0 if wrong slide_type
    """
    connection = None
    result = tuple()
    try:
        connection, cursor = get_connection(database)
        if slide_type == 'song':
            result = cursor.execute('SELECT folder FROM songs').fetchall()
        elif slide_type == 'custom':
            result = cursor.execute('SELECT folder FROM customSlides').fetchall()
        elif slide_type == 'images':
            result = cursor.execute('SELECT folder FROM imageThumbnails').fetchall()
        elif slide_type == 'videos':
            result = cursor.execute('SELECT folder FROM videos').fetchall()
        elif slide_type == 'web':
            result = cursor.execute('SELECT folder FROM web').fetchall()
        else:
            connection.close()
            return 0
        connection.close()
    except Exception:
        if connection:
            connection.close()
        error_log()

    folders = set()
    for item in result:
        folder_name = item[0].strip()
        if len(folder_name) > 0:
            folders.add(folder_name)

    return list(folders)


def get_audio_clip_names(database) -> list[str] | int:
    """
    Retrievers all info from the "name" column of the audio table
    :param str database: string path to the database
    :return: list[str]: all audio clip names | int: -1 on exception
    """
    connection = None
    try:
        connection, cursor = get_connection(database)
        result = cursor.execute('SELECT "name" FROM "audio";').fetchall()
        connection.close()
        return result
    except Exception:
        error_log()
        if connection:
            connection.close()
        return -1


def get_audio_data(database: str, name: str) -> tuple[QByteArray, str] | int:
    """
    Retrieves all the audio data for the given audio clip
    :param str database: string path to the database
    :param name: The name of the qudio clip
    :return: list[str]: all audio data | int: -1 on exception
    """
    connection = None
    try:
        connection, cursor = get_connection(database)
        result = cursor.execute(f'SELECT data, format FROM audio WHERE name="{name}";').fetchone()
        if len(result) == 0:
            return -2
        connection.close()
        return result
    except Exception:
        error_log()
        if connection:
            connection.close()
        return -1


def save_audio(database: str, name: str, audio_format: str, audio_data: bytes) -> int:
    """
    Saves an audio clip to the database
    :param str database: string path to the database
    :param str name: The name of the qudio clip
    :param str audio_format: The format the audio clip is rendered as
    :param bytes audio_data: The audio clip's data
    :return: int: 0 on success, -2 on failed execute, -1 on exception
    """
    connection = None
    try:
        connection, cursor = get_connection(database)
        result = cursor.execute(f'SELECT "name" FROM "audio" WHERE "name"="{name}";').fetchall()
        if len(result) > 0:
            return -2
        cursor.execute(
            f'INSERT INTO audio (name, format, data) VALUES ("{name}", "{audio_format}", ?);', (audio_data,))
        connection.commit()
        connection.close()
        return 0
    except Exception:
        error_log()
        if connection:
            connection.close()
        return -1


def copy_image(image_dir: str, file: str) -> None | int:
    """
    Creates a copy of an image file chosen by the user and stores it in this program's data folder
    :param str image_dir: string path to the ProjectOn image directory
    :param str file: the image's file name
    :return: None | int: -1 on exception
    """
    try:
        file_split = file.split('/')
        file_name = file_split[len(file_split) - 1]

        if not exists(image_dir + '/' + file_name):
            shutil.copy(file, image_dir + '/' + file_name)
    except Exception:
        error_log()
        return -1


def save_song(database: str, data: dict, old_title: str = None) -> None | int:
    """
    Takes song data as a dictionary, converts the dictionary keys to the database's columns,
    and inserts or updates that data in the database.
    :param str database: string path to the database
    :param dict data: The song's data
    :param str old_title: Optional, the song's original title so that it can be updated instead of inserted
    :return: None | int: -1 on exception
    """
    connection = None
    try:
        for key in data.keys():
            if type(data[key]) == str:
                data[key] = data[key].replace('"', '""')

        connection, cursor = get_connection(database)

        # if old_title has been provided, this song already exists in the database and we need to use UPDATE
        if old_title:
            sql = 'UPDATE songs SET '
            for key in data.keys():
                if key in SLIDE_DICTIONARY_TO_SONG_SQL_COLUMN.keys():
                    sql += f'{SLIDE_DICTIONARY_TO_SONG_SQL_COLUMN[key]}="{data[key]}",'
            sql = sql[:-1] + f' WHERE title="{old_title}";'
        else:  # use INSERT INTO instead
            sql = 'INSERT INTO songs ('
            for key in data.keys():
                if key in SLIDE_DICTIONARY_TO_SONG_SQL_COLUMN.keys():
                    sql += SLIDE_DICTIONARY_TO_SONG_SQL_COLUMN[key] + ','
            sql = sql[:-1] + ') VALUES ("'
            for key in data.keys():
                if key in SLIDE_DICTIONARY_TO_SONG_SQL_COLUMN.keys():
                    sql += f'{data[key]}","'
            sql = sql[:-2] + ');'

        cursor.execute(sql)
        connection.commit()
        connection.close()
    except Exception:
        error_log()
        if connection:
            connection.close()
        return -1


def get_song_titles(database) -> list[str] | int:
    """
    Retrieves just the titles of all songs in the database.
    :param str database: string path to the database
    :return: list[str] of song titles | int: -1 on exception
    """
    connection = None
    try:
        connection, cursor = get_connection(database)
        data = cursor.execute('SELECT title FROM songs ORDER BY title').fetchall()
        song_titles = []
        for item in data:
            song_titles.append(item[0])

        return song_titles
    except Exception:
        error_log()
        if connection:
            connection.close()
        return -1


def get_custom_titles(database) -> list[str] | int:
    """
    Retrieves just the titles of all custom slides in the database.
    :param str database: string path to the database
    :return list[str]: Custom slide titles | int: -1 on exception
    """
    connection = None
    try:
        connection, cursor = get_connection(database)
        data = cursor.execute('SELECT title FROM customSlides').fetchall()
        custom_titles = []
        for item in data:
            custom_titles.append(item[0])

        return custom_titles
    except Exception:
        if connection:
            connection.close()
        error_log()
        return -1


def save_custom(database: str, data: dict, old_title: str | None = None) -> None | int:
    """
    Takes custom slide data as a dict, converts the dictionary keys to the database's columns,
    and inserts or updates that data in the database.
    :param str database: string path to the database
    :param dict data: The custom slide's data in columnar order
    :param str old_title: Optional, the custom slide's original title so that it can be updated instead of inserted
    :return: None | int: -1 on exception
    """
    connection = None

    try:
        for key in data.keys():
            if type(data[key]) == str:
                data[key] = data[key].replace('"', '""')
        connection, cursor = get_connection(database)

        # if old_title has been provided, this song already exists in the database and we need to use UPDATE
        if old_title:
            sql = 'UPDATE customSlides SET '
            for key in data.keys():
                if key in SLIDE_DICTIONARY_TO_CUSTOM_SQL_COLUMN.keys():
                    sql += f'{SLIDE_DICTIONARY_TO_CUSTOM_SQL_COLUMN[key]}="{data[key]}",'
            sql = sql[:-1] + f' WHERE title="{old_title}";'
        else:  # use INSERT INTO instead
            sql = 'INSERT INTO customSlides ('
            for key in data.keys():
                if key in SLIDE_DICTIONARY_TO_CUSTOM_SQL_COLUMN.keys():
                    sql += SLIDE_DICTIONARY_TO_CUSTOM_SQL_COLUMN[key] + ','
            sql = sql[:-1] + ') VALUES ("'
            for key in data.keys():
                if key in SLIDE_DICTIONARY_TO_CUSTOM_SQL_COLUMN.keys():
                    sql += f'{data[key]}","'
            sql = sql[:-2] + ');'

        cursor.execute(sql)
        connection.commit()
        connection.close()
    except Exception:
        error_log()
        if connection:
            connection.close()
        return -1


def save_image(database, data: dict, old_title: str | None = None) -> None | int:
    """
    Saves an image to the database by first scaling the image to a standardized thumbnail, then inserts or updates
    the database with the info in its dictionary.
    :param str database: string path to the database
    :param dict data: The dictionary associated with the image
    :param old_title: optional: The title of an image already existant in the database
    :return: None | int: -1 on exception
    """
    connection = None
    try:
        connection, cursor = get_connection(database)
        for key in data.keys():
            if type(data[key]) == str:
                data[key] = data[key].replace('"', '""')

        pixmap = data['background'].scaled(
            96,
            54,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        array = QByteArray()
        buffer = QBuffer(array)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        pixmap.save(buffer, 'JPG')
        blob = bytes(array.data())

        # if old_title has been provided, this image already exists in the database and we need to use UPDATE
        if old_title:
            sql = (f'UPDATE imageThumbnails SET '
                   f'filename="{data["title"]}",'
                   f'image=?,'
                   f'folder="{data["folder"]}" '
                   f'WHERE filename="{old_title}";')

            cursor.execute(sql, (blob,))
            connection.commit()
            connection.close()
        else:  # use INSERT INTO instead

            sql = (f'INSERT INTO imageThumbnails (filename, image, folder) VALUES ('
                   f'"{data["title"]}",'
                   f'?,'
                   f'"{data["folder"]}");')
            cursor.execute(sql, (blob,))
            connection.commit()
            connection.close()

    except Exception:
        error_log()
        if connection:
            connection.close()
        return -1


def save_video(database: str, data: dict, old_title: str | None = None) -> int:
    """
    Saves a video to the database by first scaling the video to a standardized thumbnail, then inserts or updates
    the database with the info in its dictionary.
    :param str database: string path to the database
    :param dict data: Dictionary associated with the video
    :param old_title: optional: The title of a video already existant in the database
    :return: int: 0 on success, -1 on exception
    """
    connection = None
    try:
        connection, cursor = get_connection(database)

        array = QByteArray()
        buffer = QBuffer(array)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        data['background'].save(buffer, 'JPG')
        blob = bytes(array.data())

        # if old_title has been provided, this video already exists in the database so we need to use UPDATE
        if old_title:
            sql = (f'UPDATE videos SET '
                   f'filename="{data["title"]}",'
                   f'thumbnail=?,'
                   f'folder="{data["folder"]}" '
                   f'WHERE filename="{old_title}";')

            cursor.execute(sql, (blob,))
            connection.commit()
            connection.close()
            return 0
        else:  # use INSERT INTO instead
            pixmap = data['background']
            array = QByteArray()
            buffer = QBuffer(array)
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            pixmap.save(buffer, 'JPG')
            blob = bytes(array.data())

            sql = (f'INSERT INTO videos (filename, thumbnail, folder) VALUES ('
                   f'"{data["title"]}",'
                   f'?,'
                   f'"{data["folder"]}");')
            cursor.execute(sql, (blob,))
            connection.commit()
            buffer.close()
            connection.close()
        return 0
    except Exception:
        if connection:
            connection.close()
        error_log()
        return -1


def save_web_item(database: str, data: dict, old_title: str | None = None) -> int:
    """
    Stores the title and url of a web slide to the program's database. Checks the database first to see if the
    given title already exists.
    :param str database: string path to the database
    :param dict data: The title of the web slide
    :param str old_title: The url the web slide is to fetch
    :return: int: 0 on success, -1 on exception
    """
    connection = None
    try:
        connection, cursor = get_connection(database)

        # if old_title has been provided, this web item already exists in the database and we need to use UPDATE
        if old_title:
            sql = (f'UPDATE web SET '
                   f'title="{data["title"]}",'
                   f'url="{data["url"]}",'
                   f'folder="{data["folder"]}" '
                   f'WHERE title="{old_title}";')

            cursor.execute(sql)
            connection.commit()
            connection.close()
        else:  # use INSERT INTO instead
            sql = (f'INSERT INTO web (title, url, folder) VALUES ('
                   f'"{data["title"]}",'
                   f'"{data["url"]}",'
                   f'"{data["folder"]}");')
            cursor.execute(sql)
            connection.commit()
            connection.close()
        return 0

    except Exception:
        error_log()
        if connection:
            connection.close()
        return -1


def delete_items_from_db(gui, items: set) -> int:
    """
    Provides a method of deleting a given item from the program's database.
    :param str database: string path to the database
    :param guiElements.gui.GUI gui: current instance of GUI
    :param str image_dir: string path to the ProjectOn images directory
    :param str video_dir: string path to the ProjectOn videos directory
    :param set items: Set of two-value tuples(type, title) to be removed
    :return: int: 0 on success, -1 on exception
    """
    connection = None
    try:
        database = gui.main.database
        image_dir = gui.main.image_dir
        video_dir = gui.main.video_dir
        connection, cursor = get_connection(database)
        for item in items:
            no_command = False
            type, title = item
            table, column = '', ''
            if type == 'song':
                table = 'songs'
                column = 'title'
            elif type == 'custom':
                table = 'customSlides'
                column = 'title'
            elif type == 'image':
                table = 'imageThumbnails'
                column = 'filename'
                os.remove(image_dir + '/' + title)
            elif type == 'video':
                # first, check to see if this video is currently queued up; get rid of the media player if so
                if (gui.live_widget.slide_list.item(0)
                        and gui.live_widget.slide_list.item(0).data(Qt.ItemDataRole.UserRole)['title'] == title):
                    # handle stopping the media player carefully to avoid an Access Violation
                    if gui.media_player:
                        if gui.media_player.state() == QMediaPlayer.State.PlayingState:
                            gui.media_player.stop()
                            if gui.timed_update:
                                gui.timed_update.stop = True

                    gui.live_widget.slide_list.clear()
                    gui.live_widget.preview_label.clear()
                    gui.live_widget.player_controls.hide()

                # remove the video from the video directory as well as its snapshot image, if it exists
                file_name = title
                os.remove(video_dir + '/' + file_name)
                filename_split = file_name.split('.')
                thumbnail_filename = '.'.join(filename_split[:len(filename_split) - 1]) + '.jpg'
                if exists(video_dir + '/' + thumbnail_filename):
                    os.remove(video_dir + '/' + thumbnail_filename)

                table = 'videos'
                column = 'filename'
            elif type == 'web':
                table = 'web'
                column = 'title'
            else:
                no_command = True

            if not no_command:
                cursor.execute(f'DELETE FROM {table} WHERE {column}="{title}"')
        connection.commit()
        connection.close()

        return 0
    except Exception:
        error_log()
        if connection:
            connection.close()
        return -1


def delete_all_songs(database, gui): # not used
    """
    Provides a method for removing all the songs from the database's 'songs' table. Checks and double-checks
    with the user that they really want to do this. Not currently accessible by the user.
    :param str database: string path to the database
    :param guiElements.gui.GUI gui: current instance of GUI
    """
    result = QMessageBox.question(
        gui.main_window,
        'Really Delete?',
        'This will remove ALL SONGS from your database. This cannot be undone. Really DELETE ALL SONGS?',
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
    )

    if result == QMessageBox.StandardButton.Yes:
        second_result = QMessageBox.question(
            gui.main_window,
            'Really Delete?',
            'Just making sure: Do you really want to DELETE ALL SONGS?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )
        if not second_result == QMessageBox.StandardButton.Yes:
            return
    else:
        return

    connection = None
    try:
        connection, cursor = get_connection(database)
        cursor.execute('DELETE FROM songs')
        connection.commit()
        connection.close()

        QMessageBox.information(
            gui.main_window,
            'Songs Deleted',
            'All songs have been removed.',
            QMessageBox.StandardButton.Ok
        )
        gui.media_widget.song_list.clear()
    except Exception:
        error_log()
        if connection:
            connection.close()


def error_log(log_text: str | None = None):
    """
    Method to write a traceback to the program's error log file as well as show the user the error.
    """
    if not log_text: # if text was provided, we're only logging information
        tb = traceback.walk_tb(sys.exc_info()[2])
        message_box_text = ''
        for frame, line_no in tb:
            clss = ''
            if 'self' in frame.f_locals.keys():
                try:
                    clss = str(frame.f_locals['self']).split('<')[1].split(' ')[0].split('.')[1]
                except IndexError:
                    clss = str(frame.f_locals['self'])
            file_name = frame.f_code.co_filename
            method = frame.f_code.co_name
            line_num = line_no
            message_box_text = (
                f'An error:\n'
                f'    {sys.exc_info()[1]},\n'
                f'occurred on line\n'
                f'    {line_num}\n'
                f'of\n'
                f'    {file_name}\n'
                f'in\n'
                f'    {clss}.{method}'
            )
            date_time = time.ctime(time.time())
            log_text = (f'\n{date_time}:\n'
                        f'    {sys.exc_info()[1]} on line {line_num} of {file_name} in {clss}.{method}')
        print(f'ProjectOn.error_log log text: {log_text}')

        message_box = QMessageBox()
        message_box.setIconPixmap(QPixmap('resources/gui_icons/face-palm.png'))
        message_box.setWindowTitle('An Error Occurred')
        message_box.setText('<strong>Well, that wasn\'t supposed to happen!</strong><br><br>' + message_box_text)
        message_box.setStandardButtons(QMessageBox.StandardButton.Close)
        message_box.exec()
    else:
        date_time = time.ctime(time.time())
        log_text = (f'\n{date_time}:\n' + log_text)

    if 'linux' in sys.platform:
        log_location = os.path.expanduser('~/.config/ProjectOn/error.log')
    else:
        log_location = os.path.expanduser('~/AppData/Roaming/ProjectOn/error.log')

    if not exists(log_location):
        with open(log_location, 'w') as file:
            pass

    with open(log_location, 'a') as file:
        file.write(log_text)