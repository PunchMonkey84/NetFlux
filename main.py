## Movie Website ##
# This a person movie website that stores watched and watchlist movies.


# Importing Flask
from flask import Flask, render_template, request

# Importing database
import sqlite3 
from sqlite3 import Error

app = Flask(__name__)

# Database file path
DATABASE = "movie.db"

# Database functions 


def create_connection(db_file):
    """
    Create a connection to SQLite database.
    Add a row_factory to sqlite3.Row to allow getting columns by key names.
    """

    conn = None

    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        return conn

    # Print any error if problem with database
    except Error as e:
        print(e)
    return conn

# Query constant combining the 3 tables to find components
QUERY = """
SELECT Movie.MovieID,
Movie.Title,
Director.Director_Fname,
Director.Director_Lname,
Genre.Genre,
Movie.Duration,
Movie.Description,
Movie.Watched_status
FROM Movie
INNER JOIN Director ON Movie.DirectorID = Director.DirectorID
INNER JOIN Genre ON Movie.GenreID = Genre.GenreID
"""


def get_filter():
    """
    Get options for a filtering form.
    """
    # Connection to database
    conn = create_connection(DATABASE)
    cursor = conn.cursor()

    # Genre filter options
    cursor.execute("SELECT DISTINCT Genre From Genre ORDER BY Genre")
    genres = [row['Genre'] for row in cursor.fetchall()]

    # Director filter options
    cursor.execute("SELECT DISTINCT Director_Fname || ' ' || Director_Lname AS FullName FROM Director ORDER BY FullName")
    directors = [row['FullName'] for row in cursor.fetchall()]

    # Getting filter options
    conn.close()
    return {
        'genres': genres,
        'directors': directors
    }

@app.route('/')
@app.route('/movies')
@app.route('/movies/<status>')
def render_filtered(status=None):
    """
    Handle movie listing and filtering.
    """
    # Grab query parameters submitted from the HTML filter form
    chosen_genre = request.args.get('genre')
    chosen_director = request.args.get('director')
    mini_duration = request.args.get('min_duration')
    maxi_duration = request.args.get('max_duration')

    # Store raw choices in a filter dictionary
    raw_filters = {
        'genre': chosen_genre,
        'director': chosen_director,
        'min_duration':mini_duration,
        'max_duration': maxi_duration
    }

    # Remove empty values and default
    work_filters = {k: v for k, v in raw_filters.items() if v and v != 'all'}

    query = QUERY
    params = []
    where = []

    # Make a where and params list where conditions are met
    if 'genre' in work_filters:
        where.append("Genre.Genre = ?")
        params.append(work_filters['genre'])

    if 'director' in work_filters:
        where.append("Director.Director_Fname || ' ' || Director.Director_Lname = ?")
        params.append(work_filters['director'])

    # For duration filter, convert text to numeric for comparison
    if 'min_duration' in work_filters:
        where.append("CAST(Movie.Duration AS INTEGER) >= ?")
        params.append(int(work_filters['min_duration']))

    if 'max_duration' in work_filters:
        where.append("CAST(Movie.Duration AS INTEGER) <= ?")
        params.append(int(work_filters['max_duration']))

    # Filter navigation for watched and watchlist movies
    if status in ['0', 'watchlist']:
        where.append("Movie.Watched_status = 0")
    elif status in ['1', 'watched']:
        where.append("Movie.Watched_status = 1")

    # Use active conditions and logic
    if where:
        query += " WHERE " + " AND ".join(where)

    # Query against SQLite database
    conn = create_connection(DATABASE)
    cursor = conn.cursor()
    cursor.execute(query, params)
    movie_list = cursor.fetchall()
    conn.close()

    # Page title for jinja display depending on what page
    if status in ['0', 'watchlist']:
        page_title = "Watchlist Movies"
    elif status in ['1', 'watched']:
        page_title = "Watched Movies"
    elif work_filters:
        page_title = "Filtered Movies"
    else:
        page_title = "All Movies"

    # Use HTML template to pass the input dataset
    return render_template(
        'movies.html',
        movies=movie_list,
        title=page_title,
        filter_options=get_filter(),
        work_filters=work_filters,
        order='asc',
        status=status or 'all'
    )


@app.route("/search", methods=['GET', 'POST'])
def search():
    """
    Create a global Search bar to find specific movies
    """
    if request.method == 'POST':
        search_item = request.form.get('search', '')
    else:
        search_item = request.args.get('search', '')

    # Get each search key with wildcard
    wildcard_search = f"%{search_item}%"

    #SQLite query search using database columns
    query = f"""
    {QUERY} 
    Where (Movie.Title LIKE ? 
    OR Director.Director_Fname LIKE ? 
    OR Director.Director_Lname LIKE ? 
    OR Genre.Genre LIKE ? 
    OR Movie.Duration LIKE ? 
    OR Movie.Description LIKE ?)
    """

    conn = create_connection(DATABASE)
    cursor = conn.cursor()
    # Use parameters to bind each wildcard placeholder
    cursor.execute(query, (wildcard_search, wildcard_search, wildcard_search, wildcard_search, wildcard_search, wildcard_search))
    movie_list = cursor.fetchall()
    conn.close()

    return render_template(
        'movies.html', 
        movies=movie_list, 
        title=f"Search Results for '{search_item}'", 
        order='asc', 
        status='all',
        filter_options=get_filter(),
        work_filters={}
        )


@app.route('/sort/<col_name>')
def render_sortpage(col_name):
    """
    Handle column sorting when table header is clicked
    """
    order = request.args.get('order', 'asc')
    status = request.args.get('status', 'all')

    # when clicked change order of sort direction
    sql_order = 'ASC' if order == 'asc' else 'DESC'
    new_order = 'desc' if order == 'asc' else 'asc'

    # Validate whether a column can be sorted
    valid_columns = ['Title','Director_Fname', 'Genre', 'Duration']
    if col_name not in valid_columns:
        col_name= 'Title'

    # Apply status filter to make sure there is still active context while sorting
    if str(status) == '0' or str(status).lower() == 'watchlist':
        sql_where = "WHERE Movie.Watched_status = 0"
        status_label = "Watchlist"
    elif str(status) == '1' or str(status).lower() == 'watched':
        sql_where = "WHERE Movie.Watched_status = 1"
        status_label = "Watched"
    else:
        sql_where = ""
        status_label = "All"

    # Validate Director column to sort
    if col_name == 'Director_Fname':
        query = f"{QUERY} {sql_where} ORDER BY Director_Fname {sql_order}, Director_Lname {sql_order}"
        display_name = 'Director'
    else:
        query = f"{QUERY} {sql_where} ORDER BY {col_name} {sql_order}"
        display_name = col_name

    # Run sorted database query
    conn = create_connection(DATABASE)
    cursor = conn.cursor()
    cursor.execute(query)
    movie_list = cursor.fetchall()
    conn.close()

    return render_template(
        'movies.html', 
        movies=movie_list, 
        title=f"{status_label} Movies Sorted by {display_name} ({sql_order})", 
        order=new_order, 
        status=status,
        filter_options=get_filter(),
        work_filters={}
        )
    
# Run website
if __name__ == '__main__':
    # Run Flask on port 5000 with auto debug
    app.run(host='0.0.0.0', port=5000, debug=True)