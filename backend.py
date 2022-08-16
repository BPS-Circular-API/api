import bs4, requests, threading



def per_url(url, old_titles, unprocessed_links, roll) -> None:
    soup = bs4.BeautifulSoup(requests.get(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"
    }).text, "lxml")

    for title in soup.select(".pd-title"):
        old_titles[roll].append(title.text)
    for link in soup.select(".btn.btn-success"):
        unprocessed_links[roll].append(link["href"])


def get_circular_list(url: list, receive: str) -> list | None:
    titles, links, unprocessed_links, threads, old_titles = [], [], [], [], []
    for URL in range(len(url)):
        old_titles.append([])
        unprocessed_links.append([])
        threads.append(threading.Thread(target=lambda: per_url(url[URL], old_titles, unprocessed_links, URL)))
        threads[-1].start()
    for thread in threads:
        thread.join()
    for unprocessed_link in unprocessed_links:
        for link in unprocessed_link:
            links.append(f"https://bpsdoha.com{link}".strip())  # Keep in mind, {link} already has a / at the start
    for old_title in old_titles:
        titles += old_title

    class Circular:
        def __init__(self, title, link):
            self.title = title
            self.link = link

        def __repr__(self) -> str:
            return f"{self.title}||{self.link}"

    # print(links)
    circulars = [Circular(title, link) for title, link in zip(titles, links)]

    if receive == "all":
        return circulars
    elif receive == "titles":
        return titles
    elif receive == "links":
        return links
    return circulars if receive == "all" else titles if receive == "titles" else links if receive == "links" else None


def get_latest_circular(category: list, receive: str) -> list | None:
    titles, links, unprocessed_links, threads, old_titles = [], [], [], [], []
    for URL in range(len(category)):
        old_titles.append([])
        unprocessed_links.append([])
        threads.append(threading.Thread(target=lambda: per_url(category[URL], old_titles, unprocessed_links, URL)))
        threads[-1].start()
    for thread in threads:
        thread.join()
    for unprocessed_link in unprocessed_links:
        for link in unprocessed_link:
            links.append(f"https://bpsdoha.com{link}".strip())  # Keep in mind, {link} already has a / at the start
    for old_title in old_titles:
        titles += old_title

    circulars = f"{titles[0]}||{links[0]}"
    return circulars if receive == "all" else titles[0].strip() if receive == "titles" else links[0].strip() if receive == "links" else None

