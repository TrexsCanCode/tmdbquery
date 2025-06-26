# tmdbquery
Query TMDB for film links

## Dependencies

Before running the script you will need a https://www.themoviedb.org/ API key.

## Usage

The script takes at least two arguments:
* --api_key - The TMDB API key
* And one of:
    * --find_link [movie 1] [movie 2] - Find the links between the two given movies
    * --movie - The name of the movie you are querying
    * --person - The name of the person you are querying

Run the script like:

```
python tmdbquery.py --api_key aaaaaa --movie Inception
```

### Movie queries

By default querying for a movie will return the first entry that matches the given name (fuzzy searching may be used),
to request a movie from a certain year the ```--year``` argument can be used.

```
python tmdbquery.py --api_key aaaaaa --movie Inception --year 2010
```

### API key

Rather than passing the TMDB API key in every time it can also be stored in the environment variable: ```TMDB_API_KEY```.

### Note
Movie or people names are not case sensitive and any names with spaces must be wrapped in quotation marks.

```
python tmdbquery.py --api_key aaaaaa --person "Christopher Nolan"
```
