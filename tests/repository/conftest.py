from typing import List

import pytest


@pytest.fixture
def fixture_users() -> List[dict]:
    return [
        {
            "name": "aragorn",
            "email": "aragorn@lotr",
            "login": "aragorn",
            "active": True,
        },
        {
            "name": "bilbo",
            "email": "bilbo@lotr",
            "login": "bilbo",
            "active": True,
        },
        {
            "name": "samwise",
            "email": "samwise@lotr",
            "login": "samwise",
            "active": True,
        },
        {
            "name": "gandalf",
            "email": "gandalf@lotr",
            "login": "gandalf",
            "active": True,
        },
        {
            "name": "gollum",
            "email": "gollum@lotr",
            "login": "gollum",
            "active": True,
        },
    ]
