Multi-tenant Patching
=====================

Updating Patches from local changes
-----------------------------------

TL;DR: ``git diff --patch --no-index <original_file> <destination_file>``

Way #1 (Simplest)
^^^^^^^^^^^^^^^^^

.. code-block:: shell

	# Prepare structure
	$ mkdir a b

	# Copy original
	$ cp ../saleor/conftest.py ./a/

	# Copy modified
	$ cp ./conftest.py ./b/

	# Create patch
	$ git diff -p --no-index --no-prefix a/conftest.py b/conftest.py


Way #2
^^^^^^

.. code-block:: shell

	$ cp ../saleor/conftest.py ./conftest.original.py
	$ git diff -p --no-renames --no-index conftest.original.py conftest.py | sed 's/conftest.original.py/conftest.py/g'
