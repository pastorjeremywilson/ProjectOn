class ParseScriptureReference:
    def __init__(self):
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
        parsed_reference = {
            'book': '',
            'chapter_start': '',
            'chapter_end': '',
            'verse_start': '',
            'verse_end': '',
            'is_standardized_book': False
        }
        location = ''

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

        if parsed_reference['book'] in self.chapterless_books:
            parsed_reference['verse_start'] = start
            parsed_reference['verse_end'] = end
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
