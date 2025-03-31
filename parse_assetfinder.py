dic_assetfinder = {}


def parser():
    with open("/home/marini/pentest/pm.ro.gov.br/assetfinder.txt") as file:
        for line in file:
            dic_assetfinder["sub_domain"] = line.rstrip("\n")
            print(dic_assetfinder)


def main():
    parser()


if __name__ == "__main__":
    main()
