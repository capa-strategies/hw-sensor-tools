import os
import argparse
from utils import process_file, process_folder

def main():
    parser = argparse.ArgumentParser(description="Process Heatwatch CSV file(s).")
    parser.add_argument('--input_files', required=True, help="Input CSV file or folder path")
    parser.add_argument('--output_folder', default='formatted', help="Output folder path (optional)")
    parser.add_argument('--ogr_driver', help="File format for export: CSV, GeoJSON, or GPKG (optional, defaults to CSV)")
    parser.add_argument('--convert_tz', action='store_true', help="Convert to local timezone or leave in UTC (optional, defaults to UTC)")
    parser.add_argument('--convert_imperial', action='store_true', help="Convert to imperial units or leave in metric (optional, defaults to leaving in metric)")
    parser.add_argument('--merge_files', action='store_true', help="Merge all CSV files in folder into a single output file (optional, only applies to folder input)")
    
    args = parser.parse_args()
    
    input_path = args.input_files
    output_dir = args.output_folder
    convert_tz = args.convert_tz
    unit_convert = args.convert_imperial
    driver = args.ogr_driver
    merge_files = args.merge_files

    if os.path.isdir(input_path):
        # Check if output_dir is relative (no root)outp
        if not os.path.isabs(output_dir):
            # Make output_dir relative to input_path folder
            output_dir = os.path.join(input_path, output_dir)

    print(driver)
    if os.path.isdir(input_path):
        process_folder(input_path, output_dir, convert_tz, unit_convert, driver, merge_files)
    elif os.path.isfile(input_path):
        if merge_files:
            print("Warning: --merge_files option ignored for single file input")
        process_file(input_path, output_dir, convert_tz, unit_convert, driver)
    else:
        print("Input path is neither a file nor a folder. Please check.")

if __name__ == "__main__":
    main()

