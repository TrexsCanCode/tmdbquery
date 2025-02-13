from argparse import ArgumentParser

import requests


BASE_URL = "https://api.themoviedb.org/3"


def query_tmdb_movie(api_key, movie_name):
    movie_query_url = f"{BASE_URL}/search/movie?query={movie_name}"

    movie_id_response = _make_request(api_key, movie_query_url)
    movie_id = movie_id_response["results"][0]["id"]

    movie_credit_url = f"{BASE_URL}/movie/{movie_id}/credits"

    credits_response = _make_request(api_key, movie_credit_url)

    # need director, writer, composer, featuring (cast)
    # think cast is limited to 10.
    count = 0
    print("Cast")
    for credit in credits_response["cast"]:
        print(f"\t{credit['name']}")

        # Follow the links for this person.
        cast_query_url = f"{BASE_URL}/search/person?query={credit['name']}"

        cast_response = _make_request(api_key, cast_query_url)

        films = cast_response["results"][0]["known_for"]
        for film in films:
            if (
                film["media_type"] == "movie"
                and film["title"].casefold() != movie_name.casefold()
            ):
                print(f"\t\t{film['title']}")

        count = count + 1
        if count >= 10:
            break

    print("Crew")
    for credit in credits_response["crew"]:
        if (
            credit["job"] == "Director"
            or credit["job"] == "Writer"
            or credit["job"] == "Director of Photography"
            or credit["job"] == "Original Music Composer"
        ):
            print(f"\t{credit['name']} - {credit['job']}")

            # Follow the links for this person.
            crew_query_url = f"{BASE_URL}/search/person?query={credit['name']}"

            crew_response = _make_request(api_key, crew_query_url)

            films = crew_response["results"][0]["known_for"]
            for film in films:
                if (
                    film["media_type"] == "movie"
                    and film["title"].casefold() != movie_name.casefold()
                ):
                    print(f"\t\t{film['title']}")


def query_tmdb_person(api_key, person):
    person_query_url = f"{BASE_URL}/search/person?query={person}"

    person_response = _make_request(api_key, person_query_url)

    # The request might do some fuzzy searching based on the name given
    # so print the name of the person the results actually respond to.
    print(person_response['results'][0]['name'])

    films = person_response["results"][0]["known_for"]
    for film in films:
        if film["media_type"] == "movie":
            print(f"\t{film['title']}")


def _make_request(api_key, url):
    api_dict = {"api_key": api_key}

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "close",
    }

    response = requests.get(
        url,
        params=api_dict,
        headers=headers,
    )
    response.raise_for_status()

    return response.json()


if __name__ == "__main__":
    parser = ArgumentParser(prog="TMDB Query", description="Query TMDB for film links")

    parser.add_argument("--api_key", help="The TMDB API key")

    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument("--movie_name", help="The name of the movie to query")
    query_group.add_argument("--person", help="The name of the movie to query")

    args = parser.parse_args()

    # Either movie name or person must be set so don't need to check both values.
    if args.movie_name:
        query_tmdb_movie(args.api_key, args.movie_name)
    else:
        query_tmdb_person(args.api_key, args.person)
