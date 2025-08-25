# wsgi.py
from dotenv import load_dotenv
import os

# This line finds the .env file in your project root and loads it.
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Now we import the app AFTER the environment is loaded.
from app import create_app

app = create_app()
