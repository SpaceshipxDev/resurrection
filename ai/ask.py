from google import genai
from google.genai import types
import os 

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])


sample = client.files.upload(
  file="ai/data_x_x2_x3.csv",
  config=dict(mime_type='text/csv')
)


response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[sample, "hwhat is this about "],
)

print(response.text)