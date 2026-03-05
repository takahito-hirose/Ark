from typing import Any

def load_state(file_path: str) -> dict[str, Any]:
    """
    Load the state from a file.

    Args:
        file_path (str): The path to the state file.

    Returns:
        dict[str, Any]: The loaded state.
    """
    with open(file_path, 'r') as file:
        return eval(file.read())

def save_state(state: dict[str, Any], file_path: str) -> None:
    """
    Save the state to a file.

    Args:
        state (dict[str, Any]): The state to be saved.
        file_path (str): The path to the state file.
    """
    with open(file_path, 'w') as file:
        file.write(repr(state))