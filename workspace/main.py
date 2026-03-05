"""
Main module of the ARK System Online project.
"""

from colorama import Fore, Style

def print_ark_system_online() -> None:
    """
    Prints 'ARK System Online!' in red color using the colorama package.

    Returns:
        None
    """
    print(Fore.RED + 'ARK System Online!' + Style.RESET_ALL)

if __name__ == "__main__":
    print_ark_system_online()