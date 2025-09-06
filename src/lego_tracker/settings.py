from dotenv import load_dotenv
import os

# Loads the dotenv file
load_dotenv()

# Gets the private information stored in the dotenv file
REBRICKABLE_API_KEY = os.getenv('REBRICKABLE_API_KEY')