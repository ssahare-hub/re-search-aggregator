import pandas
import re
import nltk
#nltk.download('stopwords')
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
from nltk.tokenize import RegexpTokenizer
#nltk.download('wordnet') 
from nltk.stem.wordnet import WordNetLemmatizer
from sklearn.feature_extraction.text import CountVectorizer
import re
from sklearn.feature_extraction.text import TfidfTransformer


def keywords_extractor(abstract):

    mydataset = [{'abstract1': abstract}]

    dataset = pandas.DataFrame(mydataset)

    #Fetch wordcount for each abstract
    dataset['word_count'] = dataset.apply(lambda x: len(str(x).split(" ")))
 

    ##Descriptive statistics of word counts
    dataset.word_count.describe()
    #print(dataset.word_count.describe())

    #Identify common words
    freq = pandas.Series(' '.join(dataset).split()).value_counts()[:20]
    # print(freq)

    #Identify uncommon words
    freq1 =  pandas.Series(' '.join(dataset).split()).value_counts()[-20:]
    # print(freq1)

    ##Creating a list of stop words and adding custom stopwords
    stop_words = set(stopwords.words("english"))
    ##Creating a list of custom stopwords
    new_words = ["using", "show", "result", "large", "also", "iv", "one", "two", "new", "previously", "shown"]
    stop_words = stop_words.union(new_words)
    # print(stop_words)

    corpus = []
    #Remove punctuations
    text = re.sub('[^a-zA-Z]', ' ', str(dataset['abstract1']))

    #Convert to lowercase
    text = text.lower()
    
    #remove tags
    text=re.sub("&lt;/?().*?&gt;"," &lt;&gt; ",text)
    
    # remove special characters and digits
    text=re.sub("(\\d|\\W)+"," ",text)
    
    ##Convert to list from string
    text = text.split()
    #print(text)
        
        
    ##Stemming
    ps=PorterStemmer()
    #Lemmatisation
    lem = WordNetLemmatizer()
    text = [lem.lemmatize(word) for word in text if not word in  
            stop_words] 
    text = " ".join(text)
    corpus.append(text)

    #View corpus item
    #corpus[0]
    cv=CountVectorizer(stop_words=stop_words, max_features=10000, ngram_range=(1,3))
    X=cv.fit_transform(corpus)

    list(cv.vocabulary_.keys())[:10]

    #Most frequently occuring words
    def get_top_n_words(corpus, n=None):
        vec = CountVectorizer().fit(corpus)
        bag_of_words = vec.transform(corpus)
        sum_words = bag_of_words.sum(axis=0) 
        words_freq = [(word, sum_words[0, idx]) for word, idx in      
                    vec.vocabulary_.items()]
        words_freq =sorted(words_freq, key = lambda x: x[1], 
                        reverse=True)
        return words_freq[:n]
    #Convert most freq words to dataframe for plotting bar plot
    top_words = get_top_n_words(corpus, n=20)
    top_df = pandas.DataFrame(top_words)
    top_df.columns=["Word", "Freq"]



    #Most frequently occuring Bi-grams
    def get_top_n2_words(corpus, n=None):
        vec1 = CountVectorizer(ngram_range=(2,2),  
                max_features=2000).fit(corpus)
        bag_of_words = vec1.transform(corpus)
        sum_words = bag_of_words.sum(axis=0) 
        words_freq = [(word, sum_words[0, idx]) for word, idx in     
                    vec1.vocabulary_.items()]
        words_freq =sorted(words_freq, key = lambda x: x[1], 
                    reverse=True)
        return words_freq[:n]
    top2_words = get_top_n2_words(corpus, n=20)
    top2_df = pandas.DataFrame(top2_words)
    top2_df.columns=["Bi-gram", "Freq"]
    #print(top2_df)

    #Most frequently occuring Tri-grams
    def get_top_n3_words(corpus, n=None):
        vec1 = CountVectorizer(ngram_range=(3,3), 
            max_features=2000).fit(corpus)
        bag_of_words = vec1.transform(corpus)
        sum_words = bag_of_words.sum(axis=0) 
        words_freq = [(word, sum_words[0, idx]) for word, idx in     
                    vec1.vocabulary_.items()]
        words_freq =sorted(words_freq, key = lambda x: x[1], 
                    reverse=True)
        return words_freq[:n]
    top3_words = get_top_n3_words(corpus, n=20)
    top3_df = pandas.DataFrame(top3_words)
    top3_df.columns=["Tri-gram", "Freq"]
    #print(top3_df)


    tfidf_transformer=TfidfTransformer(smooth_idf=True,use_idf=True)
    tfidf_transformer.fit(X)
    # get feature names
    feature_names=cv.get_feature_names()
    
    # fetch document for which keywords needs to be extracted
    #print (corpus)
    doc=corpus[0]
    
    #generate tf-idf for the given document
    tf_idf_vector=tfidf_transformer.transform(cv.transform([doc]))

    #Function for sorting tf_idf in descending order
    from scipy.sparse import coo_matrix
    def sort_coo(coo_matrix):
        tuples = zip(coo_matrix.col, coo_matrix.data)
        return sorted(tuples, key=lambda x: (x[1], x[0]), reverse=True)
    
    def extract_topn_from_vector(feature_names, sorted_items, topn=10):
        """get the feature names and tf-idf score of top n items"""
        
        #use only topn items from vector
        sorted_items = sorted_items[:topn]
    
        score_vals = []
        feature_vals = []
        
        # word index and corresponding tf-idf score
        for idx, score in sorted_items:
            
            #keep track of feature name and its corresponding score
            score_vals.append(round(score, 3))
            feature_vals.append(feature_names[idx])
    
        #create a tuples of feature,score
        #results = zip(feature_vals,score_vals)
        results= {}
        for idx in range(len(feature_vals)):
            results[feature_vals[idx]]=score_vals[idx]
        
        return results
    #sort the tf-idf vectors by descending order of scores
    sorted_items=sort_coo(tf_idf_vector.tocoo())
    #extract only the top n; n here is 10
    keywords=extract_topn_from_vector(feature_names,sorted_items,5)
    
    # now print the results
    #print("\nAbstract:")
    #print(doc)
    abstract_keywords = []
    print("\nKeywords:")
    for k in keywords:
        abstract_keywords.append(k)
        #print(k,keywords[k])
    #(abstract_keywords)
    return abstract_keywords


keywords_extractor('Recent advances in machine learning open up new and attractive approaches for solving classic problems in computing systems. For storage systems, cache replacement is one such problem because of its enormous impact on performance. We classify workloads as a composition of four workload primitive types — LFU-friendly, LRU-friendly, scan, and churn. We then design and evaluate CACHEUS, a new class of fully adaptive, machine-learned caching algorithms that utilize a combination of experts designed to address these workload primitive types. The experts used by CACHEUS include the state-of-the-art ARC, LIRS and LFU, and two new ones – SR-LRU, a scan-resistant version of LRU, and CR-LFU, a churn-resistant version of LFU.')