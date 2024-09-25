# Import necessary libraries for the application
import streamlit as st
from langchain_openai import ChatOpenAI
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os
import time
from spotipy.exceptions import SpotifyException

# Load environment variables from a .env file (for API keys and other sensitive data)
load_dotenv()

# Streamlit configuration settings (page title, icon, and layout)
st.set_page_config(page_title="Spotify AI Playlist Generator", page_icon="🎵", layout="wide")
st.title('Spotify AI Playlist Generator 🎵')

# Retrieve API keys and client details from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
spotify_redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")

# Define the Spotify authorization scope for creating playlists and accessing user data
scope = "playlist-modify-public user-library-read"

# Function to initialize the Spotify OAuth client
def get_spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=spotify_client_id,
        client_secret=spotify_client_secret,
        redirect_uri=spotify_redirect_uri,
        scope=scope
    ))

# Function to initialize the OpenAI Chat client
def create_openai_client():
    try:
        return ChatOpenAI(
            temperature=0.5,
            openai_api_key=openai_api_key,
            model="gpt-3.5-turbo"
        )
    except Exception as e:
        st.error(f"Error initializing OpenAI client: {e}")
        return None

# Function to create a typewriter effect for displaying text in Streamlit
def typewriter(text: str, speed: int = 10):
    tokens = list(text)
    container = st.empty()
    for index in range(len(tokens) + 1):
        curr_full_text = "".join(tokens[:index])
        container.markdown(curr_full_text)
        time.sleep(1 / speed)

# Function to analyze user input using the OpenAI model to generate keywords for song search
def analyze_input(input_text):
    llm = create_openai_client()
    if not llm:
        return "error"
    try:
        input_analysis = llm.invoke(f"Analyze the input that the user gives to create a music recommendation that follows the prompt and return a short phrase or keywords suitable for searching: {input_text}")
        return input_analysis.content.strip().lower()
    except Exception as e:
        st.error(f"Error analyzing input: {e}")
        return "error"

# Function to retrieve the monthly listeners for a given artist based on their Spotify ID
def get_artist_monthly_listeners(artist_id):
    sp = get_spotify_client()
    artist = sp.artist(artist_id)
    return artist['followers']['total']

# Function to search for songs on Spotify based on input_text, limiting the results to song_limit and filtering artists by max_listeners
def get_songs(input_text, song_limit, max_listeners):
    sp = get_spotify_client()

    if not input_text or input_text == "error":
        return []

    # Truncate the input text to avoid overly long search queries
    input_text = input_text[:200]

    unique_songs = {}
    exclude_keywords = ['remix', 'edit', 'version', 'live', 'rework', 'acoustic', 'cover', 'tribute', 'karaoke']
    track_ids_seen = set()
    song_titles_seen = set()
    offset = 0
    batch_size = 50

    # Loop through search results until the desired number of songs is found or no more results
    while len(unique_songs) < song_limit:
        try:
            results = sp.search(q=input_text, type='track', limit=batch_size, offset=offset, market='US')
        except SpotifyException as e:
            st.error(f"Error searching for songs: {e}")
            return []

        if not results['tracks']['items']:
            break

        # Filter the songs to avoid duplicates and unwanted versions
        for track in results['tracks']['items']:
            song_name = track['name'].lower()
            track_id = track['id']

            unique_key = song_name

            # Ensure the song is not a remix, live version, etc., and that the artist's listeners are within the limit
            if (
                unique_key not in song_titles_seen and
                track_id not in track_ids_seen and
                not any(keyword in song_name for keyword in exclude_keywords)
            ):
                artist_id = track['artists'][0]['id']
                if get_artist_monthly_listeners(artist_id) <= max_listeners:
                    unique_songs[unique_key] = (
                        track['id'],
                        track['name'],
                        track['artists'][0]['name'],
                        track['external_urls']['spotify']
                    )
                    track_ids_seen.add(track_id)
                    song_titles_seen.add(unique_key)

                if len(unique_songs) >= song_limit:
                    break

        offset += batch_size

    return list(unique_songs.values())[:song_limit]

# Function to explain why a particular song fits the user's input based on the genre/style using the OpenAI model
def explain_song_choice(input_text, track_name, artist):
    llm = create_openai_client()
    if not llm:
        return "error"
    try:
        explanation = llm.invoke(f"In one sentence, explain why the song '{track_name}' by {artist} fits the prompt '{input_text}'. Focus on musical style/genre.")
        explanation_content = explanation.content.strip().split('additional_kwargs')[0]
        return explanation_content
    except Exception as e:
        st.error(f"Error explaining song choice: {e}")
        return "error"

# Function to create a Spotify playlist and add the generated songs to it
def create_spotify_playlist(sp, user_id, playlist_name, track_ids):
    playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=True)
    sp.playlist_add_items(playlist_id=playlist['id'], items=track_ids)
    return playlist

# Streamlit form for gathering user input to generate the playlist
with st.form('playlist_form'):
    journal_text = st.text_area(
        '✨ Describe what kind of playlist you would like:',
        placeholder='E.g., I want a playlist that contains exciting songs',
        height=200
    )

    playlist_name = st.text_input('🎶 Enter your Spotify playlist name:')

    num_songs = st.number_input('🎵 How many songs would you like in the playlist?', min_value=1, max_value=100, value=1)

    max_listeners = st.number_input('🎤 Maximum number of monthly listeners for the artists:', min_value=0, value=10000, step=1000)

    submitted = st.form_submit_button('Generate Playlist 🎶')

    # Process the form when submitted
    if submitted:
        # Check if the OpenAI API key is valid
        if not openai_api_key or not openai_api_key.startswith('sk-'):
            typewriter('Please enter your OpenAI API key! ⚠', speed=100)
        else:
            # Analyze the user's input to generate mood/keywords for song search
            input_mood = analyze_input(journal_text)
            typewriter("Let's find some popular songs that match your vibe. 🎧", speed=100)

            # Retrieve a list of suggested songs based on the input
            song_list = get_songs(input_mood, num_songs, max_listeners)
            typewriter("Suggested Songs 🎵", speed=100)

            # Display the songs along with an explanation of why they fit
            if song_list:
                track_ids = []
                for idx, (track_id, name, artist, url) in enumerate(song_list, start=1):
                    explanation = explain_song_choice(input_mood, name, artist)
                    typewriter(f"{idx}. **{name}** by {artist} - [Listen on Spotify]({url}) 🎧", speed=100)
                    typewriter(f"This song fits your input because: {explanation}", speed=100)
                    track_ids.append(track_id)

                # Save the track IDs and playlist info to session state
                st.session_state['track_ids'] = track_ids
                st.session_state['playlist_name'] = playlist_name
                st.session_state['journal_text'] = journal_text
                st.session_state['num_songs'] = num_songs
                st.session_state['max_listeners'] = max_listeners

            else:
                typewriter("No suitable songs found.", speed=100)

# Button to create the playlist on Spotify using the generated track IDs
if 'track_ids' in st.session_state and st.session_state['track_ids']:
    create_playlist_button = st.button('Create Playlist on Spotify 🎉')

    if create_playlist_button:
        sp = get_spotify_client()
        user_info = sp.current_user()
        user_id = user_info['id']
        track_ids = st.session_state['track_ids']
        playlist_name = st.session_state.get('playlist_name', 'My Spotify Playlist')

        # Create the playlist and add songs to it
        if playlist_name and track_ids:
            playlist = create_spotify_playlist(sp, user_id, playlist_name, track_ids)
            playlist_url = playlist['external_urls']['spotify']
            st.success(f"Playlist '{playlist_name}' created! Redirecting you to the playlist...")
            st.markdown(f"[Click here to view the playlist]({playlist_url})", unsafe_allow_html=True)
        else:
            st.error("Please provide a valid playlist name.")

    # Button to regenerate the playlist with different songs based on the same input
    regenerate_button = st.button('Not happy? Generate a new playlist 🔄')

    if regenerate_button:
        # Regenerate the playlist using the previously entered input
        if 'journal_text' in st.session_state:
            journal_text = st.session_state['journal_text']
            input_mood = analyze_input(journal_text)
            typewriter("Let's find some different songs that match your vibe. 🎧", speed=100)

            # Use the previous number of songs and max_listeners from session state
            num_songs = st.session_state.get('num_songs', 10)  # Default value 10 if not found
            max_listeners = st.session_state.get('max_listeners', 10000)  # Default value if not found

            # Retrieve a new list of songs
            song_list = get_songs(input_mood, num_songs, max_listeners)
            typewriter("Suggested Songs 🎵", speed=100)

            # Display the regenerated list of songs
            if song_list:
                track_ids = []
                for idx, (track_id, name, artist, url) in enumerate(song_list, start=1):
                    explanation = explain_song_choice(input_mood, name, artist)
                    typewriter(f"{idx}. **{name}** by {artist} - [Listen on Spotify]({url}) 🎧", speed=100)
                    typewriter(f"This song fits your input because: {explanation}", speed=100)
                    track_ids.append(track_id)

                # Save the new track IDs to session state
                st.session_state['track_ids'] = track_ids
                st.session_state['playlist_name'] = playlist_name
            else:
                typewriter("No suitable songs found.", speed=100)
        else:
            st.error("Please submit the form first to generate a playlist.")
