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
    # check if ./data/config.ini exists
    if os.path.exists('./data/config.ini'):
        config.read('data/config.ini')
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
        categories[category] = int(categories[category])

    log.debug(categories)

except Exception as err:
    log.critical("Error reading config.ini. Error: " + str(err))
    log_level = "INFO"

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
                page_list.append(f"{base_api_url}/circular-image/{file_id}.png")
            else:
                page_list.append(f"{base_api_url}/circular-image/{file_id}-{i + 1}.png")

        return page_list

    pdf_file = requests.get(download_url, headers=headers)

    # we're redirected to https://bpsdoha.com/component/users/ which means the file doesn't exist
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
    # Try to find the circular in the database
    if os.path.exists(".data/data.db"):
        con = sqlite3.connect(".data/data.db")
    elif os.path.exists("../data/data.db"):
        con = sqlite3.connect("../data/data.db")
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
