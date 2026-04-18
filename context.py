def extract_context(file_path, error_line, window=3):
    context=[]

    with open(file_path,"r") as f:
        lines=f.readlines()

    start=max(0,error_line-window-1)
    end=min(len(lines),error_line+window)

    for i in range(start,end):
        context.append(f"{i + 1}: {'>> ' if i + 1 == error_line else ''}{lines[i].strip()}")

    return context