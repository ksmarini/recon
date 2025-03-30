dic_sublist3r = {}


def parser():
    with open("/home/marini/pentest/pm.ro.gov.br/sublist3r.txt") as file:
        for line in file:
            dic_sublist3r["sub_domain"] = line.rstrip("\n")
            print(dic_sublist3r)


def main():
    parser()


if __name__ == "__main__":
    main()
