Instant View
============

.. image:: https://img.shields.io/pypi/v/simplebot_instantview.svg
   :target: https://pypi.org/project/simplebot_instantview

.. image:: https://img.shields.io/pypi/pyversions/simplebot_instantview.svg
   :target: https://pypi.org/project/simplebot_instantview

.. image:: https://pepy.tech/badge/simplebot_instantview
   :target: https://pepy.tech/project/simplebot_instantview

.. image:: https://img.shields.io/pypi/l/simplebot_instantview.svg
   :target: https://pypi.org/project/simplebot_instantview

.. image:: https://github.com/adbenitez/simplebot_instantview/actions/workflows/python-ci.yml/badge.svg
   :target: https://github.com/adbenitez/simplebot_instantview/actions/workflows/python-ci.yml

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black

A `SimpleBot`_ plugin that allows users to preview web sites in `Delta Chat`_.

Install
-------

To install run::

  pip install simplebot-instantview

Customization
-------------

By default maximum file size is 10485760 (10MB), to customize::

  simplebot -a bot@example.com db -s simplebot_instantview/max_size 5242880

To set the nitter instance used for twitter links::

  simplebot -a bot@example.com db -s simplebot_instantview/twitter_proxy "https://twiiit.com"

To set the invidious instance used for youtube links::

  simplebot -a bot@example.com db -s simplebot_instantview/youtube_proxy "https://invidious.snopyta.org"

To set the teddit instance used for reddit links::

  simplebot -a bot@example.com db -s simplebot_instantview/reddit_proxy "https://teddit.net"


.. _SimpleBot: https://github.com/simplebot-org/simplebot
.. _Delta Chat: https://delta.chat
