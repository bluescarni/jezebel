"""Root Jezebel module.

.. moduleauthor:: Francesco Biscani <bluescarni@gmail.com>

"""

__all__ = ['rpc', 'xmpp', 'master', 'directions', 'example']

# Temporarily here.
def enable_logging():
	import logging
	l = logging.getLogger('jezebel')
	l.setLevel(logging.INFO)
	ch = logging.StreamHandler()
	ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
	l.addHandler(ch)
