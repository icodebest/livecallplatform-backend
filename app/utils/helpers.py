from datetime import datetime, timezone
from bson import ObjectId


def now_utc() -> datetime:
    """Always store timestamps in UTC so duration math stays predictable."""
    return datetime.now(timezone.utc)


def serialize_doc(doc: dict | None) -> dict | None:
    """Convert Mongo documents into JSON-friendly API dictionaries."""
    if not doc:
        return None
    result = dict(doc)
    if "_id" in result:
        result["id"] = str(result.pop("_id"))
    for key, value in list(result.items()):
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
    return result
