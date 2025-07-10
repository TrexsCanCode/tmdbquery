from unittest import TestCase

import pytest

from tmdbquery import _filter_movies, _generate_movie_title, _parse_movie_cast_credits, _parse_movie_crew_credits, find_link


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

    def test_find_link_returns_early_if_movie_titles_are_the_same(self):
        find_link("apikey", "movie", "movie")
        out, _ = self.capsys.readouterr()

        self.assertEqual(
            "Must provide two different movies to find link between\n", out
        )

    def test_filter_movies_removes_documentaries(self):
        release_year = 2000
        test_movies = [
            {"title": "NotDocumentary", "genre_ids": [28], "release_date": f"{release_year}-01-01", "vote_count": 20},
            {"title": "Documentary", "genre_ids": [99], "release_date": f"{release_year}-01-01", "vote_count": 20},
            {"title": "PartDocumentary", "genre_ids": [28, 99], "release_date": f"{release_year}-01-01", "vote_count": 20},
        ]

        filtered_movies = _filter_movies(test_movies)

        self.assertEqual(1, len(filtered_movies))
        self.assertEqual(test_movies[0], filtered_movies[0])

    def test_filter_movies_removes_movies_with_vote_count_greater_than_10(self):
        release_year = 2000
        test_movies = [
            {"title": "PopularMovie", "genre_ids": [28], "release_date": f"{release_year}-01-01", "vote_count": 10},
            {"title": "NotSoPopularMovie", "genre_ids": [30], "release_date": f"{release_year}-01-01", "vote_count": 9},
            {"title": "VeryPopularMovie", "genre_ids": [28], "release_date": f"{release_year}-01-01", "vote_count": 20},
        ]

        filtered_movies = _filter_movies(test_movies)

        self.assertEqual(1, len(filtered_movies))
        self.assertEqual(test_movies[2], filtered_movies[0])

    def test_parse_movie_cast_credits_returns_expected_result(self):
        release_year = 2000
        test_movies = [
            {"title": "NotDocumentary", "genre_ids": [28], "release_date": f"{release_year}-01-01", "vote_count": 20},
            {"title": "Documentary", "genre_ids": [99], "release_date": f"{release_year}-01-01", "vote_count": 20},
            {"title": "PartDocumentary", "genre_ids": [28, 99], "release_date": f"{release_year}-01-01", "vote_count": 20},
        ]

        parsed_movies = _parse_movie_cast_credits(test_movies)

        self.assertEqual(1, len(parsed_movies))
        self.assertEqual(f"{test_movies[0]['title']} ({release_year})", parsed_movies[0])

    def test_parse_movie_crew_credits_returns_empty_dict_if_no_jobs_match_interested_jobs(self):
        release_year = 2000
        test_movies = [
            {"title": "Movie1", "genre_ids": [28], "release_date": f"{release_year}-01-01", "vote_count": 20, "job": "handyman"},
            {"title": "Movie2", "genre_ids": [28], "release_date": f"{release_year}-01-01", "vote_count": 20, "job": "coach"},
            {"title": "Movie3", "genre_ids": [28], "release_date": f"{release_year}-01-01", "vote_count": 20, "job": "man"},
        ]

        parsed_movies = _parse_movie_crew_credits(test_movies)

        self.assertEqual(0, len(parsed_movies))

    def test_parse_movie_crew_credits_returns_expected_result(self):
        release_year = 2000
        test_movies = [
            {"title": "Movie1", "genre_ids": [28], "release_date": f"{release_year}-01-01", "vote_count": 20, "job": "Director"},
            {"title": "Movie2", "genre_ids": [28], "release_date": f"{release_year}-01-01", "vote_count": 20, "job": "Writer"},
            {"title": "Movie3", "genre_ids": [28], "release_date": f"{release_year}-01-01", "vote_count": 20, "job": "man"},
        ]

        parsed_movies = _parse_movie_crew_credits(test_movies)

        self.assertEqual(2, len(parsed_movies))
        self.assertIsNotNone(parsed_movies[f"{test_movies[0]['title']} ({release_year})"])
        self.assertEqual(["Director"], parsed_movies[f"{test_movies[0]['title']} ({release_year})"])
        self.assertIsNotNone(parsed_movies[f"{test_movies[1]['title']} ({release_year})"])
        self.assertEqual(["Writer"], parsed_movies[f"{test_movies[1]['title']} ({release_year})"])

    def test_parse_movie_crew_credits_with_multiple_jobs_for_same_movie_returns_expected_result(self):
        release_year = 2000
        test_movies = [
            {"title": "Movie1", "genre_ids": [28], "release_date": f"{release_year}-01-01", "vote_count": 20, "job": "Director"},
            {"title": "Movie1", "genre_ids": [28], "release_date": f"{release_year}-01-01", "vote_count": 20, "job": "Writer"},
            {"title": "Movie2", "genre_ids": [28], "release_date": f"{release_year}-01-01", "vote_count": 20, "job": "Writer"},
            {"title": "Movie3", "genre_ids": [28], "release_date": f"{release_year}-01-01", "vote_count": 20, "job": "man"},
        ]

        parsed_movies = _parse_movie_crew_credits(test_movies)

        self.assertEqual(2, len(parsed_movies))
        self.assertIsNotNone(parsed_movies[f"{test_movies[0]['title']} ({release_year})"])
        self.assertEqual(["Director", "Writer"], parsed_movies[f"{test_movies[0]['title']} ({release_year})"])
        self.assertIsNotNone(parsed_movies[f"{test_movies[2]['title']} ({release_year})"])
        self.assertEqual(["Writer"], parsed_movies[f"{test_movies[2]['title']} ({release_year})"])
