import os
import unittest
from unittest.mock import patch

from miniagent.tools.basic_tools import (
    calculator,
    get_current_time,
    system_info,
    disk_usage,
    file_stats,
    web_search,
)


class TestCalculator(unittest.TestCase):
    def test_addition(self):
        result = calculator('2 + 2')
        self.assertEqual(result['result'], 4)

    def test_math_functions(self):
        result = calculator('sqrt(16)')
        self.assertEqual(result['result'], 4.0)

    def test_invalid_expression(self):
        result = calculator('import os')
        self.assertIn('error', result)

    def test_division_by_zero(self):
        result = calculator('1 / 0')
        self.assertIn('error', result)
        self.assertIn('division by zero', result['error'].lower())

    def test_complex_expression(self):
        result = calculator('2 ** 10')
        self.assertEqual(result['result'], 1024)


class TestGetCurrentTime(unittest.TestCase):
    def test_returns_dict_with_keys(self):
        result = get_current_time()
        self.assertIn('iso', result)
        self.assertIn('formatted', result)


class TestSystemInfo(unittest.TestCase):
    def test_returns_dict_with_platform(self):
        result = system_info()
        self.assertIsInstance(result, dict)
        self.assertIn('platform', result)
        self.assertIn('python_version', result)

    def test_contains_cpu_info(self):
        result = system_info()
        self.assertIn('processor', result)


class TestDiskUsage(unittest.TestCase):
    def test_returns_dict(self):
        result = disk_usage()
        self.assertIsInstance(result, dict)
        self.assertIn('total_bytes', result)
        self.assertIn('free_bytes', result)


class TestFileStats(unittest.TestCase):
    def test_existing_directory(self):
        result = file_stats('.')
        self.assertIsInstance(result, dict)
        self.assertIn('file_count', result)

    def test_nonexistent_path(self):
        """file_stats raises ValueError for nonexistent paths."""
        with self.assertRaises(ValueError):
            file_stats('/nonexistent_path_12345')


class TestWebSearch(unittest.TestCase):
    def test_missing_api_key(self):
        """web_search should return error list when SERPAPI_KEY is missing."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure SERPAPI_KEY is not set
            os.environ.pop('SERPAPI_KEY', None)
            result = web_search('test query')
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1)
            self.assertIn('error', result[0])
            self.assertIn('SERPAPI_KEY', result[0]['error'])


if __name__ == '__main__':
    unittest.main()