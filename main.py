from fastapi import FastAPI
from data.backend import *
from data.search_algo import SearchCorpus
import copy
import re
import sqlite3
from starlette.responses import JSONResponse
from fastapi.responses import FileResponse

app = FastAPI(
    title="BPS Circular API",
    description="An API that can work with the circulars of Birla Public School",
    version="1.0.0",
    # docs_url="../docs",
)


@app.exception_handler(500)
async def handler_500(err, e):
    error_content = copy.deepcopy(error_response)
    error_content["error"] = str(err)
    return JSONResponse(content=error_content, status_code=500)


@app.exception_handler(404)
async def handler_404(err, e):
    error_content = copy.deepcopy(error_response)
    error_content['http_status'] = 404
    error_content["error"] = "Not Found"
    return JSONResponse(content=error_content, status_code=404)


@app.get("/")
async def root():
    return_list = copy.deepcopy(success_response)
    # noinspection PyTypedDict
    return_list["data"] = "Welcome to the API. Please refer to the documentation " \
                          "at https://bpsapi.rajtech.me/docs for more information."
    return return_list


@app.get("/categories")
async def _get_categories():
    return_list = copy.deepcopy(success_response)
    return_list['data'] = [i for i in categories.keys()]
    return return_list


# Get RAW circular lists
@app.get("/list")
async def _get_circular_list(category: str or int):
    # Get the category id from the category name/id provided
    if type(category) == int or category.isdigit():
        category = int(category)
    else:
        category = categories.get(category.lower())

        if category is None:
            error = copy.deepcopy(error_response)
            error['error'] = f'Invalid category'
            error['http_status'] = 400
            return JSONResponse(content=error, status_code=400)

    # Get the number of pages in the category

    num_pages = await get_num_pages(category)

    if num_pages == 0:
        error = copy.deepcopy(error_response)
        error['error'] = f'Invalid category'
        error['http_status'] = 400
        return JSONResponse(content=error, status_code=400)

    # Get the circular list
    res = await get_list(category, num_pages)

    # Add the result to the return list
    return_list = copy.deepcopy(success_response)
    return_list['data'] = res

    # if len(return_list['data']) == 0:
    #     return_list['data'] = []

    return return_list


# Get latest circular
@app.get("/latest")
async def _get_latest_circular(category: str or int):
    # Get the category id from the category name/id provided
    if type(category) == int or category.isdigit():
        category = int(category)
    else:
        category = categories.get(category.lower())

        if category is None:
            error = copy.deepcopy(error_response)
            error['error'] = f'Invalid category'
            error['http_status'] = 400
            return JSONResponse(content=error, status_code=400)

    return_list = copy.deepcopy(success_response)

    try:
        res = await get_latest(category)
        return_list['data'] = res
    except Exception as e:
        return_list['data'] = "There are no circulars in this category."
        log.error(e)

    return return_list


@app.get("/search")
async def _search(query: str or int, amount: int = 3):  # TODO try to make searching by id faster
    # check if it is a circular id or title
    if type(query) == int or query.isdigit():
        return_list = copy.deepcopy(success_response)
        res = await search_from_id(query)

        if res is not None:
            return_list['data'] = [res]
        else:
            return_list['data'] = None

        return return_list

    # If title is a circular title, get a list of all circulars by scraping the website
    mega_list = []
    for i in categories.keys():
        mega_list += await get_list(categories[i], await get_num_pages(categories[i]))
    all_titles = [circular['title'] for circular in mega_list if circular['title'] is not None]

    # Create a corpus of all the titles, and search
    corpus = SearchCorpus()

    for t in mega_list:
        corpus.add_(t['title'])
    res = corpus.search(query, amount=amount)

    return_list = copy.deepcopy(success_response)

    if res is None:
        return_list['data'] = None
        return return_list

    # find the index of the title in mega_list['title'] and return the whole circular
    circulars = [
        mega_list[all_titles.index(i)] for i in res
    ]

    # res = get_download_url(res)
    if res is not None:
        return_list['data'] = circulars
    return return_list


@app.get("/getpng")
async def _get_png(url):
    bps_circular_regex = r"^(http:\/\/www\.|https:\/\/www\.|http:\/\/|https:\/\/)bpsdoha\.(com|net|edu\.qa)" \
                         r"\/circular\/category\/[0-9]+.*\?download=[0-9]+"
    if not re.match(bps_circular_regex, url):
        error = copy.deepcopy(error_response)
        error['error'] = f'Invalid URL'
        error['http_status'] = 400
        return JSONResponse(content=error, status_code=400)

    res = await get_png(url)

    return_list = copy.deepcopy(success_response)
    # noinspection PyTypedDict
    return_list['data'] = res

    return return_list


@app.get("/circular-image/{image_path}")
async def _get_circular_images(image_path) -> FileResponse:
    # return ./cicularimages/{image_path} as an image

    if not os.path.exists(f"./circularimages/{image_path}"):

        try:
            # If the imagepath is a circular id with .png extension
            if image_path[:4].isdigit() and image_path.endswith(".png"):
                # if image is referring to not first page of circular
                if "-" in image_path:
                    raise LookupError

                # try to get the circular
                res = await search_from_id(image_path[:4])
                if res is None:
                    raise LookupError

                # Try to get the image
                res = await get_png(res['link'])
                if res is None:
                    raise LookupError

                # if the image exists now
                if os.path.exists(f"./circularimages/{image_path}"):
                    return FileResponse(f"./circularimages/{image_path}")
                else:
                    raise LookupError

            else:
                raise LookupError

        except LookupError:
            error = copy.deepcopy(error_response)
            error['error'] = f'Image not found'
            error['http_status'] = 404
            return JSONResponse(content=error, status_code=400)

    return FileResponse(f"./circularimages/{image_path}")
