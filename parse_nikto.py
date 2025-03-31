import xml.etree.ElementTree as ET


dic_nikto = {}


tree = ET.parse("/home/marini/pentest/pm.ro.gov.br/nikto.xml")
root = tree.getroot()


def parse_xml():
    for i in root.iter("scandetails"):
        dic_nikto["targetip"] = i.attrib["targetip"]
        dic_nikto["targethostname"] = i.attrib["targethostname"]
        dic_nikto["url_original"] = i.attrib["sitename"]
        dic_nikto["targetport"] = i.attrib["targetport"]
        dic_nikto["protocol"] = i.attrib["sitename"].split(":")[0]
        for scan in i:
            if scan.tag == "item":
                for item in scan:
                    if item.tag == "description":
                        dic_nikto["vuln_description"] = item.text
                    if item.tag == "uri":
                        dic_nikto["uri"] = item.text
                    if item.tag == "namelink":
                        dic_nikto["url_full"] = item.text
                print(dic_nikto)


def main():
    parse_xml()


if __name__ == "__main__":
    main()
