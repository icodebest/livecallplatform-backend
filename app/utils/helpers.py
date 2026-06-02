from datetime import datetime, timezone
from bson import ObjectId


def now_utc() -> datetime:
    """Always store timestamps in UTC so duration math stays predictable."""
    return datetime.now(timezone.utc)


def serialize_doc(doc: dict | None) -> dict | None:
    """Convert Mongo documents into JSON-friendly API dictionaries."""
    if not doc:
        return None
    return _serialize_value(doc)


def _serialize_value(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        result = {}
        for key, nested in value.items():
            result["id" if key == "_id" else key] = _serialize_value(nested)
        return result
    return value
