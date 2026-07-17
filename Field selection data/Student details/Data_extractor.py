import pandas as pd

import sys
import os

# Check if a file was provided as an argument, otherwise default to "E1 .csv"
script_dir = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    file_path = sys.argv[1]
else:
    file_path = os.path.join(script_dir, "E9 .csv")

# Read the CSV file skipping the metadata rows
try:
    df = pd.read_csv(file_path, skiprows=5)
    
    # Keep only the requested columns
    columns_to_keep = ['Registration_No', 'Name_With_Initials', 'Personal_Email']
    extracted_df = df[columns_to_keep].copy()
    
    # Rename columns to match user's request
    extracted_df.rename(columns={
        'Registration_No': 'Index Number',
        'Name_With_Initials': 'Name',
        'Personal_Email': 'Email Address'
    }, inplace=True)
    
    # Save the cleaned data to a new CSV file
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_filename = os.path.join(os.path.dirname(os.path.abspath(file_path)), f"extracted_{base_name.strip()}.csv")
    extracted_df.to_csv(output_filename, index=False)
    
    print(f"Successfully extracted {len(extracted_df)} records from {file_path}.")
    print(f"Saved to: {output_filename}\n")
    print("Preview of the data:")
    print(extracted_df.head(10).to_string())

except Exception as e:
    print(f"Error processing the file: {e}")