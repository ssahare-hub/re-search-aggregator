#def nlpprocessor()
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.datasets import fetch_20newsgroups
from sklearn.decomposition import NMF, LatentDirichletAllocation
from sklearn.decomposition import TruncatedSVD
import pandas as pd
import numpy as np
import nltk

nltk.download('stopwords')
nltk.download('wordnet')
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords
from nltk.stem.wordnet import WordNetLemmatizer
import matplotlib.pyplot as plt
import seaborn as sns
import re
import gensim
import gensim.corpora as corpora
import pyLDAvis
from pyLDAvis import sklearn as sklearn_lda
import pickle

"""# 2. Load data file

Load the data file containing research papers into a dataframe called 'dataset'.
"""

# load data file
dataset = pd.read_csv(r'research_papers.csv', encoding='ISO-8859–1')

"""# 3. Clean Data

I dropped the unnecessary columns like 'ID', 'Author','Year', 'Conference/Journal', and focused solely on the 'Abstract' and 'Conclusion' columns of each paper entry. For papers with no conclusions, I filled the empty cell with the text "No conclusion". Next, I merged the two columns 'Abstract' and 'Conclusion' to form a new column called 'PaperText'.
"""

# remove the unecessary columns
dataset = dataset.drop(columns=['Id', 'Reference', 'Authors', 'Year', 'Conference/ Journal'], axis=1)

# fill in the empty cells
dataset = dataset.fillna('No conclusion')

# merge abstract and conclusion
dataset['Paper_Text'] = dataset["Abstract"] + dataset["Conclusion"]

# show first 5 records
dataset.head()

"""# 4. Preprocess Data

Tokenize each sentence into a list of words, remove punctuations, remove stopwords and words of length less than 3, and then lemmatize.
"""


# function for lemmatization
def get_lemma(word):
    lemma = wn.morphy(word)
    if lemma is None:
        return word
    else:
        return lemma


# tokenization
tokenized_data = dataset['Paper_Text'].apply(lambda x: x.split())

# remove punctuation
tokenized_data = tokenized_data.apply(lambda x: [re.sub('[-,()\\.!?]', '', item) for item in x])

# turn to lowercase
tokenized_data = tokenized_data.apply(lambda x: [item.lower() for item in x])

# remove stop-words and short words
stop_words = stopwords.words('english')
stop_words.extend(['from', 'use', 'uses', 'user', 'users' 'well', 'study', 'survey', 'structjumper', 'think'])
tokenized_data = tokenized_data.apply(lambda x: [item for item in x if item not in stop_words and len(item) > 3])

# lemmatize by calling lemmatization function
tokenized_data = tokenized_data.apply(lambda x: [get_lemma(item) for item in x])

"""# 5. Creating Bigrams and Trigrams
Bigrams are two words frequently occurring together in the document. Trigrams are 3 words frequently occurring.

Some examples in our corpus are: ‘visually_impaired’, ‘programming_language’, ‘block_based_programming’, 'programming environment' etc.

Gensim’s Phrases model can build and implement the bigrams, trigrams, quadgrams and more. The two important arguments to Phrases are min_count and threshold. The higher the values of these param, the harder it is for words to be combined to bigrams
"""

# build the bigram and trigram models
bigram = gensim.models.Phrases(tokenized_data, min_count=5, threshold=10)  # higher threshold fewer phrases.
trigram = gensim.models.Phrases(bigram[tokenized_data], threshold=10)

# faster way to get a sentence clubbed as a trigram/bigram
bigram_mod = gensim.models.phrases.Phraser(bigram)
trigram_mod = gensim.models.phrases.Phraser(trigram)

# see trigram example
for i in range(50):
    print(trigram_mod[bigram_mod[tokenized_data[i]]])
print(trigram_mod[bigram_mod[tokenized_data[0]]])
print(trigram_mod[bigram_mod[tokenized_data[34]]])
print(trigram_mod[bigram_mod[tokenized_data[9]]])


# define functions for creating bigrams and trigrams.
def make_bigrams(texts):
    return [bigram_mod[doc] for doc in texts]


def make_trigrams(texts):
    return [trigram_mod[bigram_mod[doc]] for doc in texts]


# form Bigrams
tokenized_data_bigrams = make_bigrams(tokenized_data)

# form Trigrams
tokenized_data_trigrams = make_trigrams(tokenized_data)

# de-tokenization
detokenized_data = []
for i in range(len(dataset)):
    t = ' '.join(tokenized_data_trigrams[i])
    detokenized_data.append(t)

dataset['clean_text'] = detokenized_data
documents = dataset['clean_text']

