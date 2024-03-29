from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

import os

if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = "AIzaSyBBKHWk5C8Ar7A1EEWuhfX2jYqQAYZbPj0"

class Memory:
    def __init__(self, **kwargs):
        self._embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001") #OpenAIEmbeddings()

    def get_embeddings(self):
        return self._embeddings
