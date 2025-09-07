import json
import os
import requests
from typing import Dict, List, Any, Optional

from ..settings import REBRICKABLE_API_KEY


# Split text into individual words for searching
def split_into_search_words(text: Optional[str]) -> List[str]:
    import re
    if not text:
        return []
    # Split on spaces, commas, parentheses, and other common delimiters
    words = re.split(r'[\s,\(\)\[\]\/\-]+', text.lower())
    return [word.strip() for word in words if word.strip()]

# This gets comprehensive set information from the Rebrickable API
def get_set_info(set_id: str) -> Dict[str, Any]:
    # Get basic set information
    set_url = f"https://rebrickable.com/api/v3/lego/sets/{set_id}/"
    headers = {"Authorization": f"key {REBRICKABLE_API_KEY}"}
    
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
def create_new_set(set_id: str, set_data_dir: str = 'set_data') -> None:
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
            "completed": False,
            "parts_found": 0,
            "notes": ""
        },
        "parts": [],
        "stickers": []
    }

    # Process parts
    for part in parts:
        # Pre-compute search words for all searchable fields
        part_id = part["part"]["part_num"]
        part_name = part["part"]["name"]
        part_category = part["part"]["category_name"]
        part_color = part["color"]["name"]
        
        # Combine all searchable text and split into words
        all_search_text = f"{part_id} {part_name} {part_category} {part_color}"
        search_words = split_into_search_words(all_search_text)
        
        set_data["parts"].append({
            "id": part_id,
            "name": part_name,
            "category": part_category,
            "color": part_color,
            "need": part["quantity"],
            "have": 0,
            "image": part["part"]["part_img_url"],
            "search_words": search_words
        })

    # Process stickers
    for sticker in stickers:
        sticker_id = sticker["part"]["part_num"]
        sticker_name = sticker["part"]["name"]
        sticker_category = sticker["part"]["category_name"]
        sticker_color = sticker["color"]["name"]
        
        # Pre-compute search words for stickers too
        all_searchable_text = f"{sticker_id} {sticker_name} {sticker_category} {sticker_color}"
        search_words = split_into_search_words(all_searchable_text)
        
        set_data["stickers"].append({
            "id": sticker_id,
            "name": sticker_name,
            "category": sticker_category,
            "color": sticker_color,
            "quantity": sticker["quantity"],
            "image": sticker["part"]["part_img_url"],
            "search_words": search_words
        })

    with open(set_filename, 'w') as f:
        json.dump(set_data, f, indent=2)