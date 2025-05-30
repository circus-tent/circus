"""
Regression test for the production "fd added twice" error.
This test specifically verifies the fix prevents the ValueError.
"""
import os
from tornado.testing import gen_test
from unittest import mock

from tests.support import TestCircus
from circus.stream.redirector import Redirector
from tornado import ioloop


class TestFdAddedTwiceRegression(TestCircus):
    """Regression test for stacktraces/1.txt ValueError: fd 23 added twice"""
    
    @gen_test
    def test_fd_added_twice_fix(self):
        """
        Verify that the fix prevents ValueError: fd X added twice
        when there's a state mismatch between redirector and IOLoop.
        """
        # Create test pipes
        r, w = os.pipe()
        
        try:
            # Create redirector with mock handler
            redirector = Redirector(mock.Mock(), mock.Mock(), 
                                  loop=ioloop.IOLoop.current())
            
            # Manually add handler to IOLoop to simulate the error condition
            test_handler = lambda fd, events: None
            ioloop.IOLoop.current().add_handler(r, test_handler, ioloop.IOLoop.READ)
            
            # Now try to add through redirector - this would have raised ValueError before fix
            redirector.pipes[r] = ('stdout', mock.Mock(pid=1234), mock.Mock())
            
            # This should NOT raise ValueError with our fix
            count = redirector.start()
            
            # Verify it handled the situation gracefully
            self.assertIn(r, redirector._active)
            
        finally:
            # Clean up
            try:
                ioloop.IOLoop.current().remove_handler(r)
            except:
                pass
            if 'redirector' in locals():
                redirector.stop()
            os.close(r)
            os.close(w)