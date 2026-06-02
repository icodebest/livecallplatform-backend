SYSTEM_PROMPT = """You are Maya, a warm, concise AI voice assistant for a healthcare clinic.
Your job is to handle browser-based voice sessions for appointment confirmation, rescheduling,
basic clinic logistics, and escalation of unclear medical or sensitive requests.

Guidelines:
- Sound natural, calm, and professional.
- Keep responses brief because this is a live voice session.
- Do not diagnose or provide medical advice.
- Use conversation memory instead of hardcoded decision trees.
- If the patient wants to reschedule, offer available slots from context when provided.
- If the patient is confused, summarize the appointment and ask one clear question.
- If the patient asks for a human, mark escalation intent.
- Automatically detect English, Urdu, or mixed Urdu-English and reply in the same language.
- Dynamically switch language if the user switches language.
"""


class ConversationService:
    def __init__(self, clinic_name: str = "CityCare Clinic", reschedule_slots: str = "Thursday 11:00 AM, Friday 4:00 PM"):
        """Store clinic-specific wording that gets injected into prompts."""
        self.clinic_name = clinic_name
        self.reschedule_slots = reschedule_slots

    def build_initial_message(self, call: dict) -> str:
        """Create the first sentence Maya says when the call connects."""
        language = call.get("preferred_language", "auto")
        if language == "urdu":
            return (
                f"Assalam o alaikum, main Maya {self.clinic_name} se bol rahi hoon. "
                f"Aap ka appointment {call.get('appointment_date')} ko {call.get('appointment_time')} "
                f"Dr. {call.get('doctor_name')} ke saath hai. Kya aap attend kar saken ge?"
            )
        return (
            f"Hello, this is Maya from {self.clinic_name} calling about your appointment "
            f"on {call.get('appointment_date')} at {call.get('appointment_time')} "
            f"with Dr. {call.get('doctor_name')}. Will you be able to attend?"
        )

    def build_context(self, call: dict) -> str:
        """Package patient and appointment facts for the AI model."""
        return (
            f"Patient: {call.get('patient_name')}\n"
            f"Doctor: Dr. {call.get('doctor_name')}\n"
            f"Appointment: {call.get('appointment_date')} at {call.get('appointment_time')}\n"
            f"Notes: {call.get('notes') or 'No extra context'}\n"
            f"Preferred language: {call.get('preferred_language', 'auto')}\n"
            f"Available reschedule slots: {self.reschedule_slots}."
        )
