import argparse
import os
import socket
import time

from config import CLIENT_IP, FILE_NAME, PORT, RESULT_FILE_NAME, SERVER_IP, SETTINGS, UDP_DATA_PREFIX, UDP_END_PREFIX, UDP_START_PREFIX

def main() -> None:
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("--setting", type=int, choices=[1, 2], required=True)
    parsed_arguments = argument_parser.parse_args()

    setting_number = parsed_arguments.setting
    setting_values = SETTINGS[setting_number]

    send_delay = setting_values["send_delay"]
    chunk_size = setting_values["chunk_size"]
    timeout_seconds = setting_values["timeout"]

    if not os.path.exists(FILE_NAME):
        raise FileNotFoundError(f"{FILE_NAME} does not exist. Run make_sample.py first.")

    file_size_bytes = os.path.getsize(FILE_NAME)
    total_chunks = (file_size_bytes + chunk_size - 1) // chunk_size

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind((CLIENT_IP, 0))
    client_socket.settimeout(timeout_seconds + 3.0)

    print(f"[UDP CLIENT] Sending to {SERVER_IP}:{PORT}")
    print(f"[UDP CLIENT] Setting {setting_number}")
    print(f"[UDP CLIENT] Send delay: {send_delay:.3f} s")
    print(f"[UDP CLIENT] Chunk size: {chunk_size} bytes")
    print(f"[UDP CLIENT] Total chunks: {total_chunks}")

    start_message = f"{UDP_START_PREFIX}|{FILE_NAME}|{file_size_bytes}|{setting_number}|{total_chunks}"
    client_socket.sendto(start_message.encode("utf-8"), (SERVER_IP, PORT))

    total_sent_bytes = 0
    transfer_start_time = None

    with open(FILE_NAME, "rb") as input_file:
        sequence_number = 0

        while True:
            payload_bytes = input_file.read(chunk_size)
            if not payload_bytes:
                break

            if transfer_start_time is None:
                transfer_start_time = time.perf_counter()

            packet_prefix = f"{UDP_DATA_PREFIX}:{sequence_number}|".encode("utf-8")
            packet_bytes = packet_prefix + payload_bytes
            client_socket.sendto(packet_bytes, (SERVER_IP, PORT))

            total_sent_bytes += len(payload_bytes)
            sequence_number += 1

            if send_delay > 0:
                time.sleep(send_delay)

    end_message = f"{UDP_END_PREFIX}|done"
    client_socket.sendto(end_message.encode("utf-8"), (SERVER_IP, PORT))

    try:
        result_message, _ = client_socket.recvfrom(65535)
        decoded_result_message = result_message.decode("utf-8")
    except socket.timeout:
        decoded_result_message = "RESULT|NO_RESPONSE|protocol=UDP|bytes=0|time=0.000000|throughput=0.00"

    transfer_end_time = time.perf_counter()
    client_observed_send_time_seconds = 0.0 if transfer_start_time is None else transfer_end_time - transfer_start_time

    with open(RESULT_FILE_NAME, "w", encoding="utf-8") as result_file:
        result_file.write(decoded_result_message + "\n")

    print(f"[UDP CLIENT] Sent bytes: {total_sent_bytes}")
    print(f"[UDP CLIENT] Client observed send time: {client_observed_send_time_seconds:.6f} s")
    print(f"[UDP CLIENT] Received result: {decoded_result_message}")
    print(f"[UDP CLIENT] Saved result to {RESULT_FILE_NAME}")

    client_socket.close()

if __name__ == "__main__":
    main()