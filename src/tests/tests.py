import random
import unittest
import core.projectOn
from dataHandling.declarations import SLIDE_DATA_DATA_TYPES


class MyTestCase(unittest.TestCase):
    def test_song_data_types(self):
        song_title = 'Ah Lord God'
        da = core.projectOn.DatabaseAccess('/home/jeremy/LBCN/Nampa/ProjectOn Services/testData/projecton.db')
        connection, cursor = da.get_connection()
        song_titles = cursor.execute('SELECT title FROM songs').fetchall()
        random_songs = random.choices(song_titles, k=5)
        print(random_songs)

        for song_title in random_songs:
            song_title = song_title[0]
            result = da.get_song_data(song_title)
            self.assertIsInstance(result, dict)
            self.assertEqual(set(result.keys()), set(SLIDE_DATA_DATA_TYPES.keys()))
        
            for key in result.keys():
                with self.subTest(key=key):
                    self.assertIsInstance(result[key], SLIDE_DATA_DATA_TYPES[key])

if __name__ == '__main__':
    unittest.main()
