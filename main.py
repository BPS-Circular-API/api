from fastapi import FastAPI, Request
from backend import *
import copy
import re
from starlette.responses import JSONResponse
from fastapi.responses import FileResponse

app = FastAPI(
    title="BPS Circular API",
    description="An API that can work with the circulars of Birla Public School",
    version="1.0.0",
)

circular_list_cache = CircularListCache()


@app.exception_handler(500)
async def handler_500(request: Request, err):
    error_content = copy.deepcopy(error_response)
    error_content["error"] = str(err)
    return JSONResponse(content=error_content, status_code=500)


@app.exception_handler(404)
async def handler_404(request: Request, err):
    error_content = copy.deepcopy(error_response)
    error_content['http_status'] = 404
    error_content["error"] = "Not Found"
    return JSONResponse(content=error_content, status_code=404)


@app.get("/")
async def root(request: Request):
    return_list = copy.deepcopy(success_response)
    # noinspection PyTypedDict
    return_list["data"] = "Welcome to the API. Please refer to the documentation " \
                          f"at {request.base_url}docs for more information."
    return return_list


@app.get("/categories")
async def _get_categories():
    return_list = copy.deepcopy(success_response)
    return_list['data'] = [i for i in categories.keys()]
    return return_list


# Get RAW circular lists
@app.get("/list")
@app.get("/list/{category}")
async def _get_circular_list(category: str | int):
    # Get the category id from the category name/id provided
    if type(category) is int or category.isdigit():
        category = int(category)
    else:
        category = categories.get(category.lower())

        if category is None:
            error = copy.deepcopy(error_response)
            error['error'] = f'Invalid category'
            error['http_status'] = 422
            return JSONResponse(content=error, status_code=422)

    # Get the number of pages in the category
    num_pages = await get_num_pages(category)

    if num_pages == 0:
        error = copy.deepcopy(error_response)
        error['error'] = f'Invalid category'
        error['http_status'] = 422
        return JSONResponse(content=error, status_code=422)

    # Get the circular list
    res = await get_list(category, num_pages)

    # Add the category key to every circular object
    res = [{**data, 'category': category} for data in res]

    # Add the result to the return list
    return_list = copy.deepcopy(success_response)
    return_list['data'] = res

    # if len(return_list['data']) == 0:
    #     return_list['data'] = []

    return return_list


# Get latest circular
@app.get("/latest")
@app.get("/latest/{category}")
async def _get_latest_circular(category: str | int):
    # Get the category id from the category name/id provided
    if type(category) is int or category.isdigit():
        category = int(category)
    else:
        category = categories.get(category.lower())

        if category is None:
            log.debug("Category is none, 400'ing")

            error = copy.deepcopy(error_response)
            error['error'] = f'Invalid category'
            error['http_status'] = 422

            return JSONResponse(content=error, status_code=422)

    return_list = copy.deepcopy(success_response)

    try:
        res = await get_latest(category)
        res['category'] = category
        return_list['data'] = res

    except Exception as e:
        error = copy.deepcopy(error_response)
        error['error'] = f'Invalid category'
        error['http_status'] = 422

        return JSONResponse(content=error, status_code=422)

    return return_list


@app.get("/search")
@app.get("/search/{query}")
async def _search(query: str | int, amount: int = 3):  # TODO try to make searching by id faster
    # check if it is a circular id or title
    if type(query) == int or query.isdigit():
        log.debug("Searching by id")
        return_list = copy.deepcopy(success_response)
        res = await search_from_id(query)

        if res is not None:
            return_list['data'] = [res]
        else:
            return_list['data'] = []

        return return_list

    if amount < 1:
        amount = 3

    # If title is a circular title, get a list of all circulars by scraping the website
    res = await search_algo(circular_list_cache, query, amount)
    return_list = copy.deepcopy(success_response)

    if res is None:
        return_list['data'] = None
        return return_list

    if res is not None:
        return_list['data'] = res
    return return_list


@app.get("/getpng")
@app.get("/get-png")
async def _get_png(url):
    circular_pdf_regex = r"^(http:\/\/www\.|https:\/\/www\.|http:\/\/|https:\/\/)bpsdoha\.(com|net|edu\.qa)" \
                         r"\/circular\/category\/[0-9]+.*\?download=[0-9]+"
    if not re.match(circular_pdf_regex, url):
        error = copy.deepcopy(error_response)
        error['error'] = f'Invalid URL'
        error['http_status'] = 422
        return JSONResponse(content=error, status_code=422)

    try:
        res = await get_png(url)
    except Exception as e:
        error = copy.deepcopy(error_response)
        error['error'] = f'Error while attempting to get the PNG'
        error['http_status'] = 400
        return JSONResponse(content=error, status_code=400)

    return_list = copy.deepcopy(success_response)
    return_list['data'] = res

    return return_list


@app.get("/circular-image/{image_path}")
async def _get_circular_images(image_path) -> JSONResponse:
    # return ./circularimages/{image_path} as an image

    if not os.path.exists("./circularimages/"):
        os.makedirs("./circularimages/")

    # If the image isn't already saved to disk
    if not os.path.exists(f"./circularimages/{image_path}"):
        try:
            # If the imagepath is a circular id with .png extension
            if image_path[:4].isdigit() and image_path.endswith(".png"):

                # # if image is not referring to first page of circular
                # if "-" in image_path:
                #     log.debug("Image is not first page of circular")
                #     raise LookupError

                # Try to fetch the circular to see if it exists
                res = await search_from_id(image_path[:4])
                if res is None:
                    log.debug("Circular not found")
                    raise LookupError

                # Try to fetch the image from the website
                res = await get_png(res['link'])
                if res is None:
                    log.debug("Image not found")
                    raise LookupError

                # If the requested circular image is now on disk
                if os.path.exists(f"./circularimages/{image_path}"):
                    # Ignore the PyCharm warning here
                    return FileResponse(f"./circularimages/{image_path}")
                else:
                    log.debug("Image still not found")
                    raise LookupError

            else:
                log.debug("invalid image path")
                raise LookupError

        except LookupError:
            error = copy.deepcopy(error_response)
            error['error'] = f'Image not found'
            error['http_status'] = 404
            return JSONResponse(content=error, status_code=404)

    return FileResponse(f"./circularimages/{image_path}")


# This endpoint was added to simplify apps that notify when new circulars come out.
# It returns the circulars succeeding {circular_id}.
@app.get("/new-circulars/")
@app.get("/new-circulars/{circular_id}")
async def _new_circulars(circular_id: int = None):
    """Returns the circulars succeeding the given one."""
    circular_list = await circular_list_cache.get_cache()

    # If no circular_id is passed, every circular is 'new'
    # Search for the target circular in the sorted list and return all succeeding ones
    # If target circular is not found, return all circulars whose id is greater than the target circular
    if circular_id is None:
        passed_circular_index: None = None
    else:
        # Check if the passed circular id is a valid integer
        try:
            circular_id: int = int(circular_id)
        except ValueError:
            error = copy.deepcopy(error_response)
            error['error'] = f'Invalid circular id'
            error['http_status'] = 422
            return JSONResponse(content=error, status_code=422)

        # Iterate through the circulars in circular_list  and get the index
        # of the target circular (> circular_id)
        for index in range(len(circular_list)):
            if int(circular_list[index]['id']) == circular_id:
                passed_circular_index: int = index
                break
        # If the circular isn't found in the circular list; the ID is invalid
        # Find the index of the first valid circular >circular_id
        else:
            passed_circular_index = None
            for index in range(len(circular_list))[::-1]:
                if int(circular_list[index]['id']) > circular_id:
                    passed_circular_index = index + 1
                    break
            else:
                passed_circular_index: int = 0

    return_list = copy.deepcopy(success_response)
    return_list['data'] = circular_list[:passed_circular_index]

    return return_list

