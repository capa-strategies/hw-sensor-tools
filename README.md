# hw-sensor-tools
 Python script for formatting CAPA Strategies Heat Watch Sensor Files. Basic usage is shown below. Accepts both individual files or folders of files. 

```
usage: hw-file-format.py [-h] --input_files INPUT_FILES [--output_folder OUTPUT_FOLDER]
                         [--ogr_driver OGR_DRIVER] [--convert_tz] [--convert_imperial]

Process Heatwatch CSV file(s).

options:
  -h, --help            show this help message and exit
  --input_files INPUT_FILES
                        Input CSV file or folder path
  --output_folder OUTPUT_FOLDER
                        Output folder path (optional, defaults to a 'formatted' folder)
  --ogr_driver OGR_DRIVER
                        File format for export: CSV, GeoJSON, or Geopackage (optional, defaults to CSV)
  --convert_tz          Convert to local timezone or leave in UTC (optional, defaults to UTC)
  --convert_imperial    Convert to imperial units or leave in metric (optional, defaults to leaving in metric)
```
