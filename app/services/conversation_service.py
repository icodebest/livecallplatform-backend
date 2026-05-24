SYSTEM_PROMPT = """You are Maya, a warm and concise AI voice assistant for a healthcare clinic.
Your job is to remind patients about appointments, confirm attendance, help reschedule when needed,
answer basic clinic logistics questions, and escalate unclear medical or sensitive requests.

Guidelines:
- Sound natural, calm, and professional.
- Keep responses brief because this is a phone call.
- Do not diagnose or provide medical advice.
- Use conversation memory instead of hardcoded decision trees.
- If the patient wants to reschedule, offer available slots from context when provided.
- If the patient is confused, summarize the appointment and ask one clear question.
- If the patient asks for a human, mark escalation intent.
"""


class ConversationService:
    def __init__(self, clinic_name: str = "CityCare Clinic", reschedule_slots: str = "Thursday 11:00 AM, Friday 4:00 PM"):
        """Store clinic-specific wording that gets injected into prompts."""
        self.clinic_name = clinic_name
        self.reschedule_slots = reschedule_slots

    def build_initial_message(self, call: dict) -> str:
        """Create the first sentence Maya says when the call connects."""
        return (
            f"Hello, this is Maya from {self.clinic_name} calling about your appointment "
            f"on {call.get('appointment_date')} at {call.get('appointment_time')} "
            f"with Dr. {call.get('doctor_name')}. Will you be able to attend?"
        )

    def build_context(self, call: dict) -> str:
        """Package patient and appointment facts for the AI model."""
        return (
            f"Patient: {call.get('patient_name')}\n"
            f"Phone: {call.get('phone_number')}\n"
            f"Doctor: Dr. {call.get('doctor_name')}\n"
            f"Appointment: {call.get('appointment_date')} at {call.get('appointment_time')}\n"
            f"Notes: {call.get('notes') or 'No extra context'}\n"
            f"Available reschedule slots: {self.reschedule_slots}."
        )
