from dotenv import load_dotenv
import os

load_dotenv(dotenv_path='.env', override=True)
key = os.environ.get('NVIDIA_API_KEY', 'NOT FOUND')
print(f"KEY: {key[:15]}..." if key != 'NOT FOUND' else "NOT FOUND")
