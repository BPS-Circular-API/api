import difflib
import time
from logging.config import dictConfig
import configparser
import logging
import os
import pypdfium2 as pdfium
import requests
import sqlite3
from pydantic import BaseModel
from bs4 import BeautifulSoup, SoupStrainer
from concurrent.futures import ThreadPoolExecutor
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

success_response = {
    "status": "success",
    "http_status": 200,
    "data": []
}

error_response = {
    "status": "error",
    "http_status": 500,
    "error": ""
}

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/81.0.4044.138 Safari/537.36 "
}

bps_url = "https://bpsdoha.com"
category_id_prefixes = ["circular/category", "primaryi"]


# Initializing the Logger
class LogConfig(BaseModel):
    """Logging configuration to be set for the server"""

    LOGGER_NAME: str = "bps-circular-api"
    LOG_FORMAT: str = "%(levelprefix)s %(message)s"
    LOG_LEVEL: str = "INFO"

    # Logging config
    version: int = 1
    disable_existing_loggers: bool = False
    formatters: dict = {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }
    handlers: dict = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    }
    loggers: dict = {
        "bps-circular-api": {"handlers": ["default"], "level": LOG_LEVEL},
    }


# Initiate the logging config
dictConfig(LogConfig().dict())
log = logging.getLogger("bps-circular-api")

# Getting config
config = configparser.ConfigParser()

try:
    # check if ./data/config.ini exists
    if os.path.exists('./data/config.ini'):
        config.read('./data/config.ini')
    elif os.path.exists('api/data/config.ini'):
        config.read('api/data/config.ini')
    elif os.path.exists("../data/config.ini"):
        config.read("../data/config.ini")


except Exception as e:
    print("Error reading the config.ini file. Error: " + str(e))
    exit()

try:
    log_level: str = config.get('main', 'log_level')
    base_api_url: str = config.get('main', 'base_api_url')

    # get a dict of all the categories
    categories = dict(config.items('categories'))

    # make sure all the values are integers
    for category in categories.keys():
        try:
            categories[category] = int(categories[category])
        except ValueError:
            categories[category] = categories[category]
            log.debug("Couldn't int() a category. Must be textual")
    log.debug(categories)

except Exception as err:
    log.critical("Error reading config.ini. Error: " + str(err))
    import sys
    sys.exit()

# set log level
log.setLevel(log_level.upper() if log_level.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] else "INFO")
log.debug(f"Log level set to {log.level}")

# remove trailing slash from base_api_url
base_api_url = base_api_url.rstrip('/')


#
#
#
#
#


async def get_num_pages(category_id):
    if type(category_id) is int:
        url = f"{bps_url}/{category_id_prefixes[0]}/{category_id}"
    else:
        url = f"{bps_url}/{category_id_prefixes[1]}/{category_id}"

    response = requests.get(url, headers=headers)

    parse_only = SoupStrainer('div', class_='pagination')
    soup = BeautifulSoup(response.content, 'lxml', parse_only=parse_only)

    # Check if pagination exists on the page
    if not soup:
        return 1

    # Find the page count text
    try:
        pginline = soup.find('div', class_='pginline').text.strip()
    except AttributeError:
        return 0

    try:
        page_count = int(pginline.split()[-1])
    except IndexError:
        page_count = 1

    return page_count


def thread_get_list(category_id, page):
    if type(category_id) is int:
        url = f"{bps_url}/{category_id_prefixes[0]}/{category_id}"
    else:
        url = f"{bps_url}/{category_id_prefixes[1]}/{category_id}"

    url += f"?start={(page - 1) * 20}"

    response = requests.get(url, headers=headers)

    soup = BeautifulSoup(response.content, 'html.parser')
    fileboxes = soup.find_all('div', class_='pd-filebox')

    files = []

    for filebox in fileboxes:
        name = filebox.find('div', class_='pd-title').text.strip()
        url = bps_url + filebox.find('a', class_='btn-success')['href'].split(':')[0].strip()
        id_ = url.split('=')[1].split(':')[0].strip()

        files.append({'title': name, 'link': url, 'id': id_})

    return files


async def get_list(category_id, pages):
    with ThreadPoolExecutor() as executor:
        # scrape each page using a thread and collect the results
        futures = [executor.submit(thread_get_list, category_id, page) for page in range(1, pages + 1)]
        files_list = [future.result() for future in futures]

    # flatten the list of lists into a single list
    files = [file for files in files_list for file in files]

    # sort files by page number
    files.sort(key=lambda file: int(file['id']))

    # invert the list so that the most recent file is first
    files.reverse()

    return files


async def get_latest(category_id):
    if type(category_id) is int:
        url = f"{bps_url}/{category_id_prefixes[0]}/{category_id}"
    else:
        url = f"{bps_url}/{category_id_prefixes[1]}/{category_id}"

    response = requests.get(url, headers=headers)

    # Parse the response
    parse_only = SoupStrainer('div', class_='pd-filebox')
    soup = BeautifulSoup(response.content, 'lxml', parse_only=parse_only)

    # Find the first filebox and get the name and url
    name = soup.find('div', class_='pd-title').text.strip()
    url = bps_url + soup.find('a', class_='btn-success')['href'].split(':')[0].strip()
    id_ = url.split('=')[1].split(':')[0].strip()

    return {'title': name, 'link': url, 'id': id_}


async def get_png(download_url: str) -> str or None:
    file_id = download_url.split('=')[1].split(":")[0]  # Get the 4 digit file ID

    if os.path.isfile(f"./circularimages/{file_id}.png"):

        page_list = []
        temp = 0

        for file in os.listdir("./circularimages"):
            if file.endswith(".png"):
                if file_id in file:
                    temp += 1

        for i in range(temp):
            if i == 0:
                page_list.append(f"{base_api_url}/circular-image/{file_id}.png")
            else:
                page_list.append(f"{base_api_url}/circular-image/{file_id}-{i + 1}.png")

        return page_list

    pdf_file = requests.get(download_url, headers=headers)

    # if we're redirected to https://bpsdoha.com/component/users/ it means the file doesn't exist
    if pdf_file.url.startswith("https://bpsdoha.com/component/users/"):
        raise Exception("Circular does not exist")

    try:
        pdf = pdfium.PdfDocument(pdf_file.content)
    except Exception as e:
        log.error(f"Error parsing PDF. Error: {e}")
        return []

    if not os.path.isdir("./circularimages"):  # Create the directory if it doesn't exist
        os.mkdir("./circularimages")

    page_list = []

    async def is_blank(im):
        grey_scale = im.convert('L')

        for x, y in zip(range(0, im.height), range(0, im.width)):
            val = grey_scale.getpixel((x, y))
            if val < 200:
                return False

        return True

    for page, pgno in zip(pdf, range(len(pdf))):

        pil_image = page.render().to_pil(
            # scale=5,
            # rotation=0,
            # crop=(0, 0, 0, 0),  # Crop doesn't work for some reason
            # colour=(255, 255, 255, 255),
            # annotations=True,
            # greyscale=False,
            # optimise_mode=pdfium.OptimiseMode.NONE,
        )
        # check if the page is empty, by checking if the image is all white

        if await is_blank(pil_image):
            continue

        if pgno == 0:
            pil_image.save(f"./circularimages/{file_id}.png")
        else:
            pil_image.save(f"./circularimages/{file_id}-{pgno + 1}.png")

        pil_image.close()

        if pgno == 0:
            page_list.append(f"{base_api_url}/circular-image/{file_id}.png")
        else:
            page_list.append(f"{base_api_url}/circular-image/{file_id}-{pgno + 1}.png")

    return page_list


async def search_from_id(_id: int):
    _id = int(_id)

    # Try to find the circular in the database
    if os.path.exists(".data/data.db"):
        con = sqlite3.connect(".data/data.db")
    elif os.path.exists("../data/data.db"):
        con = sqlite3.connect("../data/data.db")
    elif os.path.exists("data/data.db"):
        con = sqlite3.connect("data/data.db")
    else:
        log.error("Could not find database")
        return None

    cur = con.cursor()

    cur.execute("SELECT * FROM list_cache WHERE id=?", (_id,))
    data = cur.fetchone()

    # If the circular is found in the database, return it
    if data:
        log.debug(f"Found circular with id {_id} in the database")
        return {"title": data[1], "link": data[2], "id": data[0]}

    # If the circular is not found in the database, scrape the website
    for category in categories:
        log.debug(f"Searching in category {category}, id {categories[category]}")
        category_id = categories[category]

        # Get the list of circulars
        circular_list = await get_list(category_id, await get_num_pages(category_id))

        # Check if the circular is in the list
        for circular in circular_list:
            circular['id'] = int(circular['id'])

            # If the given id is found on the website, add it to the database and return it
            if circular['id'] == _id:
                log.debug(f"Found circular with id {_id} in the list, adding to DB")
                cur.execute(
                    "INSERT INTO list_cache VALUES (?, ?, ?)",
                    (circular['id'], circular['title'].strip(), circular['link'].strip())
                )
                con.commit()
                return circular

    return None

class CircularListCache:
    def __init__(self):
        self._cache: list = []
        self.expiry: int = -1

    async def refresh_circulars(self) -> None:
        # expire in 6 hours
        self.expiry = int(time.time()) + 21600

        # We don't write to cache directly because we don't want other functions being affected
        # by empty/incomplete cache for the duration of get_list()
        temp_list: list = []
        for category in categories.keys():
            data = await get_list(categories[category], await get_num_pages(categories[category]))
            data = [{**item, "category": category} for item in data]

            temp_list.extend(data)

        temp_list.sort(key=lambda x: x['id'], reverse=True)

        self._cache: list = temp_list
        return

    async def get_cache(self) -> list:
        if self.expiry < time.time():
            await self.refresh_circulars()
        return self._cache



async def search_algo(circular_list_cache: CircularListCache, query: str, amount: int):
    circular_objs = await circular_list_cache.get_cache()

    search_results = []
    query = query.lower().replace("-", "").replace("&", "")

    # Remove '&' and '-' from circular titles, also make them lower case
    circulars_lower = [circular_title['title'].lower() for circular_title in circular_objs]
    circulars_lower = [circular_title.replace("&", '').replace("-", "") for circular_title in circulars_lower]

    # Initialize the stemmer and stop words
    stemmer = PorterStemmer()
    stop_words = set(stopwords.words("english"))

    keyword_stem = stemmer.stem(query)

    for index, circular in enumerate(circulars_lower):
        circular_tokens = nltk.word_tokenize(circular.lower())

        # Apply stemming and remove stop words
        circular_filtered = [stemmer.stem(word) for word in circular_tokens if word not in stop_words]
        circular_filtered = " ".join(circular_filtered)

        # Check for exact word matches first
        if keyword_stem in circular_filtered:
            search_results.append((index, circular, 1.0))
        else:
            # If no exact word match, calculate similarity for partial sentence matches
            similarity = difflib.SequenceMatcher(None, keyword_stem, circular_filtered).ratio()
            search_results.append((index, circular, similarity))

    # Sort the search results by similarity and index
    search_results.sort(key=lambda x: (-x[2], x[0]))

    if search_results[0][1] == query:
        return [circular_objs[search_results[0][0]]]

    # Otherwise, return up to 'amount' results
    results = [circular_objs[result[0]] for result in search_results[:amount]]
    return results
