import redis
import requests
import os
from pprint import pprint
from bs4 import BeautifulSoup
import re
#import pdftotext
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

    # Construct a client side representation of a blob.
    # Note `Bucket.blob` differs from `Bucket.get_blob` as it doesn't retrieve
    # any content from Google Cloud Storage. As we don't need additional data,
    # using `Bucket.blob` is preferred here.
    blob = bucket.blob(source_blob_name)
    dl = blob.download_as_string()
    print("download blob", dl)
    return dl


BUCKET_NAME = "cc-test-309723.appspot.com"
PROJECT_ID = "cc-test-309723"

# UPLOAD THIS FILE ONTO YOUR CLOUD STORAGE
c = download_blob(BUCKET_NAME, 'constants.json')
constants = json.loads(c)

ds_client = Client()

pub_client = PublisherClient()
top_path = pub_client.topic_path(PROJECT_ID, constants["job-topic"])

redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_port = os.environ.get('REDIS_PORT', '6379')

print (redis_host,redis_port, os.environ['REDIS_HOST'])
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
    publish_working_topic(data_obj)


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
    key = ds_client.key('PaperData',eid)
    entity = Entity(key=key, exclude_from_indexes=('abstract',))
    entity['abstract'] = abstract
    entity['professor'] = prof_name
    entry = '{},{}\n'.format(prof_name, abstract)
    papers.add(entry)
    if len(papers) % 500 == 0:
        with open('/tmp/texts/papers_collected.txt', 'w') as f:
            f.writelines(list(papers))
    ds_client.put(entity)


def post_professorinfo_entity(prof_obj):
    eid = str(uuid.uuid4())
    key = ds_client.key('Professor',eid)
    entity = Entity(key=key, exclude_from_indexes=('links',))
    for key in prof_obj.keys():
        entity[key] = prof_obj[key]
    ds_client.put(entity)


def parse_faculty_page(URL, data):
    level = data["Level"]
    prof_name = data["Meta"]
    jobid = data["JobId"]
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


def extract_links_isearch(URL, data):
    level = data["Level"]
    prof_name = data["Meta"]
    jobid = data["JobId"]
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
                papers = research.select("p")
                for paper in papers:
                    text_lower = paper.text.lower()
                    # add the paper content
                    papers_list.append(text_lower)
                    post_paperdata_entity(text_lower, prof_name)
                    # with open('paperdata.txt','a') as f:
                    #     f.writelines([prof_name, text_lower])
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
                isFiller = re.search("(?:google|javascript|springer|researchgate|linkedin|video|youtube|scholar|sci.asu|facebook|twitter|messenger|pinterest)", href)
                # filter links that direct to files/emails
                isFile = re.search("(?:.jpg|.png|.jpeg|@)", href)
                hasHttp = re.search("http", href)
                if not (isPerson or isFile or isFiller)  and hasHttp:
                    # and isResearch
                    post_link_job(href, data)
                    links.add(href)
            # with open('links.txt','a') as l:
            #     l.write('\n')
            #     l.writelines(links)
            #     l.write('\n')
        except Exception as e:
            print('='*40,'ISEARCH','='*40)
            # print(traceback.print_exc())
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
        try:
            # parse url and fetch webpage
            page = requests.get(URL, verify=False)
            # setup scraper api
            soup = BeautifulSoup(page.content, "html.parser")

            # find if there are any list elements
            list_elems = soup.select("li")
            for elem in list_elems:
                text = elem.text.lower()
                post_paperdata_entity(text, prof_name)
                # with open('paperdata.txt','a') as f:
                #     f.writelines([prof_name, text])
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
                        isFiller = re.search("(?:google|javascript|springer|researchgate|linkedin|video|youtube|scholar|sci.asu|facebook|twitter|messenger|pinterest)", href)
                        hasHttp = re.search("http", href)
                        isRelative = re.match(r'\\.*', href)
                        # add more jobs to respective sites
                        if not isFiller:
                            if hasKeywords and hasHttp:
                                post_link_job(href, data)
                                links.add(href)
                            elif hasKeywords and isRelative:
                                link = urljoin(URL, href)
                                post_link_job(link, data)
                                links.add(link)    
                except :
                    pass
            # with open('links.txt','a') as l:
            #     l.write('\n')
            #     l.writelines(links)
            #     l.write('\n')
        except Exception as e:
            print('='*40,'OTHERS','='*40)
            print(e)
    else:
        print("Max level reached for {}, skipping".format(URL))

def extract_abstract(pdf):
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


def parse_pdf(URL, data):
    level = data["Level"]
    prof_name = data["Meta"]
    jobid = data["JobId"]
    # page = requests.get(URL)
    def download_file(download_url, filename):
        response = urllib.request.urlopen(download_url)
        # TODO: DO mkdir and create directory
        path = '/tmp/pdfs/' + filename
        file = open(path, 'wb')
        file.write(response.read())
        file.close()
    file = URL.split('/')[-1]
    try:
        download_file(URL, file)
    except Exception as e:
        print('-'*40,'Cannot Download PDF',URL)
        print(e)
        return
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
        print('--------','Processing PDF','--------')
        print(f)

    # print('processed ', file)
    # delete pdf if processing done
    if os.path.exists(path):
        # print('deleted file ', file)
        os.remove(path)
    else:
        print("The file {} does not exist".format(file))