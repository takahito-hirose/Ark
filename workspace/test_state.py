"""ARK generated module for state file."""


def save_state(state_data: dict) -> None:
    """Save the current state to a file."""
    import json

    with open("state.json", "w") as state_file:
        json.dump(state_data, state_file)


def load_state() -> dict:
    """Load the saved state from a file."""
    try:
        with open("state.json", "r") as state_file:
            return json.load(state_file)
    except FileNotFoundError:
        return {}