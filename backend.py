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
from pydantic import BaseModel

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
    config.read('config.ini')
except Exception as e:
    print("Error reading the config.ini file. Error: " + str(e))
    exit()

try:
    default_pages: int = config.getint('main', 'default_pages')
    log_level: str = config.get('main', 'log_level')
    auto_page_increment: bool = config.getboolean('main', 'auto_page_increment')
except Exception as err:
    log.critical("Error reading config.ini. Error: " + str(err))
    auto_page_increment = True
    default_pages = -1
    log_level = "INFO"

# set log level
log.setLevel(log_level.upper() if log_level.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] else "INFO")
log.debug(f"Log level set to {log.level}")


# Functions
def increment_page_number():
    global default_pages, ptm, general, exam, page_list
    default_pages += 1

    # change the value in the config file
    config.set('main', 'default_pages', str(default_pages))
    with open('config.ini', 'w') as configfile:
        config.write(configfile)
    log.debug("Incremented the page number to " + str(default_pages))

    ptm = page_generator('ptm')
    general = page_generator('general')
    exam = page_generator('exam')

    page_list = tuple([ptm, general, exam])


def page_generator(category: str or int, pages: int = -1) -> tuple or None:
    if pages == -1:
        pages = default_pages
    preset_cats = {"general": 38, "ptm": 40, "exam": 35}
    # check if category is a number
    if category.isnumeric():
        category = int(category)
        if category < 1:
            return None

    if type(category) == str:
        category = preset_cats[category]

    urls = []
    # generate urls incrementing by 20 but starting from 0
    for i in range(0, pages * 20, 20):
        urls.append(f"https://www.bpsdoha.net/circular/category/{category}?start={i}")
    log.debug(urls)

    return tuple(urls)


def per_url(url, old_titles, unprocessed_links, roll) -> None:
    soup = bs4.BeautifulSoup(requests.get(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"
    }).text, "lxml")

    for title in soup.select(".pd-title"):
        old_titles[roll].append(title.text)
    for link in soup.select(".btn.btn-success"):
        unprocessed_links[roll].append(link["href"])


def get_circular_list(url: tuple, quiet: bool = False) -> list:
    titles, links, ids, unprocessed_links, threads, old_titles = [], [], [], [], [], []

    for URL in range(len(url)):
        old_titles.append([])
        unprocessed_links.append([])
        threads.append(threading.Thread(target=lambda: per_url(url[URL], old_titles, unprocessed_links, URL)))
        threads[-1].start()

    for thread in threads:
        thread.join()

    for unprocessed_link in unprocessed_links:
        for link in unprocessed_link:
            links.append(f"https://bpsdoha.com{(link.split(':'))[0]}".strip())
            id_ = link.split('=')[1].split(":")[0]
            ids.append(id_)

    for old_title in old_titles:
        titles += old_title

    circulars = [{"title": title, "id": id_, "link": link} for title, link, id_ in zip(titles, links, ids)]

    if len(circulars) == default_pages * 20:
        if not quiet:
            if not auto_page_increment:
                log.error(
                    "The default number of pages is too low, and older circulars may become unreachable by the web-scraper. Please increase the number of pages in config.ini")
            else:
                log.info(
                    "The default number of pages is was to low in config.ini, It has been automatically increased. If you want to disable this, set auto_page_increment to False in config.ini")
                auto_extend_page_list()

    return circulars


def get_latest_circular(category: tuple) -> dict[str, str]:
    soup = bs4.BeautifulSoup(requests.get(category[0], headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}).text,
                             "lxml")
    title = soup.select(".pd-title")[0].text
    # Keep in mind, {link} already has a / at the start
    link = "https://bpsdoha.com" + str(soup.select(".btn.btn-success")[0]["href"]).strip().split(":")[0]
    circulars = {"title": title.strip(), "link": link.strip()}
    return circulars


def thread_function_for_get_download_url(title, url, mutable):
    soup = bs4.BeautifulSoup(requests.get(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}).text,
                             "lxml")
    titles_soup = soup.select(".pd-title")
    for title_no in range(len(titles_soup)):
        if str(titles_soup[title_no].text).strip().lower() == title.strip().lower():
            mutable.append("https://bpsdoha.com" +
                           str(soup.select(".btn.btn-success")[title_no]["href"]).strip().strip().split(":")[0])
            mutable.append(str(titles_soup[title_no].text).strip())


def get_download_url(title: str) -> tuple or None:
    mutable, threads = [], []

    for URL in page_list:
        threads.append(threading.Thread(
            target=lambda: thread_function_for_get_download_url(title, URL, mutable)))
        threads[-1].start()
    for thread in threads:
        thread.join()
    if mutable:
        return mutable[1], mutable[0]
    return None


def store_latest_circular():
    while True:
        data = {
            "ptm": get_latest_circular(page_generator('ptm')),
            "general": get_latest_circular(page_generator('general')),
            "exam": get_latest_circular(page_generator('exam'))
        }
        with open("temp.pickle", "wb") as f:
            pickle.dump(data, f)
        time.sleep(3600)


def get_cached_latest_circular(category: str):
    with open("temp.pickle", "rb") as f:
        data = pickle.load(f)
    circular = {"title": data[category]['title'], "link": data[category]['link']}
    return circular


def get_png(download_url) -> str or None:
    windows_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36'}
    file_id = download_url.split('=')[1].split(":")[0]  # Get the 4 digit file ID

    if os.path.isfile(f"./circularimages/{file_id}.png"):
        return f"https://bpsapi.rajtech.me/circularpng/{file_id}.png"

    pdf_file = requests.get(download_url, headers=windows_headers)

    with open(f"./{file_id}.pdf", "wb") as f:
        f.write(pdf_file.content)



    try:
        pdf = pdfium.PdfDocument(f"./{file_id}.pdf")
    except Exception as e:
        os.remove(f"./{file_id}.pdf")
        return None


    page = pdf[0]

    pil_image = page.render_topil(
        scale=5,
        rotation=0,
        crop=(0, 0, 0, 0),  # Crop doesn't work for some reason
        colour=(255, 255, 255, 255),
        annotations=True,
        greyscale=False,
        optimise_mode=pdfium.OptimiseMode.NONE,
    )

    if not os.path.isdir("./circularimages"):  # Create the directory if it doesn't exist
        os.mkdir("./circularimages")

    pil_image.save(f"./circularimages/{file_id}.png")
    try:
        os.remove(f"./{file_id}.pdf")
    except WindowsError:
        log.error("Could not delete the original PDF file, this is a Windows error, and is not a problem with the code. Please delete the PDF file manually.")

    return f"https://bpsapi.rajtech.me/circularpng/{file_id}.png"


ptm = page_generator('ptm')
general = page_generator('general')
exam = page_generator('exam')
page_list = []
# add the items of ptm, general and exam to page_list
page_list.extend(ptm)
page_list.extend(general)
page_list.extend(exam)


def auto_extend_page_list():
    old_default_pages = default_pages
    while True:
        circulars = get_circular_list(general, quiet=True)
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

# this is a daemon thread, daemon processes get auto-terminated when the program ends, so we don't have to worry about it
log.info("Starting latest circular thread")
threading.Thread(target=store_latest_circular, daemon=True).start()

# loop auto_extend_page_list every 24 hours
if auto_page_increment:
    threading.Thread(target=thread_func_for_auto_extend_page_list, daemon=True).start()

print("Started")
