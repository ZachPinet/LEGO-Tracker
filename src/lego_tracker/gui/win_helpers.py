import tkinter as tk
from typing import Union

# This configures the size and position of the window.
def configure_size(window: Union[tk.Tk, tk.Toplevel]) -> str:
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    win_width = screen_width // 2
    win_height = screen_height // 2
    x = (screen_width // 2) - (win_width // 2)
    y = (screen_height // 2) - (win_height // 2)

    return f"{win_width}x{win_height}+{x}+{y}"


# These handle mouse wheel scrolling for canvas movement.
def on_mousewheel(canvas: tk.Canvas, event: tk.Event) -> None:
    if (canvas.canvasy(0) > 0 or 
        canvas.canvasy(canvas.winfo_height()) < canvas.bbox("all")[3]
    ):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")

def on_shift_mousewheel(canvas: tk.Canvas, event: tk.Event) -> None:
    if (
        canvas.canvasx(0) > 0 or 
        canvas.canvasx(canvas.winfo_width()) < canvas.bbox("all")[2]
    ):
        canvas.xview_scroll(int(-1*(event.delta/120)), "units")