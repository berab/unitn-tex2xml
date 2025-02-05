import pandas as pd

def main(empty_file, in_file, out_file):
    in_df, out_df = pd.read_csv(in_file), pd.read_csv(empty_file)

    for _, row in in_df.iterrows():
        grade, studentid = row[r"Grade/15.00"], row["ID number"]
        out_df.loc[out_df["Matricola"] == studentid, "Written Exam"] = grade
    out_df = out_df.sort_values(by="Cognome")
    out_df.to_csv(out_file, index=False)  # Set index=True if you want to keep the index



if __name__== "__main__":
    in_file = "csv_files/145996-First Final Exam (03022025 - 1000 - 1130)-grades.csv"
    empty_file = "csv_files/Grades 2024-2025 - esse3-03_02_2025.csv"
    out_file = "csv_files/results.csv"
    main(empty_file, in_file, out_file)
