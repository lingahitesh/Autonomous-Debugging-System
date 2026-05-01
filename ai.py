from dotenv import load_dotenv
import os
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_fix(error_info, context, strategy):
    context_text="\n".join(context)

    prompt=f"""
You are a strict Java debugging agent.

Fix the root cause while preserving original intent.

Error:
{error_info.get("message","")}

Strategy:
{strategy}

Code:
{context_text}

Rules:
- Fix only the real bug
- Preserve program behavior
- Prefer fixing source file over caller
- Do not add dummy prints, shortcuts, or bypass logic
- If loop issue, fix condition/update only
- If syntax issue, complete broken structure/statements
- If safety issue, add minimal guards
- If EOF parsing error, append missing braces on new lines
- If multiple files are shown, include file names

Output:
Single:
<line>: <code>

Multi:
START_FIX
<file>:<line>: <code>
<file>:<line>: <code>
END_FIX
"""

    response=client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role":"system",
                "content":"Output only valid Java fixes in required format."
            },
            {
                "role":"user",
                "content":prompt
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content.strip()



def verify_fix(error_info, context, fix):
    context_text="\n".join(context)

    prompt=f"""
Error:
{error_info.get("message","")}

Code:
{context_text}

Fix:
{fix}

Reply ONLY:
VALID
or
INVALID

INVALID if:
- the original error would still occur
- the fix breaks program logic
- the fix repeats a previously failed pattern
- the fix does not resolve the root cause
"""

    response=client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role":"system",
                "content":"Strict validator."
            },
            {
                "role":"user",
                "content":prompt
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content.strip()