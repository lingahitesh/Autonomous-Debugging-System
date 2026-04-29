def score_file(file, entry_file):
    score = 0
    # prefer non-main files
    if file != entry_file:
        score += 2
    # utils/helper files often contain logic
    if "util" in file.lower() or "helper" in file.lower():
        score += 2
    # deprioritize main
    if file.lower().startswith("main"):
        score -= 2
    return score