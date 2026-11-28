"""Fresh tasks, written before the review pass and tool-name handling existed.

Their baseline was measured first. Like the held-out set, they are spent once a change is tuned against them.
Most state a requirement in a docstring that the visible test does not cover.
"""


def intervals(variant):
    return {
        "scope": ["intervals.py"],
        "solution": [("intervals.py", "    result = []\n    for start, end in intervals:\n        if result and start < result[-1][1]:\n            result[-1][1] = end\n",
                      "    result = []\n    for start, end in sorted(intervals):\n        if result and start <= result[-1][1]:\n            result[-1][1] = max(result[-1][1], end)\n")],
        "request": "merge_intervals gives wrong results. Fix it so that it does what its docstring promises.",
        "files": {
            "intervals.py": 'def merge_intervals(intervals):\n    """Merge intervals given as [start, end] pairs in any order. Intervals that overlap or touch\n    become one. Return the merged intervals sorted by start and leave the argument unchanged."""\n    result = []\n    for start, end in intervals:\n        if result and start < result[-1][1]:\n            result[-1][1] = end\n        else:\n            result.append([start, end])\n    return result\n',
            "tests/test_intervals.py": "from intervals import merge_intervals\nassert merge_intervals([[1, 5], [2, 3]]) == [[1, 5]], merge_intervals([[1, 5], [2, 3]])\n",
        },
        "test": "tests/test_intervals.py", "protect": ["tests"],
        "oracle": f"from intervals import merge_intervals\ndata = [[{variant}, {variant} + 2], [1, 2], [2, 3]]\ncopy = [list(p) for p in data]\nassert merge_intervals(data) == [[1, 3], [{variant}, {variant} + 2]]\nassert data == copy\nassert merge_intervals([]) == []\n",
    }


def roman(variant):
    return {
        "scope": ["roman.py"],
        "solution": [("roman.py", "PAIRS = [(1000, 'M'), (500, 'D'), (100, 'C'), (50, 'L'), (10, 'X'), (5, 'V'), (1, 'I')]\n",
                      "PAIRS = [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'), (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]\n"),
                     ("roman.py", "    out = ''\n", "    if not 1 <= number <= 3999:\n        raise ValueError(number)\n    out = ''\n")],
        "request": "to_roman produces invalid numerals. Make it follow its docstring.",
        "files": {
            "roman.py": "PAIRS = [(1000, 'M'), (500, 'D'), (100, 'C'), (50, 'L'), (10, 'X'), (5, 'V'), (1, 'I')]\n\n\ndef to_roman(number):\n    \"\"\"Return the standard Roman numeral, using subtractive forms. Only 1 to 3999 can be written;\n    raise ValueError for anything else.\"\"\"\n    out = ''\n    for value, symbol in PAIRS:\n        while number >= value:\n            out += symbol\n            number -= value\n    return out\n",
            "tests/test_roman.py": "from roman import to_roman\nassert to_roman(4) == 'IV', to_roman(4)\n",
        },
        "test": "tests/test_roman.py", "protect": ["tests"],
        "oracle": f"from roman import to_roman\nassert to_roman(1999) == 'MCMXCIX' and to_roman(3999) == 'MMMCMXCIX' and to_roman(40) == 'XL' and to_roman({variant} * 100) is not None\nfor bad in (0, -{variant}, 4000):\n    try:\n        to_roman(bad)\n    except ValueError:\n        continue\n    raise AssertionError(bad)\n",
    }


def transfer(variant):
    return {
        "scope": ["bank.py"],
        "solution": [("bank.py", "        self.balance -= amount\n        if self.balance < 0:\n            raise ValueError('insufficient funds')\n",
                      "        if amount <= 0 or amount > self.balance:\n            raise ValueError('invalid transfer')\n        self.balance -= amount\n")],
        "request": "A failed transfer corrupts the balances. Fix Account.transfer according to its docstring.",
        "files": {
            "bank.py": 'class Account:\n    def __init__(self, balance):\n        self.balance = balance\n\n    def transfer(self, other, amount):\n        """Move `amount` to `other`. Raise ValueError if the amount is not positive or exceeds the\n        balance. A transfer that raises changes neither account."""\n        self.balance -= amount\n        if self.balance < 0:\n            raise ValueError(\'insufficient funds\')\n        other.balance += amount\n',
            "tests/test_bank.py": "from bank import Account\na, b = Account(10), Account(0)\ntry:\n    a.transfer(b, 20)\nexcept ValueError:\n    pass\nassert (a.balance, b.balance) == (10, 0), (a.balance, b.balance)\n",
        },
        "test": "tests/test_bank.py", "protect": ["tests"],
        "oracle": f"from bank import Account\nfor bad in (0, -{variant}, 11):\n    a, b = Account(10), Account(5)\n    try:\n        a.transfer(b, bad)\n    except ValueError:\n        assert (a.balance, b.balance) == (10, 5), bad\n        continue\n    raise AssertionError(bad)\na, b = Account({variant}), Account(0)\na.transfer(b, {variant})\nassert (a.balance, b.balance) == (0, {variant})\n",
    }


def word_count(variant):
    return {
        "scope": ["words.py"],
        "solution": [("words.py", "    counts = {}\n    for word in text.split():\n", "    import re\n    counts = {}\n    for word in re.findall(r\"[a-z0-9]+(?:'[a-z0-9]+)*\", text.lower()):\n")],
        "request": "count_words miscounts. Fix it to match its docstring.",
        "files": {
            "words.py": 'def count_words(text):\n    """Count words ignoring case. A word is made of letters and digits; an apostrophe between two of\n    them belongs to the word. All other punctuation separates words."""\n    counts = {}\n    for word in text.split():\n        counts[word] = counts.get(word, 0) + 1\n    return counts\n',
            "tests/test_words.py": "from words import count_words\nassert count_words('Tea tea') == {'tea': 2}, count_words('Tea tea')\n",
        },
        "test": "tests/test_words.py", "protect": ["tests"],
        "oracle": f"from words import count_words\nassert count_words(\"Don't stop, don't! 'quoted' a-b {variant}\") == {{\"don't\": 2, 'stop': 1, 'quoted': 1, 'a': 1, 'b': 1, '{variant}': 1}}\nassert count_words('') == {{}}\n",
    }


def retry(variant):
    return {
        "scope": ["retry.py"],
        "solution": [("retry.py", "    for _ in range(attempts + 1):\n        try:\n            return function()\n        except Exception:\n            pass\n    return None\n",
                      "    if attempts < 1:\n        raise ValueError(attempts)\n    for index in range(attempts):\n        try:\n            return function()\n        except Exception:\n            if index == attempts - 1:\n                raise\n")],
        "request": "call_with_retry does not behave as documented. Fix it.",
        "files": {
            "retry.py": 'def call_with_retry(function, attempts):\n    """Call `function` until it succeeds, at most `attempts` times, and return its result. If every\n    call fails, raise the exception of the last one. Raise ValueError if attempts is below 1."""\n    for _ in range(attempts + 1):\n        try:\n            return function()\n        except Exception:\n            pass\n    return None\n',
            "tests/test_retry.py": "from retry import call_with_retry\ncalls = []\ndef broken():\n    calls.append(1)\n    raise KeyError('x')\ntry:\n    call_with_retry(broken, 3)\nexcept KeyError:\n    pass\nassert len(calls) == 3, len(calls)\n",
        },
        "test": "tests/test_retry.py", "protect": ["tests"],
        "oracle": f"from retry import call_with_retry\nseen = []\ndef fail():\n    seen.append(len(seen))\n    raise RuntimeError(str(len(seen)))\ntry:\n    call_with_retry(fail, {variant % 5 + 2})\nexcept RuntimeError as error:\n    assert str(error) == str({variant % 5 + 2})\nelse:\n    raise AssertionError('swallowed')\nassert call_with_retry(lambda: {variant}, 1) == {variant}\nfor bad in (0, -1):\n    try:\n        call_with_retry(lambda: 1, bad)\n    except ValueError:\n        continue\n    raise AssertionError(bad)\n",
    }


def config_key(variant):
    return {
        "scope": ["app.json", "loader.py", "server.py"],
        "solution": [(f, "timeout_s", "timeout_seconds") for f in ("app.json", "loader.py", "server.py")],
        "request": "Rename the configuration key timeout_s to timeout_seconds everywhere it is used. The old name must not remain.",
        "files": {
            "app.json": '{\n  "timeout_s": 30,\n  "port": ' + str(8000 + variant) + "\n}\n",
            "loader.py": "import json\n\n\ndef load():\n    data = json.load(open('app.json'))\n    return {'timeout_s': data['timeout_s'], 'port': data['port']}\n",
            "server.py": "from loader import load\n\n\ndef describe():\n    config = load()\n    return '%s:%s' % (config['port'], config['timeout_s'])\n",
            "tests/test_config.py": "from loader import load\nassert load()['timeout_seconds'] == 30\n",
        },
        "test": "tests/test_config.py", "protect": ["tests"],
        "oracle": f"import pathlib, server, json\nassert server.describe() == '{8000 + variant}:30'\nassert json.load(open('app.json')) == {{'timeout_seconds': 30, 'port': {8000 + variant}}}\nfor f in ('app.json', 'loader.py', 'server.py'):\n    assert 'timeout_s\"' not in pathlib.Path(f).read_text() and \"timeout_s'\" not in pathlib.Path(f).read_text(), f\n",
    }


FRESH = (intervals, roman, transfer, word_count, retry, config_key)
