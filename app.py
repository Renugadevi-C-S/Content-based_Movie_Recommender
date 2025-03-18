import streamlit as st
import pandas as pd
import difflib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import requests
import random
import time

# Set page config (MUST BE THE FIRST STREAMLIT COMMAND)
st.set_page_config(page_title="Movie Recommender", layout="wide")

# Initialize session state for favorites, recommendations, and current page
if 'favorites' not in st.session_state:
    st.session_state.favorites = []
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = []
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Home"
if 'selected_movie' not in st.session_state:
    st.session_state.selected_movie = None
if 'filtered_movies' not in st.session_state:
    st.session_state.filtered_movies = []

# Load dataset
@st.cache_data  # Cache the dataset for faster loading
def load_data():
    movies_data = pd.read_csv('movies.csv')
    selected_features = ['genres', 'keywords', 'tagline', 'cast', 'director']
    for feature in selected_features:
        movies_data[feature] = movies_data[feature].fillna('')
    movies_data['combined_features'] = (
        movies_data['genres'] + ' ' +
        movies_data['keywords'] + ' ' +
        movies_data['tagline'] + ' ' +
        movies_data['cast'] + ' ' +
        movies_data['director']
    )
    vectorizer = TfidfVectorizer()
    feature_vectors = vectorizer.fit_transform(movies_data['combined_features'])
    similarity = cosine_similarity(feature_vectors)
    return movies_data, similarity

movies_data, similarity = load_data()

# Fetch movie poster, director, trailer, and rating using TMDB API
def fetch_movie_details(title, movies_data):
    TMDB_API_KEY = '711e04f6f9c64b4b56a9fdd452624371'  # Your TMDB API key
    base_url = 'https://api.themoviedb.org/3'
    
    try:
        # Step 1: Search for the movie
        search_url = f'{base_url}/search/movie?api_key={TMDB_API_KEY}&query={title}'
        search_response = requests.get(search_url)
        search_response.raise_for_status()  # Raise an error for bad responses
        search_data = search_response.json()
        
        if search_data['results']:
            movie_id = search_data['results'][0]['id']
            
            # Step 2: Fetch movie details
            details_url = f'{base_url}/movie/{movie_id}?api_key={TMDB_API_KEY}'
            details_response = requests.get(details_url)
            details_response.raise_for_status()
            details_data = details_response.json()
            
            # Step 3: Fetch movie poster
            poster_path = details_data.get('poster_path', '')
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "https://via.placeholder.com/500x750?text=No+Poster+Available"
            
            # Step 4: Fetch director from CSV instead of API
            movie_row = movies_data[movies_data['title'].str.lower() == title.lower()]  # Match title case-insensitively
            director = movie_row['director'].values[0] if not movie_row.empty else "Unknown"  # Get director from CSV

            # Step 5: Fetch trailer
            videos_url = f'{base_url}/movie/{movie_id}/videos?api_key={TMDB_API_KEY}'
            videos_response = requests.get(videos_url)
            videos_response.raise_for_status()
            videos_data = videos_response.json()
            
            # Extract YouTube trailer key
            trailer_key = None
            for video in videos_data.get('results', []):
                if video['type'] == 'Trailer' and video['site'] == 'YouTube':
                    trailer_key = video['key']
                    break
            
            trailer_url = f"https://www.youtube.com/embed/{trailer_key}" if trailer_key else None
            
            # Step 6: Fetch rating
            rating = details_data.get('vote_average', 0)
            
            return {
                'title': details_data.get('title', title),
                'poster': poster_url,
                'release_date': details_data.get('release_date', ''),
                'director': director,
                'trailer': trailer_url,
                'rating': rating
            }
        else:
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching movie details: {e}")
        return None

# Function to add a movie to favorites
def add_to_favorites(movie):
    if movie not in st.session_state.favorites:
        st.session_state.favorites.append(movie)
        success_message = st.success(f"Added {movie['title']} to favorites!")
        time.sleep(3)  # Wait for 3 seconds
        success_message.empty()  # Remove the message
    else:
        st.warning(f"{movie['title']} is already in favorites!")

# Custom CSS for styling
st.markdown("""
    <style>
    /* General Styles */
    .stButton button {
        background: linear-gradient(135deg, #2c3e50, #34495e);
        color: white;
        padding: 10px 20px;
        border: none;
        border-radius: 8px; /* Rounded rectangle */
        cursor: pointer;
        font-size: 14px;
        font-weight: bold;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stButton button:hover {
        background: linear-gradient(135deg, #34495e, #2c3e50);
        transform: scale(1.05);
        box-shadow: 0 6px 8px rgba(0, 0, 0, 0.2);
        color: white !important; /* Ensure text color doesn't change */
    }
    h1 {
        color: #4CAF50;
    }
    
     /* --- GENRE GRID STYLES (NEW) --- */
    .genre-card {
        text-align: center;
        cursor: pointer;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .genre-card:hover {
        transform: scale(1.05);
        box-shadow: 0px 4px 8px rgba(255, 255, 255, 0.3);
    }
    .genre-img {
        width: 100%;
        border-radius: 10px;
    }
    .genre-title {
        font-size: 16px;
        font-weight: bold;
        margin-top: 5px;
    }
            
    /* Movie Card Styles */
    .movie-card {
        position: relative;
        text-align: center;
        margin-bottom: 20px;
        background: linear-gradient(135deg, #1a1a1a, #333333);
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        overflow: hidden;
    }
    .movie-card:hover {
        transform: scale(1.03);
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.5);
    }
    .movie-card img {
        border-radius: 10px;
        width: 100%;
        height: auto;
        object-fit: cover;
        transition: transform 0.3s ease;
    }
    .movie-card:hover img {
        transform: scale(1.05);
    }
    
    /* Movie Title with Gradient Background */
    .movie-title {
        background: linear-gradient(90deg, #ff8a00, #e52e71);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 20px;
        font-weight: bold;
        margin: 15px 0 10px 0;
        position: relative;
        z-index: 2;
    }
    
    /* Movie Details */
    .movie-details {
        font-size: 14px;
        color: #ddd;
        margin: 5px 0;
    }
    .movie-details i {
        margin-right: 5px;
    }
            
    /* --- MORE INFO POPUP (NEW) --- */
    .movie-info {
        display: none;
        position: absolute;
        bottom: 10px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 5px;
        border-radius: 5px;
        font-size: 14px;
    }
    .movie-card:hover .movie-info {
        display: block;
    }
    
    /* Similarity Score Text */
    .similarity-label {
        font-size: 4px;
        color: rgba(255, 255, 255, 0.5);
        margin-bottom: 0.025px; 
    }
    
    /* Improved Progress Bar */
    .similarity-container {
        display: flex;
        align-items: center;
        margin: 10px 0;
    }
    .similarity-bar {
        flex-grow: 1;
        height: 10px;
        background-color: #444;
        border-radius: 5px;
        overflow: hidden;
    }
    .similarity-bar div {
        height: 100%;
        background: linear-gradient(90deg, #00c6ff, #0072ff);
        border-radius: 5px;
    }
    .similarity-percent {
        color: #00c6ff;
        font-weight: bold;
        font-size: 12px;
        margin-left: 10px;
    }
    
    /* Star Rating Styles */
    .star-rating {
        color: #ffd700;
        font-size: 14px;
        margin-top: 5px;
    }
    
    /* Loading Spinner Styles */
    .stSpinner > div {
        border-color: #2c3e50 !important;
        border-top-color: transparent !important;
        border-width: 3px !important;
        width: 30px !important;
        height: 30px !important;
    }
    .stSpinner > div::after {
        content: "Fetching recommendations...";
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        color: #2c3e50;
        font-size: 14px;
        font-weight: bold;
    }
    
    /* Gradient Buttons */
    .gradient-button {
        background: linear-gradient(90deg, #ff8a00, #e52e71);
        color: white;
        padding: 10px 20px;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        font-size: 14px;
        font-weight: bold;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .gradient-button:hover {
        background: linear-gradient(90deg, #e52e71, #ff8a00);
        transform: scale(1.05);
        box-shadow: 0 6px 8px rgba(0, 0, 0, 0.2);
    }
    
    /* Welcome Text */
    .welcome-text {
        font-size: 18px;
        color: #4CAF50;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# Navigation Bar
st.sidebar.title("  Menu")
page = st.sidebar.radio(" ", ["Home", "Categories", "Recommendations", "Trailers", "Favorites"], index=["Home", "Categories", "Recommendations", "Trailers", "Favorites"].index(st.session_state.current_page))

# Home Page
if page == "Home":
    st.session_state.current_page = "Home"
    st.title("🎬 Movie Recommendation System")
    st.markdown('<p class="welcome-text">Welcome to the Movie Recommender! Enter a movie you like, and we\'ll recommend similar movies.</p>', unsafe_allow_html=True)

    # Input Form
    movie_name = st.text_input("Enter a movie name:", placeholder="Type a movie name...")
    if st.button("Get Recommendations", key="get_recommendations"):
        if movie_name:
            with st.spinner(""):
                list_of_all_titles = movies_data['title'].tolist()
                find_close_match = difflib.get_close_matches(movie_name, list_of_all_titles)

                if find_close_match:
                    close_match = find_close_match[0]
                    index_of_the_movie = movies_data[movies_data.title == close_match].index[0]

                    similarity_score = list(enumerate(similarity[index_of_the_movie]))
                    sorted_similar_movies = sorted(similarity_score, key=lambda x: x[1], reverse=True)

                    # Store recommendations in session state
                    st.session_state.recommendations = []
                    for movie in sorted_similar_movies[1:11]:  # Skip the first result (input movie)
                        index = movie[0]
                        title_from_index = movies_data.iloc[index]['title']
                        genre = movies_data.iloc[index]['genres']
                        movie_details = fetch_movie_details(title_from_index,movies_data)
                        similarity_score = round(movie[1] * 100, 2)  # Convert similarity to percentage

                        if movie_details:
                            st.session_state.recommendations.append({
                                'title': title_from_index,
                                'genre': genre,
                                'poster': movie_details['poster'],
                                'release_date': movie_details['release_date'],
                                'director': movie_details['director'],
                                'trailer': movie_details['trailer'],
                                'similarity': similarity_score,
                                'rating': movie_details['rating']
                            })

                    # Redirect to Recommendations page
                    st.session_state.current_page = "Recommendations"
                    st.rerun()  # Refresh the page to switch to Recommendations
                else:
                    st.warning("No close match found. Please try another movie name.")
        else:
            st.warning("Please enter a movie name.")

# Categories Page
elif page == "Categories":
    # Ensure session state is initialized for dropdowns
    if "selected_genre" not in st.session_state:
        st.session_state.selected_genre = ""
    if "selected_director" not in st.session_state:
        st.session_state.selected_director = ""
    if "selected_decade" not in st.session_state:
        st.session_state.selected_decade = ""
    if "selected_subfilter" not in st.session_state:
        st.session_state.selected_subfilter = ""
    if "filtered_movies" not in st.session_state:
        st.session_state.filtered_movies = []
    if "movies_loaded" not in st.session_state:
        st.session_state.movies_loaded = 20

    st.session_state.current_page = "Categories"
    st.title("🎬 Categories")

    # --- Genre-Based Filtering ---
    st.subheader("📌 Filter by Genre")
    unique_genre_sets = set()
    for genre_string in movies_data['genres'].dropna():
        genre_tuple = tuple(sorted(genre_string.split(', ')))
        unique_genre_sets.add(genre_tuple)

    formatted_genres = sorted([' '.join(g) for g in unique_genre_sets])
    selected_genre = st.selectbox("Choose a genre", [""] + formatted_genres, index=0, key="selected_genre")

    # --- Director-Based Filtering ---
    st.subheader("🎥 Filter by Director")
    directors = sorted(movies_data['director'].dropna().unique().tolist())
    selected_director = st.selectbox("Choose a director", [""] + directors, index=0, key="selected_director")

    # --- Decade-Based Filtering ---
    st.subheader("⏳ Filter by Decade")
    decades = {
        "": None,
        "1920s": (1920, 1929), "1930s": (1930, 1939), "1940s": (1940, 1949),
        "1950s": (1950, 1959), "1960s": (1960, 1969), "1970s": (1970, 1979),
        "1980s": (1980, 1989), "1990s": (1990, 1999), "2000s": (2000, 2009),
        "2010s": (2010, 2019), "2020s": (2020, 2025)
    }
    selected_decade = st.selectbox("Choose a decade", list(decades.keys()), index=0, key="selected_decade")

    # --- Sub-filtering within the selected decade ---
    subfilters = {
        "1920s": ["1920-1921", "1922-1923", "1924-1925", "1926-1927", "1928-1929"],
        "1930s": ["1930-1931", "1932-1933", "1934-1935", "1936-1937", "1938-1939"],
        "1940s": ["1940-1941", "1942-1943", "1944-1945", "1946-1947", "1948-1949"],
        "1950s": ["1950-1951", "1952-1953", "1954-1955", "1956-1957", "1958-1959"],
        "1960s": ["1960-1961", "1962-1963", "1964-1965", "1966-1967", "1968-1969"],
        "1970s": ["1970-1971", "1972-1973", "1974-1975", "1976-1977", "1978-1979"],
        "1980s": ["1980-1981", "1982-1983", "1984-1985", "1986-1987", "1988-1989"],
        "1990s": ["1990-1991", "1992-1993", "1994-1995", "1996-1997", "1998-1999"],
        "2000s": ["2000-2001", "2002-2003", "2004-2005", "2006-2007", "2008-2009"],
        "2010s": ["2010-2011", "2012-2013", "2014-2015", "2016-2017", "2018-2019"],
        "2020s": ["2020-2021", "2022-2023", "2024-2025"]
    }

    if selected_decade in subfilters:
        selected_subfilter = st.selectbox("Choose a year range", [""] + subfilters[selected_decade], index=0, key="selected_subfilter")
    else:
        selected_subfilter = ""

    # --- Apply Filters ---
    filtered_movies = movies_data.copy()
    filters_applied = False
    total_movies = 0

    if selected_decade and selected_subfilter:
        start_year, end_year = map(int, selected_subfilter.split('-'))
        filtered_movies = filtered_movies[
            (filtered_movies['release_date'].astype(str).str[:4].astype(float) >= start_year) &
            (filtered_movies['release_date'].astype(str).str[:4].astype(float) <= end_year)
        ]
        total_movies = len(filtered_movies)
        filters_applied = True
    elif selected_decade:
        st.warning("Please select a sub-filter range to display movies.")

    if selected_genre:
        selected_genre_sorted = ' '.join(sorted(selected_genre.split()))
        filtered_movies = filtered_movies[
            filtered_movies['genres'].fillna('').apply(lambda g: ' '.join(sorted(g.split(', '))) == selected_genre_sorted)
        ]
        total_movies = len(filtered_movies)
        filters_applied = True

    if selected_director:
        filtered_movies = filtered_movies[filtered_movies['director'] == selected_director]
        total_movies = len(filtered_movies)
        filters_applied = True

    # --- Display Total Movies Count with Title ---
    if filters_applied:
        st.markdown("<h2 style='color: #da785b; font-size: 38px; font-weight: bold;'>🎞️ Filtered Movies</h2>", unsafe_allow_html=True)
        if total_movies > 0:
            st.success(f"Total movies in this range: **{total_movies}**")
        #else:
            #st.warning("No movies found in this range.")

    # --- Lazy Loading for All Three Filters ---
    if filters_applied and not filtered_movies.empty:
        movies_per_load = 20
        displayed_movies = filtered_movies.iloc[:st.session_state.movies_loaded]

        cols = st.columns(5)
        for i, (_, movie) in enumerate(displayed_movies.iterrows()):
            with cols[i % 5]:
                movie_title = movie['title']
                movie_details = fetch_movie_details(movie_title, movies_data)

                if movie_details:
                    release_year = str(movie.get('release_date', 'N/A'))[:4]
                    director_name = movie_details.get('director', 'N/A')
                    rating = movie_details.get('rating', 'N/A')

                    st.image(movie_details['poster'], use_container_width=True)
                    st.write(f"**{movie_title}**")
                    st.write(f"🎬 {director_name}")
                    st.write(f"📅 {release_year}  |  ⭐ {rating}")

        if len(filtered_movies) > st.session_state.movies_loaded:
            if st.button("⬇️ Load More", key="load_more", help="Click to load more movies", use_container_width=True):
                st.session_state.movies_loaded += movies_per_load
                st.rerun()
    elif filters_applied:
        st.warning("No movies found for the selected filters.")

    # --- Reset Filtering Button (Appears Only When Filters Are Applied) ---
    if selected_genre or selected_director or selected_decade or (selected_decade and selected_subfilter):
        if st.button("🔄 Reset Filtering", key="reset_filter",use_container_width=True):
            for key in ["selected_genre", "selected_director", "selected_decade", "selected_subfilter", "filtered_movies", "movies_loaded"]:
                del st.session_state[key]
            st.rerun()

# Recommendations Page
elif page == "Recommendations":
    st.session_state.current_page = "Recommendations"
    st.title("🍿 Recommendations")
    
    if st.session_state.recommendations:
        st.write("Here are the top 10 similar movies:")
        cols = st.columns(4)  # Display 4 movies per row
        for i, movie in enumerate(st.session_state.recommendations):
            with cols[i % 4]:
                # Movie card
                st.markdown(
                    f"""
                    <div class="movie-card">
                        <img src="{movie['poster']}" alt="{movie['title']}">
                        <p class="movie-title">{movie['title']}</p>
                        <p class="movie-details"><i class="fas fa-calendar-alt"></i> {movie['release_date'][:4]}</p>
                        <p class="movie-details"><i class="fas fa-user"></i> {movie['director']}</p>
                        <p class="movie-details"><i class="fas fa-film"></i> {movie['genre']}</p>
                        <div class="star-rating">
                            {'⭐' * int(round(movie['rating'] / 2))} ({movie['rating']}/10)
                        </div>
                        <p class="similarity-label">Similarity Score</p>
                        <div class="similarity-container">
                            <div class="similarity-bar">
                                <div style="width: {movie['similarity']}%;"></div>
                            </div>
                            <div class="similarity-percent">{movie['similarity']}%</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                # Add a button to add the movie to favorites
                if st.button(f"Add {movie['title']} to Favorites", key=f"add_{i}"):
                    add_to_favorites(movie)
                
                # Add a button to watch the trailer
                if st.button(f"Watch Trailer for {movie['title']}", key=f"trailer_{i}"):
                    st.session_state.selected_movie = movie
                    success_message = st.success(f"Redirecting to Trailers page to watch the trailer for {movie['title']}...")
                    time.sleep(2)  # Wait for 2 seconds
                    success_message.empty()  # Remove the message
                    st.session_state.current_page = "Trailers"
                    st.rerun()  # Redirect to Trailers page
    else:
        st.warning("No recommendations found. Please go back to the Home page and enter a movie name.")

    # Add "Reset Recommendations" button at the bottom
    st.write("---")

    # Navigation buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Reset Recommendations", key="reset_recommendations"):
            st.session_state.recommendations = []
            st.session_state.current_page = "Home"
            st.rerun()
    with col2:
        if st.button("Go to Favorites Page", key="go_to_favorites"):
            st.session_state.current_page = "Favorites"
            st.rerun()  # Redirect to Favorites Page

# Trailers Page
elif page == "Trailers":
    st.session_state.current_page = "Trailers"
    st.title("🎥 Trailers")
    
    # Navigation buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Go to Home Page"):
            st.session_state.current_page = "Home"
            st.rerun()
    with col2:
        if st.button("Go to Recommendations"):
            st.session_state.current_page = "Recommendations"
            st.rerun()
    
    # Horizontal line
    st.write("---")
    
    # Display the trailer for the selected movie
    if st.session_state.selected_movie:
        st.write(f"### Trailer for {st.session_state.selected_movie['title']}")
        if st.session_state.selected_movie['trailer']:
            st.video(st.session_state.selected_movie['trailer'])
        else:
            st.warning("No trailer available for this movie.")
    else:
        st.warning("No trailers found. Please go back to the Home page and enter a movie name.")

# Favorites Page
elif page == "Favorites":
    st.session_state.current_page = "Favorites"
    st.title("⭐ Favorites")
    
    # Add a "Clear Favorites" button
    if st.session_state.favorites:
        if st.button("Clear All Favorites"):
            st.session_state.favorites = []
            st.rerun()
    
    if st.session_state.favorites:
        st.write("Here are your favorite movies:")
        cols = st.columns(4)  # Display 4 movies per row
        for i, movie in enumerate(st.session_state.favorites):
            with cols[i % 4]:
                st.markdown(
                    f"""
                    <div class="movie-card">
                        <img src="{movie['poster']}" alt="{movie['title']}">
                        <p class="movie-title">{movie['title']}</p>
                        <p class="movie-details"><i class="fas fa-film"></i> {movie['genre']}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if st.button(f"Remove {movie['title']}", key=f"remove_{i}"):
                    st.session_state.favorites.remove(movie)
                    st.rerun()  # Refresh the page to update the list
    else:
        st.write("No favorites added yet.")

     # Horizontal line
    st.write("---")

    # Navigation buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Go to Home Page"):
            st.session_state.current_page = "Home"
            st.rerun()
    with col2:
        if st.button("Go to Recommendations"):
            st.session_state.current_page = "Recommendations"
            st.rerun()