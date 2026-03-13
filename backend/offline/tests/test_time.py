import unittest

from transit_offline.common.time import parse_gtfs_time_to_seconds


class TimeParserTest(unittest.TestCase):
    def test_extended_hours_supported(self) -> None:
        self.assertEqual(parse_gtfs_time_to_seconds("32:15:05"), 116105)

    def test_invalid_time_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_gtfs_time_to_seconds("08:61:00")
