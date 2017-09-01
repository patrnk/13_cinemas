import json
import logging
import sys

import requests
from lxml import html


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


def fetch_afisha_page():
    url = 'https://www.afisha.ru/msk/schedule_cinema/'
    return requests.get(url).text


def parse_afisha_list(raw_html):
    tree = html.fromstring(raw_html)
    movie_titles = tree.xpath('//*[@id="schedule"]/div/div[2]/h3/a/text()')
    movie_links = tree.xpath('//*[@id="schedule"]/div/div[2]/h3/a/@href')
    theater_tables = tree.xpath('//*[@id="schedule"]/div/table/tbody')
    theater_counts = [len(table.getchildren()) for table in theater_tables]
    raw_movies = list(zip(movie_titles, movie_links, theater_counts))
    movie_properties = ('title', 'url', 'theatre_count')
    return [dict(zip(movie_properties, raw_movie)) for raw_movie in raw_movies]


def fetch_movie_info_from_kinopoisk(movie_title):
    # kinopoisk search suggestion system usually gives us the result we want
    # and it probably won't ban us because of frequent requests
    logging.debug('Fetching %s', movie_title)
    url = 'https://suggest-kinopoisk.yandex.net/suggest-kinopoisk'
    headers = {
        'Host': 'suggest-kinopoisk.yandex.net',
        'Origin': 'https://plus.kinopoisk.ru',
        'Accept-Language': 'en-us',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'close',
        'Accept': '*/*',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_4) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.1 Safari/603.1.30',
        'Referer': 'https://plus.kinopoisk.ru/',
        'DNT': '1',
    }
    params = {
        'srv': 'kinopoisk',
        'part': movie_title,
        '_': '1504208262833',
    }
    response = requests.get(
        url,
        headers=headers,
        params=params
    )
    raw_json_response = response.json()
    logging.debug('raw json response: %s', raw_json_response)
    if raw_json_response[2]:
        return json.loads(raw_json_response[2][0])
    else:
        raise RuntimeWarning(
            "Couldn't get kinopoisk info for '{}'".format(movie_title)
        )


def fetch_movie_rating_info(movie_title):
    try:
        kinopoisk_info = fetch_movie_info_from_kinopoisk(movie_title)
    except RuntimeWarning as e:
        logging.warning(e)
    else:
        kinopoisk_rating = kinopoisk_info.get('rating')
        if kinopoisk_rating and kinopoisk_rating['ready']:
            rating_info = {}
            rating_info['rating'] = kinopoisk_rating['rate']
            rating_info['votes'] = kinopoisk_rating['votes']
            return rating_info
        else:
            logging.info(
                'Rating for %s is not available yet',
                movie['title']
            )


def output_rated_movie_to_stdout(movie):
    print(
        '{} - Рейтинг {} ({}) - Количество кинотеатров: {} - {}'.format(
            movie['title'],
            movie['rating'],
            movie['votes'],
            movie['theatre_count'],
            movie['url'],
        )
    )


if __name__ == '__main__':
    raw_afisha_html = fetch_afisha_page()
    movies = parse_afisha_list(raw_afisha_html)
    rated_movies = []
    for movie in movies:
        rating_info = fetch_movie_rating_info(movie['title'])
        if rating_info:
            movie['rating'] = rating_info['rating']
            movie['votes'] = rating_info['votes']
            rated_movies.append(movie)
    rated_movies.sort(
        key=lambda movie: movie['rating'],
        reverse=True
    )
    movies_to_output = 10
    for movie in rated_movies[:movies_to_output]:
        output_rated_movie_to_stdout(movie)
