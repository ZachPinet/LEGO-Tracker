import io
import json
import os
import tkinter as tk
import urllib.request
from PIL import Image, ImageTk
from tkinter import messagebox, ttk

from gui.win_helpers import configure_size, on_mousewheel, on_shift_mousewheel


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

    # Update the parts data
    existing_data["parts"] = parts_data

    # Check if set is complete or incomplete
    all_complete = all(part["have"] >= part["need"] for part in parts_data)
    existing_data["set_info"]["completed"] = all_complete

    with open(filepath, 'w') as f:
        json.dump(existing_data, f, indent=2)


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
            bg_frame.config(bg=highlight_color, bd=0, relief='solid')
        elif part_data['have'] > 0:
            highlight_color = '#ffff90'
            bg_frame.config(bg=highlight_color, bd=0, relief='solid')
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
        padx=20, pady=10, cursor='hand2'
    )
    load_window_back_button.grid(
        row=back_button_row, column=0, 
        pady=20, columnspan=6
    )