from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_extraction.text import CountVectorizer
from nltk.stem.wordnet import WordNetLemmatizer
import pandas
import re
import nltk
import os
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
from nltk.tokenize import RegexpTokenizer
nltk.download('stopwords')
nltk.download('wordnet')
from google.cloud import storage
from google.cloud.pubsub_v1 import SubscriberClient

def download_blob(bucket_name, source_blob_name):
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
    # blob.download_to_filename(destination_file_name)
    dl = blob.download_as_string()
    print("download blob", dl)
    return dl


# CHANGE THESE VALUES ACCORDING TO YOUR APP ENGINE ACCOUNT
# Or pass an environment variable thorught the start__ script
BUCKET_NAME = os.environ.get(
    "BUCKET_NAME", "staging.sss-cc-gae-310003.appspot.com")
PROJECT_ID = os.environ.get("PROJECT_ID", "sss-cc-gae-310003")
request_count = 0

# UPLOAD THIS FILE ONTO YOUR CLOUD STORAGE
download_blob(BUCKET_NAME, 'constants.json')
constants = json.loads(c)

sub_client = SubscriberClient()
sub_path = sub_client.subscription_path(
    PROJECT_ID, constants["nlp-sub"])
datastore = datastore.Client()


def keywords_extractor(abstract):

    # Creating a list of stop words and adding custom stopwords
    stop_words = set(stopwords.words("english"))
    # Creating a list of custom stopwords
    new_words = ["using", "show", "result", "large", "also",
                 "iv", "one", "two", "new", "previously", "shown"]
    stop_words = stop_words.union(new_words)
    # print(stop_words)

    corpus = []
    # Remove punctuations
    text = re.sub('\(\[NL\]\)', ' ', abstract)
    text = re.sub('[^a-zA-Z]', ' ', text)

    # Convert to lowercase
    text = text.lower()

    # remove tags
    text = re.sub("&lt;/?().*?&gt;", " &lt;&gt; ", text)

    # remove special characters and digits
    text = re.sub("(\\d|\\W)+", " ", text)

    # Convert to list from string
    text = text.split()
    # print(text)

    # Stemming
    ps = PorterStemmer()
    # Lemmatisation
    lem = WordNetLemmatizer()
    text = [lem.lemmatize(word) for word in text if not word in
            stop_words]
    text = " ".join(text)
    corpus.append(text)

    # View corpus item
    # corpus[0]
    cv = CountVectorizer(stop_words=stop_words,
                         max_features=10000, ngram_range=(2, 3))
    X = cv.fit_transform(corpus)

    list(cv.vocabulary_.keys())[:10]

    # Most frequently occuring words
    def get_top_n_words(corpus, n=None):
        vec = CountVectorizer().fit(corpus)
        bag_of_words = vec.transform(corpus)
        sum_words = bag_of_words.sum(axis=0)
        words_freq = [(word, sum_words[0, idx]) for word, idx in
                      vec.vocabulary_.items()]
        words_freq = sorted(words_freq, key=lambda x: x[1],
                            reverse=True)
        return words_freq[:n]
    # Convert most freq words to dataframe for plotting bar plot
    top_words = get_top_n_words(corpus, n=20)
    top_df = pandas.DataFrame(top_words)
    top_df.columns = ["Word", "Freq"]

    # Most frequently occuring Bi-grams

    def get_top_n2_words(corpus, n=None):
        vec1 = CountVectorizer(ngram_range=(2, 2),
                               max_features=2000).fit(corpus)
        bag_of_words = vec1.transform(corpus)
        sum_words = bag_of_words.sum(axis=0)
        words_freq = [(word, sum_words[0, idx]) for word, idx in
                      vec1.vocabulary_.items()]
        words_freq = sorted(words_freq, key=lambda x: x[1],
                            reverse=True)
        return words_freq[:n]
    top2_words = get_top_n2_words(corpus, n=20)
    top2_df = pandas.DataFrame(top2_words)
    top2_df.columns = ["Bi-gram", "Freq"]
    print(top2_df)

    # Most frequently occuring Tri-grams
    def get_top_n3_words(corpus, n=None):
        vec1 = CountVectorizer(ngram_range=(3, 3),
                               max_features=2000).fit(corpus)
        bag_of_words = vec1.transform(corpus)
        sum_words = bag_of_words.sum(axis=0)
        words_freq = [(word, sum_words[0, idx]) for word, idx in
                      vec1.vocabulary_.items()]
        words_freq = sorted(words_freq, key=lambda x: x[1],
                            reverse=True)
        return words_freq[:n]
    top3_words = get_top_n3_words(corpus, n=20)
    top3_df = pandas.DataFrame(top3_words)
    top3_df.columns = ["Tri-gram", "Freq"]
    print(top3_df)

    tfidf_transformer = TfidfTransformer(smooth_idf=True, use_idf=True)
    tfidf_transformer.fit(X)
    # get feature names
    feature_names = cv.get_feature_names()

    # fetch document for which keywords needs to be extracted
    #print (corpus)
    doc = corpus[0]

    # generate tf-idf for the given document
    tf_idf_vector = tfidf_transformer.transform(cv.transform([doc]))

    # Function for sorting tf_idf in descending order
    from scipy.sparse import coo_matrix

    def sort_coo(coo_matrix):
        tuples = zip(coo_matrix.col, coo_matrix.data)
        return sorted(tuples, key=lambda x: (x[1], x[0]), reverse=True)

    def extract_topn_from_vector(feature_names, sorted_items, topn=10):
        """get the feature names and tf-idf score of top n items"""

        # use only topn items from vector
        sorted_items = sorted_items[:topn]

        score_vals = []
        feature_vals = []

        # word index and corresponding tf-idf score
        for idx, score in sorted_items:

            # keep track of feature name and its corresponding score
            score_vals.append(round(score, 3))
            feature_vals.append(feature_names[idx])

        # create a tuples of feature,score
        #results = zip(feature_vals,score_vals)
        results = {}
        for idx in range(len(feature_vals)):
            results[feature_vals[idx]] = score_vals[idx]

        return results
    # sort the tf-idf vectors by descending order of scores
    sorted_items = sort_coo(tf_idf_vector.tocoo())
    # extract only the top n; n here is 10
    keywords = extract_topn_from_vector(feature_names, sorted_items, 15)

    # now print the results
    # print("\nAbstract:")
    abstract_keywords = []
    print("\nKeywords:")
    for k in keywords:
        abstract_keywords.append(k)
        # print(k,keywords[k])
    print(abstract_keywords)
    return abstract_keywords


def callback(message):
    data_str = message.data.decode("UTF-8")
    data = json.loads(data_str)
    abstract = data["abstract"]
    job_id = data["id"]
    keywords = keywords_extractor(abstract)
    key = datastore.key('DemoData', job_id)
    entity = Entity(key=key)
    entity['keywords'] = keywords
    datastore.put(entity)
    message.ack()


print(f"Listening for messages on {sub_path}..\n")
streaming_pull_future = subscriber.subscribe(sub_path, callback=callback)
