from fastapi import APIRouter
from app.core.database import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def dashboard_stats():
    """Calculate lightweight dashboard totals from recent calls and appointments."""
    db = get_db()
    calls = await db.calls.find({}).to_list(length=500)
    appointments = await db.appointments.find({}).to_list(length=500)

    def count_outcome(name: str) -> int:
        """Count calls that ended with a specific outcome."""
        return sum(1 for call in calls if call.get("outcome") == name)

    systems = {}
    for system_type in ("realtime", "modular"):
        scoped = [call for call in calls if call.get("system_type") == system_type]
        completed = [call for call in scoped if call.get("outcome") in {"confirmed", "rescheduled"}]
        systems[system_type] = {
            "total": len(scoped),
            "success_rate": round((len(completed) / len(scoped)) * 100, 1) if scoped else 0,
            "average_latency": _avg([call.get("latency_ms") for call in scoped]),
            "average_duration": _avg([call.get("duration") for call in scoped]),
        }

    return {
        "total_calls": len(calls),
        "active_calls": sum(1 for call in calls if call.get("status") in {"ringing", "in_progress"}),
        "confirmed_appointments": sum(1 for appt in appointments if appt.get("status") == "confirmed"),
        "rescheduled_appointments": sum(1 for appt in appointments if appt.get("status") == "rescheduled"),
        "failed_calls": count_outcome("failed"),
        "systems": systems,
    }


def _avg(values) -> int:
    """Average numeric values while ignoring missing or non-numeric fields."""
    numbers = [value for value in values if isinstance(value, (int, float))]
    return round(sum(numbers) / len(numbers)) if numbers else 0
