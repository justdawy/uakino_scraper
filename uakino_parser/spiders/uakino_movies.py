import scrapy


class UakinoMovies(scrapy.Spider):
    name = "uakino_movies"
    start_urls = ["https://uakino.best/ua/"]

    def parse(self, response):
        for movie in response.css("div.movie-item.short-item"):
            yield {
                "title": movie.css("a.movie-title::text").get(),
                "full_quality": movie.css("div.full-quality::text").get(),
                "poster_url": response.urljoin(
                    movie.css("div.movie-img img::attr(src)").get()
                ),
            }

        next_page = response.css("span.pnext a::attr(href)").get()
        print(next_page)
        if next_page is not None:
            yield response.follow(next_page, callback=self.parse)
