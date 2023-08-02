from fastapi import APIRouter

router = APIRouter()

"""
| Endpoint        | Description                  | Method |
|-----------------|------------------------------|--------|
| `/user`         | Register a new user          | POST   |
| `/user/{id}`    | Retrieve a user's details    | GET    |
| `/user/{id}`    | Update a user's details      | PATCH  |
| `/user/{id}`    | Delete a user's account      | DELETE |
"""
