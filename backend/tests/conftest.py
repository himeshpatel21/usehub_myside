import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture(autouse=True)
def mock_redis():
    pipe_mock = MagicMock()
    pipe_mock.incr = MagicMock()
    pipe_mock.expire = MagicMock()
    pipe_mock.execute = AsyncMock(return_value=[1, True])

    redis_mock = MagicMock()
    redis_mock.pipeline = MagicMock(return_value=pipe_mock)

    with patch("app.middleware.rate_limit.get_redis_client", return_value=redis_mock):
        yield


@pytest.fixture(autouse=True)
def mock_db():
    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))

    async def override_get_db():
        yield db_mock

    from app.db.session import get_db
    from app.main import app
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()