import logging
import socket

# Constants
IP_UTILS_FLAG = ","
UNKNOWN = "unknown"
LOCALHOST_IP = "0:0:0:0:0:0:0:1"
LOCALHOST_IP1 = "127.0.0.1"

# Logger setup
logger = logging.getLogger(__name__)


def get_port(request):
    return str(request.environ.get('REMOTE_PORT'))


def get_ip_addr(request):
    ip = None
    try:
        ip = request.headers.get("X-Original-Forwarded-For")
        if not ip or ip.lower() == UNKNOWN:
            ip = request.headers.get("X-Forwarded-For")
        if not ip or ip.lower() == UNKNOWN:
            ip = request.headers.get("x-forwarded-for")
        if not ip or ip.lower() == UNKNOWN:
            ip = request.headers.get("Proxy-Client-IP")
        if not ip or ip.lower() == UNKNOWN:
            ip = request.headers.get("WL-Proxy-Client-IP")
        if not ip or ip.lower() == UNKNOWN:
            ip = request.headers.get("HTTP_CLIENT_IP")
        if not ip or ip.lower() == UNKNOWN:
            ip = request.headers.get("HTTP_X_FORWARDED_FOR")
        if not ip or ip.lower() == UNKNOWN:
            ip = request.remote_addr
            if ip in [LOCALHOST_IP1, LOCALHOST_IP]:
                try:
                    ip = socket.gethostbyname(socket.gethostname())
                except socket.error as e:
                    logger.error(f"getClientIp error: {e}")
    except Exception as e:
        logger.error(f"IPUtils ERROR {e}")

    if ip and IP_UTILS_FLAG in ip:
        ip = ip.split(IP_UTILS_FLAG)[0]

    return ip
