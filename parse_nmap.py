from unicodedata import name
import xml.etree.ElementTree as ET


dic_nmap = {}


tree = ET.parse("/home/marini/pentest/pm.ro.gov.br/nmap.xml")
root = tree.getroot()


def parse_xml():
    for i in root.iter("nmaprun"):
        for nmaprun in i:
            if nmaprun.tag == "host":
                for host in nmaprun:
                    if host.tag == "address":
                        if ":" not in host.attrib["addr"]:
                            dic_nmap["ipv4"] = host.attrib["addr"]
                            dic_nmap["addrtype"] = host.attrib["addrtype"]
                    if host.tag == "ports":
                        for port in host:
                            if port.tag == "port":
                                dic_nmap["protocol"] = port.attrib["protocol"]
                                dic_nmap["portid"] = port.attrib["portid"]
                                for itens in port:
                                    if itens.tag == "state":
                                        dic_nmap["state"] = itens.attrib["state"]
                                    if itens.tag == "service":
                                        try:
                                            dic_nmap["name"] = itens.attrib["name"]
                                        except:
                                            dic_nmap["name"] = ""
                                        try:
                                            dic_nmap["version"] = itens.attrib[
                                                "version"
                                            ]
                                        except:
                                            dic_nmap["version"] = ""
                                        try:
                                            dic_nmap["product"] = itens.attrib[
                                                "product"
                                            ]
                                        except:
                                            dic_nmap["product"] = ""
                                        try:
                                            dic_nmap["cpe"] = itens.attrib["cpe"]
                                        except:
                                            dic_nmap["cpe"] = ""
                                        print(dic_nmap)


def main():
    parse_xml()


if __name__ == "__main__":
    main()
