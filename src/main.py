import json
import os
import requests
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk

import settings


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


# This configures the size and position of the window.
def configure_size(window):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    win_width = screen_width // 2
    win_height = screen_height // 2
    x = (screen_width // 2) - (win_width // 2)
    y = (screen_height // 2) - (win_height // 2)

    return f"{win_width}x{win_height}+{x}+{y}"


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
def show_set_grid(set_id, columns=3, set_data_dir='Set Data'):
    data = load_set_data(set_id, set_data_dir)

    grid = tk.Toplevel()
    grid.title(f"Viewing Set: {set_id}")
    grid.geometry(configure_size(grid))

    # Create main frame with both vertical and horizontal scrollbars
    main_frame = tk.Frame(grid)
    main_frame.pack(fill="both", expand=True)

    # Create and position the scrollbars
    v_scrollbar = ttk.Scrollbar(main_frame, orient="vertical")
    v_scrollbar.pack(side="right", fill="y")
    h_scrollbar = ttk.Scrollbar(main_frame, orient="horizontal")
    h_scrollbar.pack(side="bottom", fill="x")

    # Connect canvas to scrollbars and scrollbars to canvas
    canvas = tk.Canvas(main_frame, 
                       yscrollcommand=v_scrollbar.set,
                       xscrollcommand=h_scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)

    v_scrollbar.config(command=canvas.yview)
    h_scrollbar.config(command=canvas.xview)

    # Frame to hold the grid content
    content_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=content_frame, anchor="nw")

    # Mouse wheel scrolling events
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def on_shift_mousewheel(event):
        canvas.xview_scroll(int(-1*(event.delta/120)), "units")

    # Bind mouse wheel events
    canvas.bind("<MouseWheel>", on_mousewheel)
    canvas.bind("<Shift-MouseWheel>", on_shift_mousewheel)
    grid.bind("<MouseWheel>", on_mousewheel)
    grid.bind("<Shift-MouseWheel>", on_shift_mousewheel)

    # Set boundaries for the scrollbars
    def on_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    content_frame.bind("<Configure>", on_configure)

    '''# Save any changes made
    def update_and_save(index, entry):
        print(entry.get())
        try:
            data[index]['have'] = int(entry.get())
            save_set_data(set_id, data, set_data_dir)
        except ValueError:
            messagebox.showerror("Invalid input", "Please use a valid number.")
            # Change scope ?????
            if data[index]['have'] >= data[index]['needed']:
                messagebox.showerror("Invalid input", 
                                     "'Have' must be less than 'Needed'.")
                entry.delete(0, tk.END)
                entry.insert(0, str(data[index]['have']))'''
    
    # Revert changes from invalid entry
    def delete_and_reinsert(entry, index):
        entry.delete(0, tk.END)
        entry.insert(0, str(data[index]['have']))
    
    # Save any valid changes made
    def update_and_save(entry, index):
        try:
            value = int(entry.get())
        except ValueError:
            messagebox.showerror("Invalid Input", 
                                 "Please enter a valid number.", parent=grid)
            delete_and_reinsert(entry, index)
            return
        
        if value < 0:
            messagebox.showerror("Invalid Input", 
                                 "'Have' cannot be negative.", parent=grid)
            delete_and_reinsert(entry, index)
        elif value > data[index]['needed']:
            messagebox.showerror("Invalid Input", 
                                 "'Have' cannot be greater than 'Needed'.", parent=grid)
            delete_and_reinsert(entry, index)
        else:
            data[index]['have'] = value
            save_set_data(set_id, data, set_data_dir)

    for i, part in enumerate(data):
        tk.Label(content_frame, text=f"ID: {part['id']}").grid(row=i, column=0, padx=5, pady=2)
        tk.Label(content_frame, text=f"Color: {part['color']}").grid(row=i, column=1, padx=5, pady=2)
        tk.Label(content_frame, text=f"Need: {part['needed']}").grid(row=i, column=2, padx=5, pady=2)
        entry = tk.Entry(content_frame, width=5)
        entry.insert(0, str(part['have']))
        entry.grid(row=i, column=3, padx=5, pady=2)
        entry.bind("<FocusOut>", lambda e, ent=entry, idx=i: update_and_save(ent, idx))

    tk.Button(content_frame, text="Back", command=grid.destroy).grid(row=len(data)+1, column=0, pady=10)


# This sets up the GUI for the main menu.
def main():
    set_data_dir = 'Set Data'
    columns = 3

    root = tk.Tk()
    root.title("Lego Set Organizer")
    root.geometry(configure_size(root))

    styles = configure_styles(root)

    tk.Label(root, text="Select a Set:", 
             font=styles['label_font'], 
             bg=styles['bg'], fg='white').pack(pady=10)
    
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
