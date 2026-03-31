import unittest
from miniagent.tools.basic_tools import calculator


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


if __name__ == '__main__':
    unittest.main()