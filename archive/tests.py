import unittest
import sys
from PySide6.QtWidgets import QApplication
from main import ShirPoetApp
import model

# Initialize the application instance once for UI testing
app = QApplication.instance() or QApplication(sys.argv)


class PoetryTest(unittest.TestCase):

    def test_logic(self):
        """Check the 'brain' of the app: syllables, rhymes, and predictions."""
        # Does it count syllables correctly?
        self.assertEqual(model._syllable_count("night"), 1)
        self.assertEqual(model._syllable_count("poetry"), 3)

        # Does it detect rhymes based on the last two letters?
        self.assertTrue(model.DummyPoetryModel._rhymes("light", "night"))

        # Does the model suggest a word from the vocabulary?
        suggestion = model.predict("sky")
        self.assertIn(suggestion, model.DEFAULT_VOCABULARY)

    def test_interface(self):
        """Check if the window opens and the AI button is integrated."""
        window = ShirPoetApp()

        # Is the text editor created?
        self.assertIsNotNone(window.editor)

        # Is the window title correct?
        self.assertEqual(window.windowTitle(), "ShirPoetRe.b")

        # Is the AI action added to the window?
        self.assertTrue(hasattr(window, 'ai_action'))

        window.close()


if __name__ == "__main__":
    # Run tests and capture results
    suite = unittest.TestLoader().loadTestsFromTestCase(PoetryTest)
    result = unittest.TextTestRunner(verbosity=0).run(suite)

    # Clean summary output
    if result.wasSuccessful():
        print("\n" + "=" * 40)
        print("✅ ALL TESTS PASSED SUCCESSFULLY!")
        print("-" * 40)
        print(f"Total tests run: {result.testsRun}")
        print("1. Syllable & Rhyme logic  -> OK")
        print("2. Word prediction system  -> OK")
        print("3. UI Initialization       -> OK")
        print("4. AI Action integration   -> OK")
        print("=" * 40)
    else:
        print("\n❌ Tests failed. Please check the logs above.")
        sys.exit(1)