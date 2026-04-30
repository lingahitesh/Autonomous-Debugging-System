def choose_strategy(error_info):
    message = error_info.get("message", "").lower()
    error_type = error_info.get("type", "").lower()

    if "timeout" in message or "infinite loop" in message:
        return "loop"

    if "illegal start" in message or "expected" in message:
        return "syntax"

    if "arithmeticexception" in message or error_type == "arithmeticexception":
        return "safety"

    if "incorrect output" in message:
        return "logic"

    return "general"