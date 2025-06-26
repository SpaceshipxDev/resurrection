import pandas as pd

def excel_to_csv(excel_path, csv_path):
    # Read the first sheet of the Excel file
    df = pd.read_excel(excel_path)
    # Write to CSV
    df.to_csv(csv_path, index=False)

# Example usage
excel_to_csv('input.xlsx', 'output.csv')