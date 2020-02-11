# type: ignore
import os
import unittest

from simplemonitor.Loggers.file import HTMLLogger
from simplemonitor.Monitors.monitor import MonitorNull


class TestHTMLLogger(unittest.TestCase):
    def setUp(self):
        self._test_path = "test_html"
        try:
            os.mkdir(self._test_path)
        except FileExistsError:
            pass

    def test_html_logger(self):
        config_options = {
            "folder": "test_html",
            "copy_resources": True,
            "filename": "status.html",
        }
        test_logger = HTMLLogger(config_options)
        monitor = MonitorNull()
        monitor.run_test()
        test_logger.start_batch()
        test_logger.save_result2("test", monitor)
        test_logger.process_batch()
        test_logger.end_batch()

        self.assertTrue(
            os.path.exists(os.path.join("test_html", "status.html")),
            "status.html was not created",
        )
        self.assertTrue(
            os.path.exists(os.path.join("test_html", "style.css")),
            "style.css was not copied",
        )

    def tearDown(self):
        if os.path.isdir(self._test_path):
            for filename in os.listdir(self._test_path):
                try:
                    os.unlink(os.path.join(self._test_path, filename))
                except IOError:
                    pass
            try:
                os.rmdir(self._test_path)
            except IOError:
                pass
