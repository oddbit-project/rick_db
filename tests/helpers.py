import os

import pytest


def backend_unavailable(backend: str, exc: BaseException = None):
    """
    Skip when a backend is unreachable locally; FAIL when running in CI.

    Skipping suits a developer without Docker. In CI it is a green build that
    proves nothing: the tests report success, the backend was never touched, and
    nobody goes looking — coverage that silently disappears is worse than
    coverage that was never claimed, because the former is indistinguishable
    from the real thing on the dashboard.

    GitHub Actions sets CI=true for every job, so no workflow change is needed.

    :param backend: name of the backend, for the message
    :param exc: the exception that established unavailability, if any
    :raises RuntimeError: in CI
    """
    if os.environ.get("CI"):
        raise RuntimeError(
            "%s is required when CI is set, but it was unreachable. Refusing to "
            "skip: a pass here would claim coverage that did not run." % backend
        ) from exc
    pytest.skip("%s not available" % backend)
