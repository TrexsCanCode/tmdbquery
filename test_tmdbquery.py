from unittest import TestCase

import pytest

from tmdbquery import _generate_movie_title, _parse_movie_credits, find_link


class TestTmdbQuery(TestCase):
    @pytest.fixture(autouse=True)
    def capsys(self, capsys):
        self.capsys = capsys

    def test_generate_movie_title_returns_title_with_no_year_if_no_release_date_set(self):
        movie_title = "Movie"

        test_movie = {"title": movie_title, "release_date": ""}

        self.assertEqual(movie_title, _generate_movie_title(test_movie))

    def test_generate_movie_title_returns_title_with_year_if_release_date_set(self):
        movie_title = "Movie"
        release_year = 2000

        test_movie = {"title": movie_title, "release_date": f"{release_year}-01-01"}

        generated_movie_title = _generate_movie_title(test_movie)

        self.assertEqual(f"{movie_title} ({release_year})", generated_movie_title)

    def test_find_link_returns_early_if_movie_names_are_the_same(self):
        find_link("apikey", "movie", "movie")
        out, _ = self.capsys.readouterr()

        self.assertEqual(
            "Must provide two different movies to find link between\n", out
        )

    def test_parse_movie_credits_removes_documentaries(self):
        release_year = 2000
        test_movies = [
            {"title": "NotDocumentary", "genre_ids": [28], "release_date": f"{release_year}-01-01", "vote_count": 20},
            {"title": "Documentary", "genre_ids": [99], "release_date": f"{release_year}-01-01", "vote_count": 20},
            {"title": "PartDocumentary", "genre_ids": [28, 99], "release_date": f"{release_year}-01-01", "vote_count": 20},
        ]

        filtered_movies = _parse_movie_credits(test_movies)

        self.assertEqual(1, len(filtered_movies))
        self.assertEqual(f"{test_movies[0]['title']} ({release_year})", filtered_movies[0])

    def test_parse_movie_credits_removes_duplicates(self):
        release_year = 2000
        test_movies = [
            {"title": "FirstMovie", "genre_ids": [28], "release_date": f"{release_year}-01-01", "vote_count": 20},
            {"title": "SecondMovie", "genre_ids": [28], "release_date": f"{release_year}-01-01", "vote_count": 20},
            {"title": "FirstMovie", "genre_ids": [28], "release_date": f"{release_year}-01-01", "vote_count": 20},
        ]

        filtered_movies = _parse_movie_credits(test_movies)

        self.assertEqual(2, len(filtered_movies))
        self.assertIn(f"{test_movies[0]['title']} ({release_year})", filtered_movies)
        self.assertIn(f"{test_movies[1]['title']} ({release_year})", filtered_movies)
