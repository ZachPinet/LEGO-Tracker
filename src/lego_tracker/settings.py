import os
from dotenv import load_dotenv
from typing import Optional

# Loads the dotenv file
load_dotenv()

# Gets the private information stored in the dotenv file
REBRICKABLE_API_KEY:  Optional[str] = os.getenv('REBRICKABLE_API_KEY')

# Verifies the API key is set
if not REBRICKABLE_API_KEY:
    raise ValueError("REBRICKABLE_API_KEY environment variable is not set.")