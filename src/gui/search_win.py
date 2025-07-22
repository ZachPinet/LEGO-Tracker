import io
import json
import os
import re
import tkinter as tk
import urllib.request
from PIL import Image, ImageTk
from tkinter import messagebox, ttk

from gui.win_helpers import configure_size, on_mousewheel, on_shift_mousewheel


# This returns a list of set IDs that need a specific part ID.
def search_sets(input_query, set_data_dir='Set Data'):
    # Sanitize and split the search query
    query = "".join(
        c for c in input_query if c.isalnum() or c in (' ', '-', "'")
    )
    search_terms = [
        term.strip().lower() for term in query.split() if term.strip()
    ]

    # Return empty list if there are no search terms
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

                # Skip completed sets
                if data.get("set_info", {}).get("completed", False):
                    continue

                parts = data["parts"]
                set_name = set_file[:-4]
                
                for part in parts:
                    # Skip completed parts
                    if part["have"] >= part["need"]:
                        continue

                    part_key = (part["id"], part["color"])
                    
                    # Add info from each needed part
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