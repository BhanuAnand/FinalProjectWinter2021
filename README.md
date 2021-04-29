# FinalProjectWinter2021

##### Requirements
pip install fcache
pip install pretty_html_table

For sending Gmail, there are certain OAuth 2.0 configuration. Below is the link to the document containing steps and screenshots:
https://docs.google.com/document/d/17dvFPId4F7RnlSYNuQM-0c4opko8HmfdBtCosZUJtaI/edit?usp=sharing

##### Link for Project Demo: https://vimeo.com/543351472

##### Project Flow:
1)	Take email id, job search query, job location from the user
2)	Scrape the Indeed URL with user inputs from above
3)	Check data in cache corresponding to the input, if not then scrape from the website and save the data to the cache and DB
4)	If the cache was found matching the user input, that means there should be data corresponding to the jobs scraped in the table, hence fetch that from the DB.
5)	Then an email will be sent to the user on the email id that has been taken from the user.
