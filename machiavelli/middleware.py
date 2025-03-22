from django.db import connection

class DatabaseConnectionMiddleware(object):
    """
    Middleware to ensure database connections are closed properly and handle reconnection.
    """
    def process_request(self, request):
        connection.close()
        return None

    def process_response(self, request, response):
        connection.close()
        return response

    def process_exception(self, request, exception):
        connection.close()
        return None

class TimezoneFixMiddleware(object):
    """
    Middleware to fix timezone object conversion issues with old Django/Pinax.
    """
    def process_request(self, request):
        from django.db import backend
        import pytz
        from timezones import fields

        def convert_timezone(value):
            if value is None:
                return None
            if isinstance(value, (str, unicode)):
                return value
            if hasattr(value, 'zone'):
                return str(value.zone)
            if isinstance(value, pytz.tzinfo.BaseTzInfo):
                return str(value)
            return str(value)

        # Patch the database backend's timezone handling
        if hasattr(backend, 'DatabaseWrapper'):
            if hasattr(backend.DatabaseWrapper, '_cursor'):
                original_cursor = backend.DatabaseWrapper._cursor

                def _cursor(self):
                    cursor = original_cursor(self)
                    # Add our timezone converter to the cursor's connection
                    if hasattr(cursor.connection, 'encoders'):
                        # Get the TimeZone class from pytz
                        cursor.connection.encoders[pytz.timezone('UTC').__class__] = convert_timezone
                        cursor.connection.encoders[pytz.tzinfo.BaseTzInfo] = convert_timezone
                        # Also handle string timezone values
                        cursor.connection.encoders[str] = lambda x, m: "'%s'" % str(x).replace("'", "''") if x is not None else x
                        cursor.connection.encoders[unicode] = lambda x, m: "'%s'" % str(x).replace("'", "''") if x is not None else x
                    return cursor

                backend.DatabaseWrapper._cursor = _cursor

        # Also patch the TimeZoneField's get_db_prep_save method
        original_get_db_prep_save = fields.TimeZoneField.get_db_prep_save

        def new_get_db_prep_save(self, value, connection=None):
            if value is not None:
                if hasattr(value, 'zone'):
                    value = str(value.zone)
                else:
                    value = str(value)
            return original_get_db_prep_save(self, value, connection=connection)

        fields.TimeZoneField.get_db_prep_save = new_get_db_prep_save

        return None 