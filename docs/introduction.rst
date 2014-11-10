Introduction
==================

Unstructured data is popular and convenient. Although weak structure may allow a
better representation of data by the producer of the data, it also makes the
data more difficult to consume and process.

Micromodels add convenience and structure to unstructured data.

Micromodels works with Python dictionaries. Convenience functions are
included for the manipulation of JSON, but any other format of data will need to
be manipulated into a dictionary before it can be used with micromodels.

Quickstart
-----------

Really simple example
~~~~~~~~~~~~~~~~~~~~~~~~~

    >>> import micromodels
    >>> class Author(micromodels.Model):
    ...     first_name = micromodels.CharField()
    ...     last_name = micromodels.CharField()
    ...     date_of_birth = micromodels.DateField(format="%Y-%m-%d")
    ...
    ...     @property
    ...     def full_name(self):
    ...         return "%s %s" % (self.first_name, self.last_name)
    >>> douglas_data = {
    ...     "first_name": "Douglas",
    ...     "last_name": "Adams",
    ...     "date_of_birth": "1952-03-11",
    ... }
    >>> douglas = Author.from_dict(douglas_data)
    >>> print "%s was born in %s" % (douglas.full_name, douglas.date_of_birth.strftime("%Y"))


Slightly more complex example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    >>> import json
    >>> from urllib2 import urlopen
    >>> import micromodels
    >>> class TwitterUser(micromodels.Model):
    ...     id = micromodels.IntegerField()
    ...     screen_name = micromodels.CharField()
    ...     name = micromodels.CharField()
    ...     description = micromodels.CharField()
    ...
    ...     def get_profile_url(self):
    ...         return 'http://twitter.com/%s' % self.screen_name
    ...
    >>> class Tweet(micromodels.Model):
    ...     id = micromodels.IntegerField()
    ...     text = micromodels.CharField()
    ...     created_at = micromodels.DateTimeField(format="%a %b %d %H:%M:%S +0000 %Y")
    ...     user = micromodels.ModelField(TwitterUser)
    ...
    >>> json_data = urlopen('http://api.twitter.com/1/statuses/show/20.json').read()
    >>> tweet = Tweet.from_dict(json_data, is_json=True)
    >>> print tweet.user.name
    >>> print tweet.user.get_profile_url()
    >>> print tweet.id
    >>> print tweet.created_at.strftime('%A')

New fields can also be added to the model instance. A method needs to be used to do this to handle serialization:

    >>> tweet.add_field('retweet_count', 44, micromodels.IntegerField())
    >>> print tweet.retweet_count

The data can be cast to a dict (still containing time object):

    >>> print tweet.to_dict()

Tt can also be cast to JSON (fields handle their own serialization):

    >>> print tweet.to_json()
    >>> #tweet.to_json() is equivalent to this call
    >>> json.dumps(tweet.to_dict(serial=True))
