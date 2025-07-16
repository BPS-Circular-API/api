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

# Get the absolute path to the directory containing this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'data', 'config.ini')

try:
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Configuration file not found at {CONFIG_PATH}")
    config.read(CONFIG_PATH)

except Exception as e:
    log.error(f"Error reading the config.ini file: {e}")
    exit()

try:
    log_level: str = config.get('main', 'log_level')
    base_api_url: str = config.get('main', 'base_api_url')
    # The following lines for db_path and temp_dir are removed as they are handled below

except configparser.NoOptionError as e:
    log.error(f"Configuration error: {e}")
    exit()

# Define paths relative to the script's location
DB_PATH = os.path.join(BASE_DIR, 'data', 'data.db')
TEMP_DIR = os.path.join(BASE_DIR, 'data', 'temp')

# Ensure the temp directory exists
os.makedirs(TEMP_DIR, exist_ok=True)


class CircularListCache:
    def __init__(self):
        """
        A class that caches the circular list in a database.
        """
        self.conn = sqlite3.connect(DB_PATH)
        self.cur = self.conn.cursor()
        self.create_table()
        self.porter_stemmer = PorterStemmer()

    def create_table(self):
        """
        Creates the list_cache table if it doesn't exist.
        """
        self.cur.execute(
            """
            CREATE TABLE IF NOT EXISTS list_cache (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                link TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    async def close(self):
        """
        Closes the database connection.
        """
        await self.conn.close()

    async def refresh_circulars(self) -> None:
        # expire in 1 min
        self.expiry = int(time.time()) + 60

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


async def get_pdf(url):
    """
    Downloads a PDF from a URL and saves it to a temporary directory.
    :param url: The URL of the PDF to download.
    :return: The path to the downloaded PDF.
    """
    # Get the filename from the URL
    filename = url.split("/")[-1]

    # Create the temporary directory if it doesn't exist
    os.makedirs(TEMP_DIR, exist_ok=True)

    # Download the file
    r = requests.get(url, allow_redirects=True)
    with open(os.path.join(TEMP_DIR, filename), 'wb') as f:
        f.write(r.content)

    # Return the path to the downloaded file
    return os.path.join(TEMP_DIR, filename)


async def get_text_from_pdf(file_path):
    """
    Extracts text from a PDF file.
    :param file_path: The path to the PDF file.
    :return: The extracted text.
    """
    # Open the PDF file
    pdf_file = pdfium.PdfDocument(file_path)

    text = ""
    # Extract text from each page
    for page in pdf_file:
        text += page.get_textpage().get_text_range()

    """
    # Delete the temporary file
    os.remove(file_path)
    """

    return text


async def cleanup():
    """
    Cleans up temporary files and directories.
    """
    """
    # Delete all files in the temporary directory
    for file in os.listdir(TEMP_DIR):
        os.remove(os.path.join(TEMP_DIR, file))
    log.info("Cleaned up temporary files.")
    """


async def get_categories():
    """
    Gets the list of categories from the BPS website.
    :return: A dictionary of categories and their IDs.
    """
    # Get the page
    r = requests.get(f"{bps_url}/circular/category/2-circulars", headers=headers)
    soup = BeautifulSoup(r.content, "html.parser", parse_only=SoupStrainer("a"))

    # Find all links with the href containing "circular/category"
    links = soup.find_all("a", href=lambda href: href and "circular/category" in href)

    # Create a dictionary of categories and their IDs
    categories = {}
    for link in links:
        # Get the category name from the link text
        category_name = link.text.strip().lower()
        # Get the category id from the link href
        category_id = int(link['href'].split("/")[-1].split("-")[0])
        categories[category_name] = category_id

    return categories


categories = asyncio.run(get_categories())
log.info(f"Got categories: {categories}")
asyncio.run(cleanup())
CircularListCache()
