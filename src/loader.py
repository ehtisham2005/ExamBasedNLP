import os

def load_text_file(filepath, label):
    """
    Safely loads a text file and returns lines or full text.
    Handles errors if the user types a wrong path.
    """
    print(f"📂 Loading {label} from: {filepath}...")
    
    if not os.path.exists(filepath):
        print(f"❌ Error: The file '{filepath}' was not found.")
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # We strip whitespace to avoid empty lines messing up the AI
            content = [line.strip() for line in f.readlines() if line.strip()]
            
        print(f"   ✅ Loaded {len(content)} lines/items.")
        return content
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return None