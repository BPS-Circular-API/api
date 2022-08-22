from fastapi import FastAPI, HTTPException
from backend import *
from pydantic import BaseModel


class CatAndRecInput(BaseModel):
    category: str
    receive: str = "all"

class TitleInput(BaseModel):
    title: str

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Welcome to the BPS Circular API. Note that this is not an official API. Documentation can be found at https://raj.moonball.io/bpsapi/docs"}



# Get RAW circular lists
@app.get("/list/")
async def _get_circular_list(userinput: CatAndRecInput):
    category, receive = userinput.category.lower(), userinput.receive.lower()
    ptm = ["https://www.bpsdoha.net/circular/category/40"]
    general = ["https://www.bpsdoha.net/circular/category/38",
               "https://www.bpsdoha.net/circular/category/38?start=20"]
    exam = ["https://www.bpsdoha.net/circular/category/35",
            "https://www.bpsdoha.net/circular/category/35?start=20"]

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

    ptm = ["https://www.bpsdoha.net/circular/category/40"]
    general = ["https://www.bpsdoha.net/circular/category/38",
               "https://www.bpsdoha.net/circular/category/38?start=20"]
    exam = ["https://www.bpsdoha.net/circular/category/35",
            "https://www.bpsdoha.net/circular/category/35?start=20"]
    
    url = ptm if category == "ptm" else general if category == "general" else exam if category == "exam" else None
    if url is None:
        return HTTPException(status_code=400, detail="Category not found")
    if not receive.lower() in ["all", "titles", "links"]:
        return HTTPException(status_code=400, detail="Receive not found")
    
    return get_latest_circular(url, receive.lower())

@app.get("/downloadurl/")
async def _get_url(userinput: TitleInput):
    title = userinput.title.strip()
    return get_download_url(title)


@app.get("/search/")
async def _search(userinput: TitleInput):
    title = userinput.title
    print(title)
    urls = [
        "https://www.bpsdoha.net/circular/category/40", "https://www.bpsdoha.net/circular/category/38",
        "https://www.bpsdoha.net/circular/category/38?start=20", "https://www.bpsdoha.net/circular/category/35",
        "https://www.bpsdoha.net/circular/category/35?start=20"
        ]


    all_titles = get_circular_list(urls, "titles")
    print(all_titles)
    res = search(title, all_titles)
    return res



@app.get("/cached-latest/")
async def _get_cached_latest_circular(userinput: CatAndRecInput):
    x = get_cached_latest_circular(userinput.category.lower(), userinput.receive.lower())
    return x
