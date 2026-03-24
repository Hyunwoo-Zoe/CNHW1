import argparse
import os
import socket
import time

from config import CLIENT_IP, FILE_NAME, PORT, RESULT_FILE_NAME, SERVER_IP, SETTINGS, TCP_HEADER_TERMINATOR

def main() -> None:
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("--setting", type=int, choices=[1, 2], required=True)
    parsed_arguments = argument_parser.parse_args()

    setting_number = parsed_arguments.setting
    setting_values = SETTINGS[setting_number]

    send_delay = setting_values["send_delay"]
    chunk_size = setting_values["chunk_size"]
    receive_buffer_size = setting_values["recv_buffer_size"]

    if not os.path.exists(FILE_NAME):
        raise FileNotFoundError(f"{FILE_NAME} does not exist. Run make_sample.py first.")

    file_size_bytes = os.path.getsize(FILE_NAME)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.bind((CLIENT_IP, 0))
    client_socket.connect((SERVER_IP, PORT))

    print(f"[TCP CLIENT] Connected to {SERVER_IP}:{PORT}")
    print(f"[TCP CLIENT] Setting {setting_number}")
    print(f"[TCP CLIENT] Send delay: {send_delay:.3f} s")
    print(f"[TCP CLIENT] Chunk size: {chunk_size} bytes")

    header_line = f"START|{FILE_NAME}|{file_size_bytes}|{setting_number}|{chunk_size}{TCP_HEADER_TERMINATOR}"
    client_socket.sendall(header_line.encode("utf-8"))

    total_sent_bytes = 0
    transfer_start_time = None

    with open(FILE_NAME, "rb") as input_file:
        while True:
            file_chunk = input_file.read(chunk_size)
            if not file_chunk:
                break

            if transfer_start_time is None:
                transfer_start_time = time.perf_counter()

            client_socket.sendall(file_chunk)
            total_sent_bytes += len(file_chunk)

            if send_delay > 0:
                time.sleep(send_delay)

    result_message = client_socket.recv(receive_buffer_size).decode("utf-8")
    transfer_end_time = time.perf_counter()
    client_observed_send_time_seconds = 0.0 if transfer_start_time is None else transfer_end_time - transfer_start_time

    with open(RESULT_FILE_NAME, "w", encoding="utf-8") as result_file:
        result_file.write(result_message + "\n")

    print(f"[TCP CLIENT] Sent bytes: {total_sent_bytes}")
    print(f"[TCP CLIENT] Client observed send time: {client_observed_send_time_seconds:.6f} s")
    print(f"[TCP CLIENT] Received result: {result_message}")
    print(f"[TCP CLIENT] Saved result to {RESULT_FILE_NAME}")

    client_socket.close()

if __name__ == "__main__":
    main()