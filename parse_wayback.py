dic_wayback = {}


def parser():
    with open("/home/marini/pentest/pm.ro.gov.br/wayback.txt") as file:
        for line in file:
            dic_wayback["urlfull"] = line.rstrip("\n")
            dic_wayback["protocol"] = line.rstrip("\n").split(":")[0]
            print(dic_wayback)


def main():
    parser()


if __name__ == "__main__":
    main()
