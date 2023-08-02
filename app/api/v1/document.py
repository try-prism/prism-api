from fastapi import APIRouter

router = APIRouter()

"""
| Endpoint                  | Description                              | Method |
|---------------------------|------------------------------------------|--------|
| `/document`               | Upload a new document                    | POST   |
| `/document/{id}`          | Retrieve a document's details            | GET    |
| `/document/{id}`          | Update a document's details              | PATCH  |
| `/document/{id}`          | Delete a document                        | DELETE |
| `/document/search`        | Perform a search query on documents      | GET    |
"""
