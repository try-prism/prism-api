from fastapi import APIRouter

router = APIRouter()

"""
| Endpoint                          | Description                        | Method |
|-----------------------------------|------------------------------------|--------|
| `/corporate`                      | Register a new corporate           | POST   |
| `/corporate/{id}`                 | Retrieve a corporate's details     | GET    |
| `/corporate/{id}`                 | Update a corporate's details       | PATCH  |
| `/corporate/{id}/user`            | Retrieve users of a corporate      | GET    |
| `/corporate/{id}/user`            | Invite a user to a corporate       | POST   |
| `/corporate/{id}/document`        | Retrieve documents of a corporate  | GET    |
"""
