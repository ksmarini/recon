dic_httprobe = {}


def parse():
    with open("/home/marini/pentest/pm.ro.gov.br/httprobe.txt") as file:
        for i in file:
            dic_httprobe["url_original"] = i.rstrip("\n")
            dic_httprobe["protocolo"] = i.rstrip("\n").split(":")[0]
            print(dic_httprobe)


def main():
    parse()


if __name__ == "__main__":
    main()
