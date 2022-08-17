from fastapi import FastAPI, HTTPException
from backend import get_circular_list, get_latest_circular, get_download_url
from pydantic import BaseModel


class Item(BaseModel):
    name: str


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Welcome to the BPS Circular API. Note that this is not an official API. Documentation can be found at https://raj.moonball.io/bpsapi/docs"}

@app.get("/items/{item_id}")
async def read_item(item_id):
    return {"item_id": item_id}



# Get RAW circular lists
@app.get("/list/")
async def _get_circular_list(category: str, receive: str = "all"):
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
async def _get_latest_circular(category: str, receive: str = "all"):
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

@app.get("/geturl/")
async def _get_url(title: str):
    return get_download_url(title)

@app.get("/test/")
async def test(e: Item):
    print(e)
    return {"item_name": "got it"}