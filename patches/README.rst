Multi-tenant Patching
=====================

.. toctree::


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


Testing Patches
---------------

A fast way of testing and fixing patches is to run a Saleor container on the host machine,
and then copy the patch files like so:

.. code-block:: shell

	$ docker run --rm --name saleor -ti mirumee/saleor:master bash
	$ docker cp patches/ saleor:/tmp/patches

Then inside the container, apply the patches as a dry-run:

.. code-block:: shell

	# apt update && apt install -y --no-install-recommends git vim
	# git apply --summary --verbose /tmp/patches/*.patch

Doing ``git apply --summary [...]`` will allow to do "dry-run" patches and thus
allow to make changes to fix patches without affecting the Saleor files.

.. note::

	One can also use ``git`` to quickly generate new patches from that container by
	setting up a local repository.
