DB_STRUCTURE = {
    'backgroundThumbnails': {
        'fileName': 'TEXT',
        'image': 'BLOB'
    },
    'customSlides': {
        'title': 'TEXT',
        'text': 'TEXT',
        'font': 'TEXT',
        'fontColor': 'TEXT',
        'background': 'TEXT',
        'font_size': 'TEXT',
        'use_shadow': 'TEXT',
        'shadow_color': 'TEXT',
        'shadow_offset': 'TEXT',
        'use_outline': 'TEXT',
        'outline_color': 'TEXT',
        'outline_width': 'TEXT',
        'override_global': 'TEXT',
        'use_shade': 'TEXT',
        'shade_color': 'TEXT',
        'shade_opacity': 'TEXT',
        'audio_file': 'TEXT',
        'loop_audio': 'TEXT',
        'auto_play': 'TEXT',
        'slide_delay': 'TEXT',
        'split_slides': 'TEXT'
    },
    'imageThumbnails': {
        'fileName': 'TEXT',
        'image': 'BLOB'
    },
    'songs': {
        'title': 'TEXT',
        'author': 'TEXT',
        'copyright': 'TEXT',
        'ccliNum': 'TEXT',
        'lyrics': 'TEXT',
        'vorder': 'TEXT',
        'footer': 'TEXT',
        'font': 'TEXT',
        'fontColor': 'TEXT',
        'background': 'TEXT',
        'font_size': 'TEXT',
        'use_shadow': 'TEXT',
        'shadow_color': 'TEXT',
        'shadow_offset': 'TEXT',
        'use_outline': 'TEXT',
        'outline_color': 'TEXT',
        'outline_width': 'TEXT',
        'override_global': 'TEXT',
        'use_shade': 'TEXT',
        'shade_color': 'TEXT',
        'shade_opacity': 'TEXT'
    },
    'web': {
        'title': 'TEXT',
        'url': 'TEXT'
    }
}

SLIDE_DATA_DEFAULTS = {
    'type': '',
    'title': '',
    'author': '',
    'copyright': '',
    'ccli_song_number': '',
    'text': '',
    'parsed_text': '',
    'verse_order': '',
    'use_footer': True,
    'override_global': False,
    'font_family': 'Arial',
    'font_size': 72,
    'font_color': 'black',
    'background': '',
    'use_shadow': True,
    'shadow_color': 0,
    'shadow_offset': 6,
    'use_outline': True,
    'outline_color': 0,
    'outline_width': 3,
    'use_shade': False,
    'shade_color': 0,
    'shade_opacity': 50,
    'audio_file': '',
    'loop_audio': True,
    'split_slides': False,
    'auto_play': False,
    'slide_delay': 6,
    'file_name': '',
    'url': ''
}

SQL_COLUMN_TO_DICTIONARY_SONG = {
    0: 'title',
    1: 'author',
    2: 'copyright',
    3: 'ccli_song_number',
    4: 'text',
    5: 'verse_order',
    6: 'footer',
    7: 'font_family',
    8: 'font_color',
    9: 'background',
    10: 'font_size',
    11: 'use_shadow',
    12: 'shadow_color',
    13: 'shadow_offset',
    14: 'use_outline',
    15: 'outline_color',
    16: 'outline_width',
    17: 'override_global',
    18: 'use_shade',
    19: 'shade_color',
    20: 'shade_opacity'
}

SQL_COLUMN_TO_DICTIONARY_CUSTOM = {
    0: 'title',
    1: 'text',
    2: 'font',
    3: 'font_color',
    4: 'background',
    5: 'font_size',
    6: 'use_shadow',
    7: 'shadow_color',
    8: 'shadow_offset',
    9: 'use_outline',
    10: 'outline_color',
    11: 'outline_width',
    12: 'override_global',
    13: 'use_shade',
    14: 'shade_color',
    15: 'shade_opacity',
    16: 'audio_file',
    17: 'loop_audio',
    18: 'auto_play',
    19: 'slide_delay',
    20: 'split_slides'
}