import io
import json
import os
import re
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


# These handle mouse wheel scrolling for canvas movement
def on_mousewheel(canvas, event):
    if (canvas.canvasy(0) > 0 or 
        canvas.canvasy(canvas.winfo_height()) < canvas.bbox("all")[3]
    ):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")

def on_shift_mousewheel(canvas, event):
    if (
        canvas.canvasx(0) > 0 or 
        canvas.canvasx(canvas.winfo_width()) < canvas.bbox("all")[2]
    ):
        canvas.xview_scroll(int(-1*(event.delta/120)), "units")


# This gets comprehensive set information from the Rebrickable API
def get_set_info(set_id):
    # Get basic set information
    set_url = f"https://rebrickable.com/api/v3/lego/sets/{set_id}/"
    headers = {"Authorization": f"key {settings.REBRICKABLE_API_KEY}"}
    
    set_response = requests.get(set_url, headers=headers)
    if set_response.status_code != 200:
        raise Exception("Failed to fetch set info from Rebrickable API")
    
    set_info = set_response.json()

    # Get regular parts list, excluding spares
    parts_url = f"{set_url}parts/?page_size=1000"
    parts_response = requests.get(parts_url, headers=headers)
    if parts_response.status_code != 200:
        raise Exception("Failed to fetch parts data from Rebrickable API")
    
    all_parts = parts_response.json()["results"]
    regular_parts = [p for p in all_parts if not p.get("is_spare", False)]

    # Get and store category information for all parts
    categories_cache = {}
    def get_category_name(cat_id):
        if cat_id not in categories_cache:
            try:
                cat_url = (
                    f"https://rebrickable.com/api/v3/lego/"
                    f"part_categories/{cat_id}/"
                )
                cat_response = requests.get(cat_url, headers=headers)
                if cat_response.status_code == 200:
                    categories_cache[cat_id] = cat_response.json().get(
                        "name", "Unknown"
                    )
                else:
                    categories_cache[cat_id] = "Unknown"
            except:
                categories_cache[cat_id] = "Unknown"

        return categories_cache[cat_id]
    
    # Add category names to regular parts
    for part in regular_parts:
        part_cat_id = part["part"].get("part_cat_id")
        part["part"]["category_name"] = (
            get_category_name(part_cat_id) if part_cat_id else "Unknown"
        )

    # Get minifigure parts and merge duplicates
    minifigs_url = f"{set_url}minifigs/?page_size=1000"
    minifigs_response = requests.get(minifigs_url, headers=headers)
    minifig_parts = {}

    if minifigs_response.status_code != 200:
        raise Exception("Failed to fetch minifig data from Rebrickable API")
    
    minifigs = minifigs_response.json()["results"]
    for minifig in minifigs:
        minifig_code = minifig["set_num"]
        minifig_qty = minifig["quantity"]
        
        # Get parts for this specific minifigure
        minifig_parts_url = (
            f"https://rebrickable.com/api/v3/lego/minifigs/{minifig_code}/"
            f"parts/?page_size=1000"
        )
        minifig_response = requests.get(minifig_parts_url, headers=headers)
        parts_data = minifig_response.json()["results"]

        # Add each part (multiplied by minifig quantity and part quantity)
        for part_data in parts_data:
            if not part_data.get("is_spare", False):
                # Add category names to minifig parts
                part_cat_id = part_data["part"].get("part_cat_id")
                part_data["part"]["category_name"] = (
                    get_category_name(part_cat_id) 
                    if part_cat_id else "Unknown"
                )

                # Calculate total quantity needed
                part_qty_per_minifig = part_data["quantity"]
                total_qty = part_qty_per_minifig * minifig_qty

                # Merge duplicates
                part_key = (
                    part_data["part"]["part_num"], part_data["color"]["name"]
                )
                if part_key in minifig_parts:
                    minifig_parts[part_key]["quantity"] += total_qty
                else:
                    minifig_parts[part_key] = {
                        "part": part_data["part"], 
                        "color": part_data["color"], 
                        "quantity": total_qty
                    }

    # Convert minifig dictionary to list and combine with regular parts
    minifig_parts_list = list(minifig_parts.values())
    all_parts_combined = regular_parts + minifig_parts_list
    
    # Separate stickers from regular parts
    stickers = []
    parts = []
    for part in all_parts_combined:
        if "sticker" in part["part"]["name"].lower():
            stickers.append(part)
        else:
            parts.append(part)
    
    return {
        "set_info": set_info,
        "parts": parts,
        "stickers": stickers
    }


# This creates a new .txt file for a set.
def create_new_set(set_id, set_data_dir='Set Data'):
    # Get set information
    api_data = get_set_info(set_id)
    set_info = api_data["set_info"]
    parts = api_data["parts"]
    stickers = api_data["stickers"]

    # Sanitize set name just in case
    set_name = set_info["name"]
    safe_name = "".join(
        c for c in set_name if c.isalnum() or c in (' ', '-', '_')
    ).rstrip()

    # Create the new file, unless it already exists
    set_filename = os.path.join(set_data_dir, f"{set_id} - {safe_name}.txt")
    if os.path.exists(set_filename):
        raise Exception("Set already exists.")
    
    # Store the set data
    set_data = {
        "set_info": {
            "set_id": set_id,
            "name": set_name,
            "year": set_info.get("year"),
            "num_parts": set_info.get("num_parts"),
            "set_img_url": set_info.get("set_img_url")
        },
        "parts": [],
        "stickers": []
    }

    # Process parts
    for part in parts:
        set_data["parts"].append({
            "id": part["part"]["part_num"],
            "name": part["part"]["name"],
            "category": part["part"]["category_name"],
            "color": part["color"]["name"],
            "need": part["quantity"],
            "have": 0,
            "image": part["part"]["part_img_url"]
        })

    # Process stickers
    for sticker in stickers:
        set_data["stickers"].append({
            "id": sticker["part"]["part_num"],
            "name": sticker["part"]["name"],
            "category": sticker["part"]["category_name"],
            "color": sticker["color"]["name"],
            "quantity": sticker["quantity"],
            "image": sticker["part"]["part_img_url"]
        })

    with open(set_filename, 'w') as f:
        json.dump(set_data, f, indent=2)


# This loops through the .txt files in Set Data and returns the set IDs.
def list_sets(set_data_dir='Set Data'):
    sets = []
    for filename in os.listdir(set_data_dir):
        if filename.endswith(".txt"):
            sets.append(filename[:-4])
    return sets


# This loads the data from a set ID's .txt file.
def load_set_data(set_title, set_data_dir='Set Data'):
    with open(os.path.join(set_data_dir, f"{set_title}.txt"), 'r') as f:
        data = json.load(f)
    return data["parts"], data["stickers"]


# This saves any updates to the set's data.
def save_set_data(set_title, parts_data, set_data_dir='Set Data'):
    filepath = os.path.join(set_data_dir, f"{set_title}.txt")
    
    # Load existing data to preserve set_info and stickers
    with open(filepath, 'r') as f:
        existing_data = json.load(f)
    
    # Update only the parts data
    existing_data["parts"] = parts_data
    with open(filepath, 'w') as f:
        json.dump(existing_data, f, indent=2)


# This returns a list of set IDs that need a specific part ID.
def search_sets(input_query, set_data_dir='Set Data'):
    # Sanitize and split the search query
    query = "".join(
        c for c in input_query if c.isalnum() or c in (' ', '-', "'")
    )
    search_terms = [
        term.strip().lower() for term in query.split() if term.strip()
    ]

    if not search_terms:
        return []
    
    # Collect all unique parts that are still needed from each set
    needed_parts = {}
    
    for set_file in os.listdir(set_data_dir):
        if not set_file.endswith('.txt'):
            continue
            
        file_path = os.path.join(set_data_dir, set_file)
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                parts = data["parts"]
                set_name = set_file[:-4]
                
                # Add info from each needed part
                for part in parts:
                    if part["have"] < part["need"]:
                        part_key = (part["id"], part["color"])
                        
                        if part_key not in needed_parts:
                            needed_parts[part_key] = {
                                "part_id": part["id"],
                                "name": part["name"],
                                "category": part["category"],
                                "color": part["color"],
                                "image_url": part["image"],
                                "sets_needing": [],
                                "total_needed": 0
                            }
                        
                        needed_parts[part_key]["sets_needing"].append(set_name)
                        needed_parts[part_key]["total_needed"] += (
                            part["need"] - part["have"]
                        )
                        
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            continue
    
    if not needed_parts:
        return []
    
    # Filter parts based on search terms
    matching_parts = []
    
    for part_info in needed_parts.values():
        # Prepare searchable fields as word lists
        def split_into_words(text):
            if not text:
                return []
            # Split on spaces, commas, parentheses, and other common delimiters
            words = re.split(r'[\s,\(\)\[\]\/\-]+', text.lower())
            return [word.strip() for word in words if word.strip()]
        
        searchable_fields = {
            "id": split_into_words(part_info["part_id"]),
            "color": split_into_words(part_info["color"]),
            "category": split_into_words(part_info["category"]),
            "name": split_into_words(part_info["name"])
        }
        
        # Check if all search terms have a match
        all_terms_match = True
        for term in search_terms:
            term_found = False
            for field_words in searchable_fields.values():
                if term in field_words:
                    term_found = True
                    break
            if not term_found:
                all_terms_match = False
                break
        
        if all_terms_match:
            matching_parts.append(part_info)

    return matching_parts


# This shows the search interface with a grid of results
def show_search_window(columns=5, set_data_dir='Set Data'):
    search_window = tk.Toplevel()
    search_window.title("Search Parts")
    search_window.geometry(configure_size(search_window))
    search_window.configure(bg='#00173c')

    # Search bar at the top
    search_frame = tk.Frame(search_window, bg='#00173c')
    search_frame.pack(pady=10)
    
    tk.Label(
        search_frame, text="Search Parts:", font=('Arial', 14, 'bold'), 
        bg='#00173c', fg='white'
    ).pack(side="left", padx=5)
    
    search_entry = tk.Entry(search_frame, font=('Arial', 12), width=30)
    search_entry.pack(side="left", padx=5)
    
    # Results label
    results_label = tk.Label(
        search_window, text="Enter search terms above", 
        font=('Arial', 12), bg='#00173c', fg='white'
    )
    results_label.pack(pady=5)

    # Create main frame with scrollbars for the grid
    main_frame = tk.Frame(search_window, bg='#00173c')
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Create and position the scrollbars
    v_scrollbar = ttk.Scrollbar(main_frame, orient="vertical")
    v_scrollbar.pack(side="right", fill="y")
    h_scrollbar = ttk.Scrollbar(main_frame, orient="horizontal")
    h_scrollbar.pack(side="bottom", fill="x")

    # Connect canvas to scrollbars
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

    # Mouse wheel scrolling
    canvas.bind(
        "<MouseWheel>", lambda event: on_mousewheel(canvas, event)
    )
    canvas.bind(
        "<Shift-MouseWheel>", lambda event: on_shift_mousewheel(canvas, event)
    )
    search_window.bind(
        "<MouseWheel>", lambda event: on_mousewheel(canvas, event)
    )
    search_window.bind(
        "<Shift-MouseWheel>", lambda event: on_shift_mousewheel(canvas, event)
    )

    # Set boundaries for the scrollbars
    def on_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    content_frame.bind("<Configure>", on_configure)

    # Display which sets need a specific part
    def show_sets_needing_part(part_info):
        sets_text = (
            f"Sets needing {part_info['part_id']} ({part_info['color']}):\n\n"
        )
        for i, set_name in enumerate(part_info['sets_needing'], 1):
            sets_text += f"{i}. {set_name}\n"
        sets_text += f"\nTotal needed: {part_info['total_needed']}"
        
        messagebox.showinfo(
            "Sets Needing This Part", sets_text, parent=search_window
        )

    # Clear the grid of all cells
    def clear_grid():
        for widget in content_frame.winfo_children():
            widget.destroy()

    # Create the search results grid
    def create_search_grid(results):
        clear_grid()
        
        if not results:
            no_results_label = tk.Label(
                content_frame, text="No matching parts found", 
                font=('Arial', 14), 
                bg='#00173c', 
                fg='white'
            )
            no_results_label.pack(pady=20)
            return

        bg_color1 = '#f0f0f0'
        bg_color2 = '#bfbfbf'

        # Create the grid layout
        for i, part_info in enumerate(results):
            row = i // columns
            col = i % columns
            bg_color = bg_color1 if (row + col) % 2 == 0 else bg_color2
            
            # Base position for the current part
            base_row = row * 3
            base_col = col * 6

            # Create background frame for the entire parts area
            bg_frame = tk.Frame(
                content_frame, bg=bg_color, width=300, height=80
            )
            bg_frame.grid(
                row=base_row, column=base_col, 
                rowspan=3, columnspan=6, 
                padx=2, pady=2, sticky="nsew"
            )
            bg_frame.grid_propagate(False)
            
            # Make the entire frame clickable
            def on_part_click(event, part=part_info):
                show_sets_needing_part(part)
            
            bg_frame.bind("<Button-1>", on_part_click)
            bg_frame.configure(cursor="hand2")  # indicate its clickable

            # Load and display image
            try:
                with urllib.request.urlopen(part_info['image_url']) as response:
                    img_data = response.read()
                
                pil_image = Image.open(io.BytesIO(img_data))
                pil_image = (
                    pil_image.resize((60, 60), Image.Resampling.LANCZOS)
                )
                photo = ImageTk.PhotoImage(pil_image)
                
                # Create label with image
                img_label = tk.Label(
                    content_frame, image=photo, 
                    width=60, height=60
                )
                img_label.image = photo  # Keep a reference
                img_label.grid(
                    row=base_row, column=base_col, rowspan=3, 
                    padx=4, pady=4, sticky="nw"
                )
                img_label.bind("<Button-1>", on_part_click)
                img_label.configure(cursor="hand2")
            
            # Fallback to placeholder if image loading fails
            except Exception as e:
                img_frame = tk.Frame(
                    content_frame, width=60, height=60, 
                    bg='lightgray', relief='solid', bd=1
                )
                img_frame.grid(
                    row=base_row, column=base_col, rowspan=3, 
                    padx=4, pady=4, sticky="nw"
                )
                img_frame.grid_propagate(False)
                img_frame.bind("<Button-1>", on_part_click)
                img_frame.configure(cursor="hand2")
                
                img_label = tk.Label(
                    img_frame, text="IMG", 
                    bg='lightgray', font=('Arial', 8)
                )
                img_label.place(relx=0.5, rely=0.5, anchor="center")
                img_label.bind("<Button-1>", on_part_click)
                img_label.configure(cursor="hand2")

            # Part information labels
            info_labels = []
            
            # ID and Name
            id_name_label = tk.Label(
                content_frame, 
                text=f"ID: {part_info['part_id']}", 
                font=('Arial', 9, 'bold'), 
                bg=bg_color
            )
            id_name_label.grid(
                row=base_row, column=base_col+2, columnspan=4, 
                padx=4, pady=1, sticky="w"
            )
            info_labels.append(id_name_label)
            
            name_label = tk.Label(
                content_frame, 
                text=part_info['name'], 
                font=('Arial', 8), 
                bg=bg_color, 
                wraplength=180
            )
            name_label.grid(
                row=base_row+1, column=base_col+2, columnspan=4, 
                padx=4, pady=1, sticky="w"
            )
            info_labels.append(name_label)

            # Color and Category
            color_label = tk.Label(
                content_frame, 
                text=f"Color: {part_info['color']}", 
                font=('Arial', 8), 
                bg=bg_color
            )
            color_label.grid(
                row=base_row+2, column=base_col+2, columnspan=2, 
                padx=4, pady=1, sticky="w"
            )
            info_labels.append(color_label)
            
            category_label = tk.Label(
                content_frame, 
                text=f"Category: {part_info['category']}", 
                font=('Arial', 8), 
                bg=bg_color, 
                wraplength=100
            )
            category_label.grid(
                row=base_row+2, column=base_col+4, columnspan=2, 
                padx=4, pady=1, sticky="w"
            )
            info_labels.append(category_label)

            # Make all labels clickable
            for label in info_labels:
                label.bind("<Button-1>", on_part_click)
                label.configure(cursor="hand2")

        # Add back button
        back_button_row = (len(results)//columns + 1) * 3
        back_button = tk.Button(
            content_frame, text="Back", command=search_window.destroy, 
            font=('Arial', 12, 'bold'), bg='#ff3030', fg='white',
            padx=20, pady=10
        )
        back_button.grid(row=back_button_row, column=0, pady=20, columnspan=6)

    # Search sets and construct grid accordingly
    def perform_search():
        query = search_entry.get().strip()
        if not query:
            results_label.config(text="Enter search terms above")
            clear_grid()
            return
        
        results = search_sets(query, set_data_dir)
        
        if results:
            results_label.config(text=f"Found {len(results)} matching parts:")
            create_search_grid(results)
        else:
            results_label.config(text="No matching parts found")
            clear_grid()

    # Search button
    search_button = tk.Button(
        search_frame, text="Search", command=perform_search,
        font=('Arial', 12, 'bold'), bg='#30ce30', fg='white',
        padx=10, pady=2
    )
    search_button.pack(side="left", padx=5)

    # Bind Enter key to search
    search_entry.bind("<Return>", lambda e: perform_search())
    
    # Focus on search entry
    search_entry.focus()


# This shows a list of the part data from a specific set.
def show_set_grid(set_title, columns=5, set_data_dir='Set Data'):
    parts_data, stickers_data = load_set_data(set_title, set_data_dir)

    load_window = tk.Toplevel()
    load_window.title(f"Viewing Set: {set_title}")
    load_window.geometry(configure_size(load_window))
    load_window.configure(bg='#00173c')

    # Create main frame with both vertical and horizontal scrollbars
    main_frame = tk.Frame(load_window, bg='#00173c')
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

    # Mouse wheel scrolling
    canvas.bind(
        "<MouseWheel>", lambda event: on_mousewheel(canvas, event)
    )
    canvas.bind(
        "<Shift-MouseWheel>", lambda event: on_shift_mousewheel(canvas, event)
    )
    load_window.bind(
        "<MouseWheel>", lambda event: on_mousewheel(canvas, event)
    )
    load_window.bind(
        "<Shift-MouseWheel>", lambda event: on_shift_mousewheel(canvas, event)
    )

    # Set boundaries for the scrollbars
    def on_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    content_frame.bind("<Configure>", on_configure)

    # Revert changes from invalid entry
    def delete_and_reinsert(entry, index):
        entry.delete(0, tk.END)
        entry.insert(0, str(parts_data[index]['have']))

    # Check if part is completed and show/hide highlight
    def update_highlight(part_data, bg_frame, text_widgets, orig_color):
        if part_data['have'] == part_data['need']:
            highlight_color = '#90ee90'
            bg_frame.config(bg=highlight_color, bd=3, relief='solid')
        else:
            highlight_color = orig_color
            bg_frame.config(bg=highlight_color, bd=0, relief='flat')
        
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
                parent=load_window
            )
            delete_and_reinsert(entry, index)
            return
        
        if value < 0:
            messagebox.showerror(
                "Invalid Input", 
                "'Have' cannot be negative.", 
                parent=load_window
            )
            delete_and_reinsert(entry, index)
        elif value > parts_data[index]['need']:
            messagebox.showerror(
                "Invalid Input", 
                "'Have' cannot be greater than 'Need'.", 
                parent=load_window
            )
            delete_and_reinsert(entry, index)
        else:
            parts_data[index]['have'] = value
            save_set_data(set_title, parts_data, set_data_dir)
            update_highlight(
                parts_data[index], bg_frame, text_widgets, orig_color
            )
    
    bg_color1 = '#f0f0f0'
    bg_color2 = '#bfbfbf'

    # Create the grid layout. Each part takes up 3 rows and 6 columns
    for i, part in enumerate(parts_data):
        row = i // columns
        col = i % columns
        bg_color = bg_color1 if (row + col) % 2 == 0 else bg_color2
        
        # Base position for the current part
        base_row = row * 3
        base_col = col * 6

        # Create background frame for the entire parts area
        bg_frame = tk.Frame(content_frame, bg=bg_color, width=300, height=60)
        bg_frame.grid(
            row=base_row, column=base_col, 
            rowspan=2, columnspan=6, 
            padx=2, pady=2, sticky="nsew"
        )
        bg_frame.grid_propagate(False)
        
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

    # Add stickers section if they exist
    if stickers_data:
        start_row = (len(parts_data)//columns + 1) * 3

        # Add separator
        separator = tk.Frame(content_frame, height=2, bg='white')
        separator.grid(
            row=start_row, column=0, columnspan=6, pady=10, sticky="ew"
        )
        
        # Stickers title
        sticker_title = tk.Label(
            content_frame, text="Stickers:", font=('Arial', 14, 'bold'), 
            bg='#00173c', fg='white'
        )
        sticker_title.grid(row=start_row + 1, column=0, columnspan=6, pady=5)
        
        # Display sticker images
        sticker_row = start_row + 2
        for i, sticker in enumerate(stickers_data):
            try:
                with urllib.request.urlopen(sticker["image"]) as response:
                    img_data = response.read()
                
                pil_image = Image.open(io.BytesIO(img_data))
                pil_image = pil_image.resize(
                    (100, 100), Image.Resampling.LANCZOS
                )
                photo = ImageTk.PhotoImage(pil_image)
                
                sticker_label = tk.Label(content_frame, image=photo)
                sticker_label.image = photo
                sticker_label.grid(row=sticker_row, column=i, padx=5, pady=5)
                
                info_text = f"ID: {sticker['id']}\nQty: {sticker['quantity']}"
                info_label = tk.Label(
                    content_frame, text=info_text, font=('Arial', 8), 
                    bg='#00173c', fg='white'
                )
                info_label.grid(row=sticker_row + 1, column=i, padx=5)
                
            except Exception as e:
                print(f"Could not load sticker image: {e}")
        
        back_button_row = sticker_row + 2
    else:
        back_button_row = (len(parts_data)//columns + 1) * 3
    
    # Back button
    load_window_back_button = tk.Button(
        content_frame, text="Back", command=load_window.destroy, 
        font=('Arial', 12, 'bold'), bg='#ff3030', fg='white',
        padx=20, pady=10
    )
    load_window_back_button.grid(
        row=back_button_row, column=0, 
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
