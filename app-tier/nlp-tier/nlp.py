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

    
    ##Creating a list of stop words and adding custom stopwords
    stop_words = set(stopwords.words("english"))
    ##Creating a list of custom stopwords
    new_words = ["using", "show", "result", "large", "also", "iv", "one", "two", "new", "previously", "shown"]
    stop_words = stop_words.union(new_words)
    # print(stop_words)

    corpus = []
    #Remove punctuations
    text = re.sub('\(\[NL\]\)', ' ', abstract)
    text = re.sub('[^a-zA-Z]', ' ', text)

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
    cv=CountVectorizer(stop_words=stop_words, max_features=10000, ngram_range=(2,3))
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
    print(top2_df)

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
    print(top3_df)


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
    keywords=extract_topn_from_vector(feature_names,sorted_items,15)
    
    # now print the results
    #print("\nAbstract:")
    abstract_keywords = []
    print("\nKeywords:")
    for k in keywords:
        abstract_keywords.append(k)
        #print(k,keywords[k])
    print(abstract_keywords)
    return abstract_keywords


keywords_extractor("Are FPGAs Suitable for Edge Computing?([NL])Saman Biookaghazadeh([NL])Arizona State University([NL])Ming Zhao([NL])Arizona State University([NL])Fengbo Ren([NL])Arizona State University([NL])Abstract([NL])The rapid growth of Internet-of-things (IoT) and artificial([NL])intelligence applications have called forth a new comput-([NL])ing paradigmedge computing. In this paper, we study([NL])the suitability of deploying FPGAs for edge computing([NL])from the perspectives of throughput sensitivity to work-([NL])load size, architectural adaptiveness to algorithm char-([NL])acteristics, and energy efficiency. This goal is accom-([NL])plished by conducting comparison experiments on an In-([NL])tel Arria 10 GX1150 FPGA and an Nvidia Tesla K40m([NL])GPU. The experiment results suggest that the key ad-([NL])vantages of adopting FPGAs for edge computing over([NL])GPUs are three-fold: 1) FPGAs can provide a consis-([NL])tent throughput invariant to the size of application work-([NL])load, which is critical to aggregating individual service([NL])requests from various IoT sensors; (2) FPGAs offer both([NL])spatial and temporal parallelism at a fine granularity and([NL])a massive scale, which guarantees a consistently high([NL])performance for accelerating both high-concurrency and([NL])high-dependency algorithms; and (3) FPGAs feature 3([NL])4 times lower power consumption and up to 30.7 times([NL])better energy efficiency, offering better thermal stability([NL])and lower energy cost per functionality.([NL])1([NL])Introduction([NL])The Internet-of-Things (IoT) will connect 50 billion de-([NL])vices and is expected to generate 400 Zetta Bytes of data([NL])per year by 2020. Even considering the fast-growing size([NL])of the cloud infrastructure, the cloud is projected to fall([NL])short by two orders of magnitude to either transfer, store,([NL])or process such vast amount of streaming data [3]. Fur-([NL])thermore, the cloud-based solution will not be able to([NL])provide timely service for many time-sensitive IoT appli-([NL])cations [1] [14]. Consequently, the consensus in the in-([NL])dustry is to expand our computational infrastructure from([NL])data centers towards the edge. Over the next decade, a([NL])vast number of edge servers will be deployed to the prox-([NL])imity of IoT devices; a paradigm that is now referred to([NL])as fog/edge computing.([NL])There are fundamental differences between traditional([NL])cloud and the emerging edge infrastructure. The cloud([NL])infrastructure is mainly designed for (1) fulfilling time-([NL])insensitive applications in a centralized environment;([NL])(2) serving interactive requests from end users; and([NL])(3) processing batches of static data loaded from mem-([NL])ory/storage systems. Differently, the emerging edge in-([NL])frastructure has distinct characteristics, as it keeps the([NL])promise for (1) servicing time-sensitive applications in([NL])a geographically distributed fashion; (2) mainly serving([NL])requests from IoT devices, and (3) processing streams of([NL])data from various input/output (I/O) channels. Existing([NL])IoT workloads often arrive with considerable variance in([NL])data size and require extensive computation, such as in([NL])the applications of artificial intelligence, machine learn-([NL])ing, and natural language processing. Also, the service([NL])requests from IoT devices are usually latency-sensitive.([NL])Therefore, having a predictable performance to various([NL])workload sizes is critical for edge servers.([NL])Existing edge servers on the market are simply a([NL])miniature version of cloud servers (cloudlet) which are([NL])primarily structured based on CPUs with tightly cou-([NL])pled co-processors (e.g., GPUs) [7] [6] [8] [2]. However,([NL])CPUs and GPUs are optimized towards batch processing([NL])of in-memory data and can hardly provide consistent nor([NL])predictable performance for processing streaming data([NL])coming dynamically from I/O channels. Furthermore,([NL])CPUs and GPUs are power hungry and have limited en-([NL])ergy efficiency [4], creating enormous difficulties for de-([NL])ploying them in energy- or thermal-constrained applica-([NL])tion scenarios. Therefore, future edge servers call for([NL])a new general-purpose computing system stack tailored([NL])for processing streaming data from various I/O channels([NL])at low power consumption and high energy efficiency.([NL])OpenCL-based([NL])field-programmable([NL])gate([NL])array([NL])(FPGA) computing is a promising technology for([NL])addressing the aforementioned challenges. FPGAs are([NL])highly energy-efficient and adaptive to a variety of([NL])workloads.([NL])Additionally, the prevalence of high-level([NL])synthesis (HLS) has made them more accessible to ex-([NL])isting computing infrastructures. In this paper, we study([NL])the suitability of deploying FPGAs for edge computing([NL])through experiments focusing on the following three([NL])perspectives: (1) sensitivity of processing throughput to([NL])the workload size of applications, (2) energy-efficiency,([NL])and (3) adaptiveness to algorithm concurrency and([NL])dependency degrees,([NL])which are important to edge([NL])workloads as discussed above.([NL])The experiments were conducted on a server node([NL])equipped with a Nvidia Tesla K40m GPU and an Intel([NL])Fog Reference Design Unit [9] equipped with two Intel([NL])Arria 10 GX1150 FPGAs. Experiment results show that([NL])(1) FPGAs can deliver a predictable performance invari-([NL])ant to the application workload size, whereas GPUs are([NL])sensitive to workload size; (2) FPGAs can provide 2.5([NL])30 times better energy efficiency compared to GPUs; and([NL])(3) FPGAs can adapt their hardware architecture to pro-([NL])vide consistent throughput across a wide range of con-([NL])ditional or inter/intra-loop dependencies, while the GPU([NL])performance can drop by up to 14 times from the low- to([NL])high-dependency scenarios.([NL])The rest of the paper is organized as follows: Sec-([NL])tion 2 introduces the background; Section 3 describes the([NL])methodology; Section 4 discusses experimental results;([NL])and Section 5 concludes the paper.([NL])2([NL])Background([NL])An FPGA is a farm of logic, computation, and storage([NL])resources that can be reconfigured dynamically to com-([NL])pose either spatial or temporal parallelism at a fine gran-([NL])ularity. Traditional FPGA design requires hardware de-([NL])scription languages, such as VHDL and Verilog, making([NL])it out of the reach of application developers. The advent([NL])of HLS technology [5] has opened enormous opportuni-([NL])ties. Today, one can develop FPGA kernel functions in([NL])high-level programming languages (e.g., OpenCL [12])([NL])and deploy the compiled hardware kernels in a run-time([NL])environment for real-time computing [10].([NL])Note that([NL])OpenCL is a universal C-based programming model that([NL])can execute on a variety of computing platforms, in-([NL])cluding CPUs, GPUs, DSP processors, and FPGAs [13].([NL])The recently-extended support of OpenCL by FPGAs([NL])has opened the gate for integrating FPGAs into hetero-([NL])geneous HPC, cloud, and edge platforms.([NL])Different from widely adopted CPUs and GPUs in the([NL])cloud, FPGAs come with several unique features ren-([NL])dering them an excellent candidate for edge comput-([NL])ing. First, unlike GPUs and CPUs that are optimized([NL])for batch processing of memory data, FPGAs are inher-([NL])ently efficient for accelerating streaming applications. A([NL])Figure 1: An Intel Fog Reference Design unit hosting([NL])two Nallatech 385A FPGA Acceleration Cards.([NL])pipelined streaming architecture with data flow control([NL])can be easily built on an FPGA to process streams of([NL])data and commands from I/O channels and generate out-([NL])put results at a constant throughput with reduced latency.([NL])Second, FPGAs can adapt to any algorithm character-([NL])istics due to their hardware flexibility. Different from([NL])CPUs and GPUs that can mostly exploit only spatial([NL])parallelism, FPGAs can exploit both spatial and tempo-([NL])ral parallelism at a finer granularity and on a massive([NL])scale. In spatial parallelism, processing elements (PEs)([NL])are replicated in space, while data is being partitioned([NL])and distributed to these PEs in parallel. In temporal par-([NL])allelism, processing tasks that have dependency among([NL])each other are mapped onto pipelined PEs in series, while([NL])each PE in the pipeline can take data with different times-([NL])tamps in parallel. FPGAs can construct both types of par-([NL])allelism using their abundant computing resources and([NL])pipeline registers [11]. This unique feature makes FP-([NL])GAs suitable for accelerating algorithms with a high de-([NL])gree of both data concurrency and dependency. There-([NL])fore, FPGAs keep the promise to serve a wider range of([NL])IoT applications efficiently.([NL])Third, FPGAs consume significantly lower power([NL])compared to CPUs and GPU [4] for delivering the same([NL])throughput, allowing for improved thermal stability and([NL])reduced cooling cost. This merit is critically needed for([NL])edge servers, considering their limited form factors.([NL])3([NL])Methodology([NL])To confirm and quantify the aforementioned benefits of([NL])FPGA-based edge computing, we designed and con-([NL])ducted three sets of experiments to evaluate FPGAs vs.([NL])GPUs from the perspectives of (1) performance sensitiv-([NL])ity to workload size, (2) adaptiveness to algorithm con-([NL])currency and dependency degrees, and (3) energy effi-([NL])ciency.([NL])All the GPU-related experiments were conducted on a([NL])server node equipped with an Nvidia Tesla K40m GPU,([NL])dual Intel Xeon E5-2637 v4 CPUs, and 64GB of main([NL])2([NL])Figure 2: Multi-stage matrix multiplication on (a) a GPU([NL])and (b) an FPGA.([NL])memory. All the FPGA-related experiments were con-([NL])ducted on an Intel Fog Reference Design unit [9] (see([NL])Figure 1) equipped with two Nallatech 385A FPGA([NL])Acceleration Cards (Intel Arria 10 GX1150 FPGA),([NL])an Intel Xeon E5-1275 v5 CPU, and 32GB of main([NL])memory. The OpenCL kernels for FPGAs were com-([NL])piled using Intel FPGA SDK for OpenCL (version 16.0)([NL])with Nallatech p385a sch ax115 board support packages([NL])(BSP). The GPU OpenCL kernels were compiled at run-([NL])time using available OpenCL library in CUDA Toolkit([NL])8.0.([NL])Results discussed in the next section will show([NL])that the FPGA substantially outperforms the GPU in([NL])several important aspects, despite that the GPU has a([NL])much higher theoretical throughput (4.29TFlops) than([NL])the FPGA (1.5TFlops).([NL])4([NL])Experiment Results([NL])4.1([NL])Sensitivity to Workload Size([NL])The purpose of this experiment is to demonstrate the sen-([NL])sitivity of FPGA and GPU to workload size. IoT devices([NL])are usually latency sensitive and expect predictable la-([NL])tency and throughput from edge servers. We used a two-([NL])stage matrix multiplication (ABC) as the benchmark,([NL])to model edge workloads. This operation is widely used([NL])in linear algebraic algorithms and is generic enough for([NL])the purpose of this experiment. Many IoT workloads,([NL])such as voice and image recognition, are heavily depen-([NL])dent on the linear algebraic operations. All three matri-([NL])ces are of dimension 32x32 and contain single-precision([NL])floating-point random numbers. Input matrices are pro-([NL])vided as a batch, and the batch size represents the work-([NL])load size. We varied the batch size between 2 to 2048 in([NL])the experiment. The processing throughput (number of([NL])matrices/ms) is defined as the ratio of the workload size([NL])over the total runtime.([NL])Figures 2a and 2b illustrate the difference of execu-([NL])tion flow between the GPU and the FPGA. To exploit([NL])spatial parallelism, the GPU must first read the data from([NL])DRAM, perform AB for the entire batch, and store the([NL])0([NL])200([NL])400([NL])600([NL])800([NL])1000([NL])2([NL])4([NL])8([NL])16([NL])32([NL])64([NL])128([NL])256([NL])512([NL])1024([NL])2048([NL])Throughput([NL])(Matrix/ms)([NL])Batch Size([NL])FPGA([NL])GPU([NL])Figure 3: Sensitivity of matrix multiplication throughput([NL])(number of computed matrices per millisecond) sensitiv-([NL])ity to batch size (number of matrices received per batch)([NL])intermediate results (I) in the GPU global memory. Once([NL])the writing of I is done, the subsequent IC can be per-([NL])formed by reading I back from the global memory. Dif-([NL])ferently, the FPGA can exploit temporal parallelism and([NL])utilize dedicated pipes (channels) to transfer the inter-([NL])mediate results from one stage to another without block-([NL])ing the execution. Unlike the GPU, the FPGA reads the([NL])input from the Ethernet I/O channel. The execution of([NL])ABC is fully pipelined by the streaming architecture([NL])implemented in the FPGA, such that the matrix samples([NL])can flow in and out of the FPGA through I/O channels([NL])one after another without waiting regardless of the batch([NL])size.([NL])Figure 3 shows the throughput comparison between([NL])the GPU and the FPGA across different batch sizes. It([NL])is shown that the FPGA can deliver a consistently high([NL])throughput by jointly exploiting spatial and temporal par-([NL])allelism. Specifically, the FPGA outperforms the GPU([NL])for small batch sizes (up to 128) in spite of its much([NL])lower operating frequency. In contrast, the GPU perfor-([NL])mance varies largely according to the batch size. GPUs([NL])rely on interleaving a large batch of input data to hide([NL])the device initialization and data communication over-([NL])head. When dealing with small batch size, such over-([NL])head will dominate total execution time and degrade the([NL])throughput especially when the operations involved have([NL])some levels of dependency. Overall, the experiment re-([NL])sults show that FPGAs not only are efficient in han-([NL])dling aggregated service requests coming from individ-([NL])ual devices in small batch sizes but also can guarantee a([NL])consistently high throughput with a well-bound latency.([NL])Therefore, FPGAs are highly suitable for edge comput-([NL])ing given the considerable variance in workload size of([NL])various IoT applications.([NL])4.2([NL])Adaptiveness([NL])To evaluate how well FPGAs and GPUs adapt to algo-([NL])rithm characteristics, we designed benchmarks to cap-([NL])ture two types of dependencies: data dependency, which([NL])represents the dependency across different iterations of a([NL])loop, and conditional dependency, which represents the([NL])dependency on conditional statements with each iteration([NL])3([NL])of the loop.([NL])Our benchmark resembles an algorithm made of a sim-([NL])ple iterative block (for-loop) where each iteration per-([NL])forms a certain number of operations. The loop length([NL])and ops variables define the total number of iterations([NL])and the total number of operations per iteration (set to([NL])262144 and 512 in the experiment), respectively. All([NL])variables are single-precision in the experiments. Note([NL])that the objective of our experiments is to reveal the im-([NL])pact of architecture adaptiveness to algorithm character-([NL])istics rather than evaluating the performance for a spe-([NL])cific algorithm. In addition, our synthetic algorithm with([NL])a single for loop is generic enough to model large set of([NL])computationally intensive applications.([NL])The benchmark captures data dependency by introduc-([NL])ing dependency among different iterations of the loop.([NL])When there is no data dependency, every single iteration([NL])is considered as independent and all the iterations can([NL])execute in parallel. With data dependency, the iterations([NL])that are dependent on one another need to be executed se-([NL])quentially as a group. Therefore, by varying the data de-([NL])pendency degree, i.e., the average size of the groups, we([NL])can control the data parallelism available in the algorithm([NL])using this benchmark. GPUs performance is closely tied([NL])to the available data parallelism. In comparison, FPGA([NL])can exploit PEs in series and receive iterations regard-([NL])less of the dependency. Different iterations can co-exist([NL])and be executed in the pipeline while traversing down the([NL])connected PEs concurrently.([NL])To introduce conditional dependency, we add if-else([NL])statements into the iterations of the loop in the bench-([NL])mark. Half of the iterations are in the if block and the([NL])other half are in the else block. Only the iterations that([NL])follow the same branch path can be executed in a data([NL])parallel fashion. To reveal the performance impact of([NL])conditional dependency, we vary the number of opera-([NL])tions in each if and else block, which affects the ini-([NL])tialization overhead and consequently the overall perfor-([NL])mance. GPU is highly sensitive to conditional depen-([NL])dency because it can parallelize only the iterations that([NL])take the same path at one time. In comparison, FPGA([NL])can configure the hardware to include all different execu-([NL])tion paths, and use a simple lookup table to direct every([NL])thread into the right pipeline and execute all threads at([NL])the same time.([NL])In order to get the best performance out of the FPGA([NL])and the GPU, the above algorithms were deployed us-([NL])ing two different methods. For the GPU, we designed([NL])an equivalent OpenCL kernel and deployed it in the([NL])NDRange mode to accelerate concurrent operations by([NL])exploiting spatial parallelism. For the FPGA, we com-([NL])piled the FPGA kernel in the single-threaded mode to([NL])accelerate dependent operations by exploiting temporal([NL])parallelism, in which case loop execution is initiated se-([NL]) 0([NL]) 500([NL]) 1000([NL]) 1500([NL]) 2000([NL]) 2500([NL]) 3000([NL]) 3500([NL])FPGA([NL])GPU([NL])540.523([NL])540.523([NL])2303.69([NL])162.535([NL])Thpt. (GFLOPS)([NL])Dependency-16([NL])Dependency-256([NL])(a) Raw Throughput([NL]) 0([NL]) 1([NL]) 2([NL]) 3([NL]) 4([NL]) 5([NL]) 6([NL])FPGA([NL])GPU([NL])1.76([NL])1.76([NL])3.09([NL])0.21([NL])Norm. Thpt.([NL])(GFLOPS/fclk)([NL])Dependency-16([NL])Dependency-256([NL])(b) Normalized Throughput([NL])Figure 4: Comparison of (a) raw and (b) normalized([NL])throughput at low and high data dependency degrees.([NL])quentially in a pipelined fashion.([NL])Data Dependency. Figures 4a and 4b show the raw and([NL])the normalized throughput (to system frequency fclk) for([NL])both a low (16) and a high (256) data dependency, re-([NL])spectively.([NL])In general, computation throughput is lin-([NL])early proportional to both fclk and architectural paral-([NL])lelism. The normalized throughput decouples fclk from([NL])the evaluation and measures the pure impact of architec-([NL])ture parallelism on throughput. For the GPU, the base([NL])frequency of the board is used as fclk. For the FPGA, fclk([NL])is extracted from the full compilation report. It is shown([NL])that the GPU performance drops by 14 times from the([NL])low to the high data concurrency. As data concurrency([NL])increases from 16 and 256, the available data parallelism([NL])(the number of loop iterations that can be executed in([NL])parallel) for the GPU drops from 16384 to 1024. It is([NL])the lack of temporal parallelism that makes GPUs hardly([NL])adaptive to such changes in concurrency and dependency([NL])degrees. On the contrary, the FPGA delivers a stable([NL])throughput regardless of such changes. This is because([NL])the hardware resources on an FPGA can be reconfigured([NL])dynamically to compose either spatial or temporal paral-([NL])lelism (interchangeable) at a fine granularity. As a result,([NL])FPGA outperforms GPU by 3.32 folds with the high data([NL])concurrency, and this gap is expected to grow as the de-([NL])pendency degree further increases.([NL])Conditional Dependency. Figure 5 shows the perfor-([NL])mance drop with respect to the conditional dependency([NL])introduced by if-else statements, as the number of oper-([NL])ations in each if and else block grows from 8 to 1024.([NL])It shows that the FPGA performance is relatively sta-([NL])ble as the conditional dependency increases. For some([NL])specific cases, the performance is even increased due to([NL])a higher clock frequency compared to the baseline ker-([NL])nel. In contrast, the GPU experiences up to 37.12 times([NL])performance drop, compared to baseline kernel with no([NL])conditional statements. Branches from the conditional([NL])statements cause different threads in a warp to follow([NL])different paths, creating instruction replay and resulting([NL])in reduced throughput. Figure 5 also shows that having([NL])fewer operations in the kernel causes more degradation([NL])for the GPU since a smaller kernel does less computa-([NL])4([NL])-20([NL])-10([NL]) 0([NL]) 10([NL]) 20([NL]) 30([NL]) 40([NL])1024([NL])512([NL])256([NL])128([NL])64([NL])32([NL])16([NL])8([NL])Performance([NL])Drop (%)([NL])Number of Ops([NL])FPGA([NL])GPU([NL])Figure 5: Performance drop comparison for kernel with([NL])conditional statements.([NL])tion and incurs relatively higher initialization and data([NL])transfer overhead.([NL])4.3([NL])Energy Efficiency([NL])To evaluate energy efficiency, we measured the work-([NL])load throughput divided by its average power usage. To([NL])project energy efficiency, the power consumptions of([NL])both devices were recorded for all of the experiments.([NL])We used the nvidia-smi command-line utility and the([NL])Nallatech memory-mapped device layer API to query the([NL])instant board-level power consumption every 500 mil-([NL])liseconds for the GPU and FPGA, respectively. We then([NL])calculated the average power usage by averaging all the([NL])power numbers recorded across five trials of each experi-([NL])ment. Note that our heterogeneous testing platform does([NL])not affect the energy calculation since we only measure([NL])the board power consumption.([NL])Figure 6a and 6b show the power consumption and([NL])energy efficiency comparison for performing the matrix([NL])multiplication tasks mentioned in Section 4.1, for dif-([NL])ferent batch sizes. Running at a much lower frequency,([NL])the FPGA consistently consumes 2.793.92 times lower([NL])power than the GPU. Taking into account the perfor-([NL])mance, it shows that the FPGA can provide 2.630.7([NL])times higher energy efficiency than the GPU for execut-([NL])ing matrix multiplication. The improvement is promi-([NL])nent, especially for small batch sizes. The low power([NL])consumption and the high energy efficiency of the FPGA([NL])suggest that deploying FPGAs for edge computing can([NL])potentially gain better thermal stability at lower cooling([NL])cost and reduced energy bill.([NL])Figure 6c depicts the energy efficiency comparison([NL])for running the workloads with different dependency de-([NL])grees (mentioned in Section 4.2). The results show that([NL])the FPGA achieves a similar throughput to the GPU for([NL])executing the kernels with a high data concurrency de-([NL])gree (low data dependency degree of 16). For the high-([NL])data-dependency (degree of 256) workload, the FPGA([NL])achieves up to 11.8 times higher energy efficiency than([NL])the GPU. Such energy efficiency improvement is ex-([NL])pected to further increase as the dependency degree([NL])grows. The experiment results indicate that the FPGA([NL]) 0([NL]) 20([NL]) 40([NL]) 60([NL]) 80([NL]) 100([NL]) 120([NL])2([NL])8([NL])32([NL])128([NL])512([NL])2048([NL])(a)([NL])Power Consumption([NL])(Watts)([NL])Batch Size([NL])FPGA([NL])GPU([NL]) 0([NL]) 5([NL]) 10([NL]) 15([NL]) 20([NL]) 25([NL])2([NL])8([NL])32([NL])128([NL])512([NL])2048([NL])(b)([NL])Energy Efficiency([NL])(Matrix/mWatt)([NL])Batch Size([NL])FPGA([NL])GPU([NL]) 0([NL]) 10([NL]) 20([NL]) 30([NL]) 40([NL]) 50([NL]) 60([NL])FPGA([NL])GPU([NL])20.66([NL])20.66([NL])22.61([NL])1.74([NL])(c)([NL])Energy Efficiency([NL])(GFlops/watt)([NL])Dependency-16([NL])Dependency-256([NL])Figure 6: The caparisons of (a) power consumption, (b)([NL])energy-efficiency for the matrix multiplication tasks, and([NL])(c) the data dependency benchmark.([NL])is almost on par with the GPU regarding energy effi-([NL])ciency for executing high-concurrency algorithms, while([NL])it significantly outperforms the GPU for executing high-([NL])dependency algorithms.([NL])5([NL])Conclusions and Future work([NL])In this paper, we studied three general requirements([NL])of IoT workloads on edge computing architectures and([NL])demonstrated the suitability of FPGA accelerators for([NL])edge servers. Our results confirm the superiority of FP-([NL])GAs over GPUs with respect to: (1) providing workload-([NL])insensitive throughput; (2) adaptiveness to both spatial([NL])and temporal parallelism at fine granularity; and (3) bet-([NL])ter energy efficiency and thermal stability. Based on our([NL])observations, we argue that FPGAs should be consid-([NL])ered a replacement or complementary solution for cur-([NL])rent processors on edge servers.([NL])Based on these results, we will further study FPGA-([NL])based edge computing along the following possible di-([NL])rections.([NL])First, we will extend the study of adaptive-([NL])ness capabilities of both GPUs and FPGAs by consid-([NL])ering other important types of algorithm characteristics.([NL])Second, we plan to improve our benchmarking kernels to([NL])reflect a wider variety of real-world algorithms. Finally,([NL])we will also extend our energy-efficiency study for other([NL])types of workloads and algorithm characteristics.([NL])6([NL])Acknowledgment([NL])This work is supported by NSF CNS-1629888. We thank([NL])our shepherd, Ada Gavrilovska, and the anonymous re-([NL])viewers for their helpful comments. We acknowledge([NL])Mr. Jason Seaholm from Intel for providing us early ac-([NL])cess to Intel Fog Reference Design units. We also thank([NL])Intel FPGA University Program for donating the FPGA([NL])boards.([NL])5([NL])References([NL])[1] CHIANG, M., AND ZHANG, T. Fog and IoT: An overview of re-([NL])search opportunities. IEEE Internet of Things Journal 3, 6 (2016),([NL])854864.([NL])[2] CISCO.([NL])Cisco ")