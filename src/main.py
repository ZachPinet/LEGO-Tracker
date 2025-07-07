import io
import json
import os
import requests
import tkinter as tk
import urllib.request
from PIL import Image, ImageTk
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
    url = (
        f"https://rebrickable.com/api/v3/lego/sets/{set_id}/parts/"
        "?page_size=1000"
    )

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
            "need": part["quantity"],
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
                if part["id"] == part_id and part["have"] < part["need"]:
                    matching_sets.append(set_file[:-4])
                    break

    return matching_sets


# This shows a list of the part data from a specific set.
def show_set_grid(set_id, columns=3, set_data_dir='Set Data'):
    data = load_set_data(set_id, set_data_dir)

    grid = tk.Toplevel()
    grid.title(f"Viewing Set: {set_id}")
    grid.geometry(configure_size(grid))

    grid.configure(bg='#00173c')
    bg_color1 = '#f0f0f0'
    bg_color2 = '#bfbfbf'

    # Create main frame with both vertical and horizontal scrollbars
    main_frame = tk.Frame(grid, bg='#00173c')
    main_frame.pack(fill="both", expand=True)

    # Create and position the scrollbars
    v_scrollbar = ttk.Scrollbar(main_frame, orient="vertical")
    v_scrollbar.pack(side="right", fill="y")
    h_scrollbar = ttk.Scrollbar(main_frame, orient="horizontal")
    h_scrollbar.pack(side="bottom", fill="x")

    # Connect canvas to scrollbars and scrollbars to canvas
    canvas = tk.Canvas(
        main_frame, 
        yscrollcommand=v_scrollbar.set,
        xscrollcommand=h_scrollbar.set,
        bg='#00173c'
    )
    canvas.pack(side="left", fill="both", expand=True)

    v_scrollbar.config(command=canvas.yview)
    h_scrollbar.config(command=canvas.xview)

    # Frame to hold the grid content
    content_frame = tk.Frame(canvas, bg='#00173c')
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

    # Revert changes from invalid entry
    def delete_and_reinsert(entry, index):
        entry.delete(0, tk.END)
        entry.insert(0, str(data[index]['have']))

    # Check if part is completed and show/hide highlight
    def update_highlight(part_data, bg_frame, text_widgets, orig_color):
        if part_data['have'] == part_data['need']:
            highlight_color = '#90EE90'
            bg_frame.config(bg=highlight_color, bd=3, relief='solid')
        else:
            highlight_color = orig_color  # Original checkered color
            bg_frame.config(bg=highlight_color, bd=0, relief='flat')
        
        # Update background colors for text widgets (no borders)
        for widget in text_widgets:
            widget.config(bg=highlight_color)
    
    # Save any valid changes made
    def update_and_save(entry, index, bg_frame, text_widgets, orig_color):
        try:
            value = int(entry.get())
        except ValueError:
            messagebox.showerror(
                "Invalid Input", 
                "Please enter a valid number.", 
                parent=grid
            )
            delete_and_reinsert(entry, index)
            return
        
        if value < 0:
            messagebox.showerror(
                "Invalid Input", 
                "'Have' cannot be negative.", 
                parent=grid
            )
            delete_and_reinsert(entry, index)
        elif value > data[index]['need']:
            messagebox.showerror(
                "Invalid Input", 
                "'Have' cannot be greater than 'Need'.", 
                parent=grid
            )
            delete_and_reinsert(entry, index)
        else:
            data[index]['have'] = value
            save_set_data(set_id, data, set_data_dir)
            update_highlight(data[index], bg_frame, text_widgets, orig_color)
    
    # Create the grid layout. Each part takes up 3 rows and 6 columns
    for i, part in enumerate(data):
        row = i // columns
        col = i % columns

        bg_color = bg_color1 if (row + col) % 2 == 0 else bg_color2
        
        # Base position for the current part
        base_row = row * 3
        base_col = col * 6

        # Create background frame for the entire part area
        bg_frame = tk.Frame(content_frame, bg=bg_color, width=300, height=60)
        bg_frame.grid(
            row=base_row, column=base_col, 
            rowspan=2, columnspan=6, 
            padx=2, pady=2, sticky="nsew"
        )
        bg_frame.grid_propagate(False)  # Prevent resizing to content
        
        # Load and display image
        try:
            with urllib.request.urlopen(part['image']) as response:
                img_data = response.read()
            
            # Open with PIL and resize to 51x51
            pil_image = Image.open(io.BytesIO(img_data))
            pil_image = pil_image.resize((51, 51), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(pil_image)
            
            # Create label with image
            img_label = tk.Label(
                content_frame, image=photo, 
                width=51, height=51
            )
            img_label.image = photo  # Keep a reference
            img_label.grid(
                row=base_row, column=base_col, rowspan=2, 
                padx=4, pady=4, sticky="nw"
            )
        
        # Fallback to placeholder if image loading fails
        except Exception as e:
            img_frame = tk.Frame(
                content_frame, width=51, height=51, 
                bg='lightgray', relief='solid', bd=1
            )
            img_frame.grid(
                row=base_row, column=base_col, rowspan=2, 
                padx=4, pady=4, sticky="nw"
            )
            img_frame.grid_propagate(False)

            img_label = tk.Label(
                img_frame, text="IMG", 
                bg='lightgray', font=('Arial', 8)
            )
            img_label.place(relx=0.5, rely=0.5, anchor="center")

        # ID field
        id_label = tk.Label(
            content_frame, text=f"ID: {part['id']}", 
            font=('Arial', 10, 'bold'), bg=bg_color
        )
        id_label.grid(
            row=base_row, column=base_col+2, 
            padx=4, pady=2, sticky="w"
        )

        # Need field
        need_label = tk.Label(
            content_frame, text=f"Need: {part['need']}", 
            font=('Arial', 10), bg=bg_color
        )
        need_label.grid(
            row=base_row, column=base_col+4, 
            padx=4, pady=2, sticky="w"
        )

        # Color field
        color_label = tk.Label(
            content_frame, text=f"Color: {part['color']}", 
            font=('Arial', 10), bg=bg_color
        )
        color_label.grid(
            row=base_row+1, column=base_col+2, 
            padx=4, pady=2, sticky="w"
        )
        
        # Have field
        have_frame = tk.Frame(content_frame, bg=bg_color)
        have_frame.grid(
            row=base_row+1, column=base_col+4, 
            padx=4, pady=2, sticky="w"
        )
        have_label = tk.Label(
            have_frame, text="Have:", 
            font=('Arial', 10), bg=bg_color
        )
        have_label.pack(side="left")

        # Handle entries for Have field
        entry = tk.Entry(have_frame, width=5, font=('Arial', 10))
        entry.insert(0, str(part['have']))
        entry.pack(side="left", padx=(4, 0))

        # Create list of text widgets to get background color updates
        text_widgets = [
            id_label, need_label, color_label, 
            have_frame, have_label
        ]

        entry.bind(
            "<FocusOut>", lambda e, ent=entry, idx=i, bgf=bg_frame, 
            widgets=text_widgets, orig_color=bg_color: 
            update_and_save(ent, idx, bgf, widgets, orig_color)
        )

        # Set initial highlight state
        update_highlight(part, bg_frame, text_widgets, bg_color)
    
    # Back button
    grid_back_button = tk.Button(
        content_frame, text="Back", command=grid.destroy, 
        font=('Arial', 12, 'bold'), bg='#ff3030', fg='white',
        padx=20, pady=10
    )
    grid_back_button.grid(
        row=(len(data)//columns + 1)*3, column=0, 
        pady=20, columnspan=6
    )


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
        part_id = simpledialog.askstring("Search", "Enter Part ID:")
        if part_id:
            results = search_sets_by_part(part_id, set_data_dir)
            if results:
                messagebox.showinfo(
                    "Found In Sets", 
                    "\n".join(results)
                )
            else:
                messagebox.showinfo(
                    "Not Found", 
                    "Part not found in any tracked set."
                )

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
        root, text="Search Part ID", command=search,
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
