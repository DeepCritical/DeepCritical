import pytest
from unittest.mock import patch

import pytest
from unittest.mock import patch
from contextlib import ExitStack

RATELIMITER_TARGETS = [
    'DeepResearch.src.tools.bioinformatics_tools.limiter.hit',
]

@pytest.fixture()
def disable_ratelimiter():
    """Disable the ratelimiter for tests."""
    with ExitStack() as stack:
        for target in RATELIMITER_TARGETS:
            stack.enter_context(patch(target, return_value=True))
        yield
