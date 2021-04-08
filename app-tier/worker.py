import requests
from pprint import pprint
from bs4 import BeautifulSoup
import re
import json
from tqdm import tqdm


def work_on_jobs(URL):
    # link to faculty page
    # TODO: Make it input
    # URL = "https://cidse.engineering.asu.edu/faculty/"
    page = requests.get(URL, verify=False)
    soup = BeautifulSoup(page.content, "html.parser")

    # getting all divs which contain prof info
    prof_divs = soup.select("div.post-content")

    # gets list of all professors in the given link
    # returns a array with all information
    prof_objs = []

    links = set()

    for prof_div in tqdm(prof_divs):
        # getting all links
        names_divs = prof_div.find_all("a")
        prof_obj = {}
        # filtering out names/emails
        for name in names_divs:
            isEmail = re.search("@", name.text)
            if isEmail:
                prof_obj["email"] = name.text
            else:
                isResearchWebsite = re.search("website", name.text.lower())
                if not isResearchWebsite:
                    prof_obj["name"] = name.text

            if name["href"]:
                href = name["href"].lower()
                # filters emails
                isLink = re.search("http", href)
                if isLink:
                    links.add(href)
                    if "links" in prof_obj:
                        prof_obj["links"].add(href)
                    else:
                        s = set()
                        s.add(href)
                        prof_obj["links"] = s
        if "links" in prof_obj:
            prof_obj["links"] = list(prof_obj["links"])
        prof_objs.append(prof_obj)


    # with open("links.txt", "w") as linkfile:
    #     json.dump(sorted(list(links)), linkfile, indent=2)

    # with open("prof_objs.txt", "w") as prof_file:
    #     json.dump(prof_objs, prof_file, indent=2)

    print("there are ", len(links), "links")
    return prof_objs, sorted(list(links))
