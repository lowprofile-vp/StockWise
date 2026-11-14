from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy.query import Query
from flask_sqlalchemy.session import Session

jwt = JWTManager()


class StockwiseSession(Session):
    def query(self, *entities, **kwargs):
        from app.data.api import ApiQuery, enabled, is_model

        if enabled() and len(entities) == 1 and is_model(entities[0]):
            return ApiQuery(entities[0])
        return super().query(*entities, **kwargs)

    def add(self, instance, _warn=True):
        from app.data.api import enabled, track_new

        if enabled():
            track_new(instance)
            return None
        return super().add(instance, _warn=_warn)

    def add_all(self, instances):
        from app.data.api import enabled, track_new

        if enabled():
            for instance in instances:
                track_new(instance)
            return None
        return super().add_all(instances)

    def delete(self, instance):
        from app.data.api import delete_instance, enabled

        if enabled():
            delete_instance(instance)
            return None
        return super().delete(instance)

    def commit(self):
        from app.data.api import commit_pending, enabled

        if enabled():
            commit_pending()
            return None
        return super().commit()

    def flush(self, objects=None):
        from app.data.api import enabled, flush_pending

        if enabled():
            flush_pending()
            return None
        return super().flush(objects=objects)

    def rollback(self):
        from app.data.api import clear_pending, enabled

        if enabled():
            clear_pending()
        return super().rollback()

    def get(self, entity, ident, **kwargs):
        from app.data.api import enabled, fetch_one, is_model

        if enabled() and is_model(entity):
            return fetch_one(entity, ident)
        return super().get(entity, ident, **kwargs)


class StockwiseQuery(Query):
    def __init__(self, entities, session=None):
        self._root = entities[0] if isinstance(entities, (tuple, list)) else entities
        super().__init__(entities, session=session)
        self._api = None

    def _remote(self):
        from app.data.api import ApiQuery, enabled, is_model

        if not enabled() or not is_model(self._root):
            return None
        if self._api is None:
            self._api = ApiQuery(self._root)
        return self._api

    def filter(self, *criterion):
        remote = self._remote()
        if remote is not None:
            remote.filter(*criterion)
            return self
        return super().filter(*criterion)

    def filter_by(self, **kwargs):
        remote = self._remote()
        if remote is not None:
            remote.filter_by(**kwargs)
            return self
        return super().filter_by(**kwargs)

    def join(self, target, *props, **kwargs):
        remote = self._remote()
        if remote is not None:
            remote.join(target, *props, **kwargs)
            return self
        return super().join(target, *props, **kwargs)

    def order_by(self, *criterion):
        remote = self._remote()
        if remote is not None:
            remote.order_by(*criterion)
            return self
        return super().order_by(*criterion)

    def limit(self, limit):
        remote = self._remote()
        if remote is not None:
            remote.limit(limit)
            return self
        return super().limit(limit)

    def offset(self, offset):
        remote = self._remote()
        if remote is not None:
            remote.offset(offset)
            return self
        return super().offset(offset)

    def with_for_update(self, *args, **kwargs):
        if self._remote() is not None:
            return self
        return super().with_for_update(*args, **kwargs)

    def all(self):
        remote = self._remote()
        if remote is not None:
            return remote.all()
        return super().all()

    def first(self):
        remote = self._remote()
        if remote is not None:
            return remote.first()
        return super().first()

    def one_or_none(self):
        remote = self._remote()
        if remote is not None:
            return remote.one_or_none()
        return super().one_or_none()

    def count(self):
        remote = self._remote()
        if remote is not None:
            return remote.count()
        return super().count()

    def delete(self, synchronize_session="evaluate"):
        remote = self._remote()
        if remote is not None:
            return remote.delete()
        return super().delete(synchronize_session=synchronize_session)

    def update(self, values, synchronize_session="evaluate", update_args=None):
        remote = self._remote()
        if remote is not None:
            return remote.update(values)
        return super().update(values, synchronize_session=synchronize_session, update_args=update_args)


db = SQLAlchemy(query_class=StockwiseQuery, session_options={"class_": StockwiseSession})
