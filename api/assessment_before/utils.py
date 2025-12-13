from .shared.session_manager import SessionManager

def update_manager_phase_assessment(manager: SessionManager, questions) -> SessionManager:
    manager.context["test_questions"] = questions
    manager.context["current_phase"] = "testing"

    return manager