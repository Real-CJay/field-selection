import re
import pandas as pd

def flatten_csv_results(input_file, output_file, subject_column_name):
    # 1. Read the entire CSV file as a single string of text
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    # 2. Define what an Index and a Grade look like, allowing for CSV quotes
    index_regex = r'"?\d{6}[A-Z]"?'
    grade_regex = r'"?(?:A\+|A\-|A|B\+|B\-|B|C\+|C\-|C|D|F|I-we|I-ca)"?'
    
    # 3. Match pairs even if they are separated by commas, spaces, or pipes
    pattern = rf'({index_regex})\s*[,\|]?\s*({grade_regex})|({grade_regex})\s*[,\|]?\s*({index_regex})'
    
    matches = re.findall(pattern, raw_text)
    
    # 4. Standard GPA conversion map
    gpa_scale = {
        'A+': 4.0, 'A': 4.0, 'A-': 3.7,
        'B+': 3.3, 'B': 3.0, 'B-': 2.7,
        'C+': 2.3, 'C': 2.0, 'C-': 1.5,
        'D': 1.0, 'F': 0.0, 'I-we': 0.0, 'I-ca': 0.0
    }

    extracted_data = []
    
    # 5. Clean up the matches and convert to decimals
    for match in matches:
        if match[0]: 
            index_num, letter_grade = match[0], match[1]
        else:
            letter_grade, index_num = match[2], match[3]
            
        # Strip any quotes that might have come from the CSV formatting
        index_num = index_num.replace('"', '').strip()
        letter_grade = letter_grade.replace('"', '').strip()
            
        extracted_data.append({
            "index_number": index_num,
            subject_column_name: gpa_scale.get(letter_grade, 0.0) 
        })

    # 6. Save to a clean, vertical CSV ready for Supabase
    df = pd.DataFrame(extracted_data)
    df.drop_duplicates(subset=['index_number'], inplace=True) 
    
    # Sort alphabetically by index number for a cleaner file
    df.sort_values(by='index_number', inplace=True)
    
    df.to_csv(output_file, index=False)
    
    print(f"✅ Successfully flattened {len(df)} grades!")
    print(f"📁 Saved to: {output_file}")
    print("\nPreview:")
    print(df.head(10).to_string())

if __name__ == "__main__":
    # Point this to your specific CS1033 CSV file
    input_csv = r"E:\kajaram\University\Project\Fieldselection\Field_selection\Field selection data\Results\MT1023_Intake 2025_Semester 1_student_view1.csv"
    output_csv = r"E:\kajaram\University\Project\Fieldselection\Field_selection\Field selection data\Results\Mt_results_supabase_ready.csv"
    
    # Change "cse" if this is for a different subject!
    flatten_csv_results(input_csv, output_csv, "MT")