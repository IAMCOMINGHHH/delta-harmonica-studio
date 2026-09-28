import unittest

from desktop_player import KEY_VKS, compact_long_rests, note_actions, parse_score


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

    def test_fractional_rest_and_legato(self):
        notes, total = parse_score("1/2~ 0/2 2*1.5~ 0/2")
        self.assertEqual(total, 3.0)
        self.assertTrue(notes[0].legato)
        self.assertTrue(notes[1].legato)

    def test_compacts_only_long_rests(self):
        notes, _ = parse_score("1 0 2 0 0 0 0 3")
        compacted = compact_long_rests(notes, max_silence=2)
        self.assertEqual([note.beat for note in compacted], [0, 2, 5])


if __name__ == "__main__":
    unittest.main()
