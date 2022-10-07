from fastapi import FastAPI, HTTPException
from backend import *
from searchAlgo import SearchCorpus
import copy, re
from starlette.responses import JSONResponse




app = FastAPI(
    title="BPS Circular API",
    description="An API that can work with the circulars of Birla Public School",
    version="1.0.0",
    # docs_url="../docs",
)

success_response = {
    "status": "success",
    "http_status": 200,
    "data": []
}

error_response = {
    "status": "error",
    "http_status": 400,
    "error": ""
}

@app.exception_handler(500)
async def error_handler(err):
    error_content = copy.deepcopy(error_response)
    error_content["error"] = str(err)
    return JSONResponse(content=error_content, status_code=500)


@app.get("/")
async def root():
    return_list = copy.deepcopy(success_response)
    # noinspection PyTypedDict
    return_list["message"] = return_list['data'] = "Welcome to the API. Please refer to the documentation at https://bpsapi.rajtech.me/docs for more information."
    return return_list


# Get RAW circular lists
@app.get("/list")
async def _get_circular_list(category: str or int):
    url = page_generator(category.lower())
    if url is None:
        raise HTTPException(
            status_code=400,
            detail=f'Invalid category. Valid categories are "ptm", "general" and "exam".'
        )

    res = get_circular_list(url)

    return_list = copy.deepcopy(success_response)

    for element in res:
        title = element['title']
        link = element['link']

        return_list['data'].append({"title": title, "link": link})

    if len(return_list['data']) == 0:
        return_list['message'] = "There are no circulars in this category."

    return return_list


# Get latest circular
@app.get("/latest")
async def _get_latest_circular(category: str or int):
    url = page_generator(category.lower())
    if url is None:
        raise HTTPException(
            status_code=400,
            detail=f'Invalid category. Valid categories are "ptm", "general" and "exam".'
        )

    return_list = copy.deepcopy(success_response)

    try:
        res = get_latest_circular(url)
        return_list['data'] = res
    except Exception as e:
        return_list['message'] = "There are no circulars in this category."
        print(e)

    return return_list


@app.get("/search")
async def _search(title: str):

    all_titles = get_circular_list(page_list)
    corpus = SearchCorpus()
    for t in all_titles:
        corpus.add_(t['title'])
    res = corpus.search(title, prnt=True)  # turn off after debugging

    return_list = copy.deepcopy(success_response)

    if res is None:
        # noinspection PyTypedDict
        return_list['data'] = None
        return return_list

    res = get_download_url(res)
    # noinspection PyTypedDict
    return_list['data'] = {"title": res[0], "link": res[1]}
    return return_list


@app.get("/cached-latest")
async def _get_cached_latest_circular(category: str or int):
    if not category.lower() in ['ptm', 'general', 'exam']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Valid categories for /carched-latest are 'ptm', 'general' and 'exam'."
        )

    res = get_cached_latest_circular(category.lower())

    return_list = copy.deepcopy(success_response)
    return_list['data'] = res
    return return_list


@app.get("/getpng")
async def _get_png(url):

    bps_circular_regex = r"^(http:\/\/www\.|https:\/\/www\.|http:\/\/|https:\/\/)bpsdoha\.(com|net|edu\.qa)\/circular\/category\/[0-9]+.*\?download=[0-9]+"
    if not re.match(bps_circular_regex, url):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid URL"
        )

    res = get_png(url)

    return_list = copy.deepcopy(success_response)
    # noinspection PyTypedDict
    return_list['data'] = res

    return return_list