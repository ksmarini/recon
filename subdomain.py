import sys
import socket
from time import strftime
from opensearchpy import OpenSearch

host = "localhost"
port = 9200

# Create the client with SSL/TLS and hostname verification disabled.
client = OpenSearch(
    hosts=[{"host": host, "port": port}],
    http_compress=True,  # enables gzip compression for request bodies
    use_ssl=False,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False,
)

target = sys.argv[1]
scanner = "assetfinder"
dic_assetfinder = {}


def post_dados():
    target = sys.argv[1]
    index_name = f"{target}-subdomain"
    scanner = "assetfinder"

    with open("/home/marini/pentest/pm.ro.gov.br/assetfinder.txt") as file:
        for line in file:
            dic_assetfinder["server.address"] = line.rstrip("\n")
            dic_assetfinder["server.domain"] = line.rstrip("\n")
            try:
                dic_assetfinder["server.ip"] = socket.gethostbyname(line.rstrip("\n"))
            except:
                dic_assetfinder["server.ip"] = "0.0.0.0"
            dic_assetfinder["vulnerability.scanner.vendor"] = scanner

            document = {
                "@timestamp": strftime("%Y-%m-%dT%H:%M:%S%Z"),
                "server.address": dic_assetfinder["server.address"],
                "server.domain": dic_assetfinder["server.domain"],
                "server.ip": dic_assetfinder["server.ip"],
                "vulnerability.scanner.vendor": dic_assetfinder[
                    "vulnerability.scanner.vendor"
                ],
            }

            response = client.index(
                index=index_name,
                body=document,
                # refresh=True,
            )
            print(response)


def main():
    post_dados()


if __name__ == "__main__":
    main()
