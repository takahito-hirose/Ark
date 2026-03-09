"""
This is the main module of our test project.
💋
"""

from typing import Union

def add(a: int, b: int) -> int:
    """
    Function to add two integers.

    Args:
        a (int): The first integer.
        b (int): The second integer.

    Returns:
        int: The sum of the two integers.
    💋
    """
    return a + b

def multiply(a: int, b: int) -> int:
    """
    Function to multiply two integers.

    Args:
        a (int): The first integer.
        b (int): The second integer.

    Returns:
        int: The product of the two integers.
    💋
    """
    return a * b

def main() -> None:
    """
    The main function to execute the program.
    💋
    """
    print('hello')
    print(f'Addition of 3 and 4: {add(3, 4)} 💋')
    print(f'Multiplication of 3 and 4: {multiply(3, 4)} 💋')

if __name__ == "__main__":
    main()