from unittest import TestCase

import pytest

from tmdbquery import _parse_movie_credits, find_link, query_tmdb_person


class TestTmdbQuery(TestCase):
    @pytest.fixture(autouse=True)
    def capsys(self, capsys):
        self.capsys = capsys

    def test_find_link_returns_early_if_movie_names_are_the_same(self):
        find_link("apikey", "movie", "movie")
        out, _ = self.capsys.readouterr()

        self.assertEqual(
            "Must provide two different movies to find link between\n", out
        )

    def test_parse_movie_credits_removes_documentaries(self):
        test_movies = [
            {"title": "NotDocumentary", "genre_ids": [28]},
            {"title": "Documentary", "genre_ids": [99]},
            {"title": "PartDocumentary", "genre_ids": [28, 99]},
        ]

        filtered_movies = _parse_movie_credits(test_movies)

        self.assertEqual(1, len(filtered_movies))
        self.assertEqual(test_movies[0]["title"], filtered_movies[0])

    def test_parse_movie_credits_removes_duplicates(self):
        test_movies = [
            {"title": "FirstMovie", "genre_ids": [28]},
            {"title": "SecondMovie", "genre_ids": [28]},
            {"title": "FirstMovie", "genre_ids": [28]},
        ]

        filtered_movies = _parse_movie_credits(test_movies)

        self.assertEqual(2, len(filtered_movies))
        self.assertIn(test_movies[0]["title"], filtered_movies)
        self.assertIn(test_movies[1]["title"], filtered_movies)

    def test_query_tmdb_person_returns_expected_output(self):
        query_tmdb_person("apikey", "person")
        out, _ = self.capsys.readouterr()

        print(out)

        self.assertFalse(True)
