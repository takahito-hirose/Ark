"""
A simple Python script to display the current system time in a stylish format
using the 'rich' library.
"""

import datetime
from rich.console import Console
from rich.text import Text
from rich.panel import Panel

def display_stylish_time() -> None:
    """
    Retrieves the current system time and displays it in a stylish panel
    using the rich library.
    """
    console = Console()
    current_time = datetime.datetime.now()
    
    # Format the datetime object into a readable string
    # Example: "2023-10-27 14:35:01"
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

    # Create a rich Text object for the formatted time with specific styling
    time_text = Text(formatted_time, style="bold yellow on #222222") # Yellow text on dark grey background

    # Create a rich Text object for the label
    label_text = Text("Current System Time:", style="italic cyan")

    # Assemble the label and time text, centered
    # Using Text.assemble to combine multiple Text objects
    # Adding a newline for better separation
    content = Text.assemble(
        label_text, "\n",
        time_text,
        justify="center" # Center the assembled text
    )

    # Create a Panel to display the content
    time_panel = Panel(
        content,
        title="[bold magenta]Time Display[/bold magenta]", # Title for the panel
        border_style="green", # Green border
        padding=(1, 4) # Vertical and horizontal padding
    )

    # Print the panel to the console
    console.print(time_panel)

if __name__ == "__main__":
    display_stylish_time()