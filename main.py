# NetLux movie databse website #
"""NetLux is a personal movie website that helps find movies."""

# Importing Flask tools for routes, form, sessions, and redirects
from flask import Flask, render_template, request, redirect, session, url_for

# Keeps function info when using login
from functools import wraps

# Connects to the SQLite3 database
import sqlite3

# Creates a Flask application
app = Flask(__name__)

# The Secret key to securely store information of session
app.secret_key = "key_for_netlux"

# Login details
EMAIL = "123@netlux.com"
PASSWORD = "123password"

# Tracking when the server started
server_started = False

# SQLite3 Database file
DATABASE = "movie.db"


def get_db_connection():
    """
    Create a connection to SQLite database.

    Add a row_factory to sqlite3.Row to allow getting columns by key names.
    """
    # Connects to the database
    conn = sqlite3.connect(DATABASE)

    # Allows database values to be accessed by their column name
    conn.row_factory = sqlite3.Row

    return conn


@app.before_request
def start_logout():
    """Clear old session data when server starts."""
    global server_started

    # Only clears the session when the server first starts
    if not server_started:
        session.clear()
        server_started = True


def login_needed(view):
    """Make sure user logins in before viewing protected data."""
    @wraps(view)
    def wrapped(*args, **kwargs):

        # Redirect users to login if they are not
        if not session.get('logged_in'):
            return redirect(url_for('login'))

        # Continue to the page if login is valid
        return view(*args, **kwargs)

    return wrapped


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Check the user's email and password is correct to allow access."""
    # Start the login with a cleared session
    session.clear()

    # No error message is displayed at the start
    error = None

    # Only process login details if form is submitted
    if request.method == 'POST':

        # Get the inputted email and password
        user_email = request.form.get('email')
        user_password = request.form.get('password')

        # Check if inputted details are correct
        if user_email == EMAIL and user_password == PASSWORD:

            # Keep the user's login session active
            session.permanent = True

            # Record that user is logged in
            session['logged_in'] = True

            # Show the welcome the screen after login
            session['show_welcome'] = True

            # Move user to the movie page
            return redirect(url_for('index'))

        # Display an error if any details are incorrect
        else:
            error = "Invalid email address or password."

    # Display the login page
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    """Log the user out and moves them to the login page."""
    # Removes all saved session information
    session.clear()

    # Returns to the Login page
    return redirect(url_for('login'))


@app.route('/')
@login_needed
def index():
    """
    Display movies from the database.

    Handles sorting, searching, filtering, and recommendations.
    """
    # Open the database
    conn = get_db_connection()

    # Show the welcome sign after successful login
    show_welcome = session.pop('show_welcome', False)

    # Get search option with text entered
    search_q = request.args.get('search', '').strip()

    # Get watch status option from URL
    status = request.args.get('status', '')

    # Get sorting options
    # Get selected sorting field
    sort_by = request.args.get('sort_by', 'Title')

    # Get sorting direction
    order = request.args.get('order', 'ASC')

    # Get filter options
    # Get genre
    select_genre = request.args.get('genre', '')

    # Get director
    select_director = request.args.get('director', '')

    # Get duration
    # Get minimum duration
    min_dur = request.args.get('min_duration', '')
    # Get maximum duration
    max_dur = request.args.get('max_duration', '')

    # Get recommendation option
    # Check whether the user requested a random movie
    recommend = request.args.get('recommend', '')

    # Checking sort values
    # Check allowed sorting options
    valid_sorts = ['Title', 'Director_Fname', 'Genre', 'Duration']

    # If Invalid option to sort, sort by title as default
    if sort_by not in valid_sorts:
        sort_by = 'Title'

    # Only allow ASC or DESC order
    if order.upper() not in ['ASC', 'DESC']:
        order = 'ASC'

    # Make order uppercase
    order = order.upper()

    # Making the movie query
    # Join the Movie, Director and Genre tables.
    query = """
    SELECT
    Movie.MovieID,
    Movie.Title,
    Director.Director_Fname,
    Director.Director_Lname,
    Genre.Genre,
    Movie.Duration,
    Movie.Description,
    Movie.Watched_status,
    CAST(Movie.Movie_poster AS TEXT) AS Movie_poster

    FROM Movie

    INNER JOIN Director
    ON Movie.DirectorID = Director.DirectorID

    INNER JOIN Genre
    ON Movie.GenreID = Genre.GenreID

    WHERE 1=1
    """

    # Stores values that are safely passed into the SQL query
    params = []

    # Filter by genre
    # Only show movies from the selected genre
    if select_genre:

        query += " AND Genre.Genre = ?"

        # Adds the selected genre to query to the parameters
        params.append(select_genre)

    # Filter by director
    # Only show movies from selected director
    if select_director:

        query += " AND Movie.DirectorID = ?"

        # Add DirectorID to query parameters
        params.append(select_director)

    # Filter by minimum duration
    # Only show movies at least this many minutes long
    if min_dur:
        query += " AND Movie.Duration >= ?"

        # Add minimum duration to query to the parameters
        params.append(min_dur)

    # Filter by maximum duration
    # Only show movies no longer than this many minutes
    if max_dur:
        query += " AND Movie.Duration <= ?"

        # Add maximum duration to query parameters
        params.append(max_dur)

    # Search for movies using any database column
    if search_q:

        query += """
        AND (
            Movie.Title LIKE ?
            OR Director.Director_Fname LIKE ?
            OR Director.Director_Lname LIKE ?
            OR Genre.Genre LIKE ?
            OR CAST(Movie.Duration AS TEXT) LIKE ?
            OR Movie.Description LIKE ?
            OR CAST(Movie.Watched_status AS TEXT) LIKE ?
        )
        """

        # Add the same search term for each searchable column
        search_term = f"%{search_q}%"

        # Allows the search text to appear anywhere in the title
        params.extend([
            search_term,
            search_term,
            search_term,
            search_term,
            search_term,
            search_term,
            search_term
            ])

    # Watch Status
    # Get Watchlist movies
    if status == 'watchlist':
        query += " AND Movie.Watched_status = 0"

    # Get Watched movies
    elif status == 'watched':
        query += " AND Movie.Watched_status = 1"

    # Random recommendation or sorting

    # Get one movie from the current filtered results
    if recommend == '1':
        query += """
        ORDER BY RANDOM()
        LIMIT 1
        """

    else:
        # Sort the matching movies using the selected column and direction
        query += f" ORDER BY {sort_by} {order}"

    # Run the movie query
    # Execute the completed SQL query
    movies = conn.execute(query, params).fetchall()

    # Get Genres
    # Get genres for the filter dropdown
    genres = conn.execute("""
    SELECT DISTINCT Genre FROM Genre
    ORDER BY Genre ASC
    """).fetchall()

    # Get Directors
    # Get directors for the filter options
    directors = conn.execute("""
    SELECT DirectorID, Director_Fname, Director_Lname FROM Director
    ORDER BY Director_Fname ASC, Director_Lname ASC
    """).fetchall()

    # Stores the director's name for the page title
    selected_director = ""

    # Only look for the director name if it was selected
    if select_director:

        # Find the selected director from dropdown data
        for director in directors:

            if str(director['DirectorID']) == str(select_director):

                # Combine first and last name
                selected_director = (
                    f"{director['Director_Fname']} "
                    f"{director['Director_Lname']}"
                )

                break

    # Stores each active option as part of the page title
    title_parts = []

    # Add the selected watch status
    if status == 'watchlist':
        title_parts.append("Watchlist")

    elif status == 'watched':
        title_parts.append("Watched")

    # Add searched text to title
    if search_q:
        title_parts.append(f'Search: "{search_q}"')

    # Add selected genre to title
    if select_genre:
        title_parts.append(f"Genre: {select_genre}")

    # Add selected director to title
    if selected_director:
        title_parts.append(f"Director: {selected_director}")

    # Add selected duration range to title
    if min_dur and max_dur:
        title_parts.append(f"Duration: {min_dur}-{max_dur} mins")

    # If only minimum duration is selected add to title
    elif min_dur:
        title_parts.append(f"Duration: {min_dur}+ mins")

    # If only maximum duration is selected add to title
    elif max_dur:
        title_parts.append(f"Duration: up to {max_dur} mins")

    # Names for each sorting field
    sort_names = {
        'Title': 'Title',
        'Director_Fname': 'Director',
        'Genre': 'Genre',
        'Duration': 'Duration'
    }

    # Only shows sorting in title if sorting selected
    if request.args.get('sort_by'):

        # Arrows representing order
        if order == 'ASC':
            sort_arrow = "↑"

        else:
            sort_arrow = "↓"

        title_parts.append(f"Sorted by {sort_names[sort_by]} {sort_arrow}")

    # Default title NetLux
    if not title_parts:
        page_title = "NetLux"

    else:
        page_title = " ~ ".join(title_parts)

    # All database work is finished
    conn.close()

    # Display movie page
    # Send all data to movies.html
    return render_template(
        'movies.html',
        movies=movies,
        genres=genres,
        directors=directors,
        title=page_title,
        show_welcome=show_welcome,
        sortby=sort_by,
        order=order
        )


# Run website
if __name__ == '__main__':
    # Run Flask on port 5000 with auto debug
    app.run(host='0.0.0.0', port=5000, debug=True)
