from __future__ import annotations

import unittest

from app.organizer.file_classifier import get_category

class TestFileClassifier(unittest.TestCase):

    def test_classifies_image_files(self) -> None:
        for filename in ("photo.jpg", "image.png", "pic.gif", "art.webp"):
            self.assertEqual(
                get_category(filename),
                "Images",
                msg=f"{filename} should be Images",
            )

    def test_classifies_document_files(self) -> None:
        for filename in ("report.pdf", "notes.txt", "letter.doc", "doc.docx"):
            self.assertEqual(
                get_category(filename),
                "Documents",
                msg=f"{filename} should be Documents",
            )

    def test_handles_uppercase_extensions(self) -> None:
        self.assertEqual(get_category("photo.JPG"), "Images")
        self.assertEqual(get_category("REPORT.PDF"), "Documents")
        self.assertEqual(get_category("Song.MP3"), "Audio")

    def test_unknown_extensions_go_to_other(self) -> None:
        self.assertEqual(get_category("file.xyz"), "Other")
        self.assertEqual(get_category("mystery"), "Other")
        self.assertEqual(get_category("archive.tar.unknown"), "Other")

    def test_videos_audio_archives_programs(self) -> None:
        self.assertEqual(get_category("clip.mp4"), "Videos")
        self.assertEqual(get_category("song.wav"), "Audio")
        self.assertEqual(get_category("bundle.zip"), "Archives")
        self.assertEqual(get_category("installer.exe"), "Programs")

    def test_code_spreadsheets_presentations(self) -> None:
        self.assertEqual(get_category("script.py"), "Code")
        self.assertEqual(get_category("table.xlsx"), "Spreadsheets")
        self.assertEqual(get_category("slides.pptx"), "Presentations")

    def test_no_extension_is_other(self) -> None:
        self.assertEqual(get_category("README"), "Other")
        self.assertEqual(get_category(""), "Other")

if __name__ == "__main__":
    unittest.main()
