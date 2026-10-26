import os
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from font_patch import (FONT_SOURCE, INPUT_SHA256, NEW_FONT_SHA256, REQUIRED_CHARS,
                        Invalid, patch, sfnt_has_characters)
from native import Serialized
from storage import sha


class FontPatchTests(unittest.TestCase):
    def setUp(self):
        self.font = FONT_SOURCE.read_bytes()

    def test_vendored_font_and_portuguese_characters(self):
        self.assertEqual(sha(self.font), NEW_FONT_SHA256)
        sfnt_has_characters(self.font, REQUIRED_CHARS + "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")

    def test_missing_characters_and_malformed_font_rejected(self):
        with self.assertRaisesRegex(Invalid, "FONT_MISSING_GLYPHS"):
            sfnt_has_characters(self.font, "\u4e00")
        with self.assertRaisesRegex(Invalid, "FONT_FORMAT"):
            sfnt_has_characters(b"invalid", "A")

    def test_unrecognized_source_rejected(self):
        with self.assertRaisesRegex(Invalid, "SOURCE_MISMATCH"):
            patch(b"not the accepted asset", self.font)

    def test_original_game_resource_when_supplied(self):
        supplied = os.environ.get("PLAYABLE_ARCHIVE_FONT_SOURCE")
        if not supplied:
            self.skipTest("Set PLAYABLE_ARCHIVE_FONT_SOURCE to the original sharedassets0.assets")
        original = Path(supplied).read_bytes()
        self.assertEqual(sha(original), INPUT_SHA256)
        output = patch(original, self.font)
        old = Serialized(original)
        new = Serialized(output)
        before = {o.path_id: old.payload(o) for o in old.objects}
        after = {o.path_id: new.payload(o) for o in new.objects}
        self.assertEqual(set(before), set(after))
        self.assertEqual([key for key in before if before[key] != after[key]], [133])
        self.assertIn(self.font, after[133])
        with self.assertRaisesRegex(Invalid, "FONT_MISMATCH"):
            patch(original, self.font[:-1])


if __name__ == "__main__":
    unittest.main()
