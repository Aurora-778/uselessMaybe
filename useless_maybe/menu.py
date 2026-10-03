from __future__ import annotations

from .models import Menu


def build_menu(menu_id: str) -> Menu:
    if menu_id == "maybe_menu":
        return Menu("maybe_menu", "uselessMaybe", [
            {"id": "do-nothing", "label": "Do nothing"},
            {"id": "maybe", "label": "Maybe"},
            {"id": "leave", "label": "Leave"},
        ])
    if menu_id == "are_you_sure":
        return Menu("are_you_sure", "Are you sure?", [
            {"id": "yes", "label": "Yes"},
            {"id": "no", "label": "No"},
            {"id": "maybe", "label": "Maybe"},
        ])
    if menu_id == "only_maybe":
        return Menu("only_maybe", "That's not an answer.", [
            {"id": "maybe", "label": "Maybe"},
        ])
    if menu_id == "debug_menu":
        return Menu("debug_menu", "MAYBE DEBUG MENU", [
            {"id": "recalculate", "label": "Recalculate"},
            {"id": "reset-nothing", "label": "Reset Nothing"},
            {"id": "exit", "label": "Exit"},
        ])
    raise ValueError(f"Unknown menu: {menu_id}")


def choose(state: dict, choice: str) -> tuple[str, Menu | None, str]:
    menu_id = state.get("pending_menu")
    normalized = choice.strip().lower()

    if not menu_id:
        return "There is no menu.\nProbably.", None, "no_menu"

    if menu_id == "maybe_menu":
        if normalized == "do-nothing":
            state["pending_menu"] = None
            return "Nothing happened.", None, "menu_do_nothing"
        if normalized == "leave":
            state["pending_menu"] = None
            return "You left.\nProbably.", None, "menu_leave"
        if normalized == "maybe":
            state["pending_menu"] = "are_you_sure"
            return "Maybe.", build_menu("are_you_sure"), "menu_maybe"
        return "That option does not exist.\nMaybe.", build_menu(menu_id), "menu_invalid"

    if menu_id == "are_you_sure":
        if normalized in {"yes", "no"}:
            state["pending_menu"] = None
            return "Answer accepted.\nIt will not be used.", None, "menu_answer_accepted"
        if normalized == "maybe":
            state["pending_menu"] = "only_maybe"
            return "That's not an answer.", build_menu("only_maybe"), "menu_deeper"
        return "That option does not exist.", build_menu(menu_id), "menu_invalid"

    if menu_id == "only_maybe":
        if normalized == "maybe":
            state["pending_menu"] = None
            return "Fine.\n\nNothing happened.", None, "menu_final_maybe"
        return "There is only one option.", build_menu(menu_id), "menu_invalid"

    if menu_id == "debug_menu":
        if normalized == "recalculate":
            value = float(state.get("last_uselessness_index", 0.0))
            return f"Uselessness Index     {value:.1f}", build_menu("debug_menu"), "debug_recalculate"
        if normalized == "reset-nothing":
            return "Nothing reset successfully.", build_menu("debug_menu"), "debug_reset_nothing"
        if normalized == "exit":
            state["pending_menu"] = None
            return "Debug menu closed.\nNothing was fixed.", None, "debug_exit"
        return "Unknown debug command.", build_menu("debug_menu"), "menu_invalid"

    state["pending_menu"] = None
    return "The menu forgot what it was.", None, "menu_lost"
