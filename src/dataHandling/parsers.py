import re

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QFont, QColor, QImage, QPainter
from PyQt5.QtWidgets import QMessageBox


def parse_song_data(display_widget, settings: dict, song_data: dict):
    """
    Method to take the stored lyrics of a song and parse them out according to their segment markers (i.e. [V1])
    :param GUI gui: The current instance of GUI
    :param dict song_data: The raw lyrics data
    """
    if 'text' not in song_data.keys() or len(song_data['text'].strip()) == 0:
        return

    # start by building a dictionary of segment text keyed to their corresponding tags
    lyric_dictionary = {}
    lyrics = song_data['text']
    if '<body' in lyrics:
        lyrics_split = re.split('<body.*?>', lyrics)
        lyrics = lyrics_split[1].split('</body>')[0].strip()
        lyrics = re.sub('<p.*?>', '<p style="text-align: center;">', lyrics)

    segment_markers = re.findall(r'\[.*?]', lyrics)
    segment_split = re.split(r'\[.*?]', lyrics)

    if len(segment_markers) > 0:
        for i in range(len(segment_markers)):
            try:
                this_segment = segment_split[i + 1]
                lyric_dictionary.update({segment_markers[i]: this_segment.strip()})
            except IndexError:
                lyric_dictionary.update({segment_markers[i]: segment_split[i + 1].strip()})
    else:
        lyrics_split = lyrics.split('<br /><br />')
        for i in range(len(lyrics_split)):
            if len(lyrics_split[i].strip()) > 0:
                lyric_dictionary.update({f'[Verse {i + 1}]': lyrics_split[i].strip()})

    new_dict = {}
    for key in lyric_dictionary:
        if ' ' in key:
            key_text = key.replace('[', '').replace(']', '')
            new_key = key_text.split(' ')[0][0].lower() + key_text.split(' ')[1]
            new_dict['[' + new_key + ']'] = lyric_dictionary[key]
        else:
            new_dict[key] = lyric_dictionary[key]
    lyric_dictionary = new_dict

    # then, build a list of song segments in their proper order with user-friendly tag names
    segments = []
    if len(song_data['verse_order']) > 0:
        song_order = song_data['verse_order']
        if ',' in song_order:
            song_order = song_order.replace(', ', ' ')
            song_order = song_order.replace(',', ' ')
        song_order = re.sub(' +', ' ', song_order)
        iterable = song_order.split(' ')
        for i in range(len(iterable)):
            iterable[i] = '[' + iterable[i] + ']'
    else:
        iterable = lyric_dictionary

    # set the font, using the song's font data if override_global is True
    if song_data['override_global']:
        font_face = song_data['font_family']
        font_size = int(song_data['font_size'])

        if 'global' in str(song_data['use_shadow']):
            use_shadow = settings['song_use_global']
        else:
            use_shadow = song_data['use_shadow']

        if 'global' in str(song_data['shadow_color']):
            shadow_color = settings['song_shadow_color']
        else:
            shadow_color = song_data['shadow_color']

        if 'global' in str(song_data['shadow_offset']):
            shadow_offset = settings['song_shadow_offset']
        else:
            shadow_offset = song_data['shadow_offset']

        if 'global' in str(song_data['use_outline']):
            use_outline = settings['song_use_outline']
        else:
            use_outline = song_data['use_outline']

        if 'global' in str(song_data['outline_color']):
            outline_color = settings['song_outline_color']
        else:
            outline_color = song_data['outline_color']

        if 'global' in str(song_data['outline_width']):
            outline_width = settings['song_outline_width']
        else:
            outline_width = song_data['outline_width']
    else:
        font_face = settings['song_font_face']
        font_size = settings['song_font_size']
        font_color = settings['song_font_color']
        use_shadow = settings['song_use_shadow']
        shadow_color = settings['song_shadow_color']
        shadow_offset = settings['song_shadow_offset']
        use_outline = settings['song_use_outline']
        outline_color = settings['song_outline_color']
        outline_width = settings['song_outline_width']

    display_widget.lyric_widget.setFont(QFont(font_face, font_size, QFont.Weight.Bold))
    display_widget.lyric_widget.use_shadow = use_shadow
    display_widget.lyric_widget.shadow_color = QColor(shadow_color, shadow_color, shadow_color)
    display_widget.lyric_widget.shadow_offset = shadow_offset
    display_widget.lyric_widget.use_outline = use_outline
    display_widget.lyric_widget.outline_color = QColor(outline_color, outline_color, outline_color)
    display_widget.lyric_widget.outline_width = outline_width

    # create a QImage to use as a canvas for the text size calculations
    image = QImage(display_widget.width(), display_widget.height(), QImage.Format.Format_ARGB32_Premultiplied)
    painter = QPainter()
    for segment in iterable:
        item_num = [i for i in segment if i.isdigit()]

        if 'v' in segment:
            segment_title = 'Verse ' + ''.join(item_num)
        elif 'c' in segment:
            segment_title = 'Chorus ' + ''.join(item_num)
        elif 'p' in segment:
            segment_title = 'Pre-Chorus ' + ''.join(item_num)
        elif 'b' in segment:
            segment_title = 'Bridge ' + ''.join(item_num)
        elif 't' in segment:
            segment_title = 'Tag ' + ''.join(item_num)
        else:
            segment_title = 'Ending ' + ''.join(item_num)

        try:
            segment_text = lyric_dictionary[segment].strip()
            segment_text = re.sub('<p.*?>', '', segment_text)
            segment_text = segment_text.replace('</p>', '')
            segment_text = segment_text.replace('\n', '<br />')
            segment_text = segment_text.replace('&quot;', '"')
        except Exception:
            segment_text = ''
            pass

        while segment_text.startswith('<br />'):
            segment_text = segment_text[6:]
        while segment_text.endswith('<br />'):
            segment_text = segment_text[:len(segment_text) - 6]

        # replace html for bold, italic, and underline with simple tags to be formatted later
        if 'span' in segment_text and 'italic' in segment_text:
            italicized_text = re.findall('<span style=" font-style:italic;">.*?</span>', segment_text)
            for text in italicized_text:
                new_text = re.sub('<span.*?italic.*?>', '<i>', text)
                new_text = re.sub('</span>', '</i>', new_text)
                segment_text = segment_text.replace(text, new_text)

        if 'span' in segment_text and 'font-weight' in segment_text:
            bold_text = re.findall('<span style=" font-weight:700;">.*?</span>', segment_text)
            for text in bold_text:
                new_text = re.sub('<span.*?font-weight.*?>', '<b>', text)
                new_text = re.sub('</span>', '</b>', new_text)
                segment_text = segment_text.replace(text, new_text)

        if 'span' in segment_text and 'text-decoration' in segment_text:
            underline_text = re.findall('<span.*?text-decoration.*?5px;">.*?</span>', segment_text)
            for text in underline_text:
                new_text = re.sub('<span.*?text-decoration.*?>', '<u>', text)
                new_text = re.sub('</span>', '</u>', new_text)
                segment_text = segment_text.replace(text, new_text)

        segment_text = '<p style="text-align: center; line-height: 120%;">' + segment_text + '</p>'

        segment_text = re.sub('<span.*?>', '', segment_text)
        segment_text = re.sub('</span>', '', segment_text)
        display_widget.lyric_widget.setText(segment_text)

        segment_count = 1

        footer_text = ''
        if song_data['use_footer'] or song_data['use_footer'] == 'True':
            if len(song_data['author']) > 0:
                footer_text += song_data['author']
            if len(song_data['copyright']) > 0:
                footer_text += '\n\u00A9' + song_data['copyright'].replace('\n', ' ')
            if len(song_data['ccli_song_number']) > 0:
                footer_text += '\nCCLI Song #: ' + song_data['ccli_song_number']
            if len(settings['ccli_num']) > 0:
                footer_text += '\nCCLI License #: ' + settings['ccli_num']

        lyric_widget_height = 0
        target_height = 0
        if painter.begin(image):
            try:
                lyrics_rect, footer_height = display_widget.lyric_widget.calculate_painted_text(painter)
                lyric_widget_height = lyrics_rect.height()
                target_height = display_widget.height() - footer_height - 40
            finally:
                painter.end()
        else:
            print('Unable to initialize painter')

        # check each segment against the lyric widget's height to see if that segment's text needs to be split in half
        if lyric_widget_height > target_height:
            segment_text_split = re.split('<br.*?/>', segment_text)
            half_lines = int(len(segment_text_split) / 2)

            halves = [[], []]
            for i in range(half_lines):
                halves[0].append(segment_text_split[i])

            for i in range(half_lines, len(segment_text_split)):
                halves[1].append(segment_text_split[i])

            half_num = 1
            for half in halves:
                text = '<br />'.join(half)

                if text.startswith('<p'):
                    text = text + '</p>'
                else:
                    text = '<p style="text-align: center; line-height: 120%;">' + text

                segment_count += 1

                # double-check for missing tags
                if '</b>' in text and '<b>' not in text:
                    text = '<b>' + text
                if '</i>' in text and '<i>' not in text:
                    text = '<i>' + text
                if '</u>' in text and '<u>' not in text:
                    text = '<u>' + text

                if '<b>' in text and '</b>' not in text:
                    text = text + '</b>'
                if '<i>' in text and '</i>' not in text:
                    text = text + '</i>'
                if '<u>' in text and '</u>' not in text:
                    text = text + '</u>'

                segments.append({'title': segment_title + ' - ' + str(half_num), 'text': text})
                half_num += 1
        else:
            segments.append({'title': segment_title, 'text': segment_text})

    return segments

def parse_scripture_by_verse(gui, text: str | list[str]):
    """
    Take a passage of scripture and split it according to how many verses will fit on the display screen, given
    the current font and size.
    :param GUI gui: The current instance of GUI
    :param str | list of str text: The bible passage to be split
    """
    # configure the lyric display widget according to the current font
    gui.display_widget.lyric_widget.setFont(QFont(gui.main.settings['bible_font_face'], gui.main.settings['bible_font_size']))
    gui.display_widget.footer_text = 'bogus reference' # just a placeholder

    # In the event that a simple string is received instead of a list of stings, this is a custom scripture passage
    # that needs to be parsed into verses and their corresponding verse numbers
    if type(text) is str:
        verse_numbers = []
        skip_next = False
        for i in range(len(text)):
            if text[i].isnumeric() and not skip_next:
                verse_number = text[i]
                if i < len(text) - 1 and text[i + 1].isnumeric():
                    verse_number += text[i + 1]
                    skip_next = True
                verse_numbers.append(verse_number)
            else:
                skip_next = False

        text_split = []
        for i in range(len(verse_numbers)):
            verse_index = text.index(verse_numbers[i])
            number_length = len(verse_numbers[i])
            if i < len(verse_numbers) - 1:
                text_split.append(
                    [
                        verse_numbers[i],
                        text[verse_index + number_length:text.index(verse_numbers[i + 1])]
                    ]
                )
            else:
                text_split.append([verse_numbers[i], text[verse_index + number_length:]])
        text: list[str] = text_split



    # clear the text of the lyric widget and instantiate a painter that will allow calculating the text height
    gui.display_widget.lyric_widget.text = ''
    lyrics_rect = QRect(0, 0, 0, 0)
    footer_height = 0
    image = QImage(gui.display_widget.width(), gui.display_widget.height(), QImage.Format_ARGB32_Premultiplied)
    painter = QPainter()
    if painter.begin(image):
        try:
            lyrics_rect, footer_height = gui.display_widget.lyric_widget.calculate_painted_text(painter)
        finally:
            painter.end()
    target_height = gui.display_widget.height() - footer_height - 40

    slide_texts = []
    verses_added = 0
    parse_failed = False
    verse_index = 0
    while verse_index < len(text):
        # add the current verse number and verse text to the lyric widget's text
        this_verse = ' '.join(text[verse_index])
        gui.display_widget.lyric_widget.text = f'{gui.display_widget.lyric_widget.text} {this_verse}'.strip()
        verses_added += 1

        # repaint to the image from the lyric widget to get its current height
        if painter.begin(image):
            try:
                lyrics_rect, footer_height = gui.display_widget.lyric_widget.calculate_painted_text(painter)
            finally:
                painter.end()

        if lyrics_rect.height() > target_height:
            if verses_added == 1:
                # just this one verse overflowed the widget, so set parse_failed and add this verse to slide_texts
                parse_failed = True
                slide_texts.append(this_verse)
            else:
                # adding this verse overflowed the widget so remove this verse from the current lyric widget text,
                # add the altered text to slide_texts, and reduce verse_index by one so that it gets added to the
                # next set
                slide_texts.append(gui.display_widget.lyric_widget.text.replace(this_verse, '').strip())
                verse_index -= 1
            gui.display_widget.lyric_widget.text = ''
            verses_added = 0
        verse_index += 1
    slide_texts.append(gui.display_widget.lyric_widget.text)

    """verse_index = 0
    segment_indices = []
    current_segment_index = 0
    recursion_count = 0
    while verse_index < len(text):
        # keep adding verses until the text overflows its widget, remove the last verse, and add to the slide texts
        segment_indices.append([])
        count = 0
        gui.display_widget.lyric_widget.text = ''
        while lyrics_rect.height() < target_height and verse_index < len(text):
            print(lyrics_rect.height(), target_height)
            if count > 0:
                if verse_index < len(text):
                    gui.display_widget.lyric_widget.text = (f'{gui.display_widget.lyric_widget.text} '
                                                            f'{text[verse_index][0]} {text[verse_index][1]}')
                    if painter.begin(image):
                        try:
                            lyrics_rect, footer_height = gui.display_widget.lyric_widget.calculate_painted_text(painter)
                        finally:
                            painter.end()
                else:
                    break
            else:
                gui.display_widget.lyric_widget.text = f'{text[verse_index][0]} {text[verse_index][1]}'
                if painter.begin(image):
                    try:
                        lyrics_rect, footer_height = gui.display_widget.lyric_widget.calculate_painted_text(painter)
                    finally:
                        painter.end()

            segment_indices[current_segment_index].append(verse_index)
            count += 1
            verse_index += 1

        if len(segment_indices[current_segment_index]) > 1:
            if not verse_index == len(text):
                segment_indices[current_segment_index].pop(len(segment_indices[current_segment_index]) - 1)
                verse_index -= 1
            elif verse_index == len(text) and lyrics_rect.height() > target_height:
                segment_indices[current_segment_index].pop(len(segment_indices[current_segment_index]) - 1)
                verse_index -= 1
        elif not verse_index == len(text):
            verse_index -= 1
        current_segment_index += 1"""

    # show an error message should parsing fail
    if parse_failed:
        QMessageBox.information(
            gui.main_window,
            'Scripture parsing failed',
            'A verse in this passage is too long to fit on the display screen. Consider decreasing the font '
            'size or use a higher resolution display.',
            QMessageBox.StandardButton.Ok
        )
        for verse in text:
            if len(verse[1].strip()) > 0:
                slide_texts.append(verse[0] + ' ' + verse[1])

    return slide_texts

def get_qcolor_from_str(main, font_color: str, slide_type: str):
    """
    Method to convert a string font color to a QColor object
    :param font_color: String font color (white, rgb(255, 255, 255), #ffffff, etc.)
    :param slide_type: The type of slide this color will be applied to
    :return QColor: QColor object
    """
    if font_color == 'white':
        font_color = QColor(Qt.GlobalColor.white)
    elif font_color == 'black':
        font_color = QColor(Qt.GlobalColor.black)
    elif '#' in font_color:
        color = font_color.replace('#', '')
        rgb_color = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
        font_color = QColor(rgb_color)
    elif 'rgb' in font_color or ',' in font_color:
        color = font_color.replace('rgb(', '').replace(')', '')
        font_color_split = color.split(', ')
        font_color = QColor(
            int(font_color_split[0]), int(font_color_split[1]), int(font_color_split[2]))
    else:
        if slide_type == 'song':
            if main.settings['song_font_color'] == 'black':
                font_color = QColor(0, 0, 0)
            elif main.settings['song_font_color'] == 'white':
                font_color = QColor(255, 255, 255)
            else:
                font_color_split = main.settings['font_color'].split(', ')
                font_color = QColor(
                    int(font_color_split[0]), int(font_color_split[1]), int(font_color_split[2]))
        else:
            if main.settings['bible_font_color'] == 'black':
                font_color = QColor(0, 0, 0)
            elif main.settings['bible_font_color'] == 'white':
                font_color = QColor(255, 255, 255)
            else:
                font_color_split = main.settings['bible_font_color'].split(', ')
                font_color = QColor(
                    int(font_color_split[0]), int(font_color_split[1]), int(font_color_split[2]))

    return font_color


class ParseScriptureReference:
    """
    Class to take a human-readable scripture reference and split/standardize it according to book, chapter(s) and verses
    """
    def __init__(self):
        """
        Class to take a human-readable scripture reference and split/standardize it according to book, chapter(s) and verses
        """
        # list of bible books and their common abbreviations
        self.books = [
            ['Genesis', 'gen', 'ge', 'gn'],
            ['Exodus', 'exod', 'exo', 'ex'],
            ['Leviticus', 'lev', 'le', 'lv'],
            ['Numbers', 'num', 'nu', 'nm', 'nb'],
            ['Deuteronomy', 'deut', 'de', 'dt'],
            ['Joshua', 'josh', 'jos', 'jsh'],
            ['Judges', 'judg', 'jg', 'jdgs'],
            ['Ruth', 'rth', 'ru'],
            ['1 Samuel', '1st samuel', '1 sa', '1sa', '1s', '1 sm', '1sm', '1st sam'],
            ['2 Samuel', '2nd samuel', '2 sa', '2sa', '2s', '2 sm', '2sm', '2nd sam'],
            ['1 Kings', '1st kings', '1 ki', '1ki', '1k', '1 kgs', '1kgs', '1st ki', '1st kgs'],
            ['2 Kings', '2nd kings', '2 ki', '2ki', '2k', '2 kgs', '2kgs', '2nd ki', '2nd kgs'],
            ['1 Chronicles', '1st chronicles', '1 ch', '1ch', '1 chron', '1chron', '1 chr', '1chr',
             '1st ch', '1st chron'],
            ['2 Chronicles', '2nd chronicles', '2 ch', '2ch', '2 chron', '2chron', '2 chr', '2chr',
             '2nd ch', '2nd chron'],
            ['Ezra', 'ezr', 'ez'],
            ['Nehemiah', 'neh', 'ne'],
            ['Esther', 'est', 'esth', 'es'],
            ['Job', 'jb'],
            ['Psalm', 'Psalms', 'psalm', 'ps', 'psa', 'psm', 'pss'],
            ['Proverbs', 'pro', 'pr', 'prv'],
            ['Ecclesiastes', 'eccles', 'eccle', 'ec', 'qoh'],
            ['Song of Solomon', 'song', 'so', 'sos', 'canticle of canticles', 'canticles', 'cant'],
            ['Isaiah', 'isa', 'is'],
            ['Jeremiah', 'jer', 'je', 'jr'],
            ['Lamentations', 'lam', 'la'],
            ['Ezekiel', 'ezek', 'eze', 'ezk'],
            ['Daniel', 'dan', 'da', 'dn'],
            ['Hosea', 'hos', 'ho'],
            ['Joel', 'joe', 'jl'],
            ['Amos', 'am'],
            ['Obadiah', 'obad', 'ob'],
            ['Jonah', 'jnh', 'jon'],
            ['Micah', 'mic', 'mc'],
            ['Nahum', 'nah', 'na'],
            ['Habakkuk', 'hab', 'hb'],
            ['Zephaniah', 'zep', 'zp'],
            ['Haggai', 'hag', 'hg'],
            ['Zechariah', 'zech', 'zec', 'zc'],
            ['Malachi', 'mal', 'ml'],
            ['Matthew', 'matt', 'mat', 'mt'],
            ['Mark', 'mk', 'mar', 'mrk', 'mr'],
            ['Luke', 'luk', 'lk'],
            ['John', 'joh', 'jhn', 'jn'],
            ['Acts', 'act', 'ac'],
            ['Romans', 'rom', 'ro', 'rm'],
            ['1 Corinthians', '1st corinthians', '1 cor', '1cor', '1 co', '1co', '1corinthians', '1st cor', '1st co'],
            ['2 Corinthians', '2nd corinthians', '2 cor', '2cor', '2 co', '2co', '2corinthians', '2nd cor', '2nd co'],
            ['Galatians', 'gal', 'ga'],
            ['Ephesians', 'ephes', 'eph'],
            ['Philippians', 'phil', 'php', 'pp'],
            ['Colossians', 'col', 'co'],
            ['1 Thessalonians', '1st thessalonians', '1 thes', '1thes', '1 th', '1th', '1thessalonians',
             '1st thes', '1st th'],
            ['2 Thessalonians', '2nd thessalonians', '2 thes', '2thes', '2 th', '2th', '2thessalonians',
             '2nd thes', '2nd th'],
            ['1 Timothy', '1st timothy', '1 tim', '1tim', '1 ti', '1ti', '1timothy', '1st tim', '1st ti'],
            ['2 Timothy', '2nd timothy', '2 tim', '2tim', '2 ti', '2ti', '2timothy', '2nd tim', '2nd ti'],
            ['Titus', 'tit', 'ti'],
            ['Philemon', 'philem', 'phm', 'pm'],
            ['Hebrews', 'heb'],
            ['James', 'jas', 'jm'],
            ['1 Peter', '1st peter', '1 pet', '1pet', '1 pe', '1pe', '1 pt', '1pt', '1 p', '1p',
             '1st pet', '1st pe', '1st pt', '1st p'],
            ['2 Peter', '2nd peter', '2 pet', '2pet', '2 pe', '2pe', '2 pt', '2pt', '2 p', '2p',
             '2nd pet', '2nd pe', '2nd pt', '2nd p'],
            ['1 John', '1st john', '1 jn', '1jn', '1 jo', '1jo', '1 joh', '1joh', '1 jhn', '1jhn', '1 j', '1j',
             '1st jn', '1st jo', '1st joh', '1st jhn'],
            ['2 John', '2nd john', '2 jn', '2jn', '2 jo', '2jo', '2 joh', '2joh', '2 jhn', '2jhn', '2 j', '2j',
             '2nd jn', '2nd jo', '2nd joh', '2nd jhn'],
            ['3 John', '3rd john', '3 jn', '3jn', '3 jo', '3jo', '3 joh', '3joh', '3 jhn', '3jhn', '3 j', '3j',
             '3rd jn', '3rd jo', '3rd joh', '3rd jhn'],
            ['Jude', 'jud', 'jd'],
            ['Revelation', 'rev', 're', 'the revelation']
        ]

        # list of bible books that have no chapters, only verses
        self.chapterless_books = [
            'obadiah',
            'obad',
            'ob',
            'philemon',
            'philem',
            'phm',
            'pm',
            '2 john',
            '2nd john',
            '2 jn',
            '2jn',
            '2 jo',
            '2jo',
            '2 joh',
            '2joh',
            '2 jhn',
            '2jhn',
            '2 j',
            '2j',
            '2nd jn',
            '2nd jo',
            '2nd joh',
            '2nd jhn',
            '3 john',
            '3rd john',
            '3 jn',
            '3jn',
            '3 jo',
            '3jo',
            '3 joh',
            '3joh',
            '3 jhn',
            '3jhn',
            '3 j',
            '3j',
            '3rd jn',
            '3rd jo',
            '3rd joh',
            '3rd jhn',
            'jude',
            'jud',
            'jd'
        ]

    def parse_reference(self, reference):
        """
        Provides a method to parse a human-readable scripture reference into its book, chapter(s) and verse(s),
        comparing the book to the commonly-used abbreviations defined in __init__ and determining if the book
        has no chapters. Returns a dictionary containing book, chapter_start, chapter_end, verse_start, verse_end,
        and a boolean stating whether the reference contains a book name that can be standardized.
        :param str reference: the scripture reference
        :return: dict
        """
        parsed_reference = {
            'book': '',
            'chapter_start': '',
            'chapter_end': '',
            'verse_start': '',
            'verse_end': '',
            'is_standardized_book': False
        }
        location = ''

        # first, split the reference at a space; check if the book includes a book number (i.e. 1 Corinthians)
        # store any information after the book name (which should be chapter/verse info) as the 'location'
        reference_split = reference.split(' ')
        if reference_split[0].isnumeric():
            parsed_reference['book'] = ' '.join(reference_split[0:2])
            if len(reference_split) > 2 and reference_split[2]:
                location = reference_split[2]
        else:
            parsed_reference['book'] = reference_split[0]
            if len(reference_split) > 1 and reference_split[1]:
                location = reference_split[1]

        start = ''
        end = ''
        if '-' not in location:
            start = location
        else:
            location_split = location.split('-')
            start = location_split[0]
            if len(location_split) > 1:
                end = location_split[1]

        if parsed_reference['book'].lower() in self.chapterless_books:
            parsed_reference['verse_start'] = start
            parsed_reference['verse_end'] = end
            parsed_reference['chapter_start'] = '1'
            parsed_reference['chapter_end'] = '1'
        else:
            if ':' not in start:
                parsed_reference['chapter_start'] = start
            else:
                start_split = start.split(':')
                parsed_reference['chapter_start'] = start_split[0]
                if len(start_split) > 1:
                    parsed_reference['verse_start'] = start_split[1]

            if ':' not in end:
                parsed_reference['verse_end'] = end
                parsed_reference['chapter_end'] = parsed_reference['chapter_start']
            else:
                end_split = end.split(':')
                if len(end_split[0]) > 0:
                    parsed_reference['chapter_end'] = end_split[0]
                else:
                    parsed_reference['chapter_end'] = parsed_reference['chapter_start']
                if len(end_split) > 1:
                    parsed_reference['verse_end'] = end_split[1]

        for item in self.books:
            for book in item:
                if parsed_reference['book'].lower() == book.lower():
                    parsed_reference['is_standardized_book'] = True

        return parsed_reference