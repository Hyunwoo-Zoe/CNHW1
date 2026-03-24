import argparse
import os
import socket
import time

from config import PORT, SERVER_IP, SETTINGS, TCP_HEADER_TERMINATOR

def receive_exact_bytes(connection_socket: socket.socket, expected_byte_count: int, receive_buffer_size: int) -> bytes:
    received_chunks = []
    total_received_bytes = 0

    while total_received_bytes < expected_byte_count:
        remaining_bytes = expected_byte_count - total_received_bytes
        current_receive_size = min(receive_buffer_size, remaining_bytes)
        received_data = connection_socket.recv(current_receive_size)

        if not received_data:
            break

        received_chunks.append(received_data)
        total_received_bytes += len(received_data)

    return b"".join(received_chunks)

def receive_header_line(connection_socket: socket.socket, receive_buffer_size: int) -> tuple[str, bytes]:
    received_bytes = b""

    while TCP_HEADER_TERMINATOR.encode() not in received_bytes:
        current_chunk = connection_socket.recv(receive_buffer_size)
        if not current_chunk:
            break
        received_bytes += current_chunk

    header_bytes, remaining_bytes = received_bytes.split(TCP_HEADER_TERMINATOR.encode(), 1)
    return header_bytes.decode("utf-8"), remaining_bytes

def parse_tcp_header(header_line: str) -> dict:
    header_parts = header_line.strip().split("|")
    if len(header_parts) != 5 or header_parts[0] != "START":
        raise ValueError("Invalid TCP header format")

    return {
        "file_name": header_parts[1],
        "file_size_bytes": int(header_parts[2]),
        "setting_number": int(header_parts[3]),
        "chunk_size": int(header_parts[4]),
    }

def main() -> None:
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("--setting", type=int, choices=[1, 2], required=True)
    parsed_arguments = argument_parser.parse_args()

    setting_number = parsed_arguments.setting
    setting_values = SETTINGS[setting_number]

    receive_buffer_size = setting_values["recv_buffer_size"]
    processing_delay = setting_values["processing_delay"]

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, receive_buffer_size)
    server_socket.bind((SERVER_IP, PORT))
    server_socket.listen(1)

    print(f"[TCP SERVER] Listening on {SERVER_IP}:{PORT}")
    print(f"[TCP SERVER] Setting {setting_number}")
    print(f"[TCP SERVER] Receive buffer size: {receive_buffer_size} bytes")
    print(f"[TCP SERVER] Processing delay: {processing_delay:.3f} s")

    connection_socket, client_address = server_socket.accept()
    print(f"[TCP SERVER] Connected by {client_address}")

    try:
        header_line, remaining_payload_bytes = receive_header_line(connection_socket, receive_buffer_size)
        header_values = parse_tcp_header(header_line)

        file_name = header_values["file_name"]
        expected_file_size_bytes = header_values["file_size_bytes"]

        output_file_name = f"received_tcp_{file_name}"
        total_received_bytes = 0
        transfer_start_time = None

        with open(output_file_name, "wb") as output_file:
            if remaining_payload_bytes:
                if transfer_start_time is None:
                    transfer_start_time = time.perf_counter()
                if processing_delay > 0:
                    time.sleep(processing_delay)
                output_file.write(remaining_payload_bytes)
                total_received_bytes += len(remaining_payload_bytes)

            while total_received_bytes < expected_file_size_bytes:
                current_receive_size = min(receive_buffer_size, expected_file_size_bytes - total_received_bytes)
                received_data = connection_socket.recv(current_receive_size)

                if not received_data:
                    break

                if transfer_start_time is None:
                    transfer_start_time = time.perf_counter()

                if processing_delay > 0:
                    time.sleep(processing_delay)

                output_file.write(received_data)
                total_received_bytes += len(received_data)

        transfer_end_time = time.perf_counter()
        transfer_time_seconds = 0.0 if transfer_start_time is None else transfer_end_time - transfer_start_time
        throughput_bytes_per_second = 0.0 if transfer_time_seconds <= 0 else total_received_bytes / transfer_time_seconds

        result_message = (
            f"RESULT|OK|protocol=TCP|bytes={total_received_bytes}"
            f"|time={transfer_time_seconds:.6f}|throughput={throughput_bytes_per_second:.2f}"
        )

        connection_socket.sendall(result_message.encode("utf-8"))

        print(f"[TCP SERVER] File saved: {output_file_name}")
        print(f"[TCP SERVER] Total received bytes: {total_received_bytes}")
        print(f"[TCP SERVER] Transfer time: {transfer_time_seconds:.6f} s")
        print(f"[TCP SERVER] Throughput: {throughput_bytes_per_second:.2f} bytes/s")
        print(f"[TCP SERVER] Sent result: {result_message}")

    finally:
        connection_socket.close()
        server_socket.close()

if __name__ == "__main__":
    main()