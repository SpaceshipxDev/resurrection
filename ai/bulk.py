from google import genai
from google.genai import types
import os 

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

my_file = client.files.upload(file="ai/Screenshot 2025-06-26 at 3.24.12 PM.png")
mon_fil_2 = client.files.upload(file="ai/Screenshot 2025-06-26 at 3.36.58 PM.png")

sample_pdf_1 = client.files.upload(
  file="ai/j228-jl-04-01-j101.pdf",
  config=dict(mime_type='application/pdf')
)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[my_file, mon_fil_2, sample_pdf_1, "how many files did i upload "],
)

print(response.text)