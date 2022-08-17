from fastapi import FastAPI, HTTPException
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from backend import get_circular_list, get_latest_circular

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
async def read_item(item_id):
    return {"item_id": item_id}


# BPS website status
@app.get("/website/status")
async def website_status():
    req = Request("https://www.bpsdoha.net/")
    try:
        response = urlopen(req)
        print("Website is working fine", response.getcode())
        return {"status": "Website is working fine", "code": response.getcode()}
    except HTTPError as e:
        print("The server couldn't fulfill the request.", e.code)
        return {"status": "The server couldn't fulfill the request.", "code": e.code}
    except URLError as e:
        print("We failed to reach the server: ", e.reason)
        return  {"status": "We failed to reach the server: ", "reason": e.reason}
    except Exception as e:
        print('Error: ', e)


# Get RAW circular lists
@app.get("/circular/list/")
async def _get_circular_list(category: str, receive: str = "all"):
    ptm = ["https://www.bpsdoha.net/circular/category/40"]
    general = ["https://www.bpsdoha.net/circular/category/38",
               "https://www.bpsdoha.net/circular/category/38?start=20"]
    exam = ["https://www.bpsdoha.net/circular/category/35",
            "https://www.bpsdoha.net/circular/category/35?start=20"]

    url = ptm if category == "ptm" else general if category == "general" else exam if category == "exam" else None
    if url is None:
        return HTTPException(status_code=400, detail="Category not found")
    if not receive in ["all", "titles", "links"]:
        return HTTPException(status_code=400, detail="Receive not found")

    return get_circular_list(url, receive)


# Get latest circular
@app.get("/circular/latest/")
async def _get_latest_circular(category: str, receive: str = "all"):
    ptm = ["https://www.bpsdoha.net/circular/category/40"]
    general = ["https://www.bpsdoha.net/circular/category/38",
               "https://www.bpsdoha.net/circular/category/38?start=20"]
    exam = ["https://www.bpsdoha.net/circular/category/35",
            "https://www.bpsdoha.net/circular/category/35?start=20"]
    
    url = ptm if category == "ptm" else general if category == "general" else exam if category == "exam" else None
    if url is None:
        return HTTPException(status_code=400, detail="Category not found")
    if not receive in ["all", "titles", "links"]:
        return HTTPException(status_code=400, detail="Receive not found")
    
    return get_latest_circular(url, receive)
