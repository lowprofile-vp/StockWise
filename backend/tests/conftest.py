import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def client():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    with app.test_client() as test_client:
        yield test_client
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
