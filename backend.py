import bs4
import nltk
import requests
import threading
import pickle
import time
from nltk.stem import PorterStemmer
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize


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
            links.append(f"https://bpsdoha.com{link}".strip())
    for old_title in old_titles:
        titles += old_title

    circulars = [Circular(title.strip(), link.strip())
                 for title, link in zip(titles, links)]
    return circulars if receive == "all" else titles if receive == "titles" else links if receive == "links" else None


def get_latest_circular(category: list, receive: str):
    soup = bs4.BeautifulSoup(requests.get(category[0], headers={
                             "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}).text, "lxml")
    title = soup.select(".pd-title")[0].text
    # Keep in mind, {link} already has a / at the start
    link = "https://bpsdoha.com" + \
        str(soup.select(".btn.btn-success")[0]["href"]).strip()
    circulars = Circular(title.strip(), link.strip())
    return circulars if receive == "all" else title.strip() if receive == "titles" else link.strip() if receive == "links" else None


def thread_function_for_get_download_url(title, URL, mutable):
    soup = bs4.BeautifulSoup(requests.get(URL, headers={
                             "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}).text, "lxml")
    titles_soup = soup.select(".pd-title")
    for title_no in range(len(titles_soup)):
        if str(titles_soup[title_no].text).strip().lower() == title.strip().lower():
            mutable.append("https://bpsdoha.com" +
                           str(soup.select(".btn.btn-success")[title_no]["href"]).strip())
            mutable.append(str(titles_soup[title_no].text).strip())


def get_download_url(title: str):
    urls = [
        "https://www.bpsdoha.net/circular/category/40", "https://www.bpsdoha.net/circular/category/38",
        "https://www.bpsdoha.net/circular/category/38?start=20", "https://www.bpsdoha.net/circular/category/35",
        "https://www.bpsdoha.net/circular/category/35?start=20"
    ]
    mutable, threads = [], []

    for URL in urls:
        threads.append(threading.Thread(
            target=lambda: thread_function_for_get_download_url(title, URL, mutable)))
        threads[-1].start()
    for thread in threads:
        thread.join()
    if mutable:
        return mutable[1], mutable[0]
    return None


def store_latest_circular():
    ptm = ["https://www.bpsdoha.net/circular/category/40"]
    general = ["https://www.bpsdoha.net/circular/category/38",
               "https://www.bpsdoha.net/circular/category/38?start=20"]
    exam = ["https://www.bpsdoha.net/circular/category/35",
            "https://www.bpsdoha.net/circular/category/35?start=20"]
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


def get_most_similar_sentence(keyword: str, sentences: list):
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


# this is a daemon thread, daemon process get autoterminated when the program ends, so dw bout the while loop
# Also these two lines of code MUST be at the end of the program! I think you should add it to main.py?
temp = threading.Thread(target=store_latest_circular, daemon=True)
print("starting thread")
temp.start()
