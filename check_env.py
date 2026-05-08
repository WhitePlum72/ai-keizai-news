from dotenv import load_dotenv
import os
load_dotenv()
key = os.environ.get('NVIDIA_API_KEY', 'NOT FOUND')
print(f"KEY: {key[:10]}..." if key != 'NOT FOUND' else "NOT FOUND")
