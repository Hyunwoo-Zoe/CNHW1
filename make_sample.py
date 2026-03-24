import os
from config import FILE_NAME

TARGET_FILE_SIZE_BYTES = 3 * 1024 * 1024

def create_sample_file(file_name: str, target_size_bytes: int) -> None:
    current_line_number = 1
    total_written_bytes = 0

    with open(file_name, "w", encoding="utf-8") as sample_file:
        while total_written_bytes < target_size_bytes:
            line_text = (
                f"Line {current_line_number:06d}: "
                f"This is a sample line for the client-server file transfer experiment. "
                f"It is used to measure transfer time, total received bytes, and throughput.\n"
            )
            encoded_line = line_text.encode("utf-8")
            sample_file.write(line_text)
            total_written_bytes += len(encoded_line)
            current_line_number += 1

def main() -> None:
    create_sample_file(FILE_NAME, TARGET_FILE_SIZE_BYTES)
    actual_file_size_bytes = os.path.getsize(FILE_NAME)
    print(f"Created {FILE_NAME}")
    print(f"File size: {actual_file_size_bytes} bytes")

if __name__ == "__main__":
    main()