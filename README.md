# tmdbquery
Query TMDB for film links

## Dependencies

Before running the script you will need a https://www.themoviedb.org/ API key.

## Usage

The script takes two arguments:
* --api_key - The TMDB API key
* And one of:
    * --movie - The name of the movie you are querying
    * --person - The name of the person you are querying

Run the script like:

```
python tmdbquery.py --api_key aaaaaa --movie Twister
```

### Note
Movie or people names are not case sensitive and any names with spaces must be wrapped in quotation marks.

```
python tmdbquery.py --api_key aaaaaa --person "Christopher Nolan"
```