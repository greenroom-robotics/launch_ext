import psutil
import socket
from launch.substitution import Substitution
import launch.logging


class ResolveHost(Substitution):
    def __init__(self, host: str):
        self.__host = host
        self.__logger = launch.logging.get_logger("launch.user")

    def perform(self, context):
        # Note this only works for IPv4 addresses
        interfaces = psutil.net_if_addrs()
        ip = None
        if self.__host in interfaces:
            for iface in interfaces[self.__host]:
                if iface.family == socket.AF_INET:
                    ip = iface.address
                    break

        if ip is None:
            try:
                ip = socket.getaddrinfo(self.__host, None, socket.AF_INET)[0][4][0]
            except socket.gaierror as e:
                self.__logger.warn(f"Failed to resolve host '{self.__host}': {e}")

        self.__logger.info(f"Resolved {self.__host} to {ip}")
        return ip

    def describe(self):
        return f"ResolveHost(interface={self.__host})"

    def describe_condition(self, condition):
        return self.describe()
