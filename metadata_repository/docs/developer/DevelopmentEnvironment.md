# Development Environment

## Docker

Install [Docker](https://www.docker.com/products/docker) and [Docker Compose](https://docs.docker.com/compose/install/).

1. Generate a secret key for [Flask sessions](http://flask.pocoo.org/docs/0.10/quickstart/#sessions).
   ```
   ./scripts/generate_flask_key
   ```

   Save the key in the `SESSION_KEY` environment variable in `docker-compose.yml`.

1. Start services
   ```
   cd /path/to/metadata_repository
   docker-compose up
   ```

   The default configuration is to mount the metadata repository directory as a volume on the container and serve
   the application using the [Flask development server](http://flask.pocoo.org/docs/0.10/quickstart/#debug-mode).
   This allows for files to be edited on the host and the container to detect changes and restart the app server.

   Using the tiered configuration in `docker-compose-tiered.yml` copies application code to the container and runs
   the metadata repository application using [gunicorn](http://gunicorn.org/) behind an nginx proxy.

1. Run database migrations.
   ```
   docker-compose run --rm app alembic upgrade head
   ```

   This only needs to be run when the containers are created the first time you run `docker-compose up`. Database
   data is persisted by mounting `./pgdata` as PostgreSQL's data directory on the `db` container.

1. Open [http://localhost:5000](http://localhost:5000) in a browser. If using the tiered configuration, use port 80.

1. [Configure the client](/client/docs/Configuration.md) to point to your local metadata repository.

## Vagrant

Alternatively, you can launch an instance of the metadata repository in a virtual machine. The VM is
configured to use [PostgreSQL](http://www.postgresql.org/) for the database and
[Apache](https://httpd.apache.org/) with [mod_wsgi](https://modwsgi.readthedocs.io/) for the web server.

**Note**: The VM provision script sets environment variables in `app.wsgi`. Be careful about committing them to
version control.

1. Install VirtualBox and Vagrant

   * [VirtualBox](https://www.virtualbox.org/wiki/Downloads)
   * [Vagrant](http://docs.vagrantup.com/v2/installation/index.html)

2. Launch VM

   ```Shell
   cd /path/to/bdss/metadata_repository
   vagrant up
   ```

3. Open [http://localhost:8000](http://localhost:8000) in a web browser.

   Port 8000 is forwarded to the VM's port 80.

4. [Configure the client](/client/docs/Configuration.md) to point to your local metadata repository.

## Manual

To manually set up a development environment, follow these steps:

1. [Install Python 3.4+](http://docs.python-guide.org/en/latest/starting/installation/).

2. Create a [virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/).

   ```Shell
   cd /path/to/bdss/metadata_repository
   virtualenv -p /path/to/python3 venv
   ```

3. Activate the virtualenv.

   ```Shell
   source venv/bin/activate
   ```

4. Install requirements.

   ```Shell
   pip install -r requirements.txt
   ```

5. Configure the application.

   Two configuration values are read from environment variables:

   * DATABASE_URL - Location of the database to use. See the
     [SQLAlchemy documentation](http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls) for more
     information. If you use a path to an SQLite database, it will be automatically created if it doesn't exist.
     For other database types, you may have to install an additional driver.

   * SESSION_KEY - Secret key for [Flask sessions](http://flask.pocoo.org/docs/0.10/quickstart/#sessions). To
     generate a random key, run `./scripts/generate_flask_key`.

6. Create the database schema.

   This project uses [Alembic](https://alembic.readthedocs.org/en/latest/) for database migrations.
   To migrate your database to the latest version, run:

   ```Shell
   alembic upgrade head
   ```

7. Start the development server.

   ```Shell
   ./scripts/serve
   ```

   By default, this server will only be accessible at `localhost`. To make it publicly accessible, run
   the script with the `--public` option.

8. [Configure the client](/client/docs/Configuration.md) to point to your local metadata repository.
