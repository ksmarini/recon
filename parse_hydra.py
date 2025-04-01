import json

dic_hydra = {}


def parse():
    with open("/home/marini/pentest/pm.ro.gov.br/hydra.json") as json_file:
        jsondata = json.load(json_file)
        for i in jsondata["results"]:
            dic_hydra["port"] = i["port"]
            dic_hydra["service"] = i["service"]
            dic_hydra["host"] = i["host"]
            dic_hydra["login"] = i["login"]
            dic_hydra["password"] = i["password"]
            print(dic_hydra)


def main():
    parse()


if __name__ == "__main__":
    main()
