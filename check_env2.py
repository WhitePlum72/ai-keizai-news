from dotenv import load_dotenv
import os

# パスを明示して読み込む
result = load_dotenv(dotenv_path='.env', verbose=True)
print(f"load_dotenv result: {result}")
key = os.environ.get('NVIDIA_API_KEY', 'NOT FOUND')
print(f"KEY: {key[:15]}..." if key != 'NOT FOUND' else "NOT FOUND")
