from argparse import ArgumentParser
import requests


def query_tmdb(api_key, movie_name):
    base_url = "https://api.themoviedb.org/3"

    movie_query_url = f"{base_url}/search/movie?query={movie_name}"

    api_dict = {"api_key": api_key}

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "close",
    }

    response = requests.get(
        movie_query_url,
        params=api_dict,
        headers=headers,
    )
    response.raise_for_status()

    movie_id = response.json()["results"][0]["id"]

    movie_credit_url = f"{base_url}/movie/{movie_id}/credits"

    response = requests.get(
        movie_credit_url,
        params=api_dict,
        headers=headers,
    )
    response.raise_for_status()

    credits_response = response.json()

    # need director, writer, composer, featuring (cast)
    # think cast is limited to 10.
    count = 0
    print("Cast")
    for credit in credits_response["cast"]:
        print(f"\t{credit["id"]} - {credit["name"]}")

        # Follow the links for this person.
        cast_query_url = f"{base_url}/search/person?query={credit["name"]}"

        response = requests.get(
            cast_query_url,
            params=api_dict,
            headers=headers,
        )
        response.raise_for_status()

        cast_response = response.json()
        films = cast_response["results"][0]["known_for"]
        for film in films:
            if film["media_type"] == "movie" and film["title"] != movie_name:
                print(f"\t\t{film["title"]}")

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
            print(f"\t{credit["id"]} - {credit["name"]} - {credit["job"]}")

            # Follow the links for this person.
            crew_query_url = f"{base_url}/search/person?query={credit["name"]}"

            response = requests.get(
                crew_query_url,
                params=api_dict,
                headers=headers,
            )
            response.raise_for_status()

            crew_response = response.json()
            films = crew_response["results"][0]["known_for"]
            for film in films:
                if film["media_type"] == "movie":
                    print(f"\t\t{film["title"]}")


if __name__ == "__main__":
    parser = ArgumentParser(
                    prog='TMDB Query',
                    description='Query TMDB for film links')

    parser.add_argument("--api_key", help="The TMDB API key")
    parser.add_argument("--movie_name", help="The name of the movie to query")

    args = parser.parse_args()

    query_tmdb(args.api_key, args.movie_name)
