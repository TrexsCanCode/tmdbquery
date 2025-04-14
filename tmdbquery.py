from argparse import ArgumentParser, Namespace
from os import environ
from typing import Any, Dict, List, Tuple

import requests
from requests import Response
from requests.exceptions import HTTPError


BASE_URL: str = "https://api.themoviedb.org/3"

# List of the crew roles that we are interested in.
REQUIRED_CREW_ROLES: List[str] = ["Director", "Writer", "Director of Photography", "Original Music Composer"]


def find_link(api_key: str, movie_from_name: str, movie_to_name: str) -> None:
    if movie_from_name == movie_to_name:
        print("Must provide two different movies to find link between")
        return

    (movie_from_name, movie_from_credits_response) = _query_movie_credits(api_key, movie_from_name)

    (movie_to_name, movie_to_credits_response) = _query_movie_credits(api_key, movie_to_name)

    # Get the list of cast from both films and compare them.
    cast_from_names: List[str] = [n.get('name') for n in movie_from_credits_response["cast"]]
    cast_to_names: List[str] = [n.get('name') for n in movie_to_credits_response["cast"]]

    common_cast: List[str] = list(set(cast_from_names).intersection(cast_to_names))

    # Get the list of crew from both films and compare them.
    crew_from_names: List[str] = [n.get('name') for n in movie_from_credits_response["crew"]]
    crew_to_names: List[str] = [n.get('name') for n in movie_to_credits_response["crew"]]

    common_crew: List[str] = list(set(crew_from_names).intersection(crew_to_names))

    if not common_cast and not common_crew:
        print(f"No links found between {movie_from_name} and {movie_to_name}")
    else:
        print(f"Found the following links between {movie_from_name} and {movie_to_name}:\n")
        if common_cast:
            print("Cast links:")
            [print(f"\t{cast}") for cast in common_cast]
        if common_crew:
            print("Crew links:")
            [print(f"\t{crew}") for crew in common_crew]


def query_tmdb_movie(api_key: str, movie_name: str) -> None:
    (movie_name, movie_credits_response) = _query_movie_credits(api_key, movie_name)

    print(movie_name)

    # Limit the cast to 10.
    count: int = 0
    print("\tCast")
    for credit in movie_credits_response["cast"]:
        print(f"\t\t{credit['name']}")

        # Follow the links for this person.
        person_id: int = credit['id']
        (cast_credits, _) = _query_person_movie_credits(api_key, person_id)
        cast_credits = list(filter(lambda x: x.casefold() != movie_name.casefold(), cast_credits))

        [print(f"\t\t\t{film}") for film in cast_credits]

        count = count + 1
        if count >= 10:
            break

    # Loop through the crew response, keeping track of who we have already requested.
    crew_credits_results: Dict[str, Tuple[List[str], List[str]]] = {}
    for credit in movie_credits_response["crew"]:
        crew_name: str = credit['name']
        crew_details = crew_credits_results.get(crew_name)
        if crew_details:
            # Have already got credits for this crew member so just add the new role to the role list.
            crew_details[0].append(credit['job'])
        else:
            # Haven't got this person's credits yet so follow the links for this person.
            person_id = credit['id']
            (cast_credits, crew_credits) = _query_person_movie_credits(api_key, person_id)

            # Create a combined list of both the cast and crew credits (with no duplicates).
            full_credits: List[str] = list(filter(lambda x: x.casefold() != movie_name.casefold(), cast_credits))
            full_credits.extend(x for x in crew_credits if x.casefold() != movie_name.casefold() and x not in full_credits)

            crew_credits_results[crew_name] = ([credit['job']], full_credits)

    # Now print out the crew credits.
    print("\tCrew")
    for name, (roles, credits) in crew_credits_results.items():
        print(f"\t\t{name} - {', '.join(roles)}")
        [print(f"\t\t\t{film}") for film in credits]


def query_tmdb_person(api_key: str, person: str) -> None:
    person_query_url: str = f"{BASE_URL}/search/person?query={person}"

    person_response: Any = _make_request(api_key, person_query_url)

    # The Movie DB search might do some fuzzy searching based on the name
    # given so print the name of the person the results actually respond to.
    print(person_response['results'][0]['name'])

    # Get the person's ID to then get their movie credits.
    person_id: int = person_response['results'][0]['id']

    (cast_credits, crew_credits) = _query_person_movie_credits(api_key, person_id)

    if cast_credits:
        print("\tCast")
        [print(f"\t\t{film}") for film in cast_credits]

    if crew_credits:
        print("\tCrew")
        [print(f"\t\t{film}") for film in crew_credits]


def _make_request(api_key: str, url: str) -> Any:
    api_dict: Dict[str, str] = {"api_key": api_key}

    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "close",
    }

    response: Response = requests.get(
        url,
        params=api_dict,
        headers=headers,
    )
    response.raise_for_status()

    return response.json()


def _parse_movie_credits(movie_credits: List[Any]) -> List[str]:
    # Filter out movies by the following:
    # * No documentaries (genre ID 99).
    # * Vote count must be greater than 10.
    movie_credits = list(
        filter(
            lambda x: 99 not in x['genre_ids'],
            filter(lambda x: x['vote_count'] > 10, movie_credits),
        )
    )

    # Movie credits may contain duplicates, particular for crew credits, so filter them out via a set.
    return list(set([movie_credit['title'] for movie_credit in movie_credits]))


def _query_movie_credits(api_key: str, movie_name: str) -> Tuple[str, Any]:
    movie_query_url: str = f"{BASE_URL}/search/movie?query={movie_name}"

    movie_response: Any = _make_request(api_key, movie_query_url)

    if not movie_response['results']:
        raise RuntimeError(f"Query for movie {movie_name} failed")

    movie_id: int = movie_response["results"][0]["id"]

    movie_credits_url: str = f"{BASE_URL}/movie/{movie_id}/credits"

    movie_credits_response: Any = _make_request(api_key, movie_credits_url)

    if not movie_credits_response['id']:
        raise RuntimeError(f"Query for movie credits for movie {movie_id} failed")

    # Filter the crew credits to only the roles we are interested in.
    movie_credits_response["crew"] = [n for n in movie_credits_response["crew"] if n.get('job') in REQUIRED_CREW_ROLES]

    # The Movie DB query might do some fuzzy searching based on the movie name
    # given so return the actual movie name alongside the credits.
    return (movie_response['results'][0]['title'], movie_credits_response)


def _query_person_movie_credits(api_key: str, person_id: int) -> Tuple[List[str], List[str]]:
    movie_credits_query_url: str = f"{BASE_URL}/person/{person_id}/movie_credits"

    movie_credits_response: Any = _make_request(api_key, movie_credits_query_url)

    if not movie_credits_response['id']:
        raise RuntimeError(f"Query for movie credits for person {person_id} failed")

    cast_credits: List[str] = _parse_movie_credits(movie_credits_response["cast"])
    crew_credits: List[str] = _parse_movie_credits(movie_credits_response["crew"])

    return cast_credits, crew_credits


if __name__ == "__main__":
    parser: ArgumentParser = ArgumentParser(prog="TMDB Query", description="Query TMDB for film links")

    parser.add_argument("--api_key", help="The TMDB API key")

    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument("--find_link", help="Find the link between two movies", nargs=2)
    query_group.add_argument("--movie", help="The name of the movie to query")
    query_group.add_argument("--person", help="The name of the movie to query")

    args: Namespace = parser.parse_args()

    # Check that we have an API key, either from the command line arguments
    # or an environment variable.
    api_key: str | None = args.api_key
    if not args.api_key:
        api_key = environ.get("TMDB_API_KEY")

    if api_key:
        # The query types have to be set due to the ArgumentParser configuration
        # so we don't need to check if a value has been set.
        try:
            if args.find_link:
                find_link(api_key, args.find_link[0], args.find_link[1])
            if args.movie:
                query_tmdb_movie(api_key, args.movie)
            elif args.person:
                query_tmdb_person(api_key, args.person)
        except HTTPError as e:
            print("Error occurred whilst querying TMDB")
            print(e.args[0])
        except RuntimeError as e:
            print(e)
    else:
        print("No TMDB API key was provided through the command line args or \'TMDB_API_KEY\' environment variable")
