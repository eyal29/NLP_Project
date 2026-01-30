import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

BASE_CHROMA_PATH = "chroma_db_storage"

def get_vectorstore(nom_destination):
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    
    persist_directory = os.path.join(BASE_CHROMA_PATH, nom_destination)
    pdf_path = f"crewai_tools/knowledge/{nom_destination}.pdf"
    
    if os.path.exists(persist_directory):
        return Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Le guide PDF pour {nom_destination} est introuvable à l'endroit : {pdf_path}")

    print(f"Création de la base de données pour {nom_destination}...")
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
    splits = text_splitter.split_documents(docs)
    
    vectorstore = Chroma.from_documents(
        documents=splits, 
        embedding=embeddings, 
        persist_directory=persist_directory
    )
    return vectorstore