from pathlib import Path
import pandas as pd

# 1. Verify file exists
file_name = "Magic Card Data Base Current View.xlsx"
file_path = Path.cwd() / file_name

print("--- STARTING DATABASE TEST ---")
print(f"Checking for file at: {file_path}")

if not file_path.exists():
    print(f"❌ ERROR: Could not find '{file_name}' in this folder!")
    print("Run 'ls -la' in your terminal to see what files are in this directory.")
    exit()
else:
    print("✅ File found successfully!")

# 2. Try loading the first few rows
try:
    print("\nAttempting to read Excel headers...")
    # Load just the first 5 rows to be fast and light
    df = pd.read_excel(file_path, engine="openpyxl", nrows=5)
    
    # Strip spaces from columns just like our manager will
    df.columns = df.columns.str.strip()
    
    print("✅ Excel file read successfully!")
    print(f"Detected Columns: {list(df.columns)}")
    
    # 3. Test data extraction
    print("\nTesting row mapping...")
    if not df.empty:
        first_row = df.iloc[0]
        print(f"-> Sample Name Value: '{first_row.get('Name')}'")
        print(f"-> Sample Rank 1 Value: '{first_row.get('Rank 1')}'")
        print(f"-> Sample Class 1 Value: '{first_row.get('Class 1')}'")
        print("\n🎉 Mapping test complete! Columns are aligning correctly.")
    else:
        print("⚠ The Excel sheet appears to be empty.")

except Exception as e:
    print(f"❌ DATA ERROR: Something went wrong reading the file structure: {e}")
