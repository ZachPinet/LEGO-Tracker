import json
import os
import requests
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk

import settings


# This configures the aethetics of the root window.
def configure_styles(root):
    root.configure(bg='#00173c')

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


# This uses the Rebrickable API to get a parts list for a set ID.
def get_set_parts(set_id):
    url = f"https://rebrickable.com/api/v3/lego/sets/{set_id}/parts/?page_size=1000"

    headers = {"Authorization": f"key {settings.REBRICKABLE_API_KEY}"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception("Failed to fetch data from Rebrickable API")
    return response.json()["results"]


# This creates a new .txt file for a set ID.
def create_new_set(set_id, set_data_dir='Set Data'):
    parts = get_set_parts(set_id)
    set_filename = os.path.join(set_data_dir, f"{set_id}.txt")
    if os.path.exists(set_filename):
        raise Exception("Set already exists.")
    
    # Each file contains data for each part in the set
    part_data = []
    for part in parts:
        part_data.append({
            "id": part["part"]["part_num"],
            "color": part["color"]["name"],
            "needed": part["quantity"],
            "have": 0,
            "image": part["part"]["part_img_url"]
        })
    with open(set_filename, 'w') as f:
        json.dump(part_data, f, indent=2)


# This loops through the .txt files in Set Data and returns the set IDs.
def list_sets(set_data_dir='Set Data'):
    return [f[:-4] for f in os.listdir(set_data_dir) if f.endswith(".txt")]


# This loads the data from a set ID's .txt file.
def load_set_data(set_id, set_data_dir='Set Data'):
    with open(os.path.join(set_data_dir, f"{set_id}.txt"), 'r') as f:
        return json.load(f)


# This saves any updates to the set's data.
def save_set_data(set_id, data, set_data_dir='Set Data'):
    with open(os.path.join(set_data_dir, f"{set_id}.txt"), 'w') as f:
        json.dump(data, f, indent=2)


# This returns a list of set IDs that need a specific part ID.
def search_sets_by_part(part_id, set_data_dir='Set Data'):
    matching_sets = []

    for set_file in os.listdir(set_data_dir):
        if not set_file.endswith('.txt'):
            continue

        file_path = os.path.join(set_data_dir, set_file)
        with open(file_path, 'r') as f:
            content = f.read().strip()
            parts = json.loads(content)
            for part in parts:
                if part["id"] == part_id and part["have"] < part["needed"]:
                    matching_sets.append(set_file[:-4])
                    break

    return matching_sets


# This shows a list of the part data from a specific set.
def show_set_grid(set_id, set_data_dir='Set Data'):
    data = load_set_data(set_id, set_data_dir)

    grid = tk.Toplevel()
    grid.title(f"Viewing Set: {set_id}")

    canvas = tk.Canvas(grid)
    frame = ttk.Frame(canvas)
    scrollbar = ttk.Scrollbar(grid, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.create_window((0, 0), window=frame, anchor="nw")

    def on_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    frame.bind("<Configure>", on_configure)

    # Save any changes made
    def update_and_save(index, entry):
        try:
            data[index]["have"] = int(entry.get())
            save_set_data(set_id, data, set_data_dir)
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid number.")

    for i, part in enumerate(data):
        tk.Label(frame, text=f"ID: {part['id']}").grid(row=i, column=0, padx=5, pady=2)
        tk.Label(frame, text=f"Color: {part['color']}").grid(row=i, column=1, padx=5, pady=2)
        tk.Label(frame, text=f"Need: {part['needed']}").grid(row=i, column=2, padx=5, pady=2)
        entry = tk.Entry(frame, width=5)
        entry.insert(0, str(part['have']))
        entry.grid(row=i, column=3, padx=5, pady=2)
        entry.bind("<FocusOut>", lambda e, idx=i, ent=entry: update_and_save(idx, ent))

    tk.Button(frame, text="Back", command=grid.destroy).grid(row=len(data)+1, column=0, pady=10)


# This sets up the GUI for the main menu.
def main():
    set_data_dir = 'Set Data'

    root = tk.Tk()
    root.title("Lego Set Organizer")

    styles = configure_styles(root)

    # Get window size and (roughly) center it
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    win_width = screen_width // 2
    win_height = screen_height // 2
    x = (screen_width // 2) - (win_width // 2)
    y = (screen_height // 2) - (win_height // 2)

    root.geometry(f"{win_width}x{win_height}+{x}+{y}")

    tk.Label(root, text="Select a Set:", 
             font=styles['label_font'], 
             bg=styles['bg'], fg='white').pack(pady=10)
    
    sets = list_sets(set_data_dir)
    selected_set = ttk.Combobox(root, values=sets, font=styles['default_font'])
    selected_set.pack(pady=5)

    # Load the data for a selected set ID
    def load_selected():
        if selected_set.get():
            show_set_grid(selected_set.get(), set_data_dir)

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
        part_id = simpledialog.askstring("Search", "Enter Part ID:")
        if part_id:
            results = search_sets_by_part(part_id, set_data_dir)
            if results:
                messagebox.showinfo("Found In Sets", "\n".join(results))
            else:
                messagebox.showinfo("Not Found", "Part not found in any tracked set.")

    tk.Button(root, text="Load Set", command=load_selected,
              font=styles['button_font'], bg='#30ce30', fg='white',
              padx=20, pady=5).pack(pady=5)
    tk.Button(root, text="Create New Set", command=create_set,
              font=styles['button_font'], bg='#309bff', fg='white',
              padx=20, pady=5).pack(pady=5)
    tk.Button(root, text="Search Part ID", command=search,
              font=styles['button_font'], bg='#ffce30', fg='white',
              padx=20, pady=5).pack(pady=5)
    tk.Button(root, text="Exit", command=root.destroy,
              font=styles['button_font'], bg='#ff3030', fg='white',
              padx=20, pady=5).pack(pady=5)

    root.mainloop()


# This begins the program.
if __name__ == '__main__':
    main()
