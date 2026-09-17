"""Built-in course content seeded into the "Programming" track on startup.

Each module dict is upserted by title (see app.main.startup_event); editing the
content here and restarting the backend is enough to update what learners see.
"""

TRACK_NAME = "Programming"
TRACK_DESCRIPTION = "Core programming concepts"

MODULES = [
    {
        "title": "Python Programming",
        "order": 1,
        "policy": "Explain concepts clearly with runnable Python examples; encourage the learner to try the exercises themselves before revealing solutions.",
        "content": (
            "# Python Programming\n\n"
            "A complete beginner-to-intermediate path through Python: syntax, core data types, "
            "control flow, functions, object-oriented programming, error handling, files, and modules.\n\n"
            "## What you will learn\n"
            "- Python syntax, variables, and data types\n"
            "- Operators and control flow (if/else, loops)\n"
            "- Functions and scope\n"
            "- Core built-in structures: lists, tuples, dictionaries, sets\n"
            "- String manipulation\n"
            "- Reading and writing files\n"
            "- Handling errors with try/except\n"
            "- Object-oriented programming (classes and objects)\n"
            "- Modules, packages, and using pip\n\n"
            "## Reference\n"
            "- https://docs.python.org/3/tutorial/\n"
        ),
        "lessons": [
            {
                "title": "Introduction to Python",
                "order": 1,
                "content": (
                    "# Introduction to Python\n\n"
                    "Python is a high-level, interpreted, general-purpose programming language known "
                    "for readable syntax and a huge ecosystem of libraries.\n\n"
                    "## Why Python\n"
                    "- Readable, beginner-friendly syntax\n"
                    "- Used in web development, data science, automation, AI/ML, and scripting\n"
                    "- Huge standard library plus third-party packages (via `pip`)\n\n"
                    "## Your first program\n"
                    "```python\n"
                    "print(\"Hello, World!\")\n"
                    "```\n\n"
                    "## Running Python\n"
                    "- Interactive shell (REPL): type `python` in a terminal\n"
                    "- Script files: save code in a `.py` file and run `python file.py`\n\n"
                    "## Comments\n"
                    "```python\n"
                    "# This is a single-line comment\n"
                    "\"\"\"This is a\n"
                    "multi-line comment/docstring\"\"\"\n"
                    "```\n\n"
                    "## Indentation matters\n"
                    "Python uses indentation (not braces) to define code blocks. Consistent spacing "
                    "(4 spaces is standard) is required, not just a style preference.\n\n"
                    "## Exercises\n"
                    "1. Print your name and favorite programming topic on two separate lines.\n"
                    "2. Write a comment explaining what your program does above the code.\n\n"
                    "## Reference\n"
                    "- https://docs.python.org/3/tutorial/introduction.html\n"
                ),
            },
            {
                "title": "Variables and Data Types",
                "order": 2,
                "content": (
                    "# Variables and Data Types\n\n"
                    "A variable is a name bound to a value. Python is dynamically typed: you don't "
                    "declare a type, and a variable can be rebound to a different type later.\n\n"
                    "## Assigning variables\n"
                    "```python\n"
                    "name = \"Ada\"\n"
                    "age = 28\n"
                    "height = 1.68\n"
                    "is_student = False\n"
                    "```\n\n"
                    "## Core built-in types\n"
                    "| Type | Example | Notes |\n"
                    "|---|---|---|\n"
                    "| `int` | `42` | whole numbers |\n"
                    "| `float` | `3.14` | decimal numbers |\n"
                    "| `str` | `\"hello\"` | text, immutable |\n"
                    "| `bool` | `True`/`False` | boolean logic |\n"
                    "| `NoneType` | `None` | absence of a value |\n\n"
                    "## Checking and converting types\n"
                    "```python\n"
                    "type(age)          # <class 'int'>\n"
                    "str(age)           # \"28\"\n"
                    "int(\"28\")          # 28\n"
                    "float(\"3.14\")      # 3.14\n"
                    "```\n\n"
                    "## Naming rules\n"
                    "- Must start with a letter or underscore, not a digit\n"
                    "- Case-sensitive (`age` and `Age` are different)\n"
                    "- Convention: `snake_case` for variables and functions\n\n"
                    "## Exercises\n"
                    "1. Create variables for your name, age, and GPA, then print all three.\n"
                    "2. Convert the string `\"100\"` to an integer and add 1 to it.\n\n"
                    "## Reference\n"
                    "- https://docs.python.org/3/library/stdtypes.html\n"
                ),
            },
            {
                "title": "Operators and Expressions",
                "order": 3,
                "content": (
                    "# Operators and Expressions\n\n"
                    "## Arithmetic operators\n"
                    "```python\n"
                    "7 + 3    # 10\n"
                    "7 - 3    # 4\n"
                    "7 * 3    # 21\n"
                    "7 / 3    # 2.333... (true division)\n"
                    "7 // 3   # 2 (floor division)\n"
                    "7 % 3    # 1 (modulo/remainder)\n"
                    "7 ** 2   # 49 (power)\n"
                    "```\n\n"
                    "## Comparison operators\n"
                    "`==`, `!=`, `>`, `<`, `>=`, `<=` — all return a `bool`.\n\n"
                    "## Logical operators\n"
                    "```python\n"
                    "True and False   # False\n"
                    "True or False    # True\n"
                    "not True         # False\n"
                    "```\n\n"
                    "## Assignment operators\n"
                    "```python\n"
                    "x = 5\n"
                    "x += 1   # x = x + 1\n"
                    "x -= 1\n"
                    "x *= 2\n"
                    "```\n\n"
                    "## Operator precedence\n"
                    "Parentheses first, then `**`, then `*`/`/`/`//`/`%`, then `+`/`-`, then comparisons, "
                    "then `not`, `and`, `or`.\n\n"
                    "## Exercises\n"
                    "1. Compute the area of a circle given its radius (`area = 3.14159 * r ** 2`).\n"
                    "2. Write an expression that checks if a number is even using `%`.\n\n"
                    "## Reference\n"
                    "- https://docs.python.org/3/reference/expressions.html\n"
                ),
            },
            {
                "title": "Control Flow: Conditionals and Loops",
                "order": 4,
                "content": (
                    "# Control Flow: Conditionals and Loops\n\n"
                    "## if / elif / else\n"
                    "```python\n"
                    "age = 20\n"
                    "if age < 13:\n"
                    "    print(\"Child\")\n"
                    "elif age < 20:\n"
                    "    print(\"Teenager\")\n"
                    "else:\n"
                    "    print(\"Adult\")\n"
                    "```\n\n"
                    "## while loops\n"
                    "```python\n"
                    "count = 0\n"
                    "while count < 5:\n"
                    "    print(count)\n"
                    "    count += 1\n"
                    "```\n\n"
                    "## for loops\n"
                    "```python\n"
                    "for i in range(5):\n"
                    "    print(i)\n\n"
                    "for fruit in [\"apple\", \"banana\", \"cherry\"]:\n"
                    "    print(fruit)\n"
                    "```\n\n"
                    "## break, continue, else on loops\n"
                    "```python\n"
                    "for n in range(10):\n"
                    "    if n == 5:\n"
                    "        break        # stop the loop entirely\n"
                    "    if n % 2 == 0:\n"
                    "        continue     # skip to the next iteration\n"
                    "    print(n)\n"
                    "```\n\n"
                    "## Exercises\n"
                    "1. Print all numbers from 1 to 20 that are divisible by 3.\n"
                    "2. Write a program that asks (simulate with a variable) for a password and loops "
                    "until it matches `\"secret\"`.\n\n"
                    "## Reference\n"
                    "- https://docs.python.org/3/tutorial/controlflow.html\n"
                ),
            },
            {
                "title": "Functions",
                "order": 5,
                "content": (
                    "# Functions\n\n"
                    "Functions group reusable logic under a name.\n\n"
                    "## Defining and calling\n"
                    "```python\n"
                    "def greet(name):\n"
                    "    return f\"Hello, {name}!\"\n\n"
                    "print(greet(\"Ada\"))\n"
                    "```\n\n"
                    "## Default and keyword arguments\n"
                    "```python\n"
                    "def power(base, exponent=2):\n"
                    "    return base ** exponent\n\n"
                    "power(3)              # 9\n"
                    "power(3, exponent=3)  # 27\n"
                    "```\n\n"
                    "## *args and **kwargs\n"
                    "```python\n"
                    "def total(*numbers):\n"
                    "    return sum(numbers)\n\n"
                    "def describe(**info):\n"
                    "    for key, value in info.items():\n"
                    "        print(f\"{key}: {value}\")\n"
                    "```\n\n"
                    "## Scope\n"
                    "Variables defined inside a function are local to it unless declared `global`. "
                    "Prefer passing values in and returning results out over relying on globals.\n\n"
                    "## Exercises\n"
                    "1. Write a function `is_prime(n)` that returns `True`/`False`.\n"
                    "2. Write a function `average(*numbers)` that returns the mean of any number of arguments.\n\n"
                    "## Reference\n"
                    "- https://docs.python.org/3/tutorial/controlflow.html#defining-functions\n"
                ),
            },
            {
                "title": "Core Data Structures: Lists, Tuples, Dicts, Sets",
                "order": 6,
                "content": (
                    "# Core Data Structures: Lists, Tuples, Dicts, Sets\n\n"
                    "## Lists (ordered, mutable)\n"
                    "```python\n"
                    "fruits = [\"apple\", \"banana\"]\n"
                    "fruits.append(\"cherry\")\n"
                    "fruits[0] = \"kiwi\"\n"
                    "fruits[1:3]     # slicing\n"
                    "```\n\n"
                    "## Tuples (ordered, immutable)\n"
                    "```python\n"
                    "point = (3, 4)\n"
                    "x, y = point    # unpacking\n"
                    "```\n\n"
                    "## Dictionaries (key/value pairs)\n"
                    "```python\n"
                    "person = {\"name\": \"Ada\", \"age\": 28}\n"
                    "person[\"age\"] = 29\n"
                    "person.get(\"email\", \"unknown\")\n"
                    "for key, value in person.items():\n"
                    "    print(key, value)\n"
                    "```\n\n"
                    "## Sets (unordered, unique elements)\n"
                    "```python\n"
                    "a = {1, 2, 3}\n"
                    "b = {2, 3, 4}\n"
                    "a | b   # union {1, 2, 3, 4}\n"
                    "a & b   # intersection {2, 3}\n"
                    "a - b   # difference {1}\n"
                    "```\n\n"
                    "## Comprehensions\n"
                    "```python\n"
                    "squares = [n ** 2 for n in range(10)]\n"
                    "evens = [n for n in range(10) if n % 2 == 0]\n"
                    "```\n\n"
                    "## Exercises\n"
                    "1. Given a list of numbers, use a comprehension to build a list of their squares.\n"
                    "2. Count how many times each word appears in a sentence using a dictionary.\n\n"
                    "## Reference\n"
                    "- https://docs.python.org/3/tutorial/datastructures.html\n"
                ),
            },
            {
                "title": "Strings and String Methods",
                "order": 7,
                "content": (
                    "# Strings and String Methods\n\n"
                    "Strings are immutable sequences of characters.\n\n"
                    "## Common operations\n"
                    "```python\n"
                    "s = \"Hello, World!\"\n"
                    "s.lower()          # \"hello, world!\"\n"
                    "s.upper()          # \"HELLO, WORLD!\"\n"
                    "s.strip()          # remove leading/trailing whitespace\n"
                    "s.replace(\"World\", \"Python\")\n"
                    "s.split(\", \")      # [\"Hello\", \"World!\"]\n"
                    "\"-\".join([\"a\", \"b\", \"c\"])  # \"a-b-c\"\n"
                    "```\n\n"
                    "## Slicing and indexing\n"
                    "```python\n"
                    "s[0]      # 'H'\n"
                    "s[-1]     # '!'\n"
                    "s[0:5]    # 'Hello'\n"
                    "s[::-1]   # reversed string\n"
                    "```\n\n"
                    "## f-strings (formatting)\n"
                    "```python\n"
                    "name = \"Ada\"\n"
                    "score = 95.5\n"
                    "print(f\"{name} scored {score:.1f}%\")\n"
                    "```\n\n"
                    "## Exercises\n"
                    "1. Write a function that checks if a string is a palindrome.\n"
                    "2. Given a sentence, count how many vowels it contains.\n\n"
                    "## Reference\n"
                    "- https://docs.python.org/3/library/stdtypes.html#string-methods\n"
                ),
            },
            {
                "title": "File Handling",
                "order": 8,
                "content": (
                    "# File Handling\n\n"
                    "## Reading a file\n"
                    "```python\n"
                    "with open(\"notes.txt\", \"r\") as f:\n"
                    "    content = f.read()\n\n"
                    "with open(\"notes.txt\", \"r\") as f:\n"
                    "    for line in f:\n"
                    "        print(line.strip())\n"
                    "```\n\n"
                    "## Writing a file\n"
                    "```python\n"
                    "with open(\"output.txt\", \"w\") as f:\n"
                    "    f.write(\"Hello, file!\\n\")\n\n"
                    "with open(\"output.txt\", \"a\") as f:\n"
                    "    f.write(\"Appended line\\n\")\n"
                    "```\n\n"
                    "## Why use `with`\n"
                    "The `with` statement (a context manager) automatically closes the file, even if an "
                    "error occurs, so resources don't leak.\n\n"
                    "## Working with CSV/JSON (standard library)\n"
                    "```python\n"
                    "import json\n"
                    "data = {\"name\": \"Ada\", \"age\": 28}\n"
                    "with open(\"data.json\", \"w\") as f:\n"
                    "    json.dump(data, f)\n"
                    "```\n\n"
                    "## Exercises\n"
                    "1. Write a program that counts the number of lines in a text file.\n"
                    "2. Write a program that reads a list of numbers from a file and prints their sum.\n\n"
                    "## Reference\n"
                    "- https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files\n"
                ),
            },
            {
                "title": "Error Handling with try/except",
                "order": 9,
                "content": (
                    "# Error Handling with try/except\n\n"
                    "## Basic try/except\n"
                    "```python\n"
                    "try:\n"
                    "    result = 10 / 0\n"
                    "except ZeroDivisionError:\n"
                    "    print(\"Cannot divide by zero\")\n"
                    "```\n\n"
                    "## Handling multiple exception types\n"
                    "```python\n"
                    "try:\n"
                    "    value = int(input_str)\n"
                    "except ValueError:\n"
                    "    print(\"Not a valid number\")\n"
                    "except TypeError:\n"
                    "    print(\"Wrong type provided\")\n"
                    "```\n\n"
                    "## else and finally\n"
                    "```python\n"
                    "try:\n"
                    "    f = open(\"data.txt\")\n"
                    "except FileNotFoundError:\n"
                    "    print(\"File missing\")\n"
                    "else:\n"
                    "    print(\"File opened successfully\")\n"
                    "finally:\n"
                    "    print(\"This always runs\")\n"
                    "```\n\n"
                    "## Raising your own exceptions\n"
                    "```python\n"
                    "def withdraw(balance, amount):\n"
                    "    if amount > balance:\n"
                    "        raise ValueError(\"Insufficient funds\")\n"
                    "    return balance - amount\n"
                    "```\n\n"
                    "## Exercises\n"
                    "1. Write a function that safely converts a string to an int, returning `None` on failure.\n"
                    "2. Write code that catches a `KeyError` when looking up a missing dictionary key.\n\n"
                    "## Reference\n"
                    "- https://docs.python.org/3/tutorial/errors.html\n"
                ),
            },
            {
                "title": "Object-Oriented Programming: Classes and Objects",
                "order": 10,
                "content": (
                    "# Object-Oriented Programming: Classes and Objects\n\n"
                    "## Defining a class\n"
                    "```python\n"
                    "class Dog:\n"
                    "    def __init__(self, name, age):\n"
                    "        self.name = name\n"
                    "        self.age = age\n\n"
                    "    def bark(self):\n"
                    "        return f\"{self.name} says Woof!\"\n\n"
                    "rex = Dog(\"Rex\", 3)\n"
                    "print(rex.bark())\n"
                    "```\n\n"
                    "## Key concepts\n"
                    "- **Class**: a blueprint for objects\n"
                    "- **Object/instance**: a concrete value created from a class\n"
                    "- **`self`**: refers to the specific instance inside methods\n"
                    "- **`__init__`**: the constructor, run when an object is created\n\n"
                    "## Inheritance\n"
                    "```python\n"
                    "class Animal:\n"
                    "    def __init__(self, name):\n"
                    "        self.name = name\n"
                    "    def speak(self):\n"
                    "        return \"...\"\n\n"
                    "class Cat(Animal):\n"
                    "    def speak(self):\n"
                    "        return f\"{self.name} says Meow!\"\n"
                    "```\n\n"
                    "## Encapsulation (convention)\n"
                    "Python has no strict private fields; a leading underscore (`_balance`) signals "
                    "\"internal use\" by convention.\n\n"
                    "## Exercises\n"
                    "1. Create a `BankAccount` class with `deposit` and `withdraw` methods.\n"
                    "2. Create a `Shape` base class and `Circle`/`Rectangle` subclasses that each implement "
                    "an `area()` method.\n\n"
                    "## Reference\n"
                    "- https://docs.python.org/3/tutorial/classes.html\n"
                ),
            },
            {
                "title": "Modules, Packages, and pip",
                "order": 11,
                "content": (
                    "# Modules, Packages, and pip\n\n"
                    "## Importing standard library modules\n"
                    "```python\n"
                    "import math\n"
                    "math.sqrt(16)     # 4.0\n\n"
                    "from datetime import datetime\n"
                    "datetime.now()\n"
                    "```\n\n"
                    "## Writing your own module\n"
                    "Any `.py` file is a module. If you have `helpers.py` with a function `add(a, b)`, "
                    "another file in the same folder can do:\n"
                    "```python\n"
                    "import helpers\n"
                    "helpers.add(2, 3)\n"
                    "```\n\n"
                    "## Packages\n"
                    "A folder containing an `__init__.py` (or, in modern Python, just a folder of modules) "
                    "is a package, letting you organize related modules together.\n\n"
                    "## Installing third-party packages with pip\n"
                    "```bash\n"
                    "pip install requests\n"
                    "```\n"
                    "```python\n"
                    "import requests\n"
                    "response = requests.get(\"https://api.example.com\")\n"
                    "```\n\n"
                    "## Virtual environments\n"
                    "Use a virtual environment per project so dependencies don't conflict:\n"
                    "```bash\n"
                    "python -m venv venv\n"
                    "source venv/bin/activate   # or venv\\Scripts\\activate on Windows\n"
                    "pip install -r requirements.txt\n"
                    "```\n\n"
                    "## Exercises\n"
                    "1. Split a program into two files: one with helper functions, one that imports and uses them.\n"
                    "2. List three standard library modules you might use in a real project and what each is for.\n\n"
                    "## Reference\n"
                    "- https://docs.python.org/3/tutorial/modules.html\n"
                ),
            },
        ],
    },
    {
        "title": "Data Structures",
        "order": 2,
        "policy": "Explain concepts clearly with examples.",
        "content": (
            "# Data Structures\n\n"
            "Learn how to organize data so your programs are faster, simpler, and easier to reason about.\n\n"
            "## What you will learn\n"
            "- How to measure performance (time/space complexity)\n"
            "- Core structures: arrays, linked lists, stacks, queues\n"
            "- Lookup structures: hash tables\n"
            "- Hierarchies and networks: trees and graphs\n"
            "- Practical toolkit: searching and sorting\n\n"
            "## Reference\n"
            "- https://www.w3schools.com/dsa/\n"
        ),
        "lessons": [
            {
                "title": "Course Introduction",
                "order": 1,
                "content": (
                    "# What Are Data Structures?\n\n"
                    "A **data structure** is a way to store data so you can **use it efficiently**.\n\n"
                    "We structure data differently depending on:\n"
                    "- the type of data\n"
                    "- what we want to do (search, insert, delete, sort, traverse)\n"
                    "- performance constraints (speed and memory)\n\n"
                    "## A real-world analogy: Family Tree\n"
                    "If you store data about relatives, a **family tree** is a natural structure.\n"
                    "It adds relationships (links), so questions like:\n"
                    "- Who is my mother's mother?\n"
                    "- Show several generations back\n"
                    "become easy.\n\n"
                    "Without links, you only have a list of people and relationships are hard to compute.\n\n"
                    "## Why data structures matter\n"
                    "Data structures help manage large amounts of data for:\n"
                    "- databases\n"
                    "- search engines\n"
                    "- social networks\n"
                    "- maps and navigation\n\n"
                    "They are essential ingredients for fast algorithms and scalable systems.\n\n"
                    "## Primitive vs Abstract data structures\n"
                    "### Primitive\n"
                    "Single values provided by languages: int, float, char, boolean.\n\n"
                    "### Abstract\n"
                    "Built from primitives to solve real problems:\n"
                    "- arrays\n"
                    "- linked lists\n"
                    "- stacks / queues\n"
                    "- hash tables\n"
                    "- trees / graphs\n\n"
                    "## What are algorithms?\n"
                    "An **algorithm** is step-by-step instructions to solve a problem.\n\n"
                    "### Analogy: Recipe\n"
                    "A recipe is an algorithm: precise steps to achieve a goal.\n"
                    "In programming, algorithms are written in code and use data structures as tools.\n\n"
                    "## Data Structures + Algorithms (DSA)\n"
                    "DSA go together:\n"
                    "- A structure is not useful if you cannot search/update it efficiently\n"
                    "- Many algorithms are designed for specific structures\n\n"
                    "By learning DSA, you can:\n"
                    "- choose the best approach for a situation\n"
                    "- build faster programs\n"
                    "- use less memory\n"
                    "- solve complex problems systematically\n\n"
                    "## Where DSA is needed (examples)\n"
                    "- finding the shortest route in GPS\n"
                    "- search engine ranking and indexing\n"
                    "- scheduling tasks on servers\n"
                    "- sorting/filtering large datasets\n\n"
                    "## How to use this course\n"
                    "For each lesson:\n"
                    "1. Read the explanation\n"
                    "2. Study operations + complexity\n"
                    "3. Run examples\n"
                    "4. Solve exercises\n"
                    "5. Ask the tutor questions (example: explain more)\n\n"
                    "## Reference\n"
                    "- https://www.w3schools.com/dsa/\n"
                ),
            },
            {
                "title": "Big-O and Complexity",
                "order": 2,
                "content": (
                    "# Big-O and Complexity\n\n"
                    "Big-O describes how runtime or memory grows as input size `n` grows.\n\n"
                    "## Time vs space\n"
                    "- Time complexity: how many steps\n"
                    "- Space complexity: extra memory used\n\n"
                    "## Common complexities (intuition)\n"
                    "- **O(1)** constant\n"
                    "- **O(log n)** grows slowly (divide-and-conquer)\n"
                    "- **O(n)** one pass\n"
                    "- **O(n log n)** fast sorting\n"
                    "- **O(n^2)** nested loops\n\n"
                    "## Examples\n"
                    "- Find min in list: **O(n)**\n"
                    "- Binary search on sorted array: **O(log n)**\n"
                    "- Hash table lookup: average **O(1)**\n\n"
                    "## Best / average / worst case\n"
                    "Some algorithms have different cases. Example:\n"
                    "- Quicksort average **O(n log n)**, worst **O(n^2)**\n\n"
                    "## Rules of thumb\n"
                    "- Drop constants: O(2n) -> O(n)\n"
                    "- Keep the dominant term: O(n^2 + n) -> O(n^2)\n"
                    "- Nested loops multiply: O(n) * O(n) = O(n^2)\n\n"
                    "## Exercises\n"
                    "1. What is the time complexity of three nested loops over `n` items?\n"
                    "2. Why does sorting enable binary search?\n"
                    "3. What is the space complexity of copying an array of length `n`?\n\n"
                    "## Reference\n"
                    "- https://www.w3schools.com/dsa/\n"
                ),
            },
            {
                "title": "Arrays and Dynamic Arrays (ArrayList)",
                "order": 3,
                "content": (
                    "# Arrays and Dynamic Arrays (ArrayList)\n\n"
                    "Arrays store elements **next to each other in memory**. That gives fast indexing.\n"
                    "A dynamic array (Java `ArrayList`, Python `list`) grows automatically.\n\n"
                    "## Why arrays are fast\n"
                    "If the first element address is `base`, then element `i` is at:\n"
                    "`base + i * element_size` -> direct computation -> usually **O(1)**.\n\n"
                    "## Operation table (typical)\n"
                    "| Operation | Dynamic Array | Explanation |\n"
                    "|---|---:|---|\n"
                    "| get/set by index | O(1) | direct access |\n"
                    "| append | amortized O(1) | resize sometimes |\n"
                    "| insert/remove at front | O(n) | shift elements |\n"
                    "| insert/remove in middle | O(n) | shift elements |\n"
                    "| search (unsorted) | O(n) | scan |\n\n"
                    "## Resizing (amortized O(1))\n"
                    "When capacity is full:\n"
                    "1. allocate a bigger array (often 2x)\n"
                    "2. copy old elements\n"
                    "3. append new element\n\n"
                    "Most appends do not resize, so average cost per append stays constant.\n\n"
                    "## Example (Java)\n"
                    "```java\n"
                    "import java.util.ArrayList;\n"
                    "\n"
                    "public class Main {\n"
                    "  public static void main(String[] args) {\n"
                    "    ArrayList<String> cars = new ArrayList<>();\n"
                    "    cars.add(\"Volvo\");\n"
                    "    cars.add(\"BMW\");\n"
                    "    cars.add(\"Ford\");\n"
                    "\n"
                    "    cars.set(1, \"Tesla\");\n"
                    "    System.out.println(cars.get(0));\n"
                    "    System.out.println(cars.size());\n"
                    "  }\n"
                    "}\n"
                    "```\n\n"
                    "## Example (Python)\n"
                    "```python\n"
                    "a = [10, 20, 30]\n"
                    "a.append(40)\n"
                    "a.insert(1, 15)\n"
                    "a.pop(0)\n"
                    "print(a)\n"
                    "```\n\n"
                    "## Exercises\n"
                    "1. Why is inserting at index 0 slow?\n"
                    "2. Implement a function that removes all duplicates from an array.\n"
                    "3. Given an array, rotate it right by `k` steps.\n\n"
                    "## Mini quiz\n"
                    "1. Which is faster for random access: array or linked list?\n"
                    "2. What does amortized mean?\n\n"
                    "## Reference\n"
                    "- https://www.w3schools.com/dsa/\n"
                ),
            },
            {
                "title": "Linked Lists",
                "order": 4,
                "content": (
                    "# Linked Lists\n\n"
                    "A linked list stores elements in **nodes**. Each node stores:\n"
                    "- data\n"
                    "- pointer/reference to next node (and sometimes previous)\n\n"
                    "## Types\n"
                    "- Singly: `node -> next`\n"
                    "- Doubly: `prev <- node -> next`\n"
                    "- Circular: tail points back to head\n\n"
                    "## Operation table (typical)\n"
                    "| Operation | Linked List | Notes |\n"
                    "|---|---:|---|\n"
                    "| insert at head | O(1) | update head |\n"
                    "| remove at head | O(1) | update head |\n"
                    "| insert after node | O(1) | if node is known |\n"
                    "| remove after node | O(1) | if node is known |\n"
                    "| search by value | O(n) | must scan |\n"
                    "| get by index | O(n) | walk the list |\n\n"
                    "## When linked lists are useful\n"
                    "- frequent inserts/removes when you already have node references\n"
                    "- building structures like stacks/queues\n\n"
                    "## When arrays are better\n"
                    "- you need fast `get(i)`\n"
                    "- you need memory locality / speed\n\n"
                    "## Mini example (Python)\n"
                    "```python\n"
                    "class Node:\n"
                    "    def __init__(self, value, next=None):\n"
                    "        self.value = value\n"
                    "        self.next = next\n"
                    "\n"
                    "head = Node(1, Node(2, Node(3)))\n"
                    "cur = head\n"
                    "while cur:\n"
                    "    print(cur.value)\n"
                    "    cur = cur.next\n"
                    "```\n\n"
                    "## Exercises\n"
                    "1. Why is `get(i)` O(n) in a linked list?\n"
                    "2. Implement `push_front` and `pop_front`.\n\n"
                    "## Challenge\n"
                    "Reverse a linked list in-place.\n\n"
                    "## Reference\n"
                    "- https://www.w3schools.com/dsa/\n"
                ),
            },
            {
                "title": "Stacks",
                "order": 5,
                "content": (
                    "# Stacks\n\n"
                    "A stack is **LIFO** (Last In, First Out).\n\n"
                    "Analogy: stack of plates.\n"
                    "- push: add plate on top\n"
                    "- pop: remove top plate\n\n"
                    "## Operations\n"
                    "- `push(x)`\n"
                    "- `pop()`\n"
                    "- `peek()`\n\n"
                    "## Complexity\n"
                    "- Typical implementations: `push` and `pop` are **O(1)**\n\n"
                    "## Implementation\n"
                    "- dynamic array (common)\n"
                    "- linked list (also common)\n\n"
                    "## Use cases\n"
                    "- Undo/redo\n"
                    "- Function calls\n"
                    "- Parsing expressions\n\n"
                    "## Example: balanced parentheses\n"
                    "```python\n"
                    "def balanced(s: str) -> bool:\n"
                    "    stack = []\n"
                    "    pairs = {')': '(', ']': '[', '}': '{'}\n"
                    "    for ch in s:\n"
                    "        if ch in '([{':\n"
                    "            stack.append(ch)\n"
                    "        elif ch in ')]}':\n"
                    "            if not stack or stack.pop() != pairs[ch]:\n"
                    "                return False\n"
                    "    return not stack\n"
                    "```\n\n"
                    "## Exercises\n"
                    "1. Evaluate a postfix expression (RPN).\n"
                    "2. Implement a stack with `get_min()` in O(1).\n\n"
                    "## Reference\n"
                    "- https://www.w3schools.com/dsa/\n"
                ),
            },
            {
                "title": "Queues and Deques",
                "order": 6,
                "content": (
                    "# Queues and Deques\n\n"
                    "A queue is **FIFO** (First In, First Out). A deque supports both ends.\n\n"
                    "Analogy: line at a store.\n\n"
                    "## Operations\n"
                    "- `enqueue(x)` / `dequeue()`\n"
                    "- `push_front(x)` / `pop_back()` (deque)\n\n"
                    "## Implementation\n"
                    "- circular buffer (array-based)\n"
                    "- linked list with head/tail\n\n"
                    "## Use cases\n"
                    "- Scheduling\n"
                    "- Breadth-first search (BFS)\n"
                    "- Sliding window problems\n\n"
                    "## Exercise\n"
                    "Simulate a customer queue: each minute one customer is served.\n\n"
                    "## Challenge\n"
                    "Sliding window maximum using a deque in O(n).\n\n"
                    "## Reference\n"
                    "- https://www.w3schools.com/dsa/\n"
                ),
            },
            {
                "title": "Hash Tables (Maps/Sets)",
                "order": 7,
                "content": (
                    "# Hash Tables (Maps/Sets)\n\n"
                    "A hash table stores:\n"
                    "- key/value pairs (map)\n"
                    "- unique keys (set)\n\n"
                    "It uses a **hash function** to map keys to bucket indices.\n\n"
                    "## Core idea\n"
                    "1. compute `h = hash(key)`\n"
                    "2. map to bucket index\n"
                    "3. store/find item in that bucket\n\n"
                    "## Why they are powerful\n"
                    "- Average **O(1)** insert, delete, lookup\n\n"
                    "## Collisions\n"
                    "Two keys can map to the same bucket.\n"
                    "Common strategies:\n"
                    "- chaining (bucket holds a list)\n"
                    "- open addressing (probe other slots)\n\n"
                    "## Load factor and resizing\n"
                    "As the table becomes full, collisions increase.\n"
                    "Implementations often resize when the load factor gets high.\n\n"
                    "## Example (Python)\n"
                    "```python\n"
                    "freq = {}\n"
                    "for ch in \"banana\":\n"
                    "    freq[ch] = freq.get(ch, 0) + 1\n"
                    "print(freq)\n"
                    "```\n\n"
                    "## Exercises\n"
                    "1. Count word frequency in a paragraph.\n"
                    "2. Solve two-sum using a set.\n\n"
                    "## Challenges\n"
                    "1. Group anagrams using a map.\n"
                    "2. Find the first non-repeating character in a string.\n\n"
                    "## Reference\n"
                    "- https://www.w3schools.com/dsa/\n"
                ),
            },
            {
                "title": "Trees (Binary Trees and BST)",
                "order": 8,
                "content": (
                    "# Trees (Binary Trees and BST)\n\n"
                    "A tree is a hierarchy of nodes.\n"
                    "A **binary tree** has up to 2 children per node.\n\n"
                    "## Vocabulary\n"
                    "- root: top node\n"
                    "- leaf: node with no children\n"
                    "- depth: distance from root\n"
                    "- height: longest path to a leaf\n\n"
                    "## BST rule\n"
                    "Left subtree values < node value < right subtree values.\n\n"
                    "## Complexity (BST)\n"
                    "- Average search/insert: **O(log n)**\n"
                    "- Worst case: **O(n)**\n\n"
                    "Worst case happens when the tree becomes skewed (like a linked list).\n\n"
                    "## Traversals\n"
                    "- In-order, pre-order, post-order, level-order\n\n"
                    "## Exercise\n"
                    "Build a balanced BST from a sorted array.\n\n"
                    "## Challenge\n"
                    "Implement level-order traversal using a queue.\n\n"
                    "## Reference\n"
                    "- https://www.w3schools.com/dsa/\n"
                ),
            },
            {
                "title": "Graphs (BFS and DFS)",
                "order": 9,
                "content": (
                    "# Graphs (BFS and DFS)\n\n"
                    "A graph is a set of vertices (nodes) connected by edges.\n\n"
                    "Graphs model:\n"
                    "- roads between cities\n"
                    "- friendships in social networks\n"
                    "- dependencies between tasks\n\n"
                    "## Representations\n"
                    "- Adjacency list\n"
                    "- Adjacency matrix\n\n"
                    "Adjacency lists are usually best for sparse graphs.\n\n"
                    "## BFS vs DFS\n"
                    "- BFS explores layer-by-layer\n"
                    "- DFS explores deep paths\n\n"
                    "## BFS (queue)\n"
                    "- good for shortest path in unweighted graphs\n\n"
                    "## DFS (stack/recursion)\n"
                    "- good for components, cycle detection, ordering problems\n\n"
                    "## Exercise\n"
                    "Count connected components in an undirected graph.\n\n"
                    "## Challenge\n"
                    "Detect whether a graph contains a cycle.\n\n"
                    "## Reference\n"
                    "- https://www.w3schools.com/dsa/\n"
                ),
            },
            {
                "title": "Searching and Sorting Toolkit",
                "order": 10,
                "content": (
                    "# Searching and Sorting Toolkit\n\n"
                    "Sorting and searching are essential building blocks.\n\n"
                    "## Searching\n"
                    "- Linear search: **O(n)**\n"
                    "- Binary search: **O(log n)**\n\n"
                    "## Sorting (overview)\n"
                    "- Simple sorts: **O(n²)**\n"
                    "- Efficient sorts: **O(n log n)**\n\n"
                    "## Why sorting helps\n"
                    "- enables binary search\n"
                    "- makes duplicates easy to handle\n"
                    "- improves many algorithms\n\n"
                    "## Practice\n"
                    "1. Implement binary search.\n"
                    "2. Explain why sorting helps you search faster.\n\n"
                    "## Challenges\n"
                    "1. Implement merge sort.\n"
                    "2. Explain stable vs unstable sorting.\n"
                    "3. Compare bubble sort vs quicksort.\n\n"
                    "## Reference\n"
                    "- https://www.w3schools.com/dsa/\n"
                ),
            },
        ],
    },
]


# Diagnostic assessment question bank (specs/001-diagnostic-assessment).
# Keyed by exact Lesson title so it's seeded/matched the same idempotent way
# as module/lesson content (see app.main._seed_diagnostic_questions).
# Each question is single-choice, worth 1 point; `correct_choices` holds the
# index (or indices, for multi_choice) of the right answer(s) in `choices`.
# v1 covers the first five "Python Programming" lessons, mirroring the
# Basics -> Variables -> Conditionals -> Loops -> Functions example in
# spec.md so the feature is demoable end-to-end.
DIAGNOSTIC_QUESTIONS = {
    "Introduction to Python": [
        {
            "prompt": "Which best describes Python as a language?",
            "choices": [
                "A markup language for web pages",
                "A high-level, interpreted, general-purpose language",
                "A low-level assembly language",
                "A database query language",
            ],
            "correct_choices": [1],
        },
        {
            "prompt": "What does Python use to define a block of code (instead of curly braces)?",
            "choices": ["Semicolons", "The 'begin'/'end' keywords", "Curly braces {}", "Indentation"],
            "correct_choices": [3],
        },
        {
            "prompt": "Which symbol starts a single-line comment in Python?",
            "choices": ["//", "#", "--", "<!--"],
            "correct_choices": [1],
        },
    ],
    "Variables and Data Types": [
        {
            "prompt": "Which statement about Python variables is true?",
            "choices": [
                "You must declare a variable's type before assigning a value",
                "Variables cannot be reassigned to a different type",
                "Python is dynamically typed, so you don't declare a variable's type",
                "Variable names can start with a digit",
            ],
            "correct_choices": [2],
        },
        {
            "prompt": "What does type(3.14) return?",
            "choices": ["<class 'int'>", "<class 'str'>", "<class 'double'>", "<class 'float'>"],
            "correct_choices": [3],
        },
        {
            "prompt": "Which of these is a valid, conventional Python variable name?",
            "choices": ["2fast", "student-age", "class", "student_age"],
            "correct_choices": [3],
        },
    ],
    "Operators and Expressions": [
        {
            "prompt": "What is the result of 7 // 3 in Python?",
            "choices": ["2.33", "3", "2", "1"],
            "correct_choices": [2],
        },
        {
            "prompt": "What is the result of 7 % 3?",
            "choices": ["0", "1", "2", "3"],
            "correct_choices": [1],
        },
        {
            "prompt": "Which operator returns True only when both operands are true?",
            "choices": ["or", "not", "xor", "and"],
            "correct_choices": [3],
        },
    ],
    "Control Flow: Conditionals and Loops": [
        {
            "prompt": "Which keyword skips the rest of the current loop iteration and moves to the next one?",
            "choices": ["break", "pass", "continue", "return"],
            "correct_choices": [2],
        },
        {
            "prompt": "What does this print?\nfor i in range(3):\n    print(i)",
            "choices": ["1 2 3", "0 1 2", "0 1 2 3", "3 2 1"],
            "correct_choices": [1],
        },
        {
            "prompt": "Which keyword immediately exits a loop entirely?",
            "choices": ["continue", "stop", "exit", "break"],
            "correct_choices": [3],
        },
    ],
    "Functions": [
        {
            "prompt": "Which keyword defines a function in Python?",
            "choices": ["function", "func", "def", "lambda"],
            "correct_choices": [2],
        },
        {
            "prompt": "def power(base, exponent=2):\n    return base ** exponent\n\nWhat does power(3) return?",
            "choices": ["3", "6", "Error: missing argument", "9"],
            "correct_choices": [3],
        },
        {
            "prompt": "What does *args let a function accept?",
            "choices": [
                "Exactly one argument only",
                "A variable number of positional arguments",
                "Keyword arguments only",
                "No arguments at all",
            ],
            "correct_choices": [1],
        },
    ],
}
