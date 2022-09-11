from fastapi import FastAPI, HTTPException
from backend import *
from pydantic import BaseModel

ptm = cat_dict["ptm"]
general = cat_dict["general"]
exam = cat_dict["exam"]

class CatAndRecInput(BaseModel):
    category: str
    receive: str = "all"


class TitleInput(BaseModel):
    title: str

class UrlInput(BaseModel):
    url: str


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Welcome to the BPS Circular API. Note that this is not an official API. Documentation can be found at https://bpsapi.rajtech.me/docs"}


# Get RAW circular lists
@app.get("/list/")
async def _get_circular_list(userinput: CatAndRecInput):
    category, receive = userinput.category.lower(), userinput.receive.lower()

    url = ptm if category == "ptm" else general if category == "general" else exam if category == "exam" else None
    if url is None:
        return HTTPException(status_code=400, detail="Category not found")
    if not receive.lower() in ["all", "titles", "links"]:
        return HTTPException(status_code=400, detail="Receive not found")

    return get_circular_list(url, receive.lower())


# Get latest circular
@app.get("/latest/")
async def _get_latest_circular(userinput: CatAndRecInput):
    category, receive = userinput.category.lower(), userinput.receive.lower()

    url = ptm if category == "ptm" else general if category == "general" else exam if category == "exam" else None
    if url is None:
        return HTTPException(status_code=400, detail="Category not found")
    if not receive.lower() in ["all", "titles", "links"]:
        return HTTPException(status_code=400, detail="Receive not found")

    return get_latest_circular(url, receive.lower())


@app.get("/search/")
async def _search(userinput: TitleInput):
    title = userinput.title

    all_titles = get_circular_list(pages_list, "titles")
    res = get_most_similar_sentence(title, all_titles)
    return get_download_url(res)


@app.get("/cached-latest/")
async def _get_cached_latest_circular(userinput: CatAndRecInput):
    x = get_cached_latest_circular(userinput.category.lower(), userinput.receive.lower())
    return x

@app.get("/getpng")
async def _get_png(urlinput: UrlInput):
    return get_png(urlinput.url)