import os
import hashlib

# ---------------------------------------------------------
# CONFIG: Where did your previous script save the text files?
CACHE_DIR = "cache_content" 
# ---------------------------------------------------------

def audit_cache():
    if not os.path.exists(CACHE_DIR):
        print(f"❌ Error: Folder '{CACHE_DIR}' not found.")
        return

    print(f"🕵️  Auditing files in '{CACHE_DIR}'...")
    
    seen_hashes = {}
    files = [f for f in os.listdir(CACHE_DIR) if f.endswith('.txt')]
    
    duplicates_found = 0
    empty_found = 0
    
    for filename in files:
        filepath = os.path.join(CACHE_DIR, filename)
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().strip()
            
        # 1. Check for Empty/Junk Files
        if len(content) < 100:
            print(f"⚠️  TOO SHORT: '{filename}' ({len(content)} chars) -> Likely a CAPTCHA or blocked page.")
            empty_found += 1
            continue

        # 2. Check for Duplicates (The 1.0000 Correlation Bug)
        # Create a unique fingerprint for the file content
        file_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        
        if file_hash in seen_hashes:
            original_file = seen_hashes[file_hash]
            print(f"❌ DUPLICATE: '{filename}'")
            print(f"   Matches:   '{original_file}'")
            print(f"   -> Meaning: Google gave the exact same generic page for both.")
            duplicates_found += 1
        else:
            seen_hashes[file_hash] = filename

    print("\n" + "="*30)
    print("📢  AUDIT REPORT")
    print("="*30)
    if duplicates_found == 0 and empty_found == 0:
        print("✅  PASSED: Data looks clean.")
    else:
        print(f"🔴  DUPLICATES: {duplicates_found} (Delete these!)")
        print(f"🟠  TOO SHORT:  {empty_found} (Delete these!)")
        print("💡  ACTION: Delete the files listed above and re-run your downloader.")

if __name__ == "__main__":
    audit_cache()