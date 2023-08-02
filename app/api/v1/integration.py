from fastapi import APIRouter

router = APIRouter()

"""
| Endpoint                      | Description                          | Method |
|-------------------------------|--------------------------------------|--------|
| `/integration`                | Add a new cloud storage integration  | POST   |
| `/integration/{id}`           | Retrieve an integration's details    | GET    |
| `/integration/{id}`           | Update an integration's details      | PATCH  |
| `/integration/{id}`           | Remove a cloud storage integration   | DELETE |
"""
