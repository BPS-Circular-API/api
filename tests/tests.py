import unittest
import starlette.responses
import asyncio

from main import (
    _get_circular_list,
    _get_latest_circular,
    _search,
    _get_png,
    _get_categories,
    root,
    _get_circular_images,
    _new_circulars
)
from backend import categories
import json

class CircularList(unittest.TestCase):
    def test_category(self):
        val = asyncio.run(_get_circular_list("ptm"))

        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)
        self.assertEqual(type(val), dict)

        self.assertNotEqual(val['data'][0]['title'], "")
        self.assertNotEqual(val['data'][0]['link'], "")
        self.assertNotEqual(val['data'][0]['id'], "")

    def test_invalid_category(self):
        val = asyncio.run(_get_circular_list("invalid"))

        self.assertEqual(type(val), starlette.responses.JSONResponse)

    def test_category_id(self):
        val = asyncio.run(_get_circular_list(55))  # general, as of 8/4/24

        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)
        self.assertEqual(type(val), dict)

        self.assertNotEqual(val['data'][0]['title'], "")
        self.assertNotEqual(val['data'][0]['link'], "")
        self.assertNotEqual(val['data'][0]['id'], "")

    def test_invalid_category_id(self):
        val = asyncio.run(_get_circular_list(9999))  # unlikely to exist

        self.assertEqual(type(val), starlette.responses.JSONResponse)
        self.assertEqual(val.status_code, 422)
        self.assertIn('Invalid category', val.body.decode())

    def test_empty_category(self):
        val = asyncio.run(_get_circular_list(""))

        self.assertEqual(type(val), starlette.responses.JSONResponse)
        self.assertEqual(val.status_code, 422)
        self.assertIn('Invalid category', val.body.decode())


class CircularLatest(unittest.TestCase):
    def test_category(self):
        val = asyncio.run(_get_latest_circular("general"))

        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)
        self.assertEqual(type(val), dict)

        self.assertNotEqual(val['data']['title'], "")
        self.assertNotEqual(val['data']['link'], "")
        self.assertNotEqual(val['data']['id'], "")

    def test_invalid_category(self):
        val = asyncio.run(_get_latest_circular("invalid"))

        self.assertEqual(type(val), starlette.responses.JSONResponse)
        self.assertEqual(val.status_code, 422)
        self.assertIn('Invalid category', val.body.decode())

    def test_category_id(self):
        val = asyncio.run(_get_latest_circular(55))

        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)
        self.assertEqual(type(val), dict)

        self.assertNotEqual(val['data']['title'], "")
        self.assertNotEqual(val['data']['link'], "")
        self.assertNotEqual(val['data']['id'], "")

    def test_invalid_category_id(self):
        val = asyncio.run(_get_latest_circular(9999))  # unlikely to exist

        self.assertEqual(type(val), starlette.responses.JSONResponse)
        self.assertEqual(val.status_code, 422)
        self.assertIn('Invalid category', val.body.decode())


class CircularSearch(unittest.TestCase):
    def test_query(self):
        val = asyncio.run(_search("ptm"))

        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)
        self.assertEqual(type(val), dict)

        self.assertEqual(type(val['data']), list)
        self.assertEqual(len(val['data']), 3)

    def test_invalid_query(self):
        val = asyncio.run(_search("invalid_query"))
        print(val)

        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)
        self.assertEqual(type(val), dict)

        self.assertEqual(type(val['data']), list)
        self.assertEqual(len(val['data']), 0)

    def test_amount(self):
        val = asyncio.run(_search("ptm", 5))

        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)
        self.assertEqual(type(val), dict)

        self.assertEqual(type(val['data']), list)
        self.assertEqual(len(val['data']), 5)

    def test_invalid_amount(self):
        val = asyncio.run(_search("ptm", -3))

        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)
        self.assertEqual(type(val), dict)

        self.assertEqual(type(val['data']), list)
        self.assertEqual(len(val['data']), 3)

    def test_id(self):
        val = asyncio.run(_search(1618, 5))

        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)
        self.assertEqual(type(val), dict)

        self.assertEqual(type(val['data']), list)
        self.assertEqual(len(val['data']), 1)

    def test_invalid_id(self):
        val = asyncio.run(_search(99999, 5))  # unlikely to exist

        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)
        self.assertEqual(type(val), dict)

        self.assertEqual(type(val['data']), list)
        self.assertEqual(len(val['data']), 0)


class CircularPNG(unittest.TestCase):
    def test_valid_png(self):
        val = asyncio.run(
            _get_png("https://bpsdoha.com/circular/category/45-exam-time-table-syllabus-2023-24?download=1337"))

        self.assertEqual(type(val), dict)
        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)

        self.assertEqual(type(val["data"]), list)

    def test_invalid_id(self):
        val = asyncio.run(
            _get_png("https://bpsdoha.com/circular/category/55-academic-year-2023-24?download=6969"))

        self.assertEqual(type(val), starlette.responses.JSONResponse)
        self.assertEqual(val.status_code, 400)
        self.assertIn('Error while attempting to get the PNG', val.body.decode())

    def test_invalid_url(self):
        val = asyncio.run(
            _get_png("https://notbpsdoha.com/circular/category/55-academic-year-2023-24?download=1337"))

        self.assertEqual(type(val), starlette.responses.JSONResponse)
        self.assertEqual(val.status_code, 422)
        self.assertIn('Invalid URL', val.body.decode())


class NewCirculars(unittest.TestCase):
    def test_existing_circular_id(self):
        # Replace with an existing circular ID to test
        circular_id = 1969
        val = asyncio.run(_new_circulars(circular_id))

        # Assuming that the response is successful when a valid circular ID is provided
        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)
        self.assertEqual(type(val), dict)

        # Check that the data returned is a list of circulars
        self.assertEqual(type(val["data"]), list)
        # Ensure that no circular in the list matches the provided circular_id
        self.assertNotIn(circular_id, [circular['id'] for circular in val['data']])

    def test_invalid_circular_id(self):
        # Replace with a circular ID that doesn't exist but the id is between 2 real circular ids
        circular_id = 1913
        val = asyncio.run(_new_circulars(circular_id))
        print(val)

        # Assuming that the response is successful when a valid circular ID is provided
        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)
        self.assertEqual(type(val), dict)

        # Check that the data returned is a list of circulars
        self.assertEqual(type(val["data"]), list)
        # Ensure that no circular in the list matches the provided circular_id
        self.assertNotIn(circular_id, [circular['id'] for circular in val['data']])
        # Ensure that no circular id in the list has id <circular_id
        self.assertNotEqual(0, len([int(circular['id']) < circular_id for circular in val['data']]))


    def test_9999_circular_id(self):
        # Test with an unlikely to exist circular ID (e.g., 9999)
        circular_id = 9999
        val = asyncio.run(_new_circulars(circular_id))
        print(val)

        # Since this ID is invalid, expect an error response
        self.assertEqual(len(val['data']), 0)



class AdditionalTests(unittest.TestCase):
    def test_get_categories(self):
        val = asyncio.run(_get_categories())

        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)
        self.assertEqual(val['data'], [i for i in categories.keys()])

    def test_root(self):
        val = asyncio.run(root())

        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)
        self.assertEqual(val["data"], "Welcome to the API. Please refer to the documentation at https://bpsapi.rajtech.me/docs for more information.")


if __name__ == '__main__':
    unittest.main()
