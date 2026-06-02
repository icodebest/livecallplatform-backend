from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.core.database import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def dashboard_stats(user: dict = Depends(get_current_user)):
    """Calculate lightweight dashboard totals from recent sessions and appointments."""
    db = get_db()
    sessions = await db.calls.find({"user_id": user["_id"]}).to_list(length=500)
    appointments = await db.appointments.find({"user_id": user["_id"]}).to_list(length=500)

    def count_outcome(name: str) -> int:
        """Count sessions that ended with a specific outcome."""
        return sum(1 for session in sessions if session.get("outcome") == name)

    systems = {}
    for system_type in ("realtime", "modular"):
        scoped = [session for session in sessions if session.get("system_type") == system_type]
        completed = [session for session in scoped if session.get("outcome") in {"confirmed", "rescheduled"}]
        systems[system_type] = {
            "total": len(scoped),
            "success_rate": round((len(completed) / len(scoped)) * 100, 1) if scoped else 0,
            "average_latency": _avg([session.get("latency_ms") for session in scoped]),
            "average_duration": _avg([session.get("duration") for session in scoped]),
        }

    return {
        "total_sessions": len(sessions),
        "active_sessions": sum(1 for session in sessions if session.get("status") in {"created", "in_progress"}),
        "confirmed_appointments": sum(1 for appt in appointments if appt.get("status") == "confirmed"),
        "rescheduled_appointments": sum(1 for appt in appointments if appt.get("status") == "rescheduled"),
        "failed_sessions": count_outcome("failed"),
        "systems": systems,
    }


def _avg(values) -> int:
    """Average numeric values while ignoring missing or non-numeric fields."""
    numbers = [value for value in values if isinstance(value, (int, float))]
    return round(sum(numbers) / len(numbers)) if numbers else 0
