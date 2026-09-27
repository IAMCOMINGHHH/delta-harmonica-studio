import unittest

from desktop_player import KEY_VKS, note_actions, parse_score


class ScoreTests(unittest.TestCase):
    def test_parser_tracks_timing_and_extensions(self):
        notes, total = parse_score("1 #2 3/2 0 4' - 5,")
        self.assertEqual([n.token for n in notes], ["1", "#2", "3/2", "4'", "5,"])
        self.assertEqual(notes[2].duration, 0.5)
        self.assertEqual(notes[3].duration, 2)
        self.assertEqual(total, 6.5)

    def test_actions_use_mouse_modifiers_and_expected_keys(self):
        notes, _ = parse_score("#6, 1'")
        self.assertEqual(note_actions(notes[0]), (["left", "middle"], KEY_VKS[5]))
        self.assertEqual(note_actions(notes[1]), ([], KEY_VKS[7]))


if __name__ == "__main__":
    unittest.main()
