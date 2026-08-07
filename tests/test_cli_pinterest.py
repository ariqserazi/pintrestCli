import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app import cli
from app.pinterest_client import PinterestPin


class PinterestCLITests(unittest.TestCase):
    def setUp(self):
        self.sample_pins = [
            PinterestPin(
                pin_id="101",
                title="Pin One",
                description="Desc 1",
                pin_url="https://www.pinterest.com/pin/101/",
                image_url="https://i.pinimg.com/originals/101.jpg",
                width=1200,
                height=1800,
                pinner="user1",
            ),
            PinterestPin(
                pin_id="102",
                title="Pin Two",
                description="Desc 2",
                pin_url="https://www.pinterest.com/pin/102/",
                image_url="https://i.pinimg.com/originals/102.jpg",
                width=800,
                height=600,
                pinner="user2",
            ),
        ]

    def run_cli(self, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = 0
        with patch.object(sys, "argv", ["clipsearch"] + args):
            with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                try:
                    cli.main()
                except SystemExit as exc:
                    exit_code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    @patch("app.cli.search_public_pinterest", new_callable=AsyncMock)
    def test_search_success_json_schema_and_aspect_ratio(self, mock_search):
        mock_search.return_value = ("https://www.pinterest.com/search/pins/?q=test", self.sample_pins)

        code, out, err = self.run_cli(["pinterest", "search", "abandoned mall", "--limit", "2", "--json"])

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        data = json.loads(out)
        self.assertTrue(data["ok"])
        self.assertEqual(data["command"], "search")
        self.assertEqual(data["source"], "pinterest")
        self.assertEqual(data["query"], "abandoned mall")
        self.assertEqual(data["count"], 2)
        
        results = data["results"]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["index"], 1)
        self.assertEqual(results[0]["pin_id"], "101")
        self.assertEqual(results[0]["aspect_ratio"], round(1200 / 1800, 4))
        self.assertIsNone(results[0]["local_path"])
        self.assertEqual(results[1]["index"], 2)
        self.assertEqual(results[1]["aspect_ratio"], round(800 / 600, 4))

    @patch("app.cli.search_public_pinterest", new_callable=AsyncMock)
    def test_search_zero_results(self, mock_search):
        mock_search.return_value = ("https://www.pinterest.com/search/pins/?q=nonexistent", [])

        code, out, err = self.run_cli(["pinterest", "search", "nonexistent", "--json"])

        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["ok"])
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])

    def test_search_limit_validation(self):
        code, out, err = self.run_cli(["pinterest", "search", "query", "--limit", "100", "--json"])
        self.assertEqual(code, 2)
        data = json.loads(out)
        self.assertFalse(data["ok"])
        self.assertEqual(data["error"]["code"], "INVALID_ARGUMENT")

    @patch("app.cli.search_public_pinterest", new_callable=AsyncMock)
    @patch("app.cli.download_pinterest_pin", new_callable=AsyncMock)
    def test_download_valid_index(self, mock_download, mock_search):
        mock_search.return_value = ("https://www.pinterest.com/search/pins/?q=test", self.sample_pins)
        mock_download.return_value = Path("./images/abandoned-mall-02-102.jpg")

        with tempfile.TemporaryDirectory() as temp_dir:
            code, out, err = self.run_cli([
                "pinterest", "download",
                "--query", "abandoned mall",
                "--index", "2",
                "--output", temp_dir,
                "--json"
            ])

        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["ok"])
        self.assertEqual(data["command"], "download")
        result = data["result"]
        self.assertEqual(result["index"], 2)
        self.assertEqual(result["pin_id"], "102")
        self.assertEqual(result["pin_url"], "https://www.pinterest.com/pin/102/")
        self.assertEqual(result["local_path"], str(Path("./images/abandoned-mall-02-102.jpg")))

    @patch("app.cli.search_public_pinterest", new_callable=AsyncMock)
    def test_download_invalid_index_out_of_bounds(self, mock_search):
        mock_search.return_value = ("https://www.pinterest.com/search/pins/?q=test", self.sample_pins)

        code, out, err = self.run_cli([
            "pinterest", "download",
            "--query", "abandoned mall",
            "--index", "5",
            "--json"
        ])

        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertFalse(data["ok"])
        self.assertEqual(data["error"]["code"], "INVALID_INDEX")

    @patch("app.cli.search_public_pinterest", new_callable=AsyncMock)
    def test_download_no_results(self, mock_search):
        mock_search.return_value = ("https://www.pinterest.com/search/pins/?q=test", [])

        code, out, err = self.run_cli([
            "pinterest", "download",
            "--query", "empty query",
            "--index", "1",
            "--json"
        ])

        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertFalse(data["ok"])
        self.assertEqual(data["error"]["code"], "NO_RESULTS")

    @patch("app.cli.search_public_pinterest", new_callable=AsyncMock)
    @patch("app.cli.download_pinterest_pin", new_callable=AsyncMock)
    def test_download_failure(self, mock_download, mock_search):
        mock_search.return_value = ("https://www.pinterest.com/search/pins/?q=test", self.sample_pins)
        mock_download.side_effect = ValueError("Image download forbidden")

        code, out, err = self.run_cli([
            "pinterest", "download",
            "--query", "abandoned mall",
            "--index", "1",
            "--json"
        ])

        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertFalse(data["ok"])
        self.assertEqual(data["error"]["code"], "PINTEREST_DOWNLOAD_FAILED")

    @patch("app.cli.search_public_pinterest", new_callable=AsyncMock)
    @patch("app.cli.download_pinterest_pin", new_callable=AsyncMock)
    def test_fetch_multiple_and_partial_failures(self, mock_download, mock_search):
        mock_search.return_value = ("https://www.pinterest.com/search/pins/?q=test", self.sample_pins)
        
        async def fake_download(pin, destination_stem):
            if pin.pin_id == "102":
                raise ValueError("Image unavailable")
            return destination_stem.with_suffix(".jpg")

        mock_download.side_effect = fake_download

        with tempfile.TemporaryDirectory() as temp_dir:
            code, out, err = self.run_cli([
                "pinterest", "fetch",
                "abandoned mall",
                "--limit", "2",
                "--output", temp_dir,
                "--json"
            ])

        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["ok"])
        self.assertEqual(data["command"], "fetch")
        self.assertEqual(data["requested"], 2)
        self.assertEqual(data["downloaded"], 1)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["pin_id"], "101")
        self.assertEqual(len(data["errors"]), 1)
        self.assertEqual(data["errors"][0]["pin_id"], "102")
        self.assertIn("Image unavailable", data["errors"][0]["error"])

    @patch("app.cli.search_public_pinterest", new_callable=AsyncMock)
    def test_search_failure_network_error(self, mock_search):
        mock_search.side_effect = ValueError("Pinterest returned a non-JSON search response")

        code, out, err = self.run_cli(["pinterest", "search", "failed query", "--json"])

        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertFalse(data["ok"])
        self.assertEqual(data["error"]["code"], "PINTEREST_SEARCH_FAILED")
        self.assertIn("Pinterest returned a non-JSON", data["error"]["details"])

    @patch("app.cli.search_public_pinterest", new_callable=AsyncMock)
    def test_human_readable_output(self, mock_search):
        mock_search.return_value = ("https://www.pinterest.com/search/pins/?q=test", self.sample_pins)

        code, out, err = self.run_cli(["pinterest", "search", "abandoned mall", "--limit", "2"])

        self.assertEqual(code, 0)
        self.assertIn("Pinterest results for: abandoned mall", out)
        self.assertIn("[1] Pin One (1200x1800)", out)
        self.assertIn("[2] Pin Two (800x600)", out)


if __name__ == "__main__":
    unittest.main()
