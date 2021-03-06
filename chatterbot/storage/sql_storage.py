from chatterbot.storage import StorageAdapter


class SQLStorageAdapter(StorageAdapter):
    """
    The SQLStorageAdapter allows ChatterBot to store conversation
    data in any database supported by the SQL Alchemy ORM.

    All parameters are optional, by default a sqlite database is used.

    It will check if tables are present, if they are not, it will attempt
    to create the required tables.

    :keyword database_uri: eg: sqlite:///database_test.db',
        The database_uri can be specified to choose database driver.
    :type database_uri: str
    """

    def __init__(self, **kwargs):
        super(SQLStorageAdapter, self).__init__(**kwargs)

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        self.database_uri = self.kwargs.get('database_uri', False)

        # None results in a sqlite in-memory database as the default
        if self.database_uri is None:
            self.database_uri = 'sqlite://'

        # Create a file database if the database is not a connection string
        if not self.database_uri:
            self.database_uri = 'sqlite:///db.sqlite3'

        self.engine = create_engine(self.database_uri, convert_unicode=True)

        if self.database_uri.startswith('sqlite://'):
            from sqlalchemy.engine import Engine
            from sqlalchemy import event

            @event.listens_for(Engine, 'connect')
            def set_sqlite_pragma(dbapi_connection, connection_record):
                dbapi_connection.execute('PRAGMA journal_mode=WAL')
                dbapi_connection.execute('PRAGMA synchronous=NORMAL')

        if not self.engine.dialect.has_table(self.engine, 'Statement'):
            self.create_database()

        self.Session = sessionmaker(bind=self.engine, expire_on_commit=True)

        # ChatterBot's internal query builder is not yet supported for this adapter
        self.adapter_supports_queries = False

    def get_statement_model(self):
        """
        Return the statement model.
        """
        from chatterbot.ext.sqlalchemy_app.models import Statement
        return Statement

    def get_tag_model(self):
        """
        Return the conversation model.
        """
        from chatterbot.ext.sqlalchemy_app.models import Tag
        return Tag

    def model_to_object(self, statement):
        from chatterbot.conversation import Statement as StatementObject

        return StatementObject(**statement.serialize())

    def count(self):
        """
        Return the number of entries in the database.
        """
        Statement = self.get_model('statement')

        session = self.Session()
        statement_count = session.query(Statement).count()
        session.close()
        return statement_count

    def remove(self, statement_text):
        """
        Removes the statement that matches the input text.
        Removes any responses from statements where the response text matches
        the input text.
        """
        Statement = self.get_model('statement')
        session = self.Session()

        query = session.query(Statement).filter_by(text=statement_text)
        record = query.first()

        session.delete(record)

        self._session_finish(session)

    def filter(self, **kwargs):
        """
        Returns a list of objects from the database.
        The kwargs parameter can contain any number
        of attributes. Only objects which contain all
        listed attributes and in which all values match
        for all listed attributes will be returned.
        """
        Statement = self.get_model('statement')
        Tag = self.get_model('tag')

        session = self.Session()

        order_by = kwargs.pop('order_by', None)
        tags = kwargs.pop('tags', [])

        # Convert a single sting into a list if only one tag is provided
        if type(tags) == str:
            tags = [tags]

        if len(kwargs) == 0:
            statements = session.query(Statement).filter()
        else:
            statements = session.query(Statement).filter_by(**kwargs)

        if tags:
            statements = statements.join(Statement.tags).filter(
                Tag.name.in_(tags)
            )

        if order_by:

            if 'created_at' in order_by:
                index = order_by.index('created_at')
                order_by[index] = Statement.created_at.asc()

            statements = statements.order_by(*order_by)

        results = []

        for statement in statements:
            results.append(self.model_to_object(statement))

        session.close()

        return results

    def create(self, **kwargs):
        """
        Creates a new statement matching the keyword arguments specified.
        Returns the created statement.
        """
        Statement = self.get_model('statement')
        Tag = self.get_model('tag')

        session = self.Session()

        tags = set(kwargs.pop('tags', []))

        if 'search_text' not in kwargs:
            kwargs['search_text'] = self.stemmer.stem(kwargs['text'])

        if 'search_in_response_to' not in kwargs:
            if kwargs.get('in_response_to'):
                kwargs['search_in_response_to'] = self.stemmer.stem(kwargs['in_response_to'])

        statement = Statement(**kwargs)

        for tag_name in tags:
            tag = session.query(Tag).get(tag_name)

            if not tag:
                # Create the tag
                tag = Tag(name=tag_name)

            statement.tags.append(tag)

        session.add(statement)

        session.flush()

        session.refresh(statement)

        statement_object = self.model_to_object(statement)

        self._session_finish(session)

        return statement_object

    def create_many(self, statements):
        """
        Creates multiple statement entries.
        """
        Statement = self.get_model('statement')
        Tag = self.get_model('tag')

        session = self.Session()

        create_statements = []
        create_tags = {}

        for statement_data in statements:

            tags = set(statement_data.pop('tags', []))

            if 'search_text' not in statement_data:
                statement_data['search_text'] = self.stemmer.stem(statement_data['text'])

            if 'search_in_response_to' not in statement_data:
                if statement_data.get('in_response_to'):
                    statement_data['search_in_response_to'] = self.stemmer.stem(statement_data['in_response_to'])

            statement = Statement(**statement_data)

            for tag_name in tags:
                if tag_name in create_tags:
                    tag = create_tags[tag_name]
                else:
                    tag = session.query(Tag).get(tag_name)

                    if not tag:
                        # Create the tag if it does not exist
                        tag = Tag(name=tag_name)

                    create_tags[tag_name] = tag

                statement.tags.append(tag)
            create_statements.append(statement)

        session.add_all(create_statements)
        session.commit()

    def update(self, statement):
        """
        Modifies an entry in the database.
        Creates an entry if one does not exist.
        """
        Statement = self.get_model('statement')
        Tag = self.get_model('tag')

        if statement is not None:
            session = self.Session()
            record = None

            if hasattr(statement, 'id') and statement.id is not None:
                record = session.query(Statement).get(statement.id)
            else:
                record = session.query(Statement).filter(
                    Statement.text == statement.text,
                    Statement.conversation == statement.conversation,
                ).first()

                # Create a new statement entry if one does not already exist
                if not record:
                    record = Statement(
                        text=statement.text,
                        conversation=statement.conversation,
                        persona=statement.persona
                    )

            # Update the response value
            record.in_response_to = statement.in_response_to

            record.created_at = statement.created_at

            record.search_text = self.stemmer.stem(statement.text)

            if statement.in_response_to:
                record.search_in_response_to = self.stemmer.stem(statement.in_response_to)

            for tag_name in statement.tags:
                tag = session.query(Tag).get(tag_name)

                if not tag:
                    # Create the record
                    tag = Tag(name=tag_name)

                record.tags.append(tag)

            session.add(record)

            self._session_finish(session)

    def get_random(self):
        """
        Returns a random statement from the database.
        """
        import random

        Statement = self.get_model('statement')

        session = self.Session()
        count = self.count()
        if count < 1:
            raise self.EmptyDatabaseException()

        random_index = random.randrange(0, count)
        random_statement = session.query(Statement)[random_index]

        statement = self.model_to_object(random_statement)

        session.close()
        return statement

    def get_response_statements(self, page_size=1000):
        """
        Return only statements that are in response to another statement.
        A statement must exist which lists the closest matching statement in the
        in_response_to field. Otherwise, the logic adapter may find a closest
        matching statement that does not have a known response.
        """
        from sqlalchemy import func

        Statement = self.get_model('statement')

        session = self.Session()

        total_statements = session.query(func.count(Statement.id)).scalar()

        start = 0
        stop = min(page_size, total_statements)

        while stop <= total_statements:

            statement_set = session.query(Statement).filter(
                Statement.in_response_to.isnot(None)
            ).slice(start, stop)

            start += page_size
            stop += page_size

            response_statements = set(
                statement.in_response_to for statement in statement_set
            )

            for statement in session.query(Statement).filter(
                Statement.text.in_(response_statements),
                ~Statement.persona.startswith('bot:')
            ):
                yield self.model_to_object(statement)

        session.close()

    def drop(self):
        """
        Drop the database.
        """
        Statement = self.get_model('statement')
        Tag = self.get_model('tag')

        session = self.Session()

        session.query(Statement).delete()
        session.query(Tag).delete()

        session.commit()
        session.close()

    def create_database(self):
        """
        Populate the database with the tables.
        """
        from chatterbot.ext.sqlalchemy_app.models import Base
        Base.metadata.create_all(self.engine)

    def _session_finish(self, session, statement_text=None):
        from sqlalchemy.exc import InvalidRequestError
        try:
            session.commit()
        except InvalidRequestError:
            # Log the statement text and the exception
            self.logger.exception(statement_text)
        finally:
            session.close()
