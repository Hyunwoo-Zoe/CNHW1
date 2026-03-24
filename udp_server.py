import argparse
import socket
import time

from config import PORT, SERVER_IP, SETTINGS, UDP_DATA_PREFIX, UDP_END_PREFIX, UDP_RESULT_PREFIX, UDP_START_PREFIX

def parse_start_message(message_text: str) -> dict:
    message_parts = message_text.strip().split("|")
    if len(message_parts) != 5 or message_parts[0] != UDP_START_PREFIX:
        raise ValueError("Invalid UDP START message")

    return {
        "file_name": message_parts[1],
        "file_size_bytes": int(message_parts[2]),
        "setting_number": int(message_parts[3]),
        "total_chunks": int(message_parts[4]),
    }

def parse_data_packet(packet_bytes: bytes) -> tuple[int, bytes]:
    separator_index = packet_bytes.find(b"|")
    if separator_index == -1:
        raise ValueError("Invalid UDP DATA packet: missing sequence separator")

    prefix_and_sequence = packet_bytes[:separator_index].decode("utf-8")
    payload_bytes = packet_bytes[separator_index + 1:]

    prefix_parts = prefix_and_sequence.split(":")
    if len(prefix_parts) != 2 or prefix_parts[0] != UDP_DATA_PREFIX:
        raise ValueError("Invalid UDP DATA packet prefix")

    sequence_number = int(prefix_parts[1])
    return sequence_number, payload_bytes

def main() -> None:
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("--setting", type=int, choices=[1, 2], required=True)
    parsed_arguments = argument_parser.parse_args()

    setting_number = parsed_arguments.setting
    setting_values = SETTINGS[setting_number]

    receive_buffer_size = setting_values["recv_buffer_size"]
    processing_delay = setting_values["processing_delay"]
    timeout_seconds = setting_values["timeout"]

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, receive_buffer_size)
    server_socket.bind((SERVER_IP, PORT))
    server_socket.settimeout(timeout_seconds)

    print(f"[UDP SERVER] Listening on {SERVER_IP}:{PORT}")
    print(f"[UDP SERVER] Setting {setting_number}")
    print(f"[UDP SERVER] Receive buffer size: {receive_buffer_size} bytes")
    print(f"[UDP SERVER] Processing delay: {processing_delay:.3f} s")
    print(f"[UDP SERVER] Timeout: {timeout_seconds:.3f} s")

    expected_file_name = None
    expected_file_size_bytes = None
    expected_total_chunks = None
    client_address = None
    transfer_start_time = None
    transfer_end_time = None
    received_chunk_map = {}

    output_file_name = None

    try:
        while True:
            try:
                received_packet, sender_address = server_socket.recvfrom(65535)
            except socket.timeout:
                print("[UDP SERVER] Timeout waiting for more UDP datagrams")
                break

            if client_address is None:
                client_address = sender_address
            elif sender_address != client_address:
                print(f"[UDP SERVER] Ignored packet from unknown sender: {sender_address}")
                continue

            if received_packet.startswith(f"{UDP_START_PREFIX}|".encode("utf-8")):
                start_message = received_packet.decode("utf-8")
                start_values = parse_start_message(start_message)
                expected_file_name = start_values["file_name"]
                expected_file_size_bytes = start_values["file_size_bytes"]
                expected_total_chunks = start_values["total_chunks"]
                output_file_name = f"received_udp_{expected_file_name}"
                received_chunk_map = {}
                transfer_start_time = None
                transfer_end_time = None

                print(f"[UDP SERVER] START received")
                print(f"[UDP SERVER] File name: {expected_file_name}")
                print(f"[UDP SERVER] Expected bytes: {expected_file_size_bytes}")
                print(f"[UDP SERVER] Expected chunks: {expected_total_chunks}")
                continue

            if received_packet.startswith(f"{UDP_END_PREFIX}|".encode("utf-8")):
                transfer_end_time = time.perf_counter()
                print("[UDP SERVER] END received")
                break

            if received_packet.startswith(f"{UDP_DATA_PREFIX}:".encode("utf-8")):
                if transfer_start_time is None:
                    transfer_start_time = time.perf_counter()

                sequence_number, payload_bytes = parse_data_packet(received_packet)

                if processing_delay > 0:
                    time.sleep(processing_delay)

                if sequence_number not in received_chunk_map:
                    received_chunk_map[sequence_number] = payload_bytes

                continue

        if transfer_end_time is None:
            transfer_end_time = time.perf_counter()

        total_received_chunks = len(received_chunk_map)
        total_received_bytes = sum(len(payload_bytes) for payload_bytes in received_chunk_map.values())
        transfer_time_seconds = 0.0 if transfer_start_time is None else transfer_end_time - transfer_start_time
        throughput_bytes_per_second = 0.0 if transfer_time_seconds <= 0 else total_received_bytes / transfer_time_seconds

        status_text = "INCOMPLETE"
        missing_sequence_numbers = []

        if expected_total_chunks is not None:
            missing_sequence_numbers = [
                sequence_number
                for sequence_number in range(expected_total_chunks)
                if sequence_number not in received_chunk_map
            ]
            if len(missing_sequence_numbers) == 0:
                status_text = "OK"

        if output_file_name is not None:
            with open(output_file_name, "wb") as output_file:
                for sequence_number in sorted(received_chunk_map.keys()):
                    output_file.write(received_chunk_map[sequence_number])

        result_message = (
            f"{UDP_RESULT_PREFIX}|{status_text}|protocol=UDP|bytes={total_received_bytes}"
            f"|chunks={total_received_chunks}/{expected_total_chunks if expected_total_chunks is not None else 0}"
            f"|time={transfer_time_seconds:.6f}|throughput={throughput_bytes_per_second:.2f}"
        )

        if missing_sequence_numbers:
            preview_missing_sequence_numbers = ",".join(str(number) for number in missing_sequence_numbers[:20])
            if len(missing_sequence_numbers) > 20:
                preview_missing_sequence_numbers += ",..."
            result_message += f"|missing={preview_missing_sequence_numbers}"

        if client_address is not None:
            server_socket.sendto(result_message.encode("utf-8"), client_address)

        print(f"[UDP SERVER] File saved: {output_file_name}")
        print(f"[UDP SERVER] Received chunks: {total_received_chunks}/{expected_total_chunks}")
        print(f"[UDP SERVER] Total received bytes: {total_received_bytes}")
        print(f"[UDP SERVER] Transfer time: {transfer_time_seconds:.6f} s")
        print(f"[UDP SERVER] Throughput: {throughput_bytes_per_second:.2f} bytes/s")
        print(f"[UDP SERVER] Sent result: {result_message}")

    finally:
        server_socket.close()

if __name__ == "__main__":
    main()