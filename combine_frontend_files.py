import os

def combine_files(base_path, file_list, output_file):
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for file_path in file_list:
            full_path = os.path.join(base_path, file_path)
            outfile.write(f"\n\n# File: {file_path}\n")
            try:
                with open(full_path, 'r', encoding='utf-8') as infile:
                    outfile.write(infile.read())
            except FileNotFoundError:
                outfile.write(f"# Error: File not found - {file_path}\n")

base_path = "analytics-dashboard/src"
files_to_combine = [
    "components/analytics/UserActivity.tsx",
    "components/common/DateRangeSelector.tsx",
    "components/dashboard/Dashboard.tsx",
    "components/layout/Layout.tsx",
    "components/layout/Navbar.tsx",
    "components/layout/Sidebar.tsx",
    "components/metrics/MetricCard.tsx",
    "components/metrics/MetricGrid.tsx",
    "components/users/UserTable.tsx",
    "services/metricService.ts",
    "types/metrics.ts",
    "utils/App.tsx"
]

output_file = "combined_frontend_files.txt"

combine_files(base_path, files_to_combine, output_file)
print(f"Files combined successfully into {output_file}")