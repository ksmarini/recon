# import sys
# import string
import json

dic_subfinder = {}


def parser():
    with open("/home/marini/pentest/pm.ro.gov.br/subfinder-json.json") as json_file:
        for line in json_file:
            json_line = line.rstrip("\n")
            json_data = json.loads(json_line)
            dic_subfinder["sub_domain"] = json_data["host"]
            dic_subfinder["source"] = json_data["source"]
            print(dic_subfinder)


def main():
    parser()


if __name__ == "__main__":
    main()
