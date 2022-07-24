# FOODGRAM PROJECT

Current library is REST API for FOODGRAM service which provides access for reading, creating and editing recipes:

## Installation

You must have Docker installed and configured on your PC.

You neeb create file .env in directory foodgram-project-react/infra/:
```
DB_ENGINE=<the db you are working with> 
DB_NAME=<db name>
POSTGRES_USER=<db login>
POSTGRES_PASSWORD=<create a password>
DB_HOST=<container name>
DB_PORT=<db port>
```

The next step is to run docker-compose:

```bash
docker-compose up -d
```
Make all necessary migrations:
```bash
docker-compose exec backend python manage.py migrate
```
Create super user:
```bash
docker-compose exec backend python manage.py createsuperuser
```
Collect static:
```bash
docker-compose exec backend python manage.py collectstatic --no-input 
```

The project is now available at http://84.252.139.107/, http://84.252.139.107/admin

Information about API http://84.252.139.107/api/docs/

Status workflow:
https://github.com/SergoSolo/foodgram-project-react/actions/workflows/foodgram_workflow.yml/badge.svg

## Resources

- **auth**: authentication.
- **users**: users.
- **recipes**: recipes created by users, you can add recipe in favorites or shopping cart.
- **ingredients**: all ingredients.


## Author :
>[Sergey](https://github.com/SergoSolo)

## License
Free