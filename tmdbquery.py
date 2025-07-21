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


class Person:
    id: int
    name: str

    cast_credits: List[str]

    # Map of movie titles to a list of roles the person had on that movie.
    crew_credits: Dict[str, List[str]]

    def __init__(self, id: int, name: str) -> None:
        self.id = id
        self.name = name

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Person):
            return self.id == other.id and self.name == other.name
        return NotImplemented

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return f"{self.name} ({self.id})"


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
) -> Tuple[str, List[Person], List[Person]]:
    (movie_title, movie_credits_response) = _query_movie_credits_by_title(api_key, movie_title, year)

    cast_credits_results: List[Person] = []
    for credit in movie_credits_response["cast"]:
        cast_person: Person = Person(credit['id'], credit['name'])

        # Follow the links for this person.
        _query_person_movie_credits(api_key, cast_person)
        cast_credits_results.append(cast_person)

    crew_credits_results: List[Person] = []
    for credit in movie_credits_response["crew"]:
        crew_person: Person = Person(credit['id'], credit['name'])

        # Follow the links for this person.
        _query_person_movie_credits(api_key, crew_person)
        crew_credits_results.append(crew_person)

    return (movie_title, cast_credits_results, crew_credits_results)


def query_tmdb_person(api_key: str, person_name: str) -> Person:
    person_query_url: str = f"{BASE_URL}/search/person?query={person_name}"

    person_response: Any = _make_request(api_key, person_query_url)

    # The Movie DB search might do some fuzzy searching based on the name
    # provided so use the name from the response.
    person: Person = Person(person_response['results'][0]['id'], person_response['results'][0]['name'])

    # Get the person's movie credits.
    _query_person_movie_credits(api_key, person)

    return person


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


def _filter_movies(movie_credits: List[Any]) -> List[Any]:
    # Filter out movies by the following:
    # * No documentaries (genre ID 99).
    # * Vote count must be greater than 10.
    return list(
        filter(
            lambda x: 99 not in x['genre_ids'],
            filter(lambda x: x['vote_count'] > 10, movie_credits),
        )
    )


def _parse_movie_cast_credits(movie_credits: List[Any]) -> List[str]:
    filtered_movie_credits: List[Any] = _filter_movies(movie_credits)

    # Return a list of just movie title's with the release year appended.
    return [
        _generate_movie_title(movie_credit)
        for movie_credit in filtered_movie_credits
    ]


def _parse_movie_crew_credits(movie_credits: List[Any]) -> Dict[str, List[str]]:
    filtered_movie_credits: List[Any] = _filter_movies(movie_credits)

    crew_credits_results: Dict[str, List[str]] = {}
    for movie_credit in filtered_movie_credits:
        movie_title = _generate_movie_title(movie_credit)
        role = movie_credit['job']

        if role in REQUIRED_CREW_ROLES:
            if role == "Novel" or role == "Screenplay":
                role = "Writer"

            movie_entry = crew_credits_results.get(movie_title)
            if movie_entry:
                # Have already got credits for this crew member so just add the new role to the role list.
                movie_entry.append(role)
            else:
                crew_credits_results[movie_title] = [role]

    return crew_credits_results


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


def _query_person_movie_credits(api_key: str, person: Person) -> None:
    movie_credits_query_url: str = f"{BASE_URL}/person/{person.id}/movie_credits"

    movie_credits_response: Any = _make_request(api_key, movie_credits_query_url)

    if not movie_credits_response['id']:
        raise RuntimeError(f"Query for movie credits for person {person.id} failed")

    person.cast_credits = _parse_movie_cast_credits(movie_credits_response["cast"])
    person.crew_credits = _parse_movie_crew_credits(movie_credits_response["crew"])


def _print(print_str: str, indentation: int, md: bool) -> None:
    output_str: str = print_str
    if md:
        # To ensure that the markdown text doesn't end up massive,
        # add a base level of indentation and add a space to front
        # of the output string.
        indentation = indentation + 3
        output_str = f" {output_str}"

    if indentation:
        indentation_str: str = "#" if md else "\t"
        output_str = f"{indentation_str * indentation}{output_str}"

    print(output_str)


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

                _print(movie_title, 0, args.md)
                _print("Cast", 1, args.md)
                for cast_person in cast_results:
                    _print(cast_person.name, 2, args.md)
                    # Print out both their cast and crew credits.
                    if cast_person.cast_credits:
                        _print("Cast credits", 3, args.md)
                        for movie in cast_person.cast_credits:
                            _print(movie, 4, args.md)

                    if cast_person.crew_credits:
                        _print("Crew credits", 3, args.md)
                        for movie, roles in cast_person.crew_credits.items():
                            _print(f"{movie} - {', '.join(roles)}", 4, args.md)

                _print("Crew", 1, args.md)
                for crew_person in crew_results:
                    _print(crew_person.name, 2, args.md)

                    # Print out both their cast and crew credits.
                    if crew_person.cast_credits:
                        _print("Cast credits", 3, args.md)
                        for movie in crew_person.cast_credits:
                            _print(movie, 4, args.md)

                    if crew_person.crew_credits:
                        _print("Crew credits", 3, args.md)
                        for movie, roles in crew_person.crew_credits.items():
                            _print(f"{movie} - {', '.join(roles)}", 4, args.md)
            elif args.person:
                person: Person = query_tmdb_person(api_key, args.person)

                _print(person.name, 0, args.md)
                if person.cast_credits:
                    _print("Cast", 1, args.md)

                    for movie in person.cast_credits:
                        _print(movie, 2, args.md)
                if person.crew_credits:
                    _print("Crew", 1, args.md)
                    for movie, roles in person.crew_credits.items():
                        _print(f"{movie} - {', '.join(roles)}", 2, args.md)
        except HTTPError as e:
            print("Error occurred whilst querying TMDB")
            print(e.args[0])
        except RuntimeError as e:
            print(e)
    else:
        print("No TMDB API key was provided through the command line args or \'TMDB_API_KEY\' environment variable")
