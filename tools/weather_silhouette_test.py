#!/usr/bin/env python3
"""Check that the capture analyser rejects lost contrast and a missing body."""
import unittest
from PIL import Image, ImageDraw
from weather_silhouette_check import body_mask, measure, MIN_CONTRAST


class SilhouetteAnalysis(unittest.TestCase):
    def setUp(self):
        self.background = Image.new('RGB', (160, 120), (65, 80, 70))
        self.debug = self.background.copy()
        ImageDraw.Draw(self.debug).rectangle((65, 30, 94, 89), fill=(240, 0, 240))
        # Changed rain/foliage and a detached debug speck must not join Link.
        ImageDraw.Draw(self.debug).rectangle((8, 8, 11, 11), fill=(240, 0, 240))
        self.mask = body_mask(self.debug, self.background)

    def test_readable_body(self):
        visible = self.background.copy()
        ImageDraw.Draw(visible).rectangle((65, 30, 94, 89), fill=(150, 150, 120))
        result = measure(visible, self.background, self.mask)
        self.assertGreater(result['contrast'], MIN_CONTRAST)
        self.assertGreater(result['paired_separation'], MIN_CONTRAST)
        self.assertEqual(self.mask.getpixel((9, 9)), 0)
        self.assertEqual(self.mask.getpixel((80, 60)), 255)

    def test_camouflaged_body_fails(self):
        result = measure(self.background, self.background, self.mask)
        self.assertLess(result['contrast'], MIN_CONTRAST)
        self.assertLess(result['paired_separation'], MIN_CONTRAST)

    def test_unmatched_background_fails(self):
        unrelated = Image.new('RGB', self.background.size, (180, 180, 180))
        with self.assertRaisesRegex(AssertionError, 'unmatched background'):
            measure(unrelated, self.background, self.mask)

    def test_missing_body_fails(self):
        with self.assertRaises(AssertionError):
            body_mask(self.background, self.background)


if __name__ == '__main__':
    unittest.main()
