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



@app.get("/status")
async def website_status():
    req = Request("https://www.bpsdoha.net/")
    try:
        response = urlopen(req)
        print('Website is working fine', response.getcode())
        return {"status": "Website is working fine", "code": response.getcode()}
    except HTTPError as e:
        print('The server couldn\'t fulfill the request.', e.code)
        return {"status": "The server couldn\'t fulfill the request.", "code": e.code}
    except URLError as e:
        print('We failed to reach the server: ', e.reason)
        return  {"status": "We failed to reach the server: ", "reason": e.reason}
    except Exception as e:
        print('Error: ', e)


