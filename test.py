from ets_forecast import DataLoader
import pandas as pd
from supabase import create_client, Client
from time import sleep

file_paths = ["./data/SEP-OCT-NOV.xlsx", "./data/DEC-JAN-FEB-MAR.xlsx"]
# file_paths = ["./data/DEC-JAN-FEB-MAR.xlsx"]
data_loader = DataLoader(file_paths=file_paths)
data = data_loader.load_data()
data = data_loader.convert_date("BillingDate")

SUPABASE_URL = "https://nygvshcremnrwwzkljpg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im55Z3ZzaGNyZW1ucnd3emtsanBnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTY2MDMxMiwiZXhwIjoyMDQxMjM2MzEyfQ.OdPPo8u0S-i-JooYU8O5uoppP0E6BSwQ1qMe8nGUtrs"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Convert dataframe to dictionary list
data_to_insert = data.to_dict(orient='records')
batch_size = 1000

for i in range(0, len(data_to_insert), batch_size):
    batch = data_to_insert[i:i + batch_size]
    response = supabase.table('sales').insert(batch).execute()
    print(f"Inserted batch {i // batch_size + 1}: {response}")
    print("------------------------------------------------")