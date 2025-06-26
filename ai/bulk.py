from google import genai
from google.genai import types
import os 

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

my_file = client.files.upload(file="ai/Screenshot 2025-06-26 at 3.24.12 PM.png")

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[my_file, "what is the file name of ht eimage i uploaded"],
)

print(response.text)