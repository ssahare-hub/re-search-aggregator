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
from tika import parser
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

redis_host = os.environ.get('REDISHOST', 'localhost')
redis_port = os.environ.get('REDISPORT', '6379')
redis_client = redis.Redis(host=redis_host, port=redis_port)
# print('flushing all messages from redis')
redis_client.set('messages_sent', 0)
print('set redis message sent count')


def publish_working_topic(data_obj):
    data_str = json.dumps(data_obj)
    data = data_str.encode("UTF-8")
    redis_client.incr('messages_sent')
    try:
        future = pub_client.publish(top_path, data)
        job_id = future.result()
    except:
        job_id = "CANNOT_PUBLISH_TO_TOPIC"


# classifies the job as profile/lab/pdf/others
def create_link_job(URL, level, prof_name):
    data = {
        "URL": URL,
        "Level": level,
        "Type": "",
        "Meta": prof_name
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


# publishes the job to topic
def publish_job(URL, level, prof_name):
    data_obj = create_link_job(URL, level, prof_name)
    publish_working_topic(data_obj)

# post the entity to datastore


papers = set()


def post_paperdata_entity(abstract, prof_name):
    if len(abstract) >= constants["min_abstract_len"]:
        # substitute new lines with special seperator
        abstract = re.sub('(?:\n|\r)+', '([NL])', abstract)
        # remove unreadable characters
        abstract = re.sub(r"[^\x00-\x7f]", r" ", abstract)
    else:
        return
    eid = str(uuid.uuid4())
    key = ds_client.key('PaperData', eid)
    entity = Entity(key=key, exclude_from_indexes=('abstract',))
    entity['abstract'] = abstract
    entity['professor'] = prof_name
    entry = '{},{}\n'.format(prof_name, abstract)
    papers.add(entry)
    if len(papers) % 500 == 0:
        with open('/tmp/texts/papers_collected.txt', 'w') as f:
            f.writelines(list(papers))
    ds_client.put(entity)


# post the entity to datastore
def post_professorinfo_entity(prof_obj):
    eid = str(uuid.uuid4())
    key = ds_client.key('Professor', eid)
    entity = Entity(key=key, exclude_from_indexes=('links',))
    for key in prof_obj.keys():
        entity[key] = prof_obj[key]
    ds_client.put(entity)


# Parses the faculty page for the link given
def parse_faculty_page(URL, level, prof_name):
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
                    prof_name = prof_obj["name"]
            if name["href"]:
                href = name["href"].lower()
                # filters emails
                isLink = re.search("http", href)
                if isLink:
                    publish_job(href, level, prof_name)
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


def extract_links_isearch(URL, level, prof_name):
    lines = []
    papers_list = []
    links = set()
    level += 1
    if level < constants["max_level"]:
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
                    publish_job(href, level, prof_name)
                    links.add(href)
        except Exception as e:
            print('='*40, 'ISEARCH', '='*40)
            print(e)
    else:
        print("Max level reached for {}, skipping".format(URL))

# parses any other pages for paper data info


def extract_links_others(URL, level, prof_name):
    papers_list = []
    links = set()
    lines = []
    level += 1
    if level < constants["max_level"]:
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
                text = re.sub("(?:\n|\r)+", "([NL])", text)
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
                                publish_job(href, level, prof_name)
                                links.add(attr["href"])
                            elif hasKeywords and isRelative:
                                link = urljoin(URL, attr["href"])
                                publish_job(link, level, prof_name)
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
    result = re.search('[\s\S]*Introduction', pdf[0])
    if result:
        return result[0]
    return ''


def extract_page(file_path, pages=1):
    from io import StringIO
    from bs4 import BeautifulSoup
    from tika import parser

    file_data = {}
    _buffer = StringIO()
    data = parser.from_file(file_path, xmlContent=True)
    xhtml_data = BeautifulSoup(data['content'])
    for page, content in enumerate(xhtml_data.find_all('div', attrs={'class': 'page'})):
        if page >= pages:
            break
        # print('Parsing page {} of pdf file...'.format(page+1))
        _buffer.write(str(content))
        parsed_content = parser.from_buffer(_buffer.getvalue())
        _buffer.truncate()
        file_data[page] = parsed_content['content']
    return file_data


abstracts = set()


def parse_pdf(URL, prof_name):
    def download_file(download_url, filename):
        response = urllib.request.urlopen(download_url)
        # TODO: DO mkdir and create directory
        path = '/tmp/pdfs/' + filename
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
    path = './pdfs/' + file
    try:
        # try processing the pdf
        pdf = extract_page(path)
        abstract = extract_abstract(pdf)
        post_paperdata_entity(abstract, prof_name)

        # TODO: Remove, only for testing
        # substitute new lines with special seperator
        abstract = re.sub('(?:\n|\r)+', '([NL])', abstract)
        # remove unreadable characters
        abstract = re.sub(r"[^\x00-\x7f]", r" ", abstract)
        abstracts.add('{}\n'.format(abstract))
        with open('/tmp/texts/abstract.txt', 'w') as f:
            f.writelines(list(abstracts))

    except Exception as f:
        print('--------', 'Processing PDF', '--------')
        print(f)

    # print('processed ', file)
    # delete pdf if processing done
    if os.path.exists(path):
        # print('deleted file ', file)
        os.remove(path)
    else:
        print("The file {} does not exist".format(file))
