from fastapi import FastAPI
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
async def handler_500(request, exc):
    error_content = copy.deepcopy(error_response)
    error_content["error"] = str(exc)
    return JSONResponse(content=error_content, status_code=500)


@app.exception_handler(404)
async def handler_404(request, exc):
    error_content = copy.deepcopy(error_response)
    error_content['http_status'] = 404
    error_content["error"] = "Not Found"
    return JSONResponse(content=error_content, status_code=404)


@app.get("/")
async def root():
    return_list = copy.deepcopy(success_response)
    # noinspection PyTypedDict
    return_list["data"] = "Welcome to the API. Please refer to the documentation " \
                          f"at {app.docs_url} for more information."
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
            error['http_status'] = 400
            return JSONResponse(content=error, status_code=400)

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
async def _search(query: str):
    # Search for the query in the circular list cache
    res = await circular_list_cache.search(query)

    return_list = copy.deepcopy(success_response)
    return_list['data'] = res
    return return_list


@app.get("/download/{category}/{filename}")
async def _download(category: str, filename: str):
    # Get the category id from the category name/id provided
    if category.isdigit():
        category = int(category)
    else:
        category = categories.get(category.lower())

        if category is None:
            error = copy.deepcopy(error_response)
            error['error'] = f'Invalid category'
            error['http_status'] = 422
            return JSONResponse(content=error, status_code=422)

    # Get the circular from the circular list cache
    circular = await circular_list_cache.get_circular_by_filename(filename)

    if circular is None:
        log.debug("Circular is none, 404'ing")
        error = copy.deepcopy(error_response)
        error['error'] = 'Not Found'
        error['http_status'] = 404
        return JSONResponse(content=error, status_code=404)

    # Download the PDF file
    file_path = await get_pdf(circular['url'])

    if file_path is None:
        error = copy.deepcopy(error_response)
        error['error'] = 'Could not download file'
        error['http_status'] = 500
        return JSONResponse(content=error, status_code=500)

    # Return the file
    return FileResponse(file_path, filename=filename)
