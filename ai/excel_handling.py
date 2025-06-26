import pandas as pd

def excel_to_csv(excel_path, csv_path):
    # Read the first sheet of the Excel file
    df = pd.read_excel(excel_path)
    # Write to CSV
    df.to_csv(csv_path, index=False)

# Example usage
excel_to_csv('/Users/hashashin/Downloads/吉利30度载具0625/吉利30度图纸+BOM/载具30BOM-1-13-16.xlsx', 'output.csv')