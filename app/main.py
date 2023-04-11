import streamlit as st
import urllib
import os
import time
import requests
import random
from collections import OrderedDict
from openai.error import OpenAIError
from langchain.docstore.document import Document

from components.sidebar import sidebar
from utils import (
    embed_docs,
    get_answer,
    get_sources,
    search_docs
)

AZURE_SEARCH_API_VERSION = '2021-04-30-Preview'
AZURE_OPENAI_API_VERSION = "2023-03-15-preview"

def clear_submit():
    st.session_state["submit"] = False

#@st.cache_data()
def get_search_results(query, indexes):
    
    headers = {'Content-Type': 'application/json','api-key': os.environ["AZURE_SEARCH_KEY"]}

    agg_search_results = []
    for index in indexes:
        url = os.environ["AZURE_SEARCH_ENDPOINT"] + '/indexes/'+ index + '/docs'
        url += '?api-version={}'.format(AZURE_SEARCH_API_VERSION)
        url += '&search={}'.format(query)
        url += '&select=*'
        url += '&$top=5'  # You can change this to anything you need/want
        url += '&queryLanguage=en-us'
        url += '&queryType=semantic'
        url += '&semanticConfiguration=my-semantic-config'
        url += '&$count=true'
        url += '&speller=lexicon'
        url += '&answers=extractive|count-3'
        url += '&captions=extractive|highlight-false'

        resp = requests.get(url, headers=headers)
        print(url)
        print(resp.status_code)

        search_results = resp.json()
        agg_search_results.append(search_results)
    
    return agg_search_results
    

st.set_page_config(page_title="GPT Smart Search", page_icon="📖", layout="wide")
st.header("GPT Smart Search Engine")

with st.sidebar:
    st.markdown("""# Instructions""")
    st.markdown("""
 Ask a question that you think can be answered with the information in about Snowflake Overview, Internals and Security Guide.

For example:
                - What is Snowflake?
                - What is the difference between Snowflake and Databricks?
                - What is the throughput of reading and writing on Snowflake?
                - Does Snowflake support true columner storage?
                - What is the pricing of Snowflake?
                - What is the pricing of Snowflake with the link to the website?
                - Does Snowflake support only Cloud or it also supports on-prem installation?
                
                \nYou will notice that the answers to these questions are diferent from the open ChatGPT, since these papers are the only possible context. This search engine does not look at the open internet to answer these questions. If the context doesn't contain information, the engine will respond: I don't know.
                """)
    st.markdown("""
            - ***Quick Answer***: GPT model only uses, as context, the captions of the results coming from Azure Search
            - ***Best Answer***: GPT model uses, as context. all of the content of the documents coming from Azure Search
            """)

coli1, coli2 = st.columns([2,1])
with coli1:
    query = st.text_input("Ask a question to your enterprise data lake", value= "What is CLP?", on_change=clear_submit)
with coli2:
    temp = st.slider('Temperature :thermometer:', min_value=0.0, max_value=1.0, step=0.1, value=0.5)

# options = ['English', 'Spanish', 'Portuguese', 'French', 'Russian']
# selected_language = st.selectbox('Answer Language:', options, index=0)

col1, col2, col3 = st.columns([1,1,3])
with col1:
    qbutton = st.button('Quick Answer')
with col2:
    bbutton = st.button('Best Answer')


if (not os.environ.get("AZURE_SEARCH_ENDPOINT")) or (os.environ.get("AZURE_SEARCH_ENDPOINT") == ""):
    st.error("Please set your AZURE_SEARCH_ENDPOINT on your Web App Settings")
elif (not os.environ.get("AZURE_SEARCH_KEY")) or (os.environ.get("AZURE_SEARCH_KEY") == ""):
    st.error("Please set your AZURE_SEARCH_ENDPOINT on your Web App Settings")
elif (not os.environ.get("AZURE_OPENAI_ENDPOINT")) or (os.environ.get("AZURE_OPENAI_ENDPOINT") == ""):
    st.error("Please set your AZURE_OPENAI_ENDPOINT on your Web App Settings")
elif (not os.environ.get("AZURE_OPENAI_API_KEY")) or (os.environ.get("AZURE_OPENAI_API_KEY") == ""):
    st.error("Please set your AZURE_OPENAI_API_KEY on your Web App Settings")

else: 
    os.environ["OPENAI_API_BASE"] = os.environ.get("AZURE_OPENAI_ENDPOINT")
    os.environ["OPENAI_API_KEY"] = os.environ.get("AZURE_OPENAI_API_KEY")
    os.environ["OPENAI_API_VERSION"] = os.environ["AZURE_OPENAI_API_VERSION"] = AZURE_OPENAI_API_VERSION


    if qbutton or bbutton or st.session_state.get("submit"):
        if not query:
            st.error("Please enter a question!")
        else:
            # Azure Search

            index1_name = "cogsrch-snowflake-index-files"
            indexes = [index1_name]
            agg_search_results = get_search_results(query, indexes)

            file_content = OrderedDict()

            try:
                for search_results in agg_search_results:
                    for result in search_results['value']:
                        if result['@search.rerankerScore'] > 1: # Show results that are at least 25% of the max possible score=4
                            file_content[result['id']]={
                                                    "title": result['title'],
                                                    "chunks": result['pages'],
                                                    "language": result['language'],
                                                    "caption": result['@search.captions'][0]['text'],
                                                    "score": result['@search.rerankerScore'],
                                                    "location": result['metadata_storage_path']                  
                                                }
            except:
                st.markdown("Not data returned from Azure Search, check connection..")


            st.session_state["submit"] = True
            # Output Columns
            placeholder = st.empty()

            try:
                docs = []
                for key,value in file_content.items():

                    if qbutton:
                        docs.append(Document(page_content=value['caption'], metadata={"source": value["location"]}))
                        add_text = "Coming up with a quick answer... ⏳"

                    if bbutton:
                        for page in value["chunks"]:
                            docs.append(Document(page_content=page, metadata={"source": value["location"]}))
                        add_text = "Reading the source documents to provide the best answer... ⏳"

                if "add_text" in locals():
                    with st.spinner(add_text):
                        if(len(docs)>0):
                            language = random.choice(list(file_content.items()))[1]["language"]
                            index = embed_docs(docs, language)
                            sources = search_docs(index,query)
                            if qbutton:
                                answer = get_answer(sources, query, deployment="gpt-35-turbo", chain_type = "stuff", temperature=temp, max_tokens=256)
                            if bbutton: 
                                answer = get_answer(sources, query, deployment="gpt-35-turbo", chain_type = "map_reduce", temperature=temp, max_tokens=500)

                        else:
                            answer = {"output_text":"No results found" }
                else:
                    answer = {"output_text":"No results found" }


                with placeholder.container():

                    st.markdown("#### Answer")
                    st.markdown(answer["output_text"].split("SOURCES:")[0])
                    st.markdown("Sources:")
                    try: 
                        for s in answer["output_text"].split("SOURCES:")[1].replace(" ","").split(","):
                            st.markdown(s) 
                    except:
                        st.markdown("N/A")
                    st.markdown("---")
                    st.markdown("#### Search Results")

                    if(len(docs)>1):
                        for key, value in file_content.items():
                            st.markdown(str(value["title"]) + '  (Score: ' + str(round(value["score"]*100/4,2)) + '%)')
                            st.markdown(value["caption"])
                            st.markdown("---")

            except OpenAIError as e:
                st.error(e)