SERVER_IP = "115.145.179.130"
CLIENT_IP = "115.145.179.236"
PORT = 5000

FILE_NAME = "sample.txt"
RESULT_FILE_NAME = "result.txt"

SETTINGS = {
    1: {
        "send_delay": 0.005,
        "chunk_size": 512,
        "processing_delay": 0.0,
        "recv_buffer_size": 65536,
        "timeout": 2.0,
    },
    2: {
        "send_delay": 0.0,
        "chunk_size": 256,
        "processing_delay": 0.002,
        "recv_buffer_size": 8192,
        "timeout": 2.0,
    },
}

TCP_HEADER_TERMINATOR = "\n"
UDP_START_PREFIX = "START"
UDP_END_PREFIX = "END"
UDP_RESULT_PREFIX = "RESULT"
UDP_DATA_PREFIX = "DATA"

UDP_MAX_DATAGRAM_SIZE = 65507
UDP_END_WAIT_SECONDS = 0.5