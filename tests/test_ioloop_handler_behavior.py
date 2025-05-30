"""
Test to understand IOLoop handler behavior - what exceptions are raised
when removing non-existent handlers.
"""
import os
from tornado.testing import AsyncTestCase
from tornado import ioloop


class TestIOLoopHandlerBehavior(AsyncTestCase):
    def test_remove_nonexistent_handler(self):
        """Test what happens when removing a handler that doesn't exist"""
        # Create a pipe to get a valid file descriptor
        r, w = os.pipe()
        
        try:
            # Try to remove a handler that was never added
            exception_caught = None
            try:
                self.io_loop.remove_handler(r)
                print("No exception raised when removing non-existent handler")
            except Exception as e:
                exception_caught = e
                print(f"Exception type: {type(e).__name__}")
                print(f"Exception message: {e}")
                
            # Verify what happened
            if exception_caught:
                self.assertIsInstance(exception_caught, (KeyError, ValueError))
            else:
                # No exception - this is what actually happens in some Tornado versions
                print("remove_handler silently succeeds for non-existent handlers")
                
        finally:
            os.close(r)
            os.close(w)
            
    def test_add_handler_twice(self):
        """Test what happens when adding the same handler twice"""
        r, w = os.pipe()
        
        try:
            # Add a handler
            handler = lambda fd, events: None
            self.io_loop.add_handler(r, handler, ioloop.IOLoop.READ)
            
            # Try to add it again
            exception_caught = None
            try:
                self.io_loop.add_handler(r, handler, ioloop.IOLoop.READ)
                print("No exception when adding handler twice")
            except Exception as e:
                exception_caught = e
                print(f"Exception type: {type(e).__name__}")
                print(f"Exception message: {e}")
                
            # This should raise ValueError
            self.assertIsInstance(exception_caught, ValueError)
            self.assertIn("added twice", str(exception_caught))
            
            # Clean up
            self.io_loop.remove_handler(r)
            
        finally:
            os.close(r)
            os.close(w)
            
    def test_remove_after_add(self):
        """Test normal add/remove cycle"""
        r, w = os.pipe()
        
        try:
            # Add handler
            handler = lambda fd, events: None
            self.io_loop.add_handler(r, handler, ioloop.IOLoop.READ)
            
            # Remove it
            exception_caught = None
            try:
                self.io_loop.remove_handler(r)
                print("Handler removed successfully")
            except Exception as e:
                exception_caught = e
                print(f"Unexpected exception: {e}")
                
            self.assertIsNone(exception_caught)
            
            # Try to remove again
            try:
                self.io_loop.remove_handler(r)
                print("Second remove also succeeded (no exception)")
            except Exception as e:
                print(f"Second remove raised: {type(e).__name__}: {e}")
                
        finally:
            os.close(r)
            os.close(w)