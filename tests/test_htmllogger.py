# type: ignore
import os
import unittest

import arrow

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
            os.path.exists(os.path.join("test_html", "main.bundle.js")),
            "main.bundle.js was not copied",
        )

    def test_old_monitor(self):
        test_logger = HTMLLogger({"folder": "test_html", "filename": "status.html"})
        monitor = MonitorNull(config_options={"gap": 12 * 3600})
        monitor.run_test()
        test_logger.start_batch()
        for hours, status in ((11, "OK"), (13, "OLD"), (25, "OLD"), (72, "OLD")):
            with self.subTest(hours=hours):
                monitor.last_update = arrow.utcnow().shift(hours=-hours)
                test_logger.save_result2("test", monitor)
                data_line = test_logger.batch_data[monitor.name]
                self.assertEqual(data_line["status_text"], status)
                self.assertAlmostEqual(data_line["age"], hours * 3600, delta=60)

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
