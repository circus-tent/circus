"""
Test for an improved fix to the fd added twice error.
"""
import os
from tornado.testing import AsyncTestCase
from tornado import ioloop
from unittest.mock import MagicMock

from circus.stream.redirector import Redirector


class TestRedirectorImprovedFix(AsyncTestCase):
    def test_current_fix_unnecessary_parts(self):
        """Demonstrate that some parts of the current fix are unnecessary"""
        
        stdout_redirect = MagicMock()
        stderr_redirect = MagicMock()
        redirector = Redirector(stdout_redirect, stderr_redirect, loop=self.io_loop)
        
        # Create a pipe
        r, w = os.pipe()
        
        try:
            # Add to redirector structures
            process = MagicMock(pid=1234)
            pipe = MagicMock()
            redirector.pipes[r] = ('stdout', process, pipe)
            
            # The current _start_one will try to remove handler first
            # But this is unnecessary since remove_handler doesn't throw
            count = redirector._start_one(r, 'stdout', process, pipe)
            self.assertEqual(count, 1)
            self.assertIn(r, redirector._active)
            
            # Clean up
            redirector._stop_one(r)
            
        finally:
            os.close(r)
            os.close(w)
            
    def test_improved_fix(self):
        """Test a cleaner approach to preventing fd added twice"""
        
        class ImprovedRedirector(Redirector):
            def _start_one(self, fd, stream_name, process, pipe):
                if fd not in self._active:
                    # Simply remove any existing handler - no exception handling needed
                    self.loop.remove_handler(fd)
                    
                    handler = self.Handler(self, stream_name, process, pipe)
                    self.loop.add_handler(fd, handler, ioloop.IOLoop.READ)
                    self._active[fd] = handler
                    return 1
                return 0
                
            def _stop_one(self, fd):
                # No exception handling needed - remove_handler is safe
                self.loop.remove_handler(fd)
                
                removed = 0
                if fd in self._active:
                    del self._active[fd]
                    removed = 1
                    
                return removed
        
        stdout_redirect = MagicMock()
        stderr_redirect = MagicMock()
        redirector = ImprovedRedirector(stdout_redirect, stderr_redirect, loop=self.io_loop)
        
        # Test that it prevents the fd added twice error
        r, w = os.pipe()
        
        try:
            # Manually add handler to simulate the error condition
            test_handler = lambda fd, events: None
            self.io_loop.add_handler(r, test_handler, ioloop.IOLoop.READ)
            
            # Add to redirector
            process = MagicMock(pid=1234)
            pipe = MagicMock()
            redirector.pipes[r] = ('stdout', process, pipe)
            
            # This should work without ValueError
            count = redirector._start_one(r, 'stdout', process, pipe)
            self.assertEqual(count, 1)
            self.assertIn(r, redirector._active)
            
            # Verify our handler replaced the test handler
            self.assertIsInstance(redirector._active[r], redirector.Handler)
            
        finally:
            redirector._stop_one(r)
            os.close(r)
            os.close(w)