from argparse import ArgumentParser, Namespace
from datetime import datetime
from os import environ
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests import Response
from requests.exceptions import HTTPError


BASE_URL: str = "https://api.themoviedb.org/3"

# List of the crew roles that we are interested in.
REQUIRED_CREW_ROLES: List[str] = ["Director", "Director of Photography", "Novel", "Original Music Composer", "Screenplay", "Writer"]


def find_link(api_key: str, movie_from_title: str, movie_to_title: str) -> None:
    if movie_from_title == movie_to_title:
        print("Must provide two different movies to find link between")
        return

    (movie_from_title, movie_from_credits_response) = _query_movie_credits_by_title(api_key, movie_from_title)

    (movie_to_title, movie_to_credits_response) = _query_movie_credits_by_title(api_key, movie_to_title)

    # Get the list of cast from both films and compare them.
    cast_from_names: List[str] = [n.get('name') for n in movie_from_credits_response["cast"]]
    cast_to_names: List[str] = [n.get('name') for n in movie_to_credits_response["cast"]]

    common_cast: List[str] = list(set(cast_from_names).intersection(cast_to_names))

    # Get the list of crew from both films and compare them.
    crew_from_names: List[str] = [n.get('name') for n in movie_from_credits_response["crew"]]
    crew_to_names: List[str] = [n.get('name') for n in movie_to_credits_response["crew"]]

    common_crew: List[str] = list(set(crew_from_names).intersection(crew_to_names))

    if not common_cast and not common_crew:
        print(f"No links found between {movie_from_title} and {movie_to_title}")
    else:
        print(f"Found the following links between {movie_from_title} and {movie_to_title}:\n")
        if common_cast:
            print("Cast links:")
            [print(f"\t{cast}") for cast in common_cast]
        if common_crew:
            print("Crew links:")
            [print(f"\t{crew}") for crew in common_crew]


def query_tmdb_movie(
    api_key: str, movie_title: str, year: Optional[int]
) -> Tuple[str, Dict[str, List[str]], Dict[str, Tuple[List[str], List[str]]]]:
    (movie_title, movie_credits_response) = _query_movie_credits_by_title(api_key, movie_title, year)

    cast_credits_results: Dict[str, List[str]] = {}
    for credit in movie_credits_response["cast"]:
        cast_name = credit['name']

        # Follow the links for this person.
        person_id: int = credit['id']
        (cast_credits, _) = _query_person_movie_credits(api_key, person_id)
        cast_credits = list(filter(lambda x: x.casefold() != movie_title.casefold(), cast_credits))
        cast_credits_results[cast_name] = cast_credits

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
            full_credits: List[str] = list(filter(lambda x: x.casefold() != movie_title.casefold(), cast_credits))
            full_credits.extend(x for x in crew_credits if x.casefold() != movie_title.casefold() and x not in full_credits)

            crew_credits_results[crew_name] = ([credit['job']], full_credits)

    return (movie_title, cast_credits_results, crew_credits_results)


def query_tmdb_person(api_key: str, person: str) -> Tuple[str, List[str], List[str]]:
    person_query_url: str = f"{BASE_URL}/search/person?query={person}"

    person_response: Any = _make_request(api_key, person_query_url)

    # The Movie DB search might do some fuzzy searching based on the name
    # provided so print the name of the person the results actually respond to.
    person_name = person_response['results'][0]['name']

    # Get the person's ID to then get their movie credits.
    person_id: int = person_response['results'][0]['id']

    (cast_credits, crew_credits) = _query_person_movie_credits(api_key, person_id)

    return (person_name, cast_credits, crew_credits)


def _generate_movie_title(movie_data: Dict[str, str]) -> str:
    movie_title_str: str = movie_data['title']
    if movie_data['release_date']:
        release_year: int = datetime.strptime(movie_data['release_date'], '%Y-%m-%d').year
        movie_title_str = f"{movie_title_str} ({release_year})"

    return movie_title_str


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

    # Add the release year to the movie title and remove duplicate movies
    # (likely to occur for for crew credits) by filtering them out via a set.
    return list(
        set(
            [
                _generate_movie_title(movie_credit)
                for movie_credit in movie_credits
            ]
        )
    )


def _query_movie_credits_by_title(api_key: str, movie_title: str, year: Optional[int] = None) -> Tuple[str, Any]:
    movie_query_url: str = f"{BASE_URL}/search/movie?query={movie_title}"

    movie_response: Any = _make_request(api_key, movie_query_url)

    if not movie_response['results']:
        raise RuntimeError(f"Query for movie {movie_title} failed")

    # If we have been provided with a year we need search the results for
    # a movie with the expected year, otherwise just take the first result.
    movie_response_data: Optional[Any] = None
    if year:
        for movie_data in movie_response['results']:
            # Not all movies will have a release date.
            if movie_data['release_date']:
                release_year: int = datetime.strptime(movie_data['release_date'], '%Y-%m-%d').year
                if release_year == year:
                    movie_response_data = movie_data
                    break

        # If no movie was found throw error.
        if not movie_response_data:
            raise RuntimeError(f"Failed to movie with title {movie_title} and release year {year}")
    else:
        movie_response_data = movie_response['results'][0]

    movie_credits_response: Any = _query_movie_credits_by_id(api_key, movie_response_data["id"])

    # Filter the crew credits to only the roles we are interested in.
    filtered_crew_list: List[Any] = []
    for crew_member in movie_credits_response["crew"]:
        if crew_member.get('job') in REQUIRED_CREW_ROLES:
            if crew_member.get('job') == "Novel" or crew_member.get('job') == "Screenplay":
                crew_member["job"] = "Writer"

            filtered_crew_list.append(crew_member)

    movie_credits_response["crew"] = filtered_crew_list

    # The Movie DB query might do some fuzzy searching based on the movie title
    # provided so return the actual movie title plus release year, alongside the credits.
    movie_title = _generate_movie_title(movie_response_data)

    return (movie_title, movie_credits_response)


def _query_movie_credits_by_id(api_key: str, movie_id: int) -> Any:
    movie_credits_url: str = f"{BASE_URL}/movie/{movie_id}/credits"

    movie_credits_response: Any = _make_request(api_key, movie_credits_url)

    if not movie_credits_response['id']:
        raise RuntimeError(f"Query for movie credits for movie {movie_id} failed")

    return movie_credits_response


def _query_person_movie_credits(api_key: str, person_id: int) -> Tuple[List[str], List[str]]:
    movie_credits_query_url: str = f"{BASE_URL}/person/{person_id}/movie_credits"

    movie_credits_response: Any = _make_request(api_key, movie_credits_query_url)

    if not movie_credits_response['id']:
        raise RuntimeError(f"Query for movie credits for person {person_id} failed")

    cast_credits: List[str] = _parse_movie_credits(movie_credits_response["cast"])
    crew_credits: List[str] = _parse_movie_credits(movie_credits_response["crew"])

    return (cast_credits, crew_credits)


if __name__ == "__main__":
    parser: ArgumentParser = ArgumentParser(prog="TMDB Query", description="Query TMDB for film links")

    parser.add_argument("--api_key", help="The TMDB API key")
    parser.add_argument("--md", help="Print the output in MD format", action='store_true')

    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument("--find_link", help="Find the link between two movies", nargs=2)
    query_group.add_argument("--movie", help="The title of the movie to query")
    query_group.add_argument("--person", help="The name of the person to query")

    # Add additional 'year' argument that can only be used with the 'movie' argument.
    parser.add_argument(
        "--year",
        type=int,
        choices=range(1900, datetime.now().year + 1),
        help="Specify the year of the movie being requested",
    )

    args: Namespace = parser.parse_args()

    if args.year and not args.movie:
        parser.error("--year can only be used in conjunction with --movie")

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
                (movie_title, cast_results, crew_results) = query_tmdb_movie(api_key, args.movie, args.year)

                if args.md:
                    print(f"### {movie_title}")
                    print("#### Cast")
                    for name, credits in cast_results.items():
                        print(f"##### {name}")
                        [print(f"###### {movie}") for movie in credits]
                    print("#### Crew")
                    for name, (roles, credits) in crew_results.items():
                        print(f"##### {name} - {', '.join(roles)}")
                        [print(f"###### {movie}") for movie in credits]
                else:
                    print(movie_title)
                    print("\tCast")
                    for name, credits in cast_results.items():
                        print(f"\t\t{name}")
                        [print(f"\t\t\t{movie}") for movie in credits]
                    print("\tCrew")
                    for name, (roles, credits) in crew_results.items():
                        print(f"\t\t{name} - {', '.join(roles)}")
                        [print(f"\t\t\t{movie}") for movie in credits]

            elif args.person:
                (person_name, cast_credits, crew_credits) = query_tmdb_person(api_key, args.person)

                if args.md:
                    print(f"### {person_name}")
                    if cast_credits:
                        print("#### Cast")
                        [print(f"##### {movie}") for movie in cast_credits]
                    if crew_credits:
                        print("#### Crew")
                        [print(f"##### {movie}") for movie in crew_credits]
                else:
                    print(person_name)
                    if cast_credits:
                        print("\tCast")
                        [print(f"\t\t {movie}") for movie in cast_credits]
                    if crew_credits:
                        print("\tCrew")
                        [print(f"\t\t {movie}") for movie in crew_credits]
        except HTTPError as e:
            print("Error occurred whilst querying TMDB")
            print(e.args[0])
        except RuntimeError as e:
            print(e)
    else:
        print("No TMDB API key was provided through the command line args or \'TMDB_API_KEY\' environment variable")
