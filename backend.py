import bs4, requests, threading, pickle, time, os
import pypdfium2 as pdfium

cat_dict = {
    "ptm": (
        "https://www.bpsdoha.net/circular/category/40", # PTM (Page 1)
        "https://www.bpsdoha.net/circular/category/40?start=20", # PTM (Page 2)
        "https://www.bpsdoha.net/circular/category/40?start=40", # PTM (Page 3)
        ),

    "general": (
        "https://www.bpsdoha.net/circular/category/38",  # General (Page 1)
        "https://www.bpsdoha.net/circular/category/38?start=20",  # General (Page 2)
        "https://www.bpsdoha.net/circular/category/38?start=40"  # General (Page 3)
        "https://www.bpsdoha.net/circular/category/38?start=60"  # General (Page 4)
    ),

    "exam": (
        "https://www.bpsdoha.net/circular/category/35",  # Exam (Page 1)
        "https://www.bpsdoha.net/circular/category/35?start=20"  # Exam (Page 2)
        "https://www.bpsdoha.net/circular/category/35?start=40"  # Exam (Page 3)
    )
}

page_list = (
    "https://www.bpsdoha.net/circular/category/40",  # PTM (Page 1)
    "https://www.bpsdoha.net/circular/category/40?start=20",  # PTM (Page 2)
    "https://www.bpsdoha.net/circular/category/40?start=40",  # PTM (Page 3)

    "https://www.bpsdoha.net/circular/category/38",  # General (Page 1)
    "https://www.bpsdoha.net/circular/category/38?start=20",  # General (Page 2)
    "https://www.bpsdoha.net/circular/category/38?start=40"  # General (Page 3)
    "https://www.bpsdoha.net/circular/category/38?start=60"  # General (Page 4)

    "https://www.bpsdoha.net/circular/category/35",  # Exam (Page 1)
    "https://www.bpsdoha.net/circular/category/35?start=20"  # Exam (Page 2)
    "https://www.bpsdoha.net/circular/category/35?start=40"  # Exam (Page 3)
)




def per_url(url, old_titles, unprocessed_links, roll) -> None:
    soup = bs4.BeautifulSoup(requests.get(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"
    }).text, "lxml")

    for title in soup.select(".pd-title"):
        old_titles[roll].append(title.text)
    for link in soup.select(".btn.btn-success"):
        unprocessed_links[roll].append(link["href"])


def get_circular_list(url: tuple):
    titles, links, unprocessed_links, threads, old_titles = [], [], [], [], []
    for URL in range(len(url)):
        old_titles.append([])
        unprocessed_links.append([])
        threads.append(threading.Thread(target=lambda: per_url(
            url[URL], old_titles, unprocessed_links, URL)))
        threads[-1].start()
    for thread in threads:
        thread.join()
    for unprocessed_link in unprocessed_links:
        for link in unprocessed_link:
            # Keep in mind, {link} already has a / at the start
            links.append(f"https://bpsdoha.com{(link.split(':'))[0]}".strip())
    for old_title in old_titles:
        titles += old_title
    circulars = [{"title": title, "link": link} for title, link in zip(titles, links)]
    return circulars


def get_latest_circular(category: tuple):
    soup = bs4.BeautifulSoup(requests.get(category[0], headers={
                             "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}).text, "lxml")
    title = soup.select(".pd-title")[0].text
    # Keep in mind, {link} already has a / at the start
    link = "https://bpsdoha.com" + str(soup.select(".btn.btn-success")[0]["href"]).strip().split(":")[0]
    circulars = {"title": title.strip(), "link": link.strip()}
    return circulars


def thread_function_for_get_download_url(title, url, mutable):
    soup = bs4.BeautifulSoup(requests.get(url, headers={
                             "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}).text, "lxml")
    titles_soup = soup.select(".pd-title")
    for title_no in range(len(titles_soup)):
        if str(titles_soup[title_no].text).strip().lower() == title.strip().lower():
            mutable.append("https://bpsdoha.com" + str(soup.select(".btn.btn-success")[title_no]["href"]).strip().strip().split(":")[0])
            mutable.append(str(titles_soup[title_no].text).strip())


def get_download_url(title: str):
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
    ptm = cat_dict["ptm"]
    general = cat_dict["general"]
    exam = cat_dict["exam"]

    while True:
        data = {
            "ptm": get_latest_circular(ptm),
            "general": get_latest_circular(general),
            "exam": get_latest_circular(exam)
        }
        with open("temp.pickle", "wb") as f:
            pickle.dump(data, f)
        time.sleep(3600)


def get_cached_latest_circular(category: str):
    with open("temp.pickle", "rb") as f:
        data = pickle.load(f)
    circular = {"title": data[category]['title'], "link": data[category]['link']}
    return circular



def get_png(download_url) -> str:
    windows_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36'}
    file_id = download_url.split('=')[1].split(":")[0]  # Get the 4 digit file ID


    if os.path.isfile(f"./circularimages/{file_id}.png"):
        return f"https://bpsapi.rajtech.me/circularpng/{file_id}.png"

    pdf_file = requests.get(download_url, headers=windows_headers)


    with open(f"./{file_id}.pdf", "wb") as f:
        f.write(pdf_file.content)

    pdf = pdfium.PdfDocument(f"./{file_id}.pdf")
    page = pdf[0]
    pil_image = page.render_topil(
        scale=2,
        rotation=0,
        crop=(0, 0, 0, 0),
        colour=(255, 255, 255, 255),
        annotations=True,
        greyscale=False,
        optimise_mode=pdfium.OptimiseMode.NONE,
    )
    pil_image.save(f"./circularimages/{file_id}.png")
    os.remove(f"./{file_id}.pdf")

    return f"https://bpsapi.rajtech.me/circularpng/{file_id}.png"


# this is a daemon thread, daemon process get auto-terminated when the program ends, so don't worry about the while loop
temp = threading.Thread(target=store_latest_circular, daemon=True)
print("Starting latest circular thread")
temp.start()
