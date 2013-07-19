import datetime
import decimal
import PySO8601
import uuid
import json


class ValidationError(Exception):
    pass


class ValidationError(Exception):
    pass


def required_validator(value):
    if value is None:
        raise ValidationError('This field is required.')


class BaseField(object):
    """Base class for all field types.

    The ``source`` parameter sets the key that will be retrieved from the source
    data. If ``source`` is not specified, the field instance will use its own
    name as the key to retrieve the value from the source data.

    """

    # Tracks each time a BaseField instance is created. Used to retain order.
    creation_counter = 0
    builtin_validators = []

    def __init__(self, source=None, default=None, required=True, validators=None):
        self.source = source
        self.default = default
        self.required = required

        self.validators = []
        if required:
            self.validators.append(required_validator)
        self.validators.extend(self.builtin_validators)
        if validators:
            self.validators.extend(validators)

        # Increase the creation counter, and save our local copy.
        self.creation_counter = BaseField.creation_counter
        BaseField.creation_counter += 1

    def populate(self, data):
        """Set the value or values wrapped by this field"""
        if callable(data):
            data = data()
        self.data = data

    def get_default(self):
        """Get the default value. If the default is callable, call it."""
        if callable(self.default):
            return self.default()
        return self.default

    def to_python(self):
        '''After being populated, this method casts the source data into a
        Python object. If no data has been set, it returns the fields default
        value.

        '''
        if self.data is None:
            if self.default is None:
                return None
            self.populate(self.get_default())
        return self._to_python()

    def _to_python(self):
        '''After being populated, this method casts the source data into a
        Python object. The default behavior is to simply return the source
        value. Subclasses should override this method.
        '''
        return self.data

    def to_serial(self, data):
        '''Used to serialize forms back into JSON or other formats.

        This method is essentially the opposite of
        :meth:`~micromodels.fields.BaseField.to_python`. A string, boolean,
        number, dictionary, list, or tuple must be returned. Subclasses should
        override this method.

        '''
        if data is None:
            return data
        return self._to_serial(data)

    def _to_serial(self, data):
        return data

    def validate(self):
        value = self.to_python()
        for validator in self.validators:
            rvalue = validator(value)
            value = value if rvalue is None else rvalue
        return value


class CharField(BaseField):
    """Field to represent a simple Unicode string value."""

    def _to_python(self):
        """Convert the data supplied using the :meth:`populate` method to a
        Unicode string.

        """
        return unicode(self.data)


class IntegerField(BaseField):
    """Field to represent an integer value"""

    def _to_python(self):
        """Convert the data supplied to the :meth:`populate` method to an
        integer.

        """
        return int(self.data)


class FloatField(BaseField):
    """Field to represent a floating point value"""

    def _to_python(self):
        """Convert the data supplied to the :meth:`populate` method to a
        float.

        """
        return float(self.data)


class DecimalField(BaseField):
    """Field to represent a :mod:`decimal.Decimal`"""

    def _to_python(self):
        if isinstance(self.data, decimal.Decimal):
            return self.data
        if isinstance(self.data, float):
            return decimal.Decimal(repr(self.data))
        return decimal.Decimal(self.data)


class BooleanField(BaseField):
    """Field to represent a boolean"""

    def populate(self, data):
        # Explicitly cast the value to a bool when we populate the field
        super(BooleanField, self).populate(data)
        self.data = bool(self.to_python())

    def _to_python(self):
        """The string ``'True'`` (case insensitive) will be converted
        to ``True``, as will any positive integers.

        """
        if isinstance(self.data, basestring):
            return self.data.strip().lower() == 'true'
        if isinstance(self.data, int):
            return self.data > 0
        return bool(self.data)


class DateTimeField(BaseField):
    """Field to represent a datetime

    The ``format`` parameter dictates the format of the input strings, and is
    used in the construction of the :class:`datetime.datetime` object.

    The ``serial_format`` parameter is a strftime formatted string for
    serialization. If ``serial_format`` isn't specified, an ISO formatted string
    will be returned by :meth:`~micromodels.DateTimeField.to_serial`.

    """
    def __init__(self, format=None, serial_format=None, **kwargs):
        super(DateTimeField, self).__init__(**kwargs)
        self.format = format
        self.serial_format = serial_format

    def _to_python(self):
        '''A :class:`datetime.datetime` object is returned.'''
        # don't parse data that is already native
        if isinstance(self.data, datetime.datetime):
            return self.data
        elif self.format is None:
            # parse as iso8601
            return PySO8601.parse(self.data)
        else:
            return datetime.datetime.strptime(self.data, self.format)

    def _to_serial(self, time_obj):
        if not self.serial_format:
            return time_obj.isoformat()
        return time_obj.strftime(self.serial_format)


class DateField(DateTimeField):
    """Field to represent a :mod:`datetime.date`"""

    def _to_python(self):
        # don't parse data that is already native
        if isinstance(self.data, datetime.date):
            return self.data

        dt = super(DateField, self)._to_python()
        return dt.date()


class TimeField(DateTimeField):
    """Field to represent a :mod:`datetime.time`"""

    def _to_python(self):
        # don't parse data that is already native
        if isinstance(self.data, datetime.datetime):
            return self.data
        elif self.format is None:
            # parse as iso8601
            return PySO8601.parse_time(self.data).time()
        else:
            return datetime.datetime.strptime(self.data, self.format).time()


class UUIDField(BaseField):
    """Field to represent a :mod:`uuid.UUID`"""

    def _to_python(self):
        if isinstance(self.data, uuid.UUID):
            return self.data
        return uuid.UUID(self.data)

    def _to_serial(self, uuid_obj):
        return uuid_obj.hex


class JSONField(BaseField):
    """Field to represent a dict or list as a JSON string."""

    def _to_python(self):
        if isinstance(self.data, basestring):
            return json.loads(self.data)
        return self.data

    def _to_serial(self, obj):
        return json.dumps(obj)


class WrappedObjectField(BaseField):
    """Superclass for any fields that wrap an object"""

    def __init__(self, wrapped_class, related_name=None, **kwargs):
        self._wrapped_class = wrapped_class
        self._related_name = related_name
        self._related_obj = None

        BaseField.__init__(self, **kwargs)


class ModelField(WrappedObjectField):
    """Field containing a model instance

    Use this field when you wish to nest one object inside another.
    It takes a single required argument, which is the nested class.
    For example, given the following dictionary::

        some_data = {
            'first_item': 'Some value',
            'second_item': {
                'nested_item': 'Some nested value',
            },
        }

    You could build the following classes
    (note that you have to define the inner nested models first)::

        class MyNestedModel(micromodels.Model):
            nested_item = micromodels.CharField()

        class MyMainModel(micromodels.Model):
            first_item = micromodels.CharField()
            second_item = micromodels.ModelField(MyNestedModel)

    Then you can access the data as follows::

        >>> m = MyMainModel(some_data)
        >>> m.first_item
        u'Some value'
        >>> m.second_item.__class__.__name__
        'MyNestedModel'
        >>> m.second_item.nested_item
        u'Some nested value'

    """
    def _to_python(self):
        if isinstance(self.data, self._wrapped_class):
            obj = self.data
        else:
            obj = self._wrapped_class.from_dict(self.data or {})

        # Set the related object to the related field
        if self._related_name is not None:
            setattr(obj, self._related_name, self._related_obj)

        return obj

    def _to_serial(self, model_instance):
        return model_instance.to_dict(serial=True)


class ModelCollectionField(WrappedObjectField):
    """Field containing a list of model instances.

    Use this field when your source data dictionary contains a list of
    dictionaries. It takes a single required argument, which is the name of the
    nested class that each item in the list should be converted to.
    For example::

        some_data = {
            'list': [
                {'value': 'First value'},
                {'value': 'Second value'},
                {'value': 'Third value'},
            ]
        }

        class MyNestedModel(micromodels.Model):
            value = micromodels.CharField()

        class MyMainModel(micromodels.Model):
            list = micromodels.ModelCollectionField(MyNestedModel)

        >>> m = MyMainModel(some_data)
        >>> len(m.list)
        3
        >>> m.list[0].__class__.__name__
        'MyNestedModel'
        >>> m.list[0].value
        u'First value'
        >>> [item.value for item in m.list]
        [u'First value', u'Second value', u'Third value']

    """
    def _to_python(self):
        object_list = []
        for item in self.data:
            obj = self._wrapped_class.from_dict(item)
            if self._related_name is not None:
                setattr(obj, self._related_name, self._related_obj)
            object_list.append(obj)

        return object_list

    def to_serial(self, model_instances):
        return [instance.to_dict(serial=True) for instance in model_instances]


class FieldCollectionField(BaseField):
    """Field containing a list of the same type of fields.

    The constructor takes an instance of the field.

    Here are some examples::

        data = {
                    'legal_name': 'John Smith',
                    'aliases': ['Larry', 'Mo', 'Curly']
        }

        class Person(Model):
            legal_name = CharField()
            aliases = FieldCollectionField(CharField())

        p = Person(data)

    And now a quick REPL session::

        >>> p.legal_name
        u'John Smith'
        >>> p.aliases
        [u'Larry', u'Mo', u'Curly']
        >>> p.to_dict()
        {'legal_name': u'John Smith', 'aliases': [u'Larry', u'Mo', u'Curly']}
        >>> p.to_dict() == p.to_dict(serial=True)
        True

    Here is a bit more complicated example involving args and kwargs::

        data = {
                    'name': 'San Andreas',
                    'dates': ['1906-05-11', '1948-11-02', '1970-01-01']
        }

        class FaultLine(Model):
            name = CharField()
            earthquake_dates = FieldCollectionField(DateField('%Y-%m-%d',
                                                    serial_format='%m-%d-%Y'),
                                                    source='dates')

        f = FaultLine(data)

    Notice that source is passed to to the
    :class:`~micromodels.FieldCollectionField`, not the
    :class:`~micromodels.DateField`.

    Let's check out the resulting :class:`~micromodels.Model` instance with the
    REPL::

        >>> f.name
        u'San Andreas'
        >>> f.earthquake_dates
        [datetime.date(1906, 5, 11), datetime.date(1948, 11, 2), datetime.date(1970, 1, 1)]
        >>> f.to_dict()
        {'earthquake_dates': [datetime.date(1906, 5, 11), datetime.date(1948, 11, 2), datetime.date(1970, 1, 1)],
         'name': u'San Andreas'}
        >>> f.to_dict(serial=True)
        {'earthquake_dates': ['05-11-1906', '11-02-1948', '01-01-1970'], 'name': u'San Andreas'}
        >>> f.to_json()
        '{"earthquake_dates": ["05-11-1906", "11-02-1948", "01-01-1970"], "name": "San Andreas"}'

    """
    def __init__(self, field_instance, **kwargs):
        super(FieldCollectionField, self).__init__(**kwargs)
        self._instance = field_instance

    def _to_python(self):
        def convert(item):
            self._instance.populate(item)
            return self._instance.to_python()
        return [convert(item) for item in self.data or []]

    def to_serial(self, list_of_fields):
        return [self._instance.to_serial(data) for data in list_of_fields]
