import pandas as pd
import os

path = "data/sap-order-to-cash-dataset/sap-o2c-data/billing_document_items/"

files = os.listdir(path)
df = pd.read_json(path + files[0], lines=True)

print(df.columns)
print(df.head(2))