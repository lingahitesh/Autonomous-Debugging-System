from dotenv import load_dotenv
import os
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_fix(error_info, context):
    context_text = "\n".join(context)

    prompt = f"""
You are a strict Java code fixer.

Fix ONLY the error in the code.

RULES:
- Output ONLY ONE LINE
- Format: <line_number>: <fixed_code>
- No explanation
- No comments
- Do not modify other lines
- Use smallest valid value

Code:
{context_text}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    return response.choices[0].message.content.strip()