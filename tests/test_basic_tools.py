import unittest
from miniagent.tools.basic_tools import CalculatorTool

class TestCalculatorTool(unittest.TestCase):
    def test_addition(self):
        calc = CalculatorTool()
        result = calc.execute('2 + 2')
        self.assertEqual(result, '4')

if __name__ == '__main__':
    unittest.main()