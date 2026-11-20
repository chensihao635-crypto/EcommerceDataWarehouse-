import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from ai_assistant import execute, validate


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'demo.db'
        with closing(sqlite3.connect(self.db)) as c:
            c.execute('CREATE TABLE dwd_order_detail(invoice_no TEXT, customer_id INTEGER, invoice_date TEXT, country TEXT, quantity INTEGER, unit_price REAL, total_amount REAL)')
            c.executemany('INSERT INTO dwd_order_detail VALUES(?,?,?,?,?,?,?)', [
                ('A', 1, '2011-11-01 10:00:00', 'UK', 1, 10, 10),
                ('A', 1, '2011-11-01 10:00:00', 'UK', 1, 20, 20),
                ('B', 1, '2011-11-30 23:59:59', 'UK', 1, 30, 30),
                ('C1', 2, '2011-11-02', 'UK', 1, 900, 900),
                ('D', 2, '2011-11-02', 'France', 1, 40, 40),
                ('E', 3, '2011-12-01', 'UK', 1, 500, 500)])
            c.commit()

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self, metric='revenue', **kw):
        return dict(metric=metric, group_by=kw.get('group_by', 'none'), start='2011-11-01', end='2011-11-30', country=kw.get('country'), limit=10, descending=True)

    def test_metrics_and_date_boundaries(self):
        for metric, value in [('revenue', 100), ('orders', 3), ('aov', 100/3), ('repeat_rate', .5)]:
            with self.subTest(metric=metric):
                self.assertAlmostEqual(execute(self.plan(metric), self.db)['rows'][0]['value'], value)

    def test_grouping(self):
        self.assertEqual(execute(self.plan(group_by='country'), self.db)['rows'][0], {'dimension': 'UK', 'value': 60})
        self.assertEqual(execute(self.plan('repeat_rate', group_by='country'), self.db)['rows'][0]['value'], 1)
        self.assertEqual(execute(self.plan(group_by='month'), self.db)['rows'][0]['dimension'], '2011-11')

    def test_injection_stays_parameter(self):
        result = execute(self.plan(country="UK' OR 1=1 --"), self.db)
        self.assertIsNone(result['rows'][0]['value'])

    def test_invalid_plans(self):
        for patch in [{'metric': 'DROP TABLE'}, {'limit': True}, {'limit': 101}, {'descending': 'yes'}, {'start': '2011-12-31'}, {'extra': 'sql'}, {'group_by': 'month', 'metric': 'repeat_rate'}]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                validate({**self.plan(), **patch})


if __name__ == '__main__':
    unittest.main()
