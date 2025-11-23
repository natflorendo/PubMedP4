```text
nathan@Nathans-MacBook-Air-6 ~ % curl -X POST http://localhost:8000/signup \
     -H "Content-Type: application/json" \
     -d '{"name": "Curator","email": "curator@example.com","password": "SuperSecret1!","roles": ["curator"]}'
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwicm9sZXMiOlsiY3VyYXRvciJdLCJleHAiOjE3NjM5MjA4ODl9.b-S9RUqa6LBf3L1nPUEsiXxbn3EnGizbBYhn1WXMxY8","token_type":"bearer","user":{"user_id":1,"name":"Curator","email":"curator@example.com","roles":["curator"],"created_at":"2025-11-23T11:36:29.531256"}}%   

nathan@Nathans-MacBook-Air-6 ~ % curl -X POST http://localhost:8000/login \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d 'username=curator@example.com&password=SuperSecret1!'
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwicm9sZXMiOlsiY3VyYXRvciJdLCJleHAiOjE3NjM5MjMzNjZ9.jtPQGLPuYxCmw90lDRxhWGTOW5-JQ4YyXDQCJI3llUE","token_type":"bearer","user":{"user_id":1,"name":"Curator","email":"curator@example.com","roles":["curator"],"created_at":"2025-11-23T11:36:29.531256"}}%  


curl -X POST "http://localhost:8000/curator/upload" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwicm9sZXMiOlsiY3VyYXRvciJdLCJleHAiOjE3NjM5MjMzNjZ9.jtPQGLPuYxCmw90lDRxhWGTOW5-JQ4YyXDQCJI3llUE" \
  -F "document=@/Users/nathan/Downloads/new-data/Anti-PD-1 Treatment-Induced Immediate Central Diabetes Insipidus  A Case Report.pdf" \
  -F "metadata_csv=@/Users/nathan/Downloads/new-data/new_csv.csv"

{"message":"Document ingested successfully.","pmid":34424037,"doc_id":2,"title":"Anti-PD-1 treatment-induced immediate central diabetes insipidus: a case report","chunks":11,"embeddings":11,"metadata_source":"csv"}%

curl -X POST http://localhost:8000/curator/upload \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwicm9sZXMiOlsiY3VyYXRvciJdLCJleHAiOjE3NjM5MjMzNjZ9.jtPQGLPuYxCmw90lDRxhWGTOW5-JQ4YyXDQCJI3llUE" \
     -F "document=@/Users/nathan/Downloads/new-data/amjcaserep-22-e934193.pdf" \ 
     -F "pmid=34898594" \
     -F "title=Adipsic Diabetes Insipidus in Children: A Case Report and Practical Guide" \
     -F "authors=AlShoomi AM, Alkanhal KI, Alsaheel AY." \
     -F "doi=10.12659/AJCR.934193" \
     -F "journal_name=Am J Case Rep" \
     -F "publication_year=2021"

{"message":"Document ingested successfully.","pmid":34898594,"doc_id":3,"title":"Adipsic Diabetes Insipidus in Children: A Case Report and Practical Guide","chunks":14,"embeddings":14,"metadata_source":"form"}%       
```