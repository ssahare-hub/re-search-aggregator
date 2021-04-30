import fitz
import redis
import requests
import os
from pprint import pprint
from bs4 import BeautifulSoup
import re
import uuid
import json
from tqdm import tqdm
from urllib.parse import urljoin
from google.cloud.pubsub_v1 import PublisherClient
from google.cloud import storage
from google.cloud.datastore import Client, Entity
import urllib
import traceback
import pandas as pd
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def download_blob(bucket_name, source_blob_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    dl = blob.download_as_string()
    print("download blob", dl)
    return dl


# CHANGE THESE VALUES ACCORDING TO YOUR APP ENGINE ACCOUNT
BUCKET_NAME = "staging.sss-cc-gae-310003.appspot.com"
PROJECT_ID = "sss-cc-gae-310003"
URL_PATTERN = (
    "((http|https)://)(www.)?"
    + "[a-zA-Z0-9@:%._\\+~#?&//=]{2,256}\\.[a-z]"
    + "{2,6}\\b([-a-zA-Z0-9@:%._\\+~#?&//=]*)"
)

# UPLOAD THIS FILE ONTO YOUR CLOUD STORAGE
c = download_blob(BUCKET_NAME, 'constants.json')
constants = json.loads(c)

ds_client = Client()

pub_client = PublisherClient()
top_path = pub_client.topic_path(PROJECT_ID, constants["job-topic"])

redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_port = os.environ.get('REDIS_PORT', '6379')

redis_client = redis.Redis(host=redis_host, port=redis_port)

print('set redis message sent count')


def publish_working_topic(data_obj):
    data_str = json.dumps(data_obj)
    data = data_str.encode("UTF-8")
    value = redis_client.incr('{}_messages_sent'.format(data_obj["JobId"]))
    # TEST PURPOSES ONLY
    eid = '1'
    key = ds_client.key('Messages', eid)
    entity = Entity(key=key, exclude_from_indexes=('description',))
    entity['description'] = "message_sent"
    entity['value'] = value
    ds_client.put(entity)
    try:
        future = pub_client.publish(top_path, data)
        job_id = future.result()
    except:
        job_id = "CANNOT_PUBLISH_TO_TOPIC"


def create_link_job(URL, data):
    # classify as profile/lab/pdf/others
    data["URL"] = URL
    data["Type"] = ""
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


def post_link_job(URL, data):
    level = data["Level"]
    prof_name = data["Meta"]
    jobid = data["JobId"]
    data_obj = create_link_job(URL, data)
    if is_link_not_in_cache(data_obj):
        publish_working_topic(data_obj)
    else:
        value = redis_client.incr('{}_messages_avoided'.format(data["JobId"]))
        # TEST PURPOSES ONLY
        eid = '3'
        key = ds_client.key('Messages', eid)
        entity = Entity(key=key, exclude_from_indexes=('description',))
        entity['description'] = "message_avoided"
        entity['value'] = value
        ds_client.put(entity)


def is_link_not_in_cache(data):
    # skip processing this link
    # as it is already processed before
    job_id = data["JobId"]
    message = data["URL"]
    return not redis_client.sismember(job_id, message)

# post the entity to datastore


papers = set()


def post_paperdata_entity(abstract, prof_name, put=False, title=''):
    if len(abstract) >= constants["min_abstract_len"]:
        # substitute new lines with special seperator
        abstract = re.sub('(?:\n|\r)+', ' ', abstract)
        # remove unreadable characters
        abstract = re.sub(r"[^\x00-\x7f]", r"", abstract)
    else:
        print("Abstract data too small")
        return
    eid = str(uuid.uuid4())
    key = ds_client.key('DemoData', eid)
    entity = Entity(key=key, exclude_from_indexes=('abstract',))
    entity['abstract'] = abstract
    entity['professor'] = prof_name
    entity['title'] = title
    entry = '{},{}\n'.format(prof_name, abstract)
    papers.add(entry)
    if put:
        ds_client.put(entity)
        # TODO: publish message in nlp topic along with id


# post the entity to datastore
def post_professorinfo_entity(prof_obj):
    eid = str(uuid.uuid4())
    key = ds_client.key('Professor', eid)
    entity = Entity(key=key, exclude_from_indexes=('links',))
    for key in prof_obj.keys():
        entity[key] = prof_obj[key]
    # ds_client.put(entity)


def parse_faculty_page(URL, data):
    level = data["Level"]
    prof_name = data["Meta"]
    jobid = data["JobId"]
    level += 1

    # link to faculty page
    page = requests.get(URL, verify=False)
    soup = BeautifulSoup(page.content, "html.parser")

    # getting all divs which contain prof info
    prof_divs = soup.select("div.post-content")

    # gets list of all professors in the given link
    # returns a array with all information
    prof_objs = []

    links = set()
    for prof_div in tqdm(prof_divs):
        # get name
        x = prof_div.select_one("div.et_pb_text_inner p strong")
        name = 'Not found'
        try:
            name = x.text
        except:
            print("Name not found for a div.")
        data["Meta"] = name
        data["Level"] = level
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
                    # TODO: add if check for prof["name"]
                    post_link_job(href, data)
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

# parse the isearch links for professor info


def extract_links_isearch(URL, data):
    level = data["Level"]
    prof_name = data["Meta"]
    jobid = data["JobId"]
    lines = []
    papers_list = []
    links = set()
    level += 1
    if level < constants["max_level"]:
        data["Level"] = level
        try:
            # parse url and fetch webpage
            page = requests.get(URL, verify=False)
            # setup scraper api
            soup = BeautifulSoup(page.content, "html.parser")
            # select research content
            research = soup.select_one("#research")
            if research:
                papers = research.select("li")
                for paper in papers:
                    text_lower = paper.text
                    # add the paper content
                    papers_list.append(text_lower)
                    post_paperdata_entity(text_lower, prof_name)
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
            more_a_tags = bio.select("a") if bio else []
            tags = a_tags + more_a_tags
            # process all selected links
            for tag in tags:
                href = tag["href"].lower()
                # filter links that redirect to people profiles
                isPerson = re.search("(?:people|profile)", href)
                # select links that are from these websites
                isFiller = re.search(
                    "(?:google|javascript|springer|researchgate|linkedin|video|youtube|scholar|sci.asu|facebook|twitter|messenger|pinterest)", href)
                # filter links that direct to files/emails
                isFile = re.search("(?:.jpg|.png|.jpeg|@)", href)
                hasHttp = re.search("http", href)
                if not (isPerson or isFile or isFiller) and hasHttp:
                    # and isResearch
                    post_link_job(href, data)
                    links.add(href)
        except Exception as e:
            print('='*40, 'ISEARCH', '='*40)
            print(e)
    else:
        print("Max level reached for {}, skipping".format(URL))


def extract_links_others(URL, data):
    level = data["Level"]
    prof_name = data["Meta"]
    jobid = data["JobId"]
    papers_list = []
    links = set()
    lines = []
    level += 1
    if level < constants["max_level"]:
        data["Level"] = level
        try:
            # parse url and fetch webpage
            page = requests.get(URL, verify=False)
            # setup scraper api
            soup = BeautifulSoup(page.content, "html.parser")

            # find if there are any list elements
            list_elems = soup.select("li")
            for elem in list_elems:
                text = elem.text
                # remove '(PDF)' or '(BibTex)' words
                text = re.sub(
                    "(?:([Pp][Dd][Ff])|([Bb][Ii][Bb][Tt][Ee][Xx]))", "", text)
                # remove unnecessary new lines
                text = re.sub("(?:\n|\r)+", " ", text)
                # remove unreadable characters
                text = re.sub(r"[^\x00-\x7f]", r" ", text)
                # append/publish only if greater than min len
                if len(text) > constants["min_abstract_len"]:
                    post_paperdata_entity(text, prof_name)
                    papers_list.append(text)

            # select all attributes
            attrs = soup.select("a")
            for attr in attrs:
                try:
                    if attr["href"]:
                        href = attr["href"].lower()
                        checker = href + "||" + attr.text
                        hasKeywords = re.search(
                            "(?:publication|research|paper|journal|project|service|link|.pdf|robot)",
                            checker,
                        )
                        isFiller = re.search(
                            "(?:.bib|google|javascript|springer|researchgate|linkedin|video|youtube|scholar|sci.asu|facebook|twitter|messenger|pinterest)",
                            href,
                        )
                        hasHttp = re.search("http", href)
                        isRelative = re.match(r"(?:\\|/|../|..\\).*", href)
                        # add more jobs to respective sites
                        if not isFiller:
                            if hasKeywords and hasHttp:
                                post_link_job(href, data)
                                links.add(href)
                            elif hasKeywords and isRelative:
                                link = urljoin(URL, href)
                                post_link_job(link, data)
                                links.add(link)
                            elif not hasHttp:
                                link = urljoin(URL, attr["href"])
                                content = re.search(URL_PATTERN, link)
                                if content:
                                    publish_job(link, level, prof_name)
                                    links.add(link)
                except:
                    pass
        except Exception as e:
            print('='*40, 'OTHERS', '='*40)
            print(e)
    else:
        print("Max level reached for {}, skipping".format(URL))


def extract_abstract(pdf):
    # parse the first page only
    # result = re.search('[\s\S]*Introduction', pdf)
    # if result:
    #     return result[0]
    # return ''
    return pdf


def extract_page(file_path, pages=1):
    # this is pymupdf
    with fitz.open(file_path) as doc:
        text=''
        for page in doc:
            text += page.getText()
        print('Processed {} - length {}'.format(file_path, len(text)))
    return text

def extract_title(body, prof_name):
    last = min(1000, len(body))
    title_search_space = body[:last]
    title_search_space_lower = title_search_space.lower()
    prof = prof_name.split(' ')[0].lower()
    title = re.search('[\s\S]*{}'.format(prof), title_search_space_lower)
    if title:
        return title[0]
    return title_search_space

def parse_pdf(URL, data):
    level = data["Level"]
    prof_name = data["Meta"]
    jobid = data["JobId"]

    def download_file(download_url, filename):
        response = urllib.request.urlopen(download_url)
        path = '/tmp/' + filename
        file = open(path, 'wb')
        file.write(response.read())
        file.close()
    # DOWNLOAD FILE
    file = URL.split('/')[-1]
    try:
        download_file(URL, file)
    except Exception as e:
        print('-'*40, 'Cannot Download PDF', URL)
        print(e)
        return
    # GIVE LOCAL PATH
    path = '/tmp/' + file
    try:
        # try processing the pdf
        pdf = extract_page(path)
        abstract = extract_abstract(pdf)
        title = extract_title(abstract, prof_name)
        post_paperdata_entity(abstract, prof_name, True, title)

    except Exception as f:
        print('--------', 'Processing PDF', '--------')
        print(f)
        print(traceback.print_exc()) 
    # delete pdf if processing done
    if os.path.exists(path):
        # print('deleted file ', file)
        os.remove(path)
    else:
        print("The file {} does not exist".format(file))
