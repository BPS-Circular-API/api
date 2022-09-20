from fastapi import FastAPI, HTTPException
from backend import *
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

error_response = {
    "status": "error",
    "http_status": 400,
    "data": []
}


@app.get("/")
async def root():
    return {"message": "Welcome to the BPS Circular API. Note that this is not an official API. Documentation can be found at https://bpsapi.rajtech.me/docs"}


# Get RAW circular lists
@app.get("/list/")
async def _get_circular_list(userinput: CategoryInput):
    category = userinput.category.lower()

    url = ptm if category == "ptm" else general if category == "general" else exam if category == "exam" else None
    if url is None:
        return HTTPException(status_code=400, detail="Category not found")

    res = get_circular_list(url)

    return_list = success_response
    print(res)

    for element in res:
        print(element)
        title = element['title']
        link = element['link']

        return_list['data'].append({"title": title, "url": link})

    return return_list


# Get latest circular
@app.get("/latest/")
async def _get_latest_circular(userinput: CategoryInput):
    category =  userinput.category.lower()

    url = ptm if category == "ptm" else general if category == "general" else exam if category == "exam" else None
    if url is None:
        return HTTPException(status_code=400, detail="Category not found")


    res = get_latest_circular(url)

    return_list = {
        "status": "success",
        "http_status": 200,
        "data": []
    }

    return_list['data'].append(res)
    return return_list


@app.get("/search/")
async def _search(userinput: TitleInput):
    title = userinput.title

    all_titles = get_circular_list(page_list)
    res = get_most_similar_sentence(title, all_titles)
    return get_download_url(res)


@app.get("/cached-latest/")
async def _get_cached_latest_circular(userinput: CategoryInput):
    res = get_cached_latest_circular(userinput.category.lower())
    return_list = success_response

    return_list['data'].append(res)
    return return_list

@app.get("/getpng")
async def _get_png(urlinput: UrlInput):
    res = get_png(urlinput.url)

    return_list = success_response
    return_list['data'].append(res)

    return return_list