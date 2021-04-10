import requests
import os
from pprint import pprint
from bs4 import BeautifulSoup
import re
import pdftotext
import uuid
import json
from tqdm import tqdm
from urllib.parse import urljoin
from google.cloud.pubsub_v1 import PublisherClient
from google.cloud.datastore import Client, Entity
import urllib

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def download_blob(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    # bucket_name = "your-bucket-name"
    # source_blob_name = "storage-object-name"
    # destination_file_name = "local/path/to/file"

    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)

    # Construct a client side representation of a blob.
    # Note `Bucket.blob` differs from `Bucket.get_blob` as it doesn't retrieve
    # any content from Google Cloud Storage. As we don't need additional data,
    # using `Bucket.blob` is preferred here.
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)

    print(
        "Blob {} downloaded to {}.".format(
            source_blob_name, destination_file_name
        )
    )


BUCKET_NAME = "staging.sss-cc-gae-310003.appspot.com"
PROJECT_ID = "sss-cc-gae-310003"


# download_blob(BUCKET_NAME, 'constants.json', 'constants.json')
with open('constants.json', 'r') as c:
    constants = json.load(c)

ds_client = Client()

pub_client = PublisherClient()
top_path = pub_client.topic_path(PROJECT_ID, constants["job-topic"])


def publish_working_topic(data_obj):
    data_str = json.dumps(data_obj)
    data = data_str.encode("UTF-8")
    # TODO: post message in topic
    try:
        future = pub_client.publish(top_path, data)
        job_id = future.result()
    except:
        job_id = "CANNOT_PUBLISH_TO_TOPIC"


def create_link_job(URL, level):
    # classify as profile/lab/pdf/others
    data = {
        "URL": URL,
        "Level": level,
        "Type": ""
    }
    URL = URL.lower()
    isProfile = re.search('(?:people|isearch)', URL)
    isLab = re.search('lab', URL)
    isPdf = re.search('.pdf', URL)
    if isProfile:
        data["Type"] = constants["profile"]
    elif isLab:
        data["Type"] = constants["lab"]
    elif isPdf:
        data["Type"] = constants["pdf"]
    else:
        data["Type"] = constants["others"]
    return data


def post_link_job(URL, level):
    level += 1
    if level < constants["max_level"]:
        data_obj = create_link_job(URL, level)
        publish_working_topic(data_obj)
    else:
        print("No more jobs will be published, max level for this link reached")


def post_paperdata_entity(title, abstract, contribs):
    if len(title) > 0:
        title = title.replace('\n',' ')
    if len(contribs) > 0:
        contribs = contribs.replace('\n',' ')
    if len(abstract) > 20:
        abstract = abstract.replace('\n',' ')
    else:
        return
    eid = str(uuid.uuid4())
    key = ds_client.key('PaperData',eid)
    entity = Entity(key=key, exclude_from_indexes=('abstract', 'contribs',))
    entity['title'] = title
    entity['abstract'] = abstract
    entity['contribs'] = contribs
    with open('paperdata.txt','a') as f:
        f.write(json.dumps(entity))
        f.write('\n')
    # ds_client.put(entity)


def post_professorinfo_entity(prof_obj):
    eid = str(uuid.uuid4())
    key = ds_client.key('Professor',eid)
    entity = Entity(key=key, exclude_from_indexes=('links',))
    for key in prof_obj.keys():
        entity[key] = prof_obj[key]
    # ds_client.put(entity)


def work_on_jobs(URL, level):
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
                    post_link_job(href, level)
                    links.add(href)
                    if "links" in prof_obj:
                        prof_obj["links"].add(href)
                    else:
                        s = set()
                        s.add(href)
                        prof_obj["links"] = s
        if "links" in prof_obj:
            prof_obj["links"] = list(prof_obj["links"])
        post_professorinfo_entity(prof_obj)
        # prof_objs.append(prof_obj)

    # print("there are ", len(links), "links")
    # return prof_objs, sorted(list(links))


def extract_links_isearch(URL, level):
    lines = []
    papers_list = []
    links = set()
    try:
        # parse url and fetch webpage
        page = requests.get(URL, verify=False)
        # setup scraper api
        soup = BeautifulSoup(page.content, "html.parser")
        # select research content
        research = soup.select_one("#research")
        if research:
            papers = research.select("p")
            for paper in papers:
                text_lower = paper.text.lower()
                # add the paper content
                papers_list.append(text_lower)
                post_paperdata_entity('', text_lower, '')
                # TODO: improve this logic
                # Extract author, paper and anything else extra
                texts = text_lower.split(")")
                obj = {"extra": []}
                for i in range(len(texts)):
                    if i == 0:
                        obj["author"] = texts[i]
                    elif i == 1:
                        obj["paper"] = texts[i]
                    elif i > 1:
                        obj["extra"].append(texts[i])
        # fetch next jobs
        # select more links inside research/bio
        a_tags = research.select("a") if research else []
        bio = soup.select_one("#bio")
        more_a_tags = bio.select("a")
        tags = a_tags + more_a_tags
        # process all selected links
        for tag in tags:
            href = tag["href"].lower()
            # filter links that redirect to people profiles
            isPerson = re.search("people", href)
            # select links that are from these websites
            # isResearch = re.search("(?:asu.edu|doi|lab|github.io|arxiv|ieeexplore|acm|springer)", href)
            isScholar = re.search("scholar", href)
            # filter links that direct to files/emails
            isFile = re.search("(?:.jpg|.png|.jpeg|@)", href)
            hasHttp = re.search("http", href)
            if not (isPerson or isFile or isScholar) and hasHttp:
                # and isResearch
                post_link_job(href, level)
                links.add(href)
        with open('links.txt','a') as l:
            l.writelines(lines)
            l.write('\n')
    except Exception as e:
        print('='*40,'ISEARCH','='*40)
        print(e)

def extract_links_others(URL, level):
    papers_list = []
    links = set()
    try:
        # parse url and fetch webpage
        page = requests.get(URL, verify=False)
        # setup scraper api
        soup = BeautifulSoup(page.content, "html.parser")

        # find if there are any list elements
        list_elems = soup.select("li")
        for elem in list_elems:
            text = elem.text.lower()
            post_paperdata_entity('', text, '')
            papers_list.append(text)

        # select all attributes
        attrs = soup.select("a")
        for attr in attrs:
            try:
                if attr["href"]:
                    href = attr["href"].lower()
                    checker = href + "||" + attr.text
                    hasKeywords = re.search(
                        "(?:publication|research|paper|journal|project|service|link)", checker)
                    hasHttp = re.search("http", href)
                    isRelative = re.match(r'\\.*', href)
                    # add more jobs to respective sites
                    if hasKeywords and hasHttp:
                        post_link_job(href, level)
                        links.add(href)
                    elif hasKeywords and isRelative:
                        link = urljoin(URL, href)
                        post_link_job(link, level)
                        links.add(link)    
            except :
                pass
        with open('links.txt','a') as l:
            l.writelines(lines)
            l.write('\n')
    except Exception as e:
        print('='*40,'OTHERS','='*40)
        print(e)

def extract_abstract(pdf):
    col1 = ''
    col2 = ''
    result = re.search('Abstract[\s\S]*Introduction', pdf[0])
    if result:
        lines = result[0].split('\n')
        for line in lines:
            line = '(SPECIAL)' + line
            sub = re.sub('\s{5,}', '(SPLIT)', line)
            # print(sub)
            cols = sub.split('(SPLIT)')
            # print('-'*100)
            # print(cols)
            for i, col in enumerate(cols):
                # print(i)
                text = re.sub('\(SPECIAL\)', '', col)
                if i == 0:
                    col1 += ' ' + text
                else:
                    col2 += ' ' + text

def extract_title(pdf):
    result = pdf[0].trim().split('\n')
    if result:
        print('-'*75)
        print('Title is ', result[0])
        return result[0]
    return ''

def extract_contribs(pdf, title):
    result = re.search('[\s\S]*Abstract')
    if result:
        result = re.sub(title,result)
        print('-'*75)
        print('contribs are ', result)
        return result
    return ''

def parse_pdf(URL):
    # page = requests.get(URL)
    def download_file(download_url, filename):
        response = urllib.request.urlopen(download_url)
        file = open(filename, 'wb')
        file.write(response.read())
        file.close()
    file = URL.split('/')[-1]
    try:
        download_file(URL, file)
        col1 = ''
        col2 = ''
        with open(file, 'rb') as pdfFile:
            pdf = pdftotext.PDF(pdfFile)
            col1, col2 = extract_abstract(pdf)
            title = extract_heading(pdf)
            contribs = extract_contribs(pdf, title)
            post_paperdata_entity(title, col1, contribs)
        if os.path.exists(file):
            os.remove(file)
        else:
            print("The file {} does not exist".format(file))
    except Exception as e:
        print('='*40,'PARSEPDF','='*40)
        print(e)