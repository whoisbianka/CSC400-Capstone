CREATE ROLE python_connection
    LOGIN
    PASSWORD 'local_postgres_password'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE;