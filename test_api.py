from Excel_Manager import ExcelManager

print("Initializing Excel Manager...")
manager = ExcelManager()

print("\n--- RUNNING LIVE PRICE RECOVERY ---")
manager.sync_sheet_with_api()

