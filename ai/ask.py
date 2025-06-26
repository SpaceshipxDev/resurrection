from google import genai
from google.genai import types
import os 

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])


with open('ai/Screenshot 2025-06-26 at 3.24.12 PM.png', 'rb') as f:
    image_bytes = f.read()


response = client.models.generate_content(
model='gemini-2.5-flash',
contents=[
    types.Part.from_bytes(
    data=image_bytes, 
    mime_type='image/jpeg',
    ),
    'what is the name of this image '
]
)

print(response.text)