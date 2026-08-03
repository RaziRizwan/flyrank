## Week 3

### Why SQLite?
SQLite requires no separate server process or installation, it stores all data in a single database file (`tasks.db`) and is included as part of Python's standard library. 
This makes it an ideal choice for a small project like this: it requires virtually no setup, is lightweight, and preserves data across application restarts. 
While SQLite is excellent for single-user or low-concurrency applications, larger systems with many simultaneous users or distributed, multi-server deployments are better served by a client-server database such as PostgreSQL.

##
### DB Browser screenshot
###
![DB Browser screenshot](Verification_screenshot_of_DB_Browser(Task4).png)