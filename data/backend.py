from logging.config import dictConfig
import bs4
import configparser
import logging
import os
import pickle
import pypdfium2 as pdfium
import requests
import threading
import time
import sqlite3
from pydantic import BaseModel
from bs4 import BeautifulSoup, SoupStrainer
from concurrent.futures import ThreadPoolExecutor

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


# Initializing the Logger
class LogConfig(BaseModel):
    """Logging configuration to be set for the server"""

    LOGGER_NAME: str = "bps-circular-api"
    LOG_FORMAT: str = "%(levelprefix)s %(message)s"
    LOG_LEVEL: str = "INFO"

    # Logging config
    version = 1
    disable_existing_loggers = False
    formatters = {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }
    handlers = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    }
    loggers = {
        "bps-circular-api": {"handlers": ["default"], "level": LOG_LEVEL},
    }


# Initiate the logging config
dictConfig(LogConfig().dict())
log = logging.getLogger("bps-circular-api")

# Getting config
config = configparser.ConfigParser()

try:
    config.read('./data/config.ini')
except Exception as e:
    print("Error reading the config.ini file. Error: " + str(e))
    exit()

try:
    default_pages: int = config.getint('main', 'default_pages')
    log_level: str = config.get('main', 'log_level')
    auto_page_increment: bool = config.getboolean('main', 'auto_page_increment')

    # get a dict of all the categories
    categories = dict(config.items('categories'))

    # make sure all the values are integers
    for category in categories.keys():
        categories[category] = int(categories[category])

    log.debug(categories)

except Exception as err:
    log.critical("Error reading config.ini. Error: " + str(err))
    auto_page_increment = True
    default_pages = -1
    log_level = "INFO"

# set log level
log.setLevel(log_level.upper() if log_level.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] else "INFO")
log.debug(f"Log level set to {log.level}")


#
#
#
#
#


async def get_num_pages(category_id):
    url = f'{bps_url}/circular/category/{category_id}'

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
    url = f'{bps_url}/circular/category/{category_id}?start={(page - 1) * 20}'

    response = requests.get(url, headers=headers)

    soup = BeautifulSoup(response.content, 'html.parser')

    fileboxes = soup.find_all('div', class_='pd-filebox')

    files = []
    for filebox in fileboxes:
        name = filebox.find('div', class_='pd-title').text
        url = bps_url + filebox.find('a', class_='btn-success')['href'].split(':')[0]
        id_ = url.split('=')[1].split(':')[0]
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
    url = f"{bps_url}/circular/category/{category_id}"
    response = requests.get(url, headers=headers)

    # Parse the response
    parse_only = SoupStrainer('div', class_='pd-filebox')
    soup = BeautifulSoup(response.content, 'lxml', parse_only=parse_only)

    # Find the first filebox and get the name and url
    name = soup.find('div', class_='pd-title').text
    url = bps_url + soup.find('a', class_='btn-success')['href'].split(':')[0]
    id_ = url.split('=')[1].split(':')[0]

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
                page_list.append(f"https://bpsapi.rajtech.me/circularpng/{file_id}.png")
            else:
                page_list.append(f"https://bpsapi.rajtech.me/circularpng/{file_id}-{i + 1}.png")

        return page_list

    pdf_file = requests.get(download_url, headers=windows_headers)

    with open(f"./{file_id}.pdf", "wb") as f:
        f.write(pdf_file.content)

    try:
        pdf = pdfium.PdfDocument(f"./{file_id}.pdf")
    except Exception as e:
        os.remove(f"./{file_id}.pdf")
        return None

    if not os.path.isdir("./circularimages"):  # Create the directory if it doesn't exist
        os.mkdir("./circularimages")

    page_list = []

    for page, pgno in zip(pdf, range(len(pdf))):

        pil_image = page.render_topil(
            scale=5,
            rotation=0,
            crop=(0, 0, 0, 0),  # Crop doesn't work for some reason
            colour=(255, 255, 255, 255),
            annotations=True,
            greyscale=False,
            optimise_mode=pdfium.OptimiseMode.NONE,
        )
        if pgno == 0:
            pil_image.save(f"./circularimages/{file_id}.png")
        else:
            pil_image.save(f"./circularimages/{file_id}-{pgno + 1}.png")

        if pgno == 0:
            page_list.append(f"https://bpsapi.rajtech.me/circularpng/{file_id}.png")
        else:
            page_list.append(f"https://bpsapi.rajtech.me/circularpng/{file_id}-{pgno + 1}.png")

    try:
        os.remove(f"./{file_id}.pdf")
    except WindowsError:
        log.error(
            "Could not delete the original PDF file, this is a Windows error, and is not a problem with the code. Please delete the PDF file manually.")

    return page_list


page_list: list[tuple, tuple, tuple] = []
try:
    page_list.extend(page_generator(category) for category in categories.keys())
    print(page_list)
except Exception as e:
    log.error(f"Error with getting circular page list line 337: {e}")


def get_from_id(_id: int):
    # go through all the bps circular pages and look for the id in the url
    con = sqlite3.connect("./data/data.db")
    cur = con.cursor()

    cur.execute("SELECT * FROM list_cache WHERE id=?", (_id,))
    data = cur.fetchone()
    if data:
        log.debug(f"Found circular with id {_id} in the database")
        return {"title": data[1], "link": data[2], "id": data[0]}

    log.debug(page_list)

    list_of_thing = []
    for i in page_list:
        for e in i:
            list_of_thing.append(e)

    print(list_of_thing)

    circular_list = get_circular_list(list_of_thing, quiet=True)
    for i in circular_list:
        if i['id'] == _id:
            log.debug(f"Found circular with id {_id} in the list, adding to DB")
            cur.execute("INSERT INTO list_cache VALUES (?, ?, ?)", (i['id'], i['title'].strip(), i['link'].strip()))
            con.commit()
            return {"title": i['title'].strip(), "link": i['link'].strip(), "id": i['id']}
    return None


def auto_extend_page_list():
    old_default_pages = default_pages
    while True:
        circulars = get_circular_list(tuple(page_list[0]), quiet=True)
        if len(circulars) == default_pages * 20:
            increment_page_number()
        else:
            break
    if old_default_pages != default_pages:
        log.info(f"Default page number has been increased from {old_default_pages} to {default_pages}")


def thread_func_for_auto_extend_page_list():
    while True:
        auto_extend_page_list()
        time.sleep(60 * 60 * 24)


if default_pages < 1:
    auto_extend_page_list()
    log.critical("default_pages is less than 1. Setting it to 5")

# this is a daemon thread, daemon processes get auto-terminated when the program ends, so we don't have to worry 
# about it 
log.info("Starting latest circular thread")
threading.Thread(target=store_latest_circular, daemon=True).start()

# loop auto_extend_page_list every 24 hours
if auto_page_increment:
    threading.Thread(target=thread_func_for_auto_extend_page_list, daemon=True).start()
