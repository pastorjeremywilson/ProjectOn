import re
import xml.etree.ElementTree as ET
from os.path import exists

from parse_scripture_reference import ParseScriptureReference


class GetScripture:
    """
    GetScripture is a class that will retrieve a specific scripture passage from the user's xml bible based on
    what is typed in the Scripture Reference LineEdit. The xml bible is expected to be in the Zefania XML Bible format.
    """
    root = None

    def __init__(self, main):
        """
        GetScripture is a class that will retrieve a specific scripture passage from the user's xml bible based on
        what is typed in the Scripture Reference LineEdit. The xml bible is expected to be in the Zefania XML Bible format.
        :param ProjectOn main: The current instance of ProjectOn
        """
        self.main = main

        # create a xml tree from the program's default bible
        if self.main.gui.default_bible and exists(self.main.gui.default_bible):
            try:
                tree = ET.parse(main.gui.default_bible)
                self.root = tree.getroot()
            except Exception:
                self.main.error_log()

    def get_passage(self, reference):
        """
        Method to parse the user's inputted reference and retrieve the passage from the user's xml bible.
        :param str reference: The user-provided scripture reference
        """
        scripture_text = []
        standard_book = None
        if self.root:
            reference_split = reference.split(' ')
            passage = ''
            reference_ok = False
            # only attempt to retrieve a passage if something more than the book has been provided
            if not len(reference_split) > 1:
                self.main.gui.media_widget.bible_search_status_label.setText('not enough info to find passage')
                return (-1, 'not enough info to find passage')

            # use ParseScriptureReference to retrieve book, chapters, verses from the reference
            psr = ParseScriptureReference()
            parsed_reference = psr.parse_reference(reference)

            if parsed_reference['verse_start'] == '':
                self.main.gui.media_widget.bible_search_status_label.setText('no verses found')
                return (-1, 'no verses found')

            #supply chapter 1 for books with no chapters
            if parsed_reference['book'].lower() in psr.chapterless_books:
                parsed_reference['chapter_start'] = '1'
                parsed_reference['chapter_end'] = '1'

            # go on to get the passage from the xml bible if the parsing worked out
            if parsed_reference['is_standardized_book']:
                this_verse = ''
                chapters = []

                # add multiple chapters to the chapters list if chapter end is different from chapter start
                if parsed_reference['chapter_end'] == parsed_reference['chapter_start']:
                    chapters = [parsed_reference['chapter_start']]
                else:
                    for i in range(int(parsed_reference['chapter_start']), int(parsed_reference['chapter_end']) + 1):
                        chapters.append(str(i))

                end_verse = 0
                for chapter in chapters:
                    for i in range(len(psr.books)):
                        for j in range(len(psr.books[i])):
                            if parsed_reference['book'].lower() == psr.books[i][j].lower():
                                standard_book = psr.books[i][0]
                                book_number = j + 1

                    if standard_book:
                        book_element = None
                        for child in self.root:
                            if child.get('bname'):
                                if child.get('bname').lower() == standard_book.lower():
                                    book_element = child

                        if book_element:
                            chapter_element = None
                            for child in book_element:
                                if child.get('cnumber') == str(chapter):
                                    chapter_element = child

                            if not chapter_element:
                                self.main.gui.media_widget.bible_search_status_label.setText('unable to get chapter')
                                return (-1, 'unable to get chapter')

                            for child in chapter_element:
                                try:
                                    # if more than one chapter is involved and we're not working on the last chapter
                                    # set the end verse rediculously high so that all verses to the end of the chapter
                                    # are fetched. Also, set the start verse to 1 if we're not on the first chapter.
                                    verse_start = int(parsed_reference['verse_start'])
                                    if parsed_reference['verse_end'] == '':
                                        verse_end = int(parsed_reference['verse_start'])
                                    else:
                                        verse_end = int(parsed_reference['verse_end'])

                                    if len(chapters) > 0:
                                        if not str(chapter) == parsed_reference['chapter_end']:
                                            verse_end = 300
                                        if not chapter == chapters[0]:
                                            verse_start = 1

                                    if (verse_start <= int(child.get('vnumber')) <= verse_end):
                                        verse_number = child.get('vnumber')
                                        this_verse = child.text
                                        scripture_text.append(
                                            [
                                                verse_number,
                                                re.sub('\s+', ' ', this_verse).strip() + ' '
                                            ]
                                        )
                                except ValueError:
                                    self.main.gui.media_widget.bible_search_status_label.setText('missing verse value')
                                    return (-1, 'missing verse value')

                        else:
                            self.main.gui.media_widget.bible_search_status_label.setText('unable to find book element')
                            return (-1, 'unable to find book element')
                    else:
                        self.main.gui.media_widget.bible_search_status_label.setText('unable to standardize book')
                        return (-1, 'unable to standardize book')

            else:
                self.main.gui.media_widget.bible_search_status_label.setText('unable to parse reference')
                return (-1, 'unable to parse reference')

        if len(scripture_text) > 0:
            self.main.gui.media_widget.bible_search_status_label.clear()
            return (standard_book, scripture_text)
        else:
            self.main.gui.media_widget.bible_search_status_label.setText('scripture text not found')
            return (-1, 'scripture text not found')
