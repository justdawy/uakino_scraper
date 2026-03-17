import re
from datetime import datetime

import scrapy
from parsel import Selector


class UakinoMovies(scrapy.Spider):
    name = "movies"
    allowed_domains = ["uakino.best", "ashdi.vip"]
    url: str = "https://uakino.best/ua/"

    async def start(self):
        yield scrapy.Request(self.url, self.parse_listpage)

    async def parse_listpage(self, response):
        movie_urls = response.css(
            "div.main-section-wr.with-sidebar.coloredgray.clearfix "
            "a.movie-title::attr(href)"
        ).getall()
        for url in movie_urls:
            yield response.follow(url, callback=self.parse_movie)

        next_page_url = response.css("span.pnext a::attr(href)").get()
        if next_page_url:
            yield response.follow(next_page_url, callback=self.parse_listpage)

    async def parse_movie(self, response):
        movie_id = response.url.split("/")[-1].split("-")[0]
        rating_section = response.css("div.main-sliders-rate.ignore-select")
        meta = response.xpath('//div[@itemscope and contains(@itemtype, "schema.org")]')
        schema_type = meta.xpath("./@itemtype").get().split("/")[-1]
        duration = meta.xpath('.//*[@itemprop="duration"]/@content').get()
        season = meta.xpath('.//*[@itemprop="season"]/@content').get()
        episode = meta.xpath('.//*[@itemprop="episode"]/@content').get()
        trailer_url = meta.xpath('.//*[@itemprop="trailer"]/@value').get()
        directors = [
            d.strip()
            for value in response.xpath('//*[@itemprop="director"]/@content').getall()
            for d in value.split(",")
            if d.strip()
        ]
        movie_info = await self.process_movie_info(response.css("div.film-info"))
        movie_right = response.css("div.movie-right")
        description = movie_right.xpath('string(.//div[@itemprop="description"])').get()
        franchise = movie_right.css("div.mov-dop u::text").get()
        screenshots = [
            response.urljoin(s)
            for s in movie_right.css("div.screens-section a::attr(href)").getall()
        ]
        collections = [
            c.strip() for c in movie_right.css("a.colection-n-link::text").getall()
        ]
        iframe = movie_right.css("iframe::attr(src)").get()
        if not franchise:
            franchise = movie_right.css("div.mov-dop a::text").get()
            if not franchise:
                franchise = movie_right.css("div.mov-dop::text").get()
            if franchise:
                match = re.search(r'"([^"]+)"', franchise)
                if match:
                    franchise = match.group(1)
                else:
                    franchise = None

        if franchise and "ще серіали і кінофільми українською" in franchise:
            franchise = None

        item = {
            "id": int(movie_id),
            "url": response.url,
            "schema_type": schema_type,
            "season": season,
            "episode": episode,
            "franchise": franchise,
            "uk_title": response.css("span.solototle::text").get(),
            "en_title": response.css("span.origintitle i::text").get(),
            "duration": duration,
            "description": description.strip(),
            "poster_url": response.urljoin(
                response.css("div.film-poster a::attr(href)").get()
            ),
            "trailer_url": trailer_url,
            "screenshots": screenshots,
            "likes": int(rating_section.css("a span span::text").get()),
            "dislikes": int(rating_section.css("a")[-1].css("span span::text").get()),
            **movie_info,
            "directors": directors,
            "collections": collections,
        }
        if iframe:
            item["stream"] = iframe
        playlists_ajax = response.css("div.playlists-ajax")
        xfield = playlists_ajax.css("::attr(data-xfname)").get()
        ajax_url = f"https://uakino.best/engine/ajax/playlists.php?news_id={movie_id}&xfield={xfield}&time={int(datetime.now().timestamp())}"
        yield response.follow(
            ajax_url,
            meta={"movie": item},
            callback=self.parse_ajax,
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

    async def parse_ajax(self, response):
        playlist_html = response.json().get("response")
        movie = response.meta["movie"]

        streams = []

        if movie.get("stream"):
            streams.append(
                {
                    "title": None,
                    "voice": None,
                    "player_url": self.normalize_url(movie["stream"]),
                }
            )
            del movie["stream"]
        elif playlist_html:
            sel = Selector(text=playlist_html)

            for ep in sel.css("div.playlists-videos li"):
                data_file = ep.attrib.get("data-file")
                if not data_file:
                    continue
                streams.append(
                    {
                        "title": ep.css("::text").get(default="").strip(),
                        "voice": ep.attrib.get("data-voice"),
                        "player_url": self.normalize_url(data_file),
                    }
                )
        if not streams:
            yield {**movie, "streams": []}
            return
        movie["_pending_streams"] = len(streams)
        for stream in streams:
            yield response.follow(
                stream["player_url"],
                callback=self.parse_stream,
                meta={"movie": movie, "stream": stream, "all_streams": streams},
            )

    def normalize_url(self, url):
        if not url:
            return None
        if url.startswith("//"):
            return "https:" + url
        return url

    async def parse_stream(self, response):
        movie = response.meta["movie"]
        stream = response.meta["stream"]
        all_streams = response.meta["all_streams"]
        text = response.text
        file_match = re.search(r'file\s*:\s*[\'"]([^\'"]+)[\'"]', text)
        poster_match = re.search(r'poster\s*:\s*[\'"]([^\'"]+)[\'"]', text)
        subtitle_match = re.search(r'subtitle\s*:\s*[\'"]([^\'"]*)[\'"]', text)

        stream["stream_url"] = file_match.group(1) if file_match else None
        stream["poster_url"] = poster_match.group(1) if poster_match else None
        stream["subtitle"] = subtitle_match.group(1) if subtitle_match else None

        movie["_pending_streams"] -= 1
        if movie["_pending_streams"] == 0:
            # remove helper key
            del movie["_pending_streams"]
            yield {**movie, "streams": all_streams}

    async def process_movie_info(self, info_section):
        result = {}

        items = info_section.css("div.fi-item-s, div.fi-item")

        for item in items:
            label = " ".join(item.css(".fi-label ::text").getall()).strip()
            label = label.replace(":", "").lower()

            text_values = [
                t.strip() for t in item.css(".fi-desc ::text").getall() if t.strip()
            ]
            link_values = [
                t.strip() for t in item.css(".fi-desc a::text").getall() if t.strip()
            ]

            if "списки" in label:
                a_tags = item.css(".fi-desc a::text").getall()
                if not a_tags:
                    a_tags = item.css("a::text").getall()
                result["lists"] = [t.strip() for t in a_tags if t.strip()]
                continue

            if "якість" in label:
                result["quality"] = text_values[0] if text_values else None

            elif "рік виходу" in label:
                result["year"] = int(text_values[0]) if text_values else None

            elif "вік" in label:
                result["age_rating"] = text_values[0] if text_values else None

            elif "країна" in label:
                result["country"] = link_values

            elif "жанр" in label:
                result["genres"] = link_values

            elif "режисер" in label:
                result["director"] = link_values

            elif "актори" in label:
                result["actors"] = link_values

            elif "озвучення" in label:
                result["voice"] = text_values[0] if text_values else None

            elif "доступно на" in label:
                devices = item.css(".devices-item::text").getall()
                result["available_on"] = [d.strip() for d in devices if d.strip()]

            elif (
                "imdb" in "".join(item.css(".fi-label img::attr(alt)").getall()).lower()
            ):
                rating_text = text_values[0] if text_values else None
                if rating_text and "/" in rating_text:
                    rating, votes = rating_text.split("/")
                    result["imdb_rating"] = float(rating)
                    result["imdb_votes"] = int(votes.replace(" ", ""))

        return result
