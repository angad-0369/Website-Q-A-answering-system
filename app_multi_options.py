import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
#from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from urllib.parse import urlparse, urlunparse
from extract_all_urls import internal_links_from_url, internal_subdomain_links_from_url

#load_dotenv()


def format_url(url):
    """
    Format a URL to ensure it has the correct scheme, netloc, and path.
    """
    # Check if the URL has a scheme, if not, assume 'https' and prepend '//' for proper parsing
    if not urlparse(url).scheme:
        url = '//' + url

    # Parse the URL
    parsed_url = urlparse(url, scheme='https')

    # Scheme handling: Ensure the scheme is 'https'
    scheme = 'https'

    # Netloc handling: Directly use the parsed netloc, avoiding adding 'www.' if not appropriate
    netloc = parsed_url.netloc

    # Special handling to avoid adding 'www.' to domains that are already subdomains or include 'www.'
    if not netloc.startswith('www.') and netloc.count('.') == 1:
        netloc = 'www.' + netloc

    # Reconsct the URL, ensuring only two slashes are used between the scheme and netloc
    formatted_url = urlunparse((scheme, netloc, parsed_url.path, parsed_url.params, parsed_url.query, parsed_url.fragment))

    return formatted_url



def get_vector_store_from_url(url, extract_option):
    """
    Get the vector store from a URL.
    """
    # get the text in document format
    reformatted_url = format_url(url)

    document_chunks = []

    if extract_option == "Extract Domain":
        # domain urls
        url_list = internal_links_from_url(reformatted_url)
    elif extract_option == "Extract Exact Page":
        # specific url
        url_list = [reformatted_url]
    else:
        # subdomain urls
        url_list = internal_subdomain_links_from_url(reformatted_url)

    print(len(url_list))
    for url_link in url_list:
        loader = WebBaseLoader(url_link)
        document = loader.load()
        # Split the document into chunks
        text_splitter = RecursiveCharacterTextSplitter()
        document_chunks = document_chunks + text_splitter.split_documents(document)

    # Create a vector store from the chunks
    vector_store = Chroma.from_documents(document_chunks, OpenAIEmbeddings())

    return vector_store



def get_context_retriever_chain(vector_store):
    """
    Get the context retriever chain.
    """
    llm = ChatOpenAI()

    retriever = vector_store.as_retriever()

    prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        ("user", "Given the above conversation, generate a search query to look up in order to get information relevant to the conversation")
    ])

    retriever_chain = create_history_aware_retriever(llm, retriever, prompt)

    return retriever_chain



def get_conversational_rag_chain(retriever_chain):
    """
    Get the conversational RAG chain.
    """
    llm = ChatOpenAI()
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer the user's questions based on the below context: \n\n{context}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
    ])
    stuff_documents_chain = create_stuff_documents_chain(llm, prompt)
    
    return create_retrieval_chain(retriever_chain, stuff_documents_chain)



def get_response(user_input):
    """
    Get the response to a user input.
    """
    # Create conversation chain
    retriever_chain = get_context_retriever_chain(st.session_state.vector_store)
    conversation_rag_chain = get_conversational_rag_chain(retriever_chain)

    response = conversation_rag_chain.invoke({
        "chat_history": st.session_state.chat_history,
        "input": user_query
    })
    return response['answer']

# app config
st.set_page_config(page_title="Chat with websites", page_icon="👽")
st.title("Chat with websites")

# sidebar
with st.sidebar:
    page_url = ""
    subdomain_url = ""
    website_url = ""
    st.header("Extract Options")
    extract_option = st.radio("Select Extract Option", ("Extract Domain", "Extract Exact Page", "Extract Subdomain"))


    if extract_option == "Extract Exact Page":
        page_url = st.text_input("Page URL")
        if st.button("Extract", key="extract_page"):
            if page_url:
                st.session_state.selected_page_url = page_url
                st.session_state.chat_history = []
            else:
                st.warning("Please provide a Page URL")

    elif extract_option == "Extract Subdomain":
        subdomain_url = st.text_input("Subdomain URL")
        if st.button("Extract", key="extract_subdomain"):
            if subdomain_url:
                st.session_state.selected_subdomain_url = subdomain_url
                st.session_state.chat_history = []
            else:
                st.warning("Please provide a Subdomain URL")

    else:
        extract_option == "Extract Domain"
        website_url = st.text_input("Website URL")
        if st.button("Extract", key="extract_domain"):
            if website_url:
                st.session_state.selected_domain_url = website_url
                st.session_state.chat_history = []
            else:
                st.warning("Please provide a Website URL")




if website_url is not None and website_url != "":
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [AIMessage(content="Document uploaded! What's your question?")]

    if "vector_state" not in st.session_state:
        st.session_state.vector_store = get_vector_store_from_url(website_url, extract_option)

    user_query = st.text_input("Type your question here...")
    if user_query is not None and user_query != "":
        response = get_response(user_query)
        st.session_state.chat_history.append(HumanMessage(content=user_query))
        st.session_state.chat_history.append(AIMessage(content=response))

    for message in st.session_state.chat_history:
        if isinstance(message, AIMessage):
            with st.chat_message("AI"):
                st.write(message.content)
        elif isinstance(message, HumanMessage):
            with st.chat_message("Human"):
                st.write(message.content)



elif subdomain_url is not None and subdomain_url != "":
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [AIMessage(content="Document uploaded! What's your question?")]

    if "vector_state" not in st.session_state:
        st.session_state.vector_store = get_vector_store_from_url(subdomain_url, extract_option)

    user_query = st.text_input("Type your question here...")
    if user_query is not None and user_query != "":
        response = get_response(user_query)
        st.session_state.chat_history.append(HumanMessage(content=user_query))
        st.session_state.chat_history.append(AIMessage(content=response))

    for message in st.session_state.chat_history:
        if isinstance(message, AIMessage):
            with st.chat_message("AI"):
                st.write(message.content)
        elif isinstance(message, HumanMessage):
            with st.chat_message("Human"):
                st.write(message.content)


elif page_url is not None and page_url != "":
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [AIMessage(content="Document uploaded! What's your question?")]

    if "vector_state" not in st.session_state:
        st.session_state.vector_store = get_vector_store_from_url(page_url, extract_option)

    user_query = st.text_input("Type your question here...")
    if user_query is not None and user_query != "":
        response = get_response(user_query)
        st.session_state.chat_history.append(HumanMessage(content=user_query))
        st.session_state.chat_history.append(AIMessage(content=response))

    for message in st.session_state.chat_history:
        if isinstance(message, AIMessage):
            with st.chat_message("AI"):
                st.write(message.content)
        elif isinstance(message, HumanMessage):
            with st.chat_message("Human"):
                st.write(message.content)