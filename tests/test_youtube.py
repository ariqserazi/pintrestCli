import unittest
import asyncio
from pathlib import Path
from app.youtube_client import (
    search_youtube_videos,
    youtube_query_slug,
    _format_duration,
)
from app.cli import create_parser

class TestYouTubeClient(unittest.TestCase):
    def test_query_slug(self):
        slug = youtube_query_slug("Python Tutorial in 100 Seconds!")
        self.assertEqual(slug, "python-tutorial-in-100-seconds")

    def test_format_duration(self):
        self.assertEqual(_format_duration(144), "02:24")
        self.assertEqual(_format_duration(3665), "01:01:05")
        self.assertEqual(_format_duration(None), "N/A")

    def test_search_youtube_videos_live(self):
        videos = asyncio.run(search_youtube_videos("Python in 100 seconds", limit=2))
        self.assertGreaterEqual(len(videos), 1)
        video = videos[0]
        self.assertTrue(video.video_id)
        self.assertTrue(video.title)
        self.assertTrue(video.video_url.startswith("https://www.youtube.com"))

class TestYouTubeCLI(unittest.TestCase):
    def setUp(self):
        self.parser = create_parser()

    def test_youtube_search_args(self):
        args = self.parser.parse_args(["youtube", "search", "lofi hip hop", "--limit", "3", "--json"])
        self.assertEqual(args.service, "youtube")
        self.assertEqual(args.command, "search")
        self.assertEqual(args.query, "lofi hip hop")
        self.assertEqual(args.limit, 3)
        self.assertTrue(args.json)

    def test_youtube_download_args(self):
        args = self.parser.parse_args(["youtube", "download", "--query", "lofi hip hop", "--index", "1", "--format", "mp3"])
        self.assertEqual(args.service, "youtube")
        self.assertEqual(args.command, "download")
        self.assertEqual(args.query, "lofi hip hop")
        self.assertEqual(args.index, 1)
        self.assertEqual(args.format, "mp3")

if __name__ == "__main__":
    unittest.main()
