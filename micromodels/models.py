import json
from copy import copy
from collections import OrderedDict
from six import add_metaclass
from micromodels.fields import BaseField, ValidationError


def get_declared_fields(bases, attrs):
    """
    Create a list of model field instances from the passed in 'attrs', plus any
    similar fields on the base classes (in 'bases').
    """
    fields = list()
    attrs_items = list(attrs.items())
    for field_name, obj in attrs_items:
        if isinstance(obj, BaseField):
            if not obj.verbose_name:
                obj.verbose_name = field_name
            fields.append((field_name, attrs.pop(field_name)))
    fields.sort(key=lambda x: x[1].creation_counter)

    for base in bases[::-1]:
        if hasattr(base, '_clsfields'):
            fields = list(base._clsfields.items()) + fields

    return OrderedDict(fields)


class ModelMeta(type):
    ''' Creates the metaclass for Model. The main function of this metaclass
        is to move all of fields into the _fields variable on the class.
    '''
    def __new__(cls, name, bases, attrs):
        attrs['_clsfields'] = get_declared_fields(bases, attrs)
        new_class = super(ModelMeta, cls).__new__(cls, name, bases, attrs)
        return new_class


@add_metaclass(ModelMeta)
class Model(object):
    """The Model is the main component of micromodels. Model makes it trivial
    to parse data from many sources, including JSON APIs.

    You will probably want to initialize this class using the class methods
    :meth:`from_dict` or :meth:`from_kwargs`. If you want to initialize an
    instance without any data, just call :class:`Model` with no parameters.

    :class:`Model` instances have a unique behavior when an attribute is set
    on them. This is needed to properly format data as the fields specify.
    The variable name is referred to as the key, and the value will be called
    the value. For example, in::

        instance = Model()
        instance.age = 18

    ``age`` is the key and ``18`` is the value.

    First, the model checks if it has a field with a name matching the key.

    If there is a matching field, then :meth:`to_python` is called on the field
    with the value.
    If :meth:`to_python` does not raise an exception, then the result of
    :meth:`to_python` is set on the instance, and the method is completed.
    Essentially, this means that the first thing setting an attribute tries
    to do is process the data as if it was a "primitive" data type.

    If :meth:`to_python` does raise an exception, this means that the data
    might already be an appropriate Python type. The :class:`Model` then
    attempts to *serialize* the data into a "primitive" type using the
    field's :meth:`to_serial` method.

    If this fails, a ``TypeError`` is raised.

    If it does not fail, the value is set on the instance, and the
    method is complete.

    If the instance doesn't have a field matching the key, then the key and
    value are just set on the instance like any other assignment in Python.

    """
    # __metaclass__ = ModelMeta

    def __init__(self, **values):
        super(Model, self).__setattr__('_extra', OrderedDict())
        super(Model, self).__init__()
        self._clsfields = OrderedDict(
            [(key, copy(field)) for key, field in self._clsfields.items()]
        )
        if values:
            self.set_data(values)

    @classmethod
    def from_dict(cls, D, is_json=False):
        '''This factory for :class:`Model`
        takes either a native Python dictionary or a JSON dictionary/object
        if ``is_json`` is ``True``. The dictionary passed does not need to
        contain all of the values that the Model declares.

        '''
        instance = cls()
        instance.set_data(D, is_json=is_json)
        return instance

    @classmethod
    def from_kwargs(cls, **kwargs):
        '''This factory for :class:`Model` only takes keywork arguments.
        Each key and value pair that represents a field in the :class:`Model` is
        set on the new :class:`Model` instance.

        '''
        instance = cls()
        instance.set_data(kwargs)
        return instance

    def set_data(self, data, is_json=False):
        if is_json:
            data = json.loads(data)
        for name, field in self._clsfields.items():
            key = field.source or name
            if key in data:
                setattr(self, name, data[key])
            else:
                setattr(self, name, field.get_default())

    def __setattr__(self, key, value):
        if key in self._fields:
            field = self._fields[key]
            field.populate(value)
            field._related_obj = self
            super(Model, self).__setattr__(key, field.to_python())
        else:
            super(Model, self).__setattr__(key, value)

    def __getattr__(self, key):
        # Lazily set the default when trying to access an attribute
        # that has not otherwise been set.
        fields = object.__getattribute__(self, '_clsfields')
        extra = object.__getattribute__(self, '_extra')
        field = fields.get(key) or extra.get(key)
        if field:
            value = field.to_python()
            setattr(self, key, value)
            return value
        return object.__getattribute__(self, key)

    @property
    def _fields(self):
        return OrderedDict(self._clsfields, **self._extra)

    def add_field(self, key, value, field):
        ''':meth:`add_field` must be used to add a field to an existing
        instance of Model. This method is required so that serialization of the
        data is possible. Data on existing fields (defined in the class) can be
        reassigned without using this method.

        '''
        self._extra[key] = field
        setattr(self, key, value)

    def to_dict(self, serial=False):
        '''A dictionary representing the the data of the class is returned.
        Native Python objects will still exist in this dictionary (for example,
        a ``datetime`` object will be returned rather than a string)
        unless ``serial`` is set to True.

        '''
        if serial:
            return dict((key, self._fields[key].to_serial(getattr(self, key)))
                        for key in self._fields.keys() if hasattr(self, key))
        else:
            return dict((key, getattr(self, key)) for key in self._fields.keys()
                        if hasattr(self, key))

    def to_json(self):
        '''Returns a representation of the model as a JSON string. This method
        relies on the :meth:`~micromodels.Model.to_dict` method.

        '''
        return json.dumps(self.to_dict(serial=True))

    def validate(self):
        '''Run basic validation on the model. Returns an error dict if
        validation fails or ``None`` if it passes.

        For example:

            >>> class MyModel(Model): pass
            >>> def handle_errors(): pass
            >>> m = MyModel.from_kwargs(foo='bar', fizz='buzz')
            >>> errors = m.validate()
            >>> if errors:
            ...     handle_errors()

        '''

        error_dict = {}
        for name, field in self._fields.items():
            try:
                field.validate()
            except ValidationError as err:
                error_dict.setdefault(name, [])
                error_dict[name].append(str(err))
            try:
                getattr(self, 'validate_{0}'.format(name))()
            except AttributeError:
                continue
            except ValidationError as err:
                error_dict.setdefault(name, [])
                error_dict[name].append(str(err))
        return error_dict or None
