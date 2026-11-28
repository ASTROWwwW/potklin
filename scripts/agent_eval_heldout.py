"""Held-out tasks, written after the agent loop was tuned on the core set.

Measure a change to the agent on these only after it is finished; tuning against them ends their value.
"""


def env_override(variant):
    return {
        "scope": ["settings.py"],
        "solution": [("settings.py", "        if key in environment:\n            settings[key] = environment[key]\n",
                      "        name = 'APP_' + key.upper()\n        if name in environment:\n            raw, kind = environment[name], type(settings[key])\n            settings[key] = raw.lower() == 'true' if kind is bool else kind(raw)\n")],
        "request": "Overrides are not applied by load_settings. Make it behave as its docstring says so the tests pass.",
        "files": {
            "settings.py": 'DEFAULTS = {"port": 8000, "debug": False, "name": "svc"}\n\n\ndef load_settings(environment):\n    """Return DEFAULTS with overrides from environment variables named APP_<KEY IN UPPER CASE>.\n    Each value is converted to the type of its default; a boolean is True only for "true" in any case."""\n    settings = dict(DEFAULTS)\n    for key in settings:\n        if key in environment:\n            settings[key] = environment[key]\n    return settings\n',
            "tests/test_settings.py": "from settings import load_settings\nassert load_settings({'APP_PORT': '9000'}) == {'port': 9000, 'debug': False, 'name': 'svc'}\n",
        },
        "test": "tests/test_settings.py", "protect": ["tests"],
        "oracle": f"from settings import load_settings, DEFAULTS\nassert load_settings({{'APP_DEBUG': 'TRUE', 'APP_PORT': '{variant}'}}) == {{'port': {variant}, 'debug': True, 'name': 'svc'}}\nassert load_settings({{'APP_DEBUG': 'no'}})['debug'] is False\nassert load_settings({{'port': '1', 'APP_NAME': 'x'}}) == {{'port': 8000, 'debug': False, 'name': 'x'}}\nassert DEFAULTS['port'] == 8000\n",
    }


def pagination(variant):
    return {
        "scope": ["paging.py"],
        "solution": [("paging.py", "    start = page * size\n", "    if page < 1:\n        raise ValueError(page)\n    start = (page - 1) * size\n"),
                     ("paging.py", "    return count // size\n", "    return (count + size - 1) // size\n")],
        "request": "The paging helpers return wrong pages. Fix them according to their docstrings so the tests pass.",
        "files": {
            "paging.py": 'def paginate(items, page, size):\n    """Return page number `page`, counting from 1. Raise ValueError for a page below 1."""\n    start = page * size\n    return items[start:start + size]\n\n\ndef total_pages(count, size):\n    """Number of pages needed to show `count` items; zero items need zero pages."""\n    return count // size\n',
            "tests/test_paging.py": "from paging import paginate, total_pages\nassert paginate(list(range(10)), 1, 3) == [0, 1, 2]\nassert total_pages(10, 3) == 4\n",
        },
        "test": "tests/test_paging.py", "protect": ["tests"],
        "oracle": f"from paging import paginate, total_pages\nassert paginate(list(range({variant})), 2, 4) == list(range({variant}))[4:8]\nassert total_pages(0, 5) == 0 and total_pages(9, 3) == 3\ntry:\n    paginate([1], 0, 1)\nexcept ValueError:\n    pass\nelse:\n    raise AssertionError('page 0 accepted')\n",
    }


def lru_cache(variant):
    return {
        "scope": ["cache.py"],
        "solution": [("cache.py", "        return self.data.get(key)\n", "        if key not in self.data:\n            return None\n        self.data.move_to_end(key)\n        return self.data[key]\n"),
                     ("cache.py", "        self.data[key] = value\n", "        self.data[key] = value\n        self.data.move_to_end(key)\n")],
        "request": "The cache evicts the wrong entry. Fix LRUCache so that it really drops the least recently used key.",
        "files": {
            "cache.py": "from collections import OrderedDict\n\n\nclass LRUCache:\n    def __init__(self, capacity):\n        self.capacity = capacity\n        self.data = OrderedDict()\n\n    def get(self, key):\n        return self.data.get(key)\n\n    def put(self, key, value):\n        self.data[key] = value\n        if len(self.data) > self.capacity:\n            self.data.popitem(last=False)\n",
            "tests/test_cache.py": "from cache import LRUCache\nc = LRUCache(2)\nc.put('a', 1)\nc.put('b', 2)\nassert c.get('a') == 1\nc.put('c', 3)\nassert c.get('b') is None, 'b should have been evicted'\nassert c.get('a') == 1\n",
        },
        "test": "tests/test_cache.py", "protect": ["tests"],
        "oracle": f"from cache import LRUCache\nc = LRUCache(2)\nc.put('x', {variant})\nc.put('y', 2)\nc.put('x', {variant} + 1)\nc.put('z', 3)\nassert c.get('y') is None and c.get('x') == {variant} + 1 and c.get('z') == 3\nassert c.get('missing') is None\nassert len(c.data) == 2\n",
    }


def two_bugs(variant):
    return {
        "scope": ["orders"],
        "solution": [("orders/parse.py", "line.split(',')", "line.split(';')"),
                     ("orders/total.py", "        amount += row['price']\n", "        amount += row['price'] * row['quantity']\n")],
        "request": "The order report is broken: the tests fail. There may be more than one problem. Fix the source code.",
        "files": {
            "orders/__init__.py": "",
            "orders/parse.py": "def parse_line(line):\n    \"\"\"Parse 'name;quantity;price'.\"\"\"\n    name, quantity, price = line.split(',')\n    return {'name': name.strip(), 'quantity': int(quantity), 'price': float(price)}\n",
            "orders/total.py": "from .parse import parse_line\n\n\ndef order_total(lines):\n    amount = 0\n    for line in lines:\n        row = parse_line(line)\n        amount += row['price']\n    return round(amount, 2)\n",
            "tests/test_orders.py": "from orders.total import order_total\nassert order_total(['apple;3;0.5', 'pear;2;1.25']) == 4.0\n",
        },
        "test": "tests/test_orders.py", "protect": ["tests"],
        "oracle": f"from orders.total import order_total\nfrom orders.parse import parse_line\nassert order_total(['a;{variant};2']) == {variant} * 2\nassert order_total([]) == 0\nassert parse_line(' kiwi ;1;3') == {{'name': 'kiwi', 'quantity': 1, 'price': 3.0}}\n",
    }


def look_alikes(variant):
    def account(index):
        rate = "amount * 0.02" if index != 87 else "amount * 0.2"
        return f"\n\nclass Account{index}:\n    code = {index}\n\n    def fee(self, amount):\n        return round({rate}, 2)\n"

    return {
        "scope": ["accounts.py"],
        "solution": [("accounts.py", "amount * 0.2,", "amount * 0.02,")],
        "request": "Account87 charges ten times the intended fee: it must charge 2 percent like the others. Fix it and change nothing else.",
        "files": {
            "accounts.py": "".join(account(i) for i in range(160)),
            "tests/test_fee.py": "from accounts import Account87\nassert Account87().fee(100) == 2.0, Account87().fee(100)\n",
        },
        "test": "tests/test_fee.py", "protect": ["tests"],
        "oracle": f"import accounts\nfor i in range(160):\n    assert getattr(accounts, 'Account%d' % i)().fee({variant} * 50) == round({variant}, 2), i\n    assert getattr(accounts, 'Account%d' % i).code == i\n",
    }


def csv_quotes(variant):
    return {
        "scope": ["reader.py"],
        "solution": [("reader.py", "    return [line.split(',') for line in text.splitlines()]\n",
                      "    import csv\n    import io\n    return list(csv.reader(io.StringIO(text, newline='')))\n")],
        "request": "parse_rows breaks on quoted fields. Make it parse valid CSV, as its docstring says.",
        "files": {
            "reader.py": 'def parse_rows(text):\n    """Parse CSV text into a list of rows. Quoted fields may contain commas, line breaks and doubled quotes."""\n    return [line.split(\',\') for line in text.splitlines()]\n',
            "tests/test_reader.py": "from reader import parse_rows\nassert parse_rows('a,\"b,c\"\\n') == [['a', 'b,c']], parse_rows('a,\"b,c\"\\n')\n",
        },
        "test": "tests/test_reader.py", "protect": ["tests"],
        "oracle": f"from reader import parse_rows\nassert parse_rows('x,\"line one\\nline two\",{variant}\\n') == [['x', 'line one\\nline two', '{variant}']]\nassert parse_rows('\"say \"\"hi\"\"\",b\\n') == [['say \"hi\"', 'b']]\nassert parse_rows('') == []\n",
    }


HELDOUT = (env_override, pagination, lru_cache, two_bugs, look_alikes, csv_quotes)
