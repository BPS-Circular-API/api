import os

import bs4, requests, threading, pickle, time
from nltk.stem import PorterStemmer
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import pypdfium2 as pdfium

cat_dict = {
    "ptm": (
        "https://www.bpsdoha.net/circular/category/40", # PTM (Page 1)
        "https://www.bpsdoha.net/circular/category/40?start=20" # PTM (Page 2)
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

pages_list = (
    "https://www.bpsdoha.net/circular/category/40",  # PTM (Page 1)
    "https://www.bpsdoha.net/circular/category/40?start=20",  # PTM (Page 2)

    "https://www.bpsdoha.net/circular/category/38",  # General (Page 1)
    "https://www.bpsdoha.net/circular/category/38?start=20",  # General (Page 2)
    "https://www.bpsdoha.net/circular/category/38?start=40"  # General (Page 3)
    "https://www.bpsdoha.net/circular/category/38?start=60"  # General (Page 4)

    "https://www.bpsdoha.net/circular/category/35",  # Exam (Page 1)
    "https://www.bpsdoha.net/circular/category/35?start=20"  # Exam (Page 2)
    "https://www.bpsdoha.net/circular/category/35?start=40"  # Exam (Page 3)
)


class Circular:
    def __init__(self, title, link):
        self.title = title
        self.link = link

    def __repr__(self) -> str:
        return f"{self.title}||{self.link}"


def per_url(url, old_titles, unprocessed_links, roll) -> None:
    soup = bs4.BeautifulSoup(requests.get(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"
    }).text, "lxml")

    for title in soup.select(".pd-title"):
        old_titles[roll].append(title.text)
    for link in soup.select(".btn.btn-success"):
        unprocessed_links[roll].append(link["href"])


def get_circular_list(url: list, receive: str):
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
            dwn_url = (link.split(":"))[0]  # Remove the redundant part of the URL
            links.append(f"https://bpsdoha.com{dwn_url}".strip())
    for old_title in old_titles:
        titles += old_title

    circulars = [Circular(title.strip(), link.strip())
                 for title, link in zip(titles, links)]
    return circulars if receive == "all" else titles if receive == "titles" else links if receive == "links" else None


def get_latest_circular(category: tuple, receive: str):
    soup = bs4.BeautifulSoup(requests.get(category[0], headers={
                             "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}).text, "lxml")
    title = soup.select(".pd-title")[0].text
    # Keep in mind, {link} already has a / at the start
    link = "https://bpsdoha.com" + str(soup.select(".btn.btn-success")[0]["href"]).strip().split(":")[0]
    circulars = Circular(title.strip(), link.strip())
    return circulars if receive == "all" else title.strip() if receive == "titles" else link.strip() if receive == "links" else None


def thread_function_for_get_download_url(title, URL, mutable):
    soup = bs4.BeautifulSoup(requests.get(URL, headers={
                             "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}).text, "lxml")
    titles_soup = soup.select(".pd-title")
    for title_no in range(len(titles_soup)):
        if str(titles_soup[title_no].text).strip().lower() == title.strip().lower():
            mutable.append("https://bpsdoha.com" + str(soup.select(".btn.btn-success")[title_no]["href"]).strip().strip().split(":")[0])
            mutable.append(str(titles_soup[title_no].text).strip())


def get_download_url(title: str):
    mutable, threads = [], []

    for URL in pages_list:
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
            "ptm": get_latest_circular(ptm, "all"),
            "general": get_latest_circular(general, "all"),
            "exam": get_latest_circular(exam, "all")
        }
        with open("temp.pickle", "wb") as f:
            pickle.dump(data, f)
        time.sleep(3600)


def get_cached_latest_circular(category: str, receive: str):
    with open("temp.pickle", "rb") as f:
        data = pickle.load(f)
    circular = Circular(data[category].title, data[category].link)
    return circular if receive == "all" else circular.title if receive == "titles" else circular.link if receive == "links" else None


def get_most_similar_sentence(keyword: str, sentences: tuple):
    ps = PorterStemmer()
    a = sentences
    # removal of stopwords
    stop_words = list(stopwords.words('english'))
    # removal of punctuation signs
    punc = '''!()-[]{};:'"\, <>./?@#$%^&*_~'''
    s = [(word_tokenize(a[i])) for i in range(len(a))]
    outer_1 = []
    for i in range(len(s)):
        inner_1 = []
        for j in range(len(s[i])):
            if s[i][j] not in (punc or stop_words):
                s[i][j] = ps.stem(s[i][j])
                if s[i][j] not in stop_words:
                    inner_1.append(s[i][j].lower())
        outer_1.append(set(inner_1))
    rvector = outer_1[0]
    for i in range(1, len(s)):
        rvector = rvector.union(outer_1[i])
    outer = []
    for i in range(len(outer_1)):
        inner = []
        for w in rvector:
            if w in outer_1[i]:
                inner.append(1)
            else:
                inner.append(0)
        outer.append(inner)
    check = (word_tokenize(keyword))
    check = [ps.stem(check[i]).lower() for i in range(len(check))]
    check1 = []
    for w in rvector:
        if w in check:
            check1.append(1)  # create a vector
        else:
            check1.append(0)
    ds = []
    for j in range(len(outer)):
        similarity_index = 0
        c = 0
        if check1 == outer[j]:
            ds.append(0)
        else:
            for i in range(len(rvector)):
                c += check1[i]*outer[j][i]
            similarity_index += c
            ds.append(similarity_index)
    maximum = max(ds)
    for i in range(len(ds)):
        if ds[i] == maximum:
            return a[i]


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
