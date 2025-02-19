from argparse import ArgumentParser

import requests


BASE_URL = "https://api.themoviedb.org/3"


def query_tmdb_movie(api_key, movie_name):
    movie_query_url = f"{BASE_URL}/search/movie?query={movie_name}"

    movie_id_response = _make_request(api_key, movie_query_url)

    # The Movie DB search might do some fuzzy searching based on the movie name
    # given so print the name of the movie the results actually respond to.
    print(movie_id_response['results'][0]['title'])

    movie_id = movie_id_response["results"][0]["id"]

    movie_credit_url = f"{BASE_URL}/movie/{movie_id}/credits"

    credits_response = _make_request(api_key, movie_credit_url)

    # Limit the cast to 10.
    count = 0
    print("\tCast")
    for credit in credits_response["cast"]:
        print(f"\t\t{credit['name']}")

        # Follow the links for this person.
        person_id = credit['id']
        (cast_credits, _) = _query_tmdb_person_movie_credits(api_key, person_id)

        for cast_credit in cast_credits:
            if cast_credit.casefold() != movie_name.casefold():
                print(f"\t\t\t{cast_credit}")

        count = count + 1
        if count >= 10:
            break

    print("\tCrew")
    for credit in credits_response["crew"]:
        if (
            credit["job"] == "Director"
            or credit["job"] == "Writer"
            or credit["job"] == "Director of Photography"
            or credit["job"] == "Original Music Composer"
        ):
            print(f"\t\t{credit['name']} - {credit['job']}")

            # Follow the links for this person.
            person_id = credit['id']
            (cast_credits, _) = _query_tmdb_person_movie_credits(api_key, person_id)

            for film in cast_credits:
                if film.casefold() != movie_name.casefold():
                    print(f"\t\t\t{film}")


def query_tmdb_person(api_key, person):
    person_query_url = f"{BASE_URL}/search/person?query={person}"

    person_response = _make_request(api_key, person_query_url)

    # The Movie DB search might do some fuzzy searching based on the name
    # given so print the name of the person the results actually respond to.
    print(person_response['results'][0]['name'])

    # Get the person's ID to then get their movie credits.
    person_id = person_response['results'][0]['id']

    (cast_credits, crew_credits) = _query_tmdb_person_movie_credits(api_key, person_id)

    if cast_credits:
        print("\tCast")
        [print(f"\t\t{film}") for film in cast_credits]

    if crew_credits:
        print("\tCrew")
        [print(f"\t\t{film}") for film in crew_credits]


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


def _parse_movie_credits(films):
    # Filter out any documentaries (whose genre ID is 99).
    films = list(filter(lambda x: 99 not in x['genre_ids'], films))

    # Movie credits may contain duplicates, particular for crew credits, so filter them out via a set.
    return list(set([film['title'] for film in films]))


def _query_tmdb_person_movie_credits(api_key, person_id):
    movie_credits_query_url = f"{BASE_URL}/person/{person_id}/movie_credits"

    movie_credits_response = _make_request(api_key, movie_credits_query_url)

    cast_credits = _parse_movie_credits(movie_credits_response["cast"])
    crew_credits = _parse_movie_credits(movie_credits_response["crew"])

    return cast_credits, crew_credits


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
