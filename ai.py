from dotenv import load_dotenv
import os
from groq import Groq

# Load environment variables
load_dotenv()

# Initialize client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_fix(error_info, context):
    context_text = "\n".join(context)

    # Safe extraction (prevents KeyError)
    error_message = error_info.get("message", "")
    error_type = error_info.get("type", "")

    # Error-type aware guidance
    extra_rule = ""

    if "ArithmeticException" in error_message or error_type == "ArithmeticException":
        extra_rule = "Ensure denominator is not zero before division."
    elif "NullPointerException" in error_message or error_type == "NullPointerException":
        extra_rule = "Ensure object is not null before accessing it."
    elif "ArrayIndexOutOfBoundsException" in error_message:
        extra_rule = "Ensure index is within valid bounds."
    elif "illegal start of expression" in error_message:
        extra_rule = "Fix syntax error by completing the expression properly."

    prompt = f"""
    You are a strict Java debugging agent.

    Your task is to fix exactly ONE error in the code while preserving the original program logic and intent.

    Error:
    {error_info.get("message", "")}

    Code:
    {context_text}

    INSTRUCTIONS (follow internally, DO NOT output these steps):
    1. Identify the root cause of the error
    2. Understand what the code is trying to do
    3. Fix ONLY the faulty statement or operation
    4. Preserve program semantics

    RULES:
    - Output ONLY ONE LINE
    - Format: <line_number>: <fixed_code>
    - Do NOT explain
    - Do NOT modify other lines
    - Do NOT introduce unrelated changes
    - Replace unsafe or abrupt program termination with safe user-facing handling when possible
    - If program does not terminate, identify problematic loops and ensure termination condition or add safe exit
    - If the program does not terminate, analyze loop constructs (for, while)
    
    SEMANTIC RULES:
    - Do NOT change variable values or assignments unless absolutely necessary
    - Prefer fixing the operation or expression rather than modifying input data
    - Preserve the intended behavior of the program
    - If the error is due to unsafe operations, handle them safely (e.g., validation, checks, guards)

    SAFETY PRINCIPLES:
    - Prevent runtime failures by adding minimal safety checks where needed
    - Avoid introducing new errors
    - Prefer local fixes over global changes

    FALLBACK:
    - If no safe semantic fix is possible, apply the smallest valid fix

    Before final answer, internally verify:
    - Does the fix address the specific error?
    - Does it preserve program intent?
    - Is it safe and minimal?

    If format is incorrect, regenerate internally before returning.

    Now produce the correct fix.
    """

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "You output only precise Java fixes in one line."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    return response.choices[0].message.content.strip()

def verify_fix(error_info, context, fix):
    context_text = "\n".join(context)

    prompt = f"""
You are a strict validator.

Given an error and a proposed fix, determine if the fix correctly resolves the issue.

Error:
{error_info.get("message", "")}

Code:
{context_text}

Proposed Fix:
{fix}

RULES:
- Answer ONLY with VALID or INVALID
- Do NOT explain

Check:
- Does the fix directly address the error?
- Is it logically correct?
- Will it avoid runtime/compile failure?

Answer:
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "You strictly validate fixes."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    return response.choices[0].message.content.strip()