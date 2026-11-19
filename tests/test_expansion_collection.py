"""Integration checks for the dated, complete-poem expansion."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from anskar.archive.importer import import_collection
from anskar.archive.repository import list_eligible
from anskar.config import PROJECT_ROOT
from anskar.db import connect
from anskar.instagram.posts import compose

COLLECTION = PROJECT_ROOT / "data/collections/varied-public-domain-2026-10-24.json"


class ExpansionCollectionTests(unittest.TestCase):
    def test_import_preserves_every_poem_and_is_idempotent(self):
        entries = json.loads(COLLECTION.read_text(encoding="utf-8"))["poems"]
        self.assertEqual(len(entries), 300)
        self.assertEqual(len({p["author"] for p in entries}), 11)
        self.assertEqual(len({(p["author"], p["title"]) for p in entries}), 300)
        with tempfile.TemporaryDirectory() as directory:
            with connect(Path(directory) / "archive.sqlite") as connection:
                first = import_collection(connection, COLLECTION, on=date(2026, 10, 24))
                self.assertEqual((first.imported, first.duplicates, first.rejected), (300, 0, ()))
                rows = connection.execute("SELECT * FROM poems ORDER BY id").fetchall()
                self.assertEqual(len(list_eligible(connection)), 300)
                for entry, row in zip(entries, rows, strict=True):
                    self.assertEqual(row["body"], entry["body"])
                    self.assertEqual(row["title"], entry["title"])
                    self.assertEqual(row["commercial_use_sweden"], "yes")
                    self.assertEqual(row["rights_verification_status"], "documented")
                    self.assertIsNone(row["translator"])
                    self.assertTrue(row["author_death_year_source"])
                    self.assertNotIn("PROJECT GUTENBERG", row["body"])
                before = [tuple(row) for row in rows]
                again = import_collection(connection, COLLECTION, on=date(2026, 10, 24))
                self.assertEqual((again.imported, again.duplicates, again.rejected), (0, 300, ()))
                self.assertEqual(before, [tuple(r) for r in connection.execute("SELECT * FROM poems ORDER BY id")])
                self.assertEqual(connection.execute("SELECT count(*) FROM selection_history").fetchone()[0], 0)

    def test_all_complete_poems_fit_actual_instagram_composer(self):
        entries = json.loads(COLLECTION.read_text(encoding="utf-8"))["poems"]
        for poem in entries:
            with self.subTest(author=poem["author"], title=poem["title"]):
                post = compose({
                    "rights": {"matched": True, "title": poem["title"], "author": poem["author"]},
                    "source_text": poem["body"],
                }, etsy_url="https://www.etsy.com/shop/Anskarartprints")
                self.assertIn(poem["body"].strip(), post["caption"])
                self.assertLessEqual(len(post["caption"]), 2200)


if __name__ == "__main__":
    unittest.main()
