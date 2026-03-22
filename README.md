<img src="https://uakino.best/templates/uakino/images/logo.png?v3"  alt="uakino logo">

# uakino_parser

A Scrapy-based web scraper for extracting movie and TV series data from [uakino.best](https://uakino.best).
Currently scrapes approx. 28k movies.

## What it scrapes

For each title, the spider collects:

- **Metadata** — Ukrainian and English titles, year, duration, age rating, country, genres, schema type (Movie / TVSeries), season/episode info
- **Ratings** — IMDb rating and vote count, site likes/dislikes
- **People** — directors, actors
- **Media** — poster URL, trailer URL, screenshots
- **Streaming** — player URLs, direct stream URLs, subtitles, voice-over info (resolved per stream)
- **Organization** — franchise, collections, lists

## Requirements

- Python 3.13+
- [Scrapy](https://scrapy.org/)

Install dependencies:

```bash
uv sync
```

## Usage

Run the spider and save output to JSON:

```bash
uv run scrapy crawl movies -o movies.json
```

## Output format

Each item is a JSON object. Example structure:

```json
{
  "id": 12345,
  "url": "https://uakino.best/...",
  "schema_type": "Movie",
  "uk_title": "Назва українською",
  "en_title": "English Title",
  "year": 2023,
  "duration": "106 хвилин (01:46)",
  "description": "...",
  "quality": "1080p",
  "age_rating": "16+",
  "country": ["США"],
  "genres": ["бойовик", "драма"],
  "directors": ["Ім'я Режисера"],
  "actors": ["Актор 1", "Актор 2"],
  "imdb_rating": 7.5,
  "imdb_votes": 120000,
  "likes": 342,
  "dislikes": 12,
  "poster_url": "https://...",
  "trailer_url": "https://...",
  "screenshots": ["https://...", "https://..."],
  "franchise": "Назва франшизи",
  "collections": ["Колекція 1"],
  "lists": ["Список 1"],
  "streams": [
    {
      "title": "Серія 1",
      "voice": "Дубляж",
      "player_url": "https://ashdi.vip/...",
      "stream_url": "https://...",
      "poster_url": "https://...",
      "subtitle": ""
    }
  ]
}
```

## Spider overview

| Method | Purpose |
|---|---|
| `start` | Seeds the crawler from the main listing page |
| `parse_listpage` | Extracts movie URLs and follows pagination |
| `parse_movie` | Scrapes all metadata from a title's page |
| `parse_ajax` | Fetches the playlist via the site's AJAX endpoint |
| `parse_stream` | Resolves each player URL to a direct stream URL |
| `process_movie_info` | Parses the structured film-info block into typed fields |

## Notes

- The spider follows pagination automatically across the full catalogue.
- Streams are resolved asynchronously — a movie item is only yielded once all its streams have been fetched.
- Allowed domains: `uakino.best`, `ashdi.vip`.