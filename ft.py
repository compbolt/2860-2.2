#!/usr/bin/env python3
import argparse
import os
import socket
import struct
import sys
from typing import Tuple

#https://docs.python.org/3/library/socket.html#functions
#############
# Constants #
#############
DEFAULT_PORT = 9090
DEFAULT_IPV4_ADDRESS = '127.0.0.1'
DEFAULT_IPV6_ADDRESS = '::1'
DEFAULT_OUTDIR = './'
BUFSIZE = 64 * 1024
MAX_FILENAME_LEN = 4096

LINE_OK = b'OK\n'
LINE_ERR = b'ERR\n'

###############
# I/O helpers #
###############

def recv_line(sock: socket.socket, max_len: int = MAX_FILENAME_LEN) -> bytes:
    """Receive a single line terminated by '\n'.
    Returns the line including everything before '\n' (without '\n').
    Raises a ValueError if more data than max_len is received.
    """
    data = bytearray()

    while True:
        chunk = sock.recv(1)

        if chunk == b"\n":
            return bytes(data)
        if not chunk:
            raise ValueError("no data?")


        data.extend(chunk)
        if len(data) > max_len:
            raise ValueError("line too long!")
        


##########
# Server #
##########

def handle_client(cliCon: socket.socket, outdir: str) -> None:
    """Handle a single client:
    1) Read filepath and sanitise it.
    2) Check existence of <outdir>/<filename>-received
    3) Reply LINE_OK/LINE_ERR accordingly
    4) If LINE_OK, receive length and payload, write file, and send final LINE_OK.
    On any error, send LINE_ERR and return.
    """
    try:
        # Receive filename line (UTF-8).
        raw_line = recv_line(cliCon)
        try:
            filename = raw_line.decode('utf-8')
        except UnicodeDecodeError:
            # Send LINE_ERR if filename is not valid UTF-8.
            # tODO: write your code here.
            cliCon.sendall(LINE_ERR)
            return

        # Sanitize filename (strip directory components).
        filename = os.path.basename(filename)
        if filename == '':
            # Send LINE_ERR if invalid filename.
            # tODO: write your code here.
            cliCon.sendall(LINE_ERR)
            return

        # Prepare output path.
        os.makedirs(outdir, exist_ok=True)
        dest_path = os.path.join(outdir, f"{filename}-received")

        # Check if file already exists.
        if os.path.exists(dest_path):
            # Send LINE_ERR if file exists.
            # ToDO: write your code here.
            cliCon.sendall(LINE_ERR)
            return
        else:
            # Send LINE_OK to proceed.
            # TOdO: write your code here.
            cliCon.sendall(LINE_OK)

        # Receive 8-byte unsigned integer (network byte order).
        hdr = bytearray()
        # TODo: write your code here.
        while len(hdr) != 8:
            chunk = cliCon.recv( 8 - len(hdr))
            if not chunk:
                raise ValueError("no data!")
            hdr.extend(chunk)


        (file_size,) = struct.unpack('!Q', hdr)

        # Receive exactly file_size bytes and write to destination.
        remaining = file_size
        try:
            with open(dest_path, 'wb') as f:
                while remaining > 0:
                    # Receive a chunk (up to BUFSIZE or remaining). (min of buf or remain)
                    # TOdO: write your code here.

                    chunk = cliCon.recv(min(BUFSIZE, remaining)) 
                    if not chunk:
                        raise ValueError("no data!")
                    f.write(chunk)
                    remaining -= len(chunk)
                f.flush()
        except Exception:
            # On failure, try to remove partial file.
            try:
                if os.path.exists(dest_path):
                    os.remove(dest_path)
            except Exception:
                pass
            raise

        # Send final LINE_OK to acknowledge successful receipt.
        # tODO: write your code here.
        cliCon.sendall(LINE_OK)


    except Exception:
        # Swallow exceptions to keep server alive; optionally could log
        try:
            # Best-effort negative acknowledgement if we failed before final OK
            pass
        except Exception:
            pass
        return


def run_server(port: int, outdir: str, ipv6: bool) -> None:
    """Start the TCP file transfer server."""
    family = socket.AF_INET6 if ipv6 else socket.AF_INET
    bind_addr = '::' if ipv6 else '0.0.0.0'
    # Create server socket, bind, listen, and accept in an infinite loop.
    # ToDO: write your code here.

    servSock = socket.socket(family, socket.SOCK_STREAM)
    servSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servSock.bind((bind_addr, port))
    servSock.listen(5)

    while True:
        cliCon, cliaddr = servSock.accept()
        handle_client(cliCon, outdir)
        cliCon.close()


##########
# Client #
##########

def run_client(server_ip: str, port: int, file_path: str, ipv6: bool) -> int:
    """Establish cliConection to server and send the specified file."""
    # Resolve filename and size.
    if not os.path.isfile(file_path):
        print(f"Not a file: {file_path}", file=sys.stderr)
        return 2
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    family = socket.AF_INET6 if ipv6 else socket.AF_INET
    cliaddr = (server_ip, port, 0, 0) if ipv6 else (server_ip, port)

    # Send filename, size, and file content (in chunks).
    # Wait for server responses according to protocol.
    # TODoO: write your code here.
    try:
        cliSock = socket.socket(family, socket.SOCK_STREAM)
        cliSock.conect(cliaddr)

        cliSock.sendall(filename.encode("utf-8") + b"\n")
        resp1 = recv_line(cliSock)
        if resp1 != b'OK':
            cliSock.close()
            return 1
        cliSock.sendall(struct.pack('!Q', file_size))

        with open(file_path, 'rb') as f:
            while chunk := f.read(BUFSIZE):
                cliSock.sendall(chunk)

        lastResp = recv_line(cliSock)
        cliSock.close()

        if lastResp == b'OK':
            return 0
        else:
            return 255
        

    except Exception:
        return 255
    







################
# Main program #
################

def parse_args(argv=None) -> argparse.Namespace:
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(description='TCP file transfer (client/server)')
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--server', action='store_true', help='Run in server mode')
    mode.add_argument('--client', action='store_true', help='Run in client mode (default)')

    p.add_argument('--port', type=int, default=DEFAULT_PORT, help='TCP port (default: 9090)')
    p.add_argument('--outdir', default=DEFAULT_OUTDIR, help='Server: output directory (default: ./)')
    p.add_argument('--connect', dest='server_ip', default=None,
                   help='Client: server IPv4/IPv6 address (default: 127.0.0.1 or ::1 with --ipv6).')
    p.add_argument('--file', dest='file_path', help='Client: path to the file to send (no default).')
    p.add_argument('--ipv6', action='store_true', help='Use IPv6 sockets.')
    return p.parse_args(argv)

def main(argv=None) -> int:
    """Main program entry point."""

    args = parse_args(argv)

    # Run in server mode if --server is specified.
    if args.server:
        outdir = args.outdir
        run_server(args.port, outdir, ipv6=args.ipv6)
        return 0

    # Default to client if neither --server nor --client are specified.
    server_ip = args.server_ip
    if server_ip is None:
        server_ip = DEFAULT_IPV6_ADDRESS if args.ipv6 else DEFAULT_IPV4_ADDRESS

    if not args.file_path:
        print('Client mode requires --file <path>', file=sys.stderr)
        return 2

    rc = run_client(server_ip, args.port, args.file_path, ipv6=args.ipv6)
    return rc

if __name__ == '__main__':
    sys.exit(main())
