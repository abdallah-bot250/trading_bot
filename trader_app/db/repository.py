from datetime import datetime


def active_only(query, model):
    deleted_at = getattr(model, "deleted_at", None)
    if deleted_at is None:
        return query
    return query.filter(deleted_at.is_(None))


def soft_delete(instance):
    if not hasattr(instance, "deleted_at"):
        raise AttributeError("model does not support soft delete")
    instance.deleted_at = datetime.utcnow()
    return instance


def restore(instance):
    if not hasattr(instance, "deleted_at"):
        raise AttributeError("model does not support soft delete")
    instance.deleted_at = None
    return instance
