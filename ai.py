from dotenv import load_dotenv
import os
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_fix(error_info, context):
    context_text="\n".join(context)
    error_message=error_info.get("message","")
    error_type=error_info.get("type","")

    extra_rule=""
    if "ArithmeticException" in error_message or error_type=="ArithmeticException":
        extra_rule="Ensure denominator is not zero before division."
    elif "NullPointerException" in error_message or error_type=="NullPointerException":
        extra_rule="Ensure object is not null before accessing it."
    elif "ArrayIndexOutOfBoundsException" in error_message:
        extra_rule="Ensure index is within valid bounds."
    elif "illegal start of expression" in error_message:
        extra_rule="Fix syntax error by completing the expression properly."

    prompt=f"""
You are a strict Java debugging agent.

Your task is to fix the ROOT CAUSE of the error.
If fixing the root cause requires modifying multiple lines, you may do so.

Error:
{error_message}

Code:
{context_text}

Guidance:
{extra_rule}

RULES:
- Prefer minimal fix, but allow multi-line fix if necessary
- If multiple lines are required, output:
  START_FIX
  <line>: code
  <line>: code
  END_FIX
- If adding a missing closing brace, place it on a NEW line after the last line
- Do NOT explain
- Do NOT modify unrelated lines
- Preserve original logic unless clearly broken
- Do NOT remove or comment out existing functional code unless it is clearly the direct cause of the error
- Do NOT change program structure (loops, function calls, class structure) unless absolutely necessary
- Do NOT replace logic with dummy prints or shortcuts
- Prefer fixing the source of error rather than bypassing it
- If multiple files are present, prioritize fixing the file where the root cause originates rather than modifying calling code.
- If multiple files are present, ALWAYS specify file name

SPECIAL CASES:
- If syntax error → ensure full statement is valid
- If structure error → ensure all blocks are properly closed
- If timeout → prioritize fixing loop conditions or repeated updates
- If the error is "reached end of file while parsing", you MUST add the missing closing brace at the NEXT line after the last line (line number = last line + 1). Do NOT replace existing lines for this case.

OUTPUT FORMAT:

For single-file fix:
<line_number>: <code>

For multi-file fix:
START_FIX
<file>:<line_number>: <code>
<file>:<line_number>: <code>
END_FIX
"""

    response=client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role":"system","content":"You output only precise Java fixes in required format."},
            {"role":"user","content":prompt}
        ],
        temperature=0
    )

    return response.choices[0].message.content.strip()



def verify_fix(error_info, context, fix):
    context_text="\n".join(context)

    prompt=f"""
You are a strict validator.

Error:
{error_info.get("message","")}

Code:
{context_text}

Proposed Fix:
{fix}

RULES:
- Answer ONLY with VALID or INVALID
- Fix must resolve the error
- If the same error would still occur, return INVALID
- Fix must not be identical to previous failed fixes

Answer:
"""

    response=client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role":"system","content":"You strictly validate fixes."},
            {"role":"user","content":prompt}
        ],
        temperature=0
    )

    return response.choices[0].message.content.strip()