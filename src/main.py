import os
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk

from gui.create_win import create_new_set
from gui.load_win import show_set_grid
from gui.search_win import show_search_window
from gui.win_helpers import configure_size


# This configures the aethetics of the window.
def configure_styles(window):
    window.configure(bg='#00173c')

    label_font = ('Rockwell', 20, 'bold', 'underline')
    button_font = ('Arial', 12, 'bold')
    default_font = ('Arial', 12)

    style = ttk.Style()
    style.configure('TButton', font=button_font, padding=10)
    style.configure('TCombobox', font=default_font)

    return {
        'bg': '#00173c',
        'label_font': label_font,
        'button_font': button_font,
        'default_font': default_font
    }


# This loops through the .txt files in Set Data and returns the set IDs.
def list_sets(set_data_dir='Set Data'):
    sets = []
    for filename in os.listdir(set_data_dir):
        if filename.endswith(".txt"):
            sets.append(filename[:-4])
    return sets


# This sets up the GUI for the main menu.
def main():
    set_data_dir = 'Set Data'
    columns = 5

    root = tk.Tk()
    root.title("Lego Set Organizer")
    root.geometry(configure_size(root))

    styles = configure_styles(root)

    # Text at the top of the menu
    text_label = tk.Label(
        root, text="Select a Set:", 
        font=styles['label_font'], 
        bg=styles['bg'], fg='white'
    )
    text_label.pack(pady=10)
    
    sets = list_sets(set_data_dir)
    selected_set = ttk.Combobox(root, values=sets, font=styles['default_font'])
    selected_set.pack(pady=5)

    # Load the data for a selected set ID
    def load_selected():
        if selected_set.get():
            show_set_grid(selected_set.get(), columns, set_data_dir)

    # Create a new file to track the data of a new set
    def create_set():
        set_id = simpledialog.askstring("Create New Set", "Enter Set ID:")
        if set_id:
            try:
                create_new_set(set_id, set_data_dir)
                messagebox.showinfo("Success", f"Set {set_id} added.")
                selected_set["values"] = list_sets(set_data_dir)
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # Search in all sets for a specific part ID
    def search():
        show_search_window(columns, set_data_dir)

    # Create buttons for the main menu
    load_button = tk.Button(
        root, text="Load Set", command=load_selected,
        font=styles['button_font'], bg='#30ce30', fg='white',
        padx=20, pady=5
    )
    load_button.pack(pady=5)
    create_button = tk.Button(
        root, text="Create New Set", command=create_set,
        font=styles['button_font'], bg='#309bff', fg='white',
        padx=20, pady=5
    )
    create_button.pack(pady=5)
    search_button = tk.Button(
        root, text="Search Parts", command=search,
        font=styles['button_font'], bg='#ffce30', fg='white',
        padx=20, pady=5
    )
    search_button.pack(pady=5)
    exit_button = tk.Button(
        root, text="Exit", command=root.destroy,
        font=styles['button_font'], bg='#ff3030', fg='white',
        padx=20, pady=5
    )
    exit_button.pack(pady=5)

    root.mainloop()


# This begins the program.
if __name__ == '__main__':
    main()
