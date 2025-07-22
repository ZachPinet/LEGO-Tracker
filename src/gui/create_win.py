import json
import os
import requests

import settings


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
            "set_img_url": set_info.get("set_img_url"),
            "completed": False
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