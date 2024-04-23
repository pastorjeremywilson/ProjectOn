import re
import xml.etree.ElementTree as ET
from os.path import exists


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
        # create a xml tree from the program's default bible
        if main.gui.default_bible and exists(main.gui.default_bible):
            try:
                tree = ET.parse(main.gui.default_bible)
                self.root = tree.getroot()
            except Exception:
                main.error_log()

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
            ['Psalms', 'psalm', 'ps', 'psa', 'psm', 'pss'],
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

    def get_passage(self, reference):
        """
        Method to parse the user's inputted reference and retrieve the passage from the user's xml bible.
        :param str reference: The user-provided scripture reference
        """
        scripture_text = []
        if self.root:
            reference_split = reference.split(' ')
            passage = ''
            reference_ok = False
            # only attempt to retrieve a passage if something more than the book has been provided
            if not len(reference_split) > 1:
                print('not enough info to find passage; aborting')
                return -1
            else:
                # some book names will be a number followed by a string (i.e. 1 Kings or 1st Corinthians)
                if any(a.isnumeric() for a in reference_split[0]) and all(b.isalpha() for b in reference_split[1]):
                    book = reference_split[0] + ' ' + reference_split[1]
                    passage = ' '.join(reference_split[2:])
                # a reference_split with no numbers in the second position likely means that two or more words were
                # given for the book (i.e. Song of Solomon, The Revelation)
                else:
                    if not any(c.isnumeric() for c in reference_split[1]):
                        book = reference_split[0] + ' ' + reference_split[1]
                        passage = ' '.join(reference_split[2:])
                        if len(reference_split) > 2:
                            if not any(d.isnumeric() for d in reference_split[2]):
                                book += ' ' + reference_split[2]
                                passage = ' '.join(reference_split[3:])
                    else:
                        book = reference_split[0]
                        passage = ' '.join(reference_split[1:])

                if passage == '':
                    print('no verses found; aborting')
                    return -1

                #supply chapter 1 for books with no chapters
                if book.lower() in self.chapterless_books:
                    passage = '1:' + passage

                # Now that the book has been stripped from the reference, parse the chapter and verse(s)
                # Check for a comma separating two different ranges
                if ',' in passage:
                    ranges = passage.split(',')
                elif passage.count(':') > 1:
                    if '-' in passage:
                        ranges = passage.split('-')
                    elif '–' in passage:
                        ranges = passage.split('–')
                    ranges[0] = ranges[0] + '-200'
                    ranges[1] = ranges[1].split(':')[0] + ':1-' + ranges[1].split(':')[1]
                else:
                    ranges = [passage]

                chapters = []
                start_end = []
                for i in range(len(ranges)):
                    reference_ok = False
                    verse_split = []

                    range_split = ranges[i].split(':')

                    if len(range_split) > 1:
                        chapters.append(range_split[0].strip())
                    else:
                        chapters.append('')
                        range_split.append(range_split[0].strip())

                    if '-' in range_split[1]:
                        verse_split = range_split[1].split('-')
                    elif '–' in range_split[1]:
                        verse_split = range_split[1].split('–')
                    else:
                        verse_split = [range_split[1]]

                    if len(verse_split) > 1:
                        start_end.append([verse_split[0].strip(), verse_split[1].strip()])
                        reference_ok = True
                    elif all(d.isnumeric for d in str(range_split[1])):
                        start_end.append([verse_split[0].strip(), verse_split[0].strip()])
                        reference_ok = True

            # go on to get the passage from the xml bible if the parsing worked out
            if reference_ok:
                book = book.replace('.', '')
                book = book.lower()
                this_verse = ''

                for i in range(len(chapters)):
                    chapter = chapters[i]
                    start_verse = start_end[i][0]
                    end_verse = start_end[i][1]

                    if chapter == '':
                        if i > 0:
                            chapter = chapters[i - 1]
                        else:
                            print('no chapter number; aborting')
                            return -1

                    standard_book = None
                    book_number = None
                    for j in range(len(self.books)):
                        for k in range(len(self.books[j])):
                            if book == self.books[j][k].lower():
                                standard_book = self.books[j][0]
                                book_number = j + 1

                    if standard_book:
                        book_element = None
                        for child in self.root:
                            if child.get('bname'):
                                if child.get('bname') == standard_book:
                                    book_element = child
                            if not book_element:
                                if child.get('bnumber'):
                                    if child.get('bnumber') == str(book_number):
                                        book_element = child

                        if book_element:
                            chapter_element = None
                            for child in book_element:
                                if child.get('cnumber') == str(chapter):
                                    chapter_element = child

                            if not chapter_element:
                                print('unable to get chapter; aborting')
                                return -1

                            for child in chapter_element:
                                try:
                                    if int(child.get('vnumber')) >= int(start_verse) and int(child.get('vnumber')) <= int(end_verse):
                                        this_verse = child.get('vnumber') + ' ' + child.text + ' '
                                        scripture_text.append(re.sub('\s+', ' ', this_verse).strip() + ' ')
                                except ValueError:
                                    print('missing verse value; aborting')
                                    return -1

                        else:
                            print('unable to find book element; aborting')
                            return -1
                    else:
                        print('unable to standardize book; aborting')
                        return -1

            else:
                print('unable to parse reference; aborting')
                return -1

        if len(scripture_text) > 0:
            return (standard_book, scripture_text)
        else:
            print('scripture text not found; aborting')
            return -1
