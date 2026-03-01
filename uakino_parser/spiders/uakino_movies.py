import scrapy
import re


class UakinoMovies(scrapy.Spider):
    name = "movies"
    allowed_domains = ["uakino.best"]
    url: str = "https://uakino.best/ua/"

    async def start(self):
        yield scrapy.Request(self.url, self.parse_listpage)

    async def parse_listpage(self, response):
        movie_urls = response.css(
            "div.main-section-wr.with-sidebar.coloredgray.clearfix a.movie-title::attr(href)"
        ).getall()
        for url in movie_urls:
            yield response.follow(url, callback=self.parse_movie)

        next_page_url = response.css("span.pnext a::attr(href)").get()
        if next_page_url:
            yield response.follow(next_page_url, callback=self.parse_listpage)

    async def parse_movie(self, response):
        rating_section = response.css("div.main-sliders-rate.ignore-select")
        movie_info = await self.process_movie_info(response.css("div.film-info"))
        movie_right = response.css("div.movie-right")
        franchise = movie_right.css("div.mov-dop u::text").get()
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

        yield {
            "url": response.url,
            "franchise": franchise,
            "uk_title": response.css("span.solototle::text").get(),
            "en_title": response.css("span.origintitle i::text").get(),
            "poster_url": response.urljoin(
                response.css("div.film-poster a::attr(href)").get()
            ),
            "likes": rating_section.css("a span span::text").get(),
            "dislikes": rating_section.css("a")[-1].css("span span::text").get(),
            **movie_info,
        }

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
                result["country"] = link_values[0] if link_values else None

            elif "жанр" in label:
                result["genres"] = link_values

            elif "режисер" in label:
                result["director"] = link_values[0] if link_values else None

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
                    result["imdb_votes"] = int(votes)

        return result
