import requests
from colorama import Fore, Style

def get_cat_fact() -> str:
    """
    Fetches a cat fact from the external API.

    Returns:
        str: A string containing a cat fact.
    """
    url = 'https://catfact.ninja/fact'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('fact', '')
    else:
        raise Exception(f"Failed to fetch cat fact. Status code: {response.status_code}")

def print_cat_fact() -> None:
    """
    Prints a cat fact in red color using the colorama package.

    Returns:
        None
    """
    try:
        cat_fact = get_cat_fact()
        if cat_fact:
            print(Fore.RED + cat_fact + Style.RESET_ALL)
        else:
            print("Failed to retrieve a cat fact.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print_cat_fact()