import unittest
import starlette.responses
import asyncio

from main import _get_circular_list, _get_latest_circular, _search, _get_png


class CircularList(unittest.TestCase):
    def test_category(self):
        val = asyncio.run(_get_circular_list("general"))

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
        val = asyncio.run(_get_circular_list(44))  # general, as of 24/7/23

        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)
        self.assertEqual(type(val), dict)

        self.assertNotEqual(val['data'][0]['title'], "")
        self.assertNotEqual(val['data'][0]['link'], "")
        self.assertNotEqual(val['data'][0]['id'], "")

    def test_invalid_category_id(self):
        val = asyncio.run(_get_circular_list(12))

        self.assertEqual(type(val), starlette.responses.JSONResponse)


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

    def test_category_id(self):
        val = asyncio.run(_get_latest_circular(44))

        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)
        self.assertEqual(type(val), dict)

        self.assertNotEqual(val['data']['title'], "")
        self.assertNotEqual(val['data']['link'], "")
        self.assertNotEqual(val['data']['id'], "")

    def test_invalid_category_id(self):
        val = asyncio.run(_get_latest_circular(12))

        self.assertEqual(type(val), starlette.responses.JSONResponse)


class CircularSearch(unittest.TestCase):
    def test_query(self):
        val = asyncio.run(_search("ptm"))

        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)
        self.assertEqual(type(val), dict)

        self.assertEqual(type(val['data']), list)
        self.assertEqual(len(val['data']), 3)

    def test_invalid_query(self):
        val = asyncio.run(_search("invalid"))

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
        val = asyncio.run(_search(1337, 5))
        print(val)

        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)
        self.assertEqual(type(val), dict)

        self.assertEqual(type(val['data']), list)
        self.assertEqual(len(val['data']), 1)

    def test_invalid_id(self):
        val = asyncio.run(_search(1001, 5))

        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)
        self.assertEqual(type(val), dict)

        self.assertEqual(type(val['data']), list)
        self.assertEqual(len(val['data']), 0)


class CircularPNG(unittest.TestCase):
    def test_singlepage(self):
        val = asyncio.run(
            _get_png("https://bpsdoha.com/circular/category/45-exam-time-table-syllabus-2023-24?download=1337"))

        self.assertEqual(type(val), dict)
        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)

        self.assertEqual(type(val["data"]), list)
        self.assertEqual(len(val["data"]), 1)

    def test_emptypage(self):
        val = asyncio.run(
            _get_png("https://bpsdoha.com/circular/category/44-academic-year-2023-24?download=1386"))

        self.assertEqual(type(val), dict)
        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)

        self.assertEqual(type(val["data"]), list)
        self.assertEqual(len(val["data"]), 1)

    def test_multipage(self):
        val = asyncio.run(
            _get_png("https://bpsdoha.com/circular/category/44-academic-year-2023-24?download=1397"))

        self.assertEqual(type(val), dict)
        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)

        self.assertEqual(type(val["data"]), list)
        self.assertEqual(len(val["data"]), 3)

    def test_invalidid(self):
        val = asyncio.run(
            _get_png("https://bpsdoha.com/circular/category/44-academic-year-2023-24?download=6969"))

        self.assertEqual(type(val), starlette.responses.JSONResponse)

    def test_invalidurl(self):
        val = asyncio.run(
            _get_png("https://notbpsdoha.com/circular/category/44-academic-year-2023-24?download=1337"))

        self.assertEqual(type(val), starlette.responses.JSONResponse)

    def test_regex1(self):
        # Test regex for bpsdoha.com
        val = asyncio.run(
            _get_png("https://bpsdoha.com/circular/category/44-academic-year-2023-24?download=1337"))

        self.assertEqual(type(val), dict)
        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)

        self.assertEqual(type(val["data"]), list)
        self.assertEqual(len(val["data"]), 1)

    def test_regex2(self):
        # Test regex for bpsdoha.net
        val = asyncio.run(
            _get_png("https://bpsdoha.net/circular/category/44-academic-year-2023-24?download=1337"))

        self.assertEqual(type(val), dict)
        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)

        self.assertEqual(type(val["data"]), list)
        self.assertEqual(len(val["data"]), 1)

    def test_regex3(self):
        # Test regex for bpsdoha.edu.qa

        val = asyncio.run(
            _get_png("https://bpsdoha.edu.qa/circular/category/44-academic-year-2023-24?download=1337"))

        self.assertEqual(type(val), dict)
        self.assertEqual(val["status"], "success")
        self.assertEqual(val["http_status"], 200)

        self.assertEqual(type(val["data"]), list)
        self.assertEqual(len(val["data"]), 1)







if __name__ == '__main__':
    unittest.main()
