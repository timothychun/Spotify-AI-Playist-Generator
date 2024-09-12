# LangChain
from langchain.chains import PALChain
from langchain.chains import LLMChain
from langchain.chains import SequentialChain
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.prompts.prompt import PromptTemplate

# Spotipy
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Etc
import os

#Connect to ChaptGPT
llm = ChatOpenAI(model_name='gpt-3.5-turbo')

#Connect to Spotify
auth = SpotifyClientCredentials(
    client_id=os.environ['SPOTIPY_CLIENT_ID'],
    client_secret=os.environ['SPOTIPY_CLIENT_SECRET']
)
sp = spotipy.Spotify(auth_manager=auth)