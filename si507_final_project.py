import requests, pandas, sqlite3, os.path, base64
from bs4 import BeautifulSoup
from fcache.cache import FileCache
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from email.mime.text import MIMEText
from apiclient import errors
from pretty_html_table import build_table


# methods for interacting with SQLite DB
def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    Parameters
    ----------
    db_file
        database file
    sql
        a SQL statement
    Returns
    -------
    Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)

    return conn

def execute_query(db, query, query_tuple=None):
    """ execote SQL query in the db
    Parameters
    ----------
    db
        Database file path
    query
        a SQL statement
    query_tuple
        query params
    Returns
    -------
    just-inserted ID
    """
    conn = create_connection(db)
    if conn is not None:
      try:
        c = conn.cursor()
        if query_tuple is None:
            c.execute(query)
        else:
            c.execute(query, query_tuple)
        conn.commit()
      except Exception as e:
        print(e)
    else:
      print("Error! cannot create the database connection.")

    return c.lastrowid

def fetch_result(db, query, query_tuple=None):
    ''' Fetches the resultset from db   
    Parameters
    ----------
    db
        Database file path
    query
        a SQL statement
    query_tuple
        query params
    Returns
    -------
    list
        resultset
    '''
    conn = create_connection(db)
    if conn is not None:
      try:
        c = conn.cursor()
        if query_tuple is None:
            result = c.execute(query).fetchall()
        else:
            result = c.execute(query, query_tuple).fetchall()
        conn.close()
      except Exception as e:
        print(e)
    else:
      print("Error! cannot create the database connection.")
    
    return result


# methods for sending email
def create_message(sender, to, subject, message_text):
  """Create a message for an email.

  Args:
    sender: Email address of the sender.
    to: Email address of the receiver.
    subject: The subject of the email message.
    message_text: The text of the email message.

  Returns:
    An object containing a base64url encoded email object.
  """
  message = MIMEText(message_text, 'html')
  message['to'] = to
  message['from'] = sender
  message['subject'] = subject
  b64_bytes = base64.urlsafe_b64encode(message.as_bytes())
  b64_string = b64_bytes.decode()
  body = {'raw': b64_string}
  return body
 
def send_message(service, user_id, message):
  """Send an email message.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    message: Message to be sent.

  Returns:
    Sent Message.
  """
  try:
    message = (service.users().messages().send(userId=user_id, body=message)
               .execute())
    print('Message Id: %s' % message['id'])
    return message
  except errors.HttpError as error:
    print('An error occurred: %s' % error)

def send_email():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)

    message = create_message(EMAIL_FROM, EMAIL_TO, EMAIL_SUBJECT, EMAIL_CONTENT)

    sent = send_message(service,'me', message)
    print(sent)


#take the input from the user
email = input("Enter your email id: ")
query = input("Enter the type of jobs you would like to search: ")
location = input("Enter the job location: ")

#validate the input received
#TODO

#first check in the cache; if not there, scrape the data from the website
indeed_cache = FileCache('fcacheFileStore', flag='cs')

unique_key = email+query+location

db = r"C:\Users\anura\Desktop\Aditi\Winter 2021\507\Final Project\Code\indeed_sqlite.db"
#create tables if do not exists
sql_create_jobs_table = """ CREATE TABLE IF NOT EXISTS jobs (
                                id integer PRIMARY KEY autoincrement,
                                title text,
                                location text,
                                company text,
                                salary text,
                                ratings text,
                                url text NOT NULL,
                                CONSTRAINT UC_jobs UNIQUE (url)
                              ); """
execute_query(db, sql_create_jobs_table)

sql_create_users_table = """ CREATE TABLE IF NOT EXISTS users (
                                id integer PRIMARY KEY autoincrement,
                                email_id text NOT NULL, 
                                search_query text NOT NULL,
                                location text NOT NULL,
                                CONSTRAINT UC_users UNIQUE (email_id,search_query,location)
                              ); """
execute_query(db, sql_create_users_table)

sql_create_users_jobs_table = """ CREATE TABLE IF NOT EXISTS users_jobs (
                                user_id integer,
                                job_id integer,
                                FOREIGN KEY(user_id) REFERENCES users(id),
                                FOREIGN KEY(job_id) REFERENCES jobs(id)
                              ); """
execute_query(db, sql_create_users_jobs_table)

l = []
df=pandas.DataFrame(l)

# using cache to check if the site is already scrapped for the user inputs
if unique_key in indeed_cache:
    print("Data in cache")
    site_data = indeed_cache[unique_key]
    print(site_data)
    
    print("Fetching from DB")
    sql_check_users_table = """SELECT * FROM users
                                    WHERE email_id = ?
                                    AND search_query = ?
                                    AND location = ?;"""
    users_query_tuple = (email, query, location)
    user_resultset = fetch_result(db, sql_check_users_table, users_query_tuple)

    sql_check_users_jobs_table = """SELECT * FROM users_jobs
                                    WHERE user_id = ?;"""
    user_id = str(user_resultset[0][0])
    users_jobs_query_tuple = (user_id,)
    users_jobs_resultset = fetch_result(db, sql_check_users_jobs_table, users_jobs_query_tuple)
    
    users_jobs_list_length = len(users_jobs_resultset)
    list_of_tuples = []
    for x in range(users_jobs_list_length):
        sql_check_jobs_table = """SELECT * FROM jobs
                                        WHERE id = ?;"""
        job_id = str(users_jobs_resultset[x][1])
        jobs_query_tuple = (job_id,)
        jobs_resultset = fetch_result(db, sql_check_jobs_table, jobs_query_tuple)
        list_of_tuples.append(jobs_resultset[0])
    df = pandas.DataFrame(list_of_tuples,columns=['S.No.','Title','Location','Company','Salary','Ratings','JobsURL'])
else:
    print("Fetching from website")
    url = 'https://indeed.com/jobs?q='+query+'&l='+location+'&sort=date'
    link = requests.get(url)
    site = BeautifulSoup(link.text, 'html.parser')

    job_title_list = []
    jobs = site.find_all(name='a', attrs={'data-tn-element': 'jobTitle'})
    for job in jobs:
        job_attr = job.attrs
        job_title_list.append(job_attr['title'])

    job_loc_list = []
    loc_div = site.find_all('div', attrs={'class': 'recJobLoc'}) 
    for loc in loc_div:
        loc_attr = loc.attrs
        job_loc_list.append(loc_attr['data-rc-loc'])

    company_name_list = []
    company_span = site.find_all('span', attrs={'class': 'company'})
    for span in company_span:
        company_name_list.append(span.text.strip())

    salary_list  = []
    jobs_divs = site.find_all('div', attrs={'class': 'jobsearch-SerpJobCard'})
    for div in jobs_divs:
        salary_span = div.find('span', attrs={'class': 'salaryText'})
        if salary_span:
            salary_list.append(salary_span.string.strip())
        else:
            salary_list.append('Not shown')

    ratings_list  = []
    jobs_divs = site.find_all('div', attrs={'class': 'jobsearch-SerpJobCard'})
    for div in jobs_divs:
        rating_span = div.find('span', attrs={'class':  'ratingsContent'})
        if rating_span:
          ratings_list.append(float(rating_span.text.strip().replace(',', '.')))
        else:
          ratings_list.append(None)

    view_job_url = 'https://indeed.com/viewjob?jk='
    apply_urls = []
    jobs_div = site.find_all(name='div', attrs={'class': 'jobsearch-SerpJobCard'})
    for div in jobs_div:
        job_id = div.attrs['data-jk']
        apply_url = view_job_url + job_id
        apply_urls.append(apply_url)

    #insert data scraped into tables
    length_of_list = len(apply_urls)
    sql_insert_users_table = """INSERT INTO users (email_id,search_query,location)
                                    VALUES(?, ?, ?);"""
    users_query_tuple = (email, query, location)
    user_id = execute_query(db, sql_insert_users_table, users_query_tuple)

    for x in range(length_of_list):
        # Before inserting into jobs table, checking if the job to be inserted is already in the table. If it is already present, we will take out the job id from the table that is to be used in the mapping table users_jobs
        sql_check_jobs_id = """SELECT * FROM jobs
                                        WHERE url = ?;"""
        query_tuple = (apply_urls[x],)
        jobs_result = fetch_result(db, sql_check_jobs_id, query_tuple)

        if len(jobs_result) == 0:
            sql_insert_jobs_table = """INSERT INTO jobs (url,title,location,company,salary,ratings)
                                            VALUES(?, ?, ?, ?, ?, ?);"""
            jobs_query_tuple = (apply_urls[x], job_title_list[x], job_loc_list[x], company_name_list[x], salary_list[x], ratings_list[x])
            job_id = execute_query(db, sql_insert_jobs_table, jobs_query_tuple)
        else:
            job_id = jobs_result[0][0]

        sql_insert_users_jobs_table = """INSERT INTO users_jobs (user_id, job_id)
                                    VALUES(?, ?);"""
        users_jobs_query_tuple = (user_id, job_id)
        execute_query(db, sql_insert_users_jobs_table, users_jobs_query_tuple)
     
    #preparing dataframe to be sent to user in a tabular format
    length_of_list = len(apply_urls)
    final_list_for_cache = []
    for x in range(length_of_list):
        d={}
        d["S.No."] = x+1
        d["Title"] = job_title_list[x]
        d["Location"] = job_loc_list[x]
        d["Company"] = company_name_list[x]
        d["Salary"] = salary_list[x]
        d["Ratings"] = ratings_list[x]
        d["JobsURL"] = apply_urls[x]
        l.append(d)
        d_copy = d.copy()
        final_list_for_cache.append(d_copy)
    
    indeed_cache[unique_key] = final_list_for_cache
    df=pandas.DataFrame(l)

#send an email to user using df
EMAIL_FROM = 'anand.aditi5@gmail.com'
EMAIL_TO = email
EMAIL_SUBJECT = 'Indeed jobs for '+query+' at '+location
EMAIL_CONTENT = build_table(df, 'blue_light')

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

send_email()
