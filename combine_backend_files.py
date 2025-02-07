import os

def read_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return f"\n\n# File: {file_path}\n\n" + file.read()
    except FileNotFoundError:
        return f"\n\n# File: {file_path}\n\n# Error: File not found"
    except Exception as e:
        return f"\n\n# File: {file_path}\n\n# Error: {str(e)}"

def combine_files():
    base_path = "dashboardbackend"
    files_to_combine = [
        "src/services/analytics_service.py",
        "src/services/metrics_service.py",
        "src/services/historical_data_service.py",
        "src/services/descope_service.py",
        "src/services/caching_service.py",
        "src/services/opensearch_service.py",
        "src/utils/query_builder.py",
        "src/api/metrics.py",
        "src/core/__init__.py",
        "tests/test_analytics_service.py",
        "requirements.txt",
        "run.py"
    ]

    combined_content = "# Combined Backend Files\n\n"

    for file_path in files_to_combine:
        full_path = os.path.join(base_path, file_path)
        combined_content += read_file(full_path)

    with open("combined_backend_files.txt", "w", encoding="utf-8") as output_file:
        output_file.write(combined_content)

    print("Files combined successfully. Output: combined_backend_files.txt")

if __name__ == "__main__":
    combine_files()