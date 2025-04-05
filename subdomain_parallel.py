#!/usr/bin/env python3
import sys
import os


target = sys.argv[1]
domain = sys.argv[2]


def parallel():
    os.system("rm -rf /docker/recon/data/" + target + "/temp/subdomain_parallel.log")
    with open(
        "/docker/recon/data/" + target + "/temp/subdomain_parallel.log", "a"
    ) as file:
        file.write(
            "python /home/marini/fontes/python/recon/auto_assetfinder.py "
            + target
            + " "
            + domain
            + "\n"
        )
        file.write(
            "python /home/marini/fontes/python/recon/auto_subfinder.py "
            + target
            + " "
            + domain
            + "\n"
        )
        file.write(
            "python /home/marini/fontes/python/recon/auto_sublist3r.py "
            + target
            + " "
            + domain
            + "\n"
        )
    print("[+] Processando subdomain \n")
    os.system(
        "cat /docker/recon/data/"
        + target
        + "/temp/subdomain_parallel.log | parallel -u"
    )


def main():
    parallel()


if __name__ == "__main__":
    main()
