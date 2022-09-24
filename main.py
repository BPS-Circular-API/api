import re

from fastapi import FastAPI, HTTPException
from backend import *
from searchAlgo import SearchCorpus
from pydantic import BaseModel

ptm = cat_dict["ptm"]
general = cat_dict["general"]
exam = cat_dict["exam"]

class CategoryInput(BaseModel):
    category: str

class TitleInput(BaseModel):
    title: str

class UrlInput(BaseModel):
    url: str


app = FastAPI()

success_response = {
    "status": "success",
    "http_status": 200,
    "data": []
}

# error_response = {
#     "status": "error",
#     "http_status": 400,
#     "error": []
# }


@app.get("/")
async def root():
    return {"message": "Welcome to the BPS Circular API. Note that this is not an official API. Documentation can be found at https://bpsapi.rajtech.me/docs"}


# Get RAW circular lists
@app.get("/list")
async def _get_circular_list(userinput: CategoryInput):
    category = userinput.category.lower()

    url = ptm if category == "ptm" else general if category == "general" else exam if category == "exam" else None
    if url is None:
        raise HTTPException(
            status_code=400,
            detail=f'Invalid category. Valid categories are "ptm", "general" and "exam".'
        )

    res = get_circular_list(url)

    return_list = {
    "status": "success",
    "http_status": 200,
    "data": []
}
    print(res)

    for element in res:
        print(element)
        title = element['title']
        link = element['link']

        return_list['data'].append({"title": title, "link": link})

    return return_list


# Get latest circular
@app.get("/latest")
async def _get_latest_circular(userinput: CategoryInput):
    category =  userinput.category.lower()

    url = ptm if category == "ptm" else general if category == "general" else exam if category == "exam" else None
    if url is None:
        raise HTTPException(
            status_code=400,
            detail=f'Invalid category. Valid categories are "ptm", "general" and "exam".'
        )


    res = get_latest_circular(url)

    return_list = {"status": "success", "http_status": 200, 'data': res}

    return return_list


@app.get("/search")
async def _search(userinput: TitleInput):
    title = userinput.title
    print(title)
    urls = [
        "https://www.bpsdoha.net/circular/category/40", "https://www.bpsdoha.net/circular/category/38",
        "https://www.bpsdoha.net/circular/category/38?start=20", "https://www.bpsdoha.net/circular/category/35",
        "https://www.bpsdoha.net/circular/category/35?start=20"
    ]

    all_titles = get_circular_list(urls, "titles")
    corpus = SearchCorpus()
    for t in all_titles:
        corpus.add_(t)
    res = corpus.search(title, prnt=True)  # turn off after debugging
    return get_download_url(res)


@app.get("/cached-latest")
async def _get_cached_latest_circular(userinput: CategoryInput):

    if not userinput.category.lower() in ["ptm", "general", "exam"]:
        raise HTTPException(
            status_code=400,
            detail=f'Invalid category. Valid categories are "ptm", "general" and "exam".'
        )

    res = get_cached_latest_circular(userinput.category.lower())
    return_list = {"status": "success", "http_status": 200, 'data': res}

    return return_list


@app.get("/getpng")
async def _get_png(urlinput: UrlInput):
    bps_circular_regex = r"^(http:\/\/www\.|https:\/\/www\.|http:\/\/|https:\/\/)bpsdoha\.com\/circular\/category\/[0-9]+.*\?download=[0-9]+"
    if not re.match(bps_circular_regex, urlinput.url):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid URL"
        )

    res = get_png(urlinput.url)

    return_list = {
        "status": "success",
        "http_status": 200,
        "data": res
    }

    return return_list