from fastapi import APIRouter

router = APIRouter()

"""
| Endpoint                             | Description                           | Method |
|--------------------------------------|---------------------------------------|--------|
| `/organization`                      | Register a new organization           | POST   |
| `/organization/{id}`                 | Retrieve a organization's details     | GET    |
| `/organization/{id}`                 | Update a organization's details       | PATCH  |
| `/organization/{id}/user`            | Retrieve users of a organization      | GET    |
| `/organization/{id}/user`            | Invite a user to a organization       | POST   |
| `/organization/{id}/document`        | Retrieve documents of a organization  | GET    |
"""
