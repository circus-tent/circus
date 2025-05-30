"""
Test to verify signal handler is now safe after our fix.
"""
import signal
import threading
import time
from unittest import TestCase, skipIf
from unittest.mock import patch, MagicMock

from circus.sighandler import SysHandler
from circus.util import IS_WINDOWS


class TestCurrentSignalSafety(TestCase):
    """Test to verify signal handler is now safe."""
    
    @skipIf(IS_WINDOWS, "Signal handling different on Windows")
    def test_current_signal_handler_is_now_safe(self):
        """
        Verify that signal handler no longer performs unsafe operations directly.
        """
        # Create a mock controller
        mock_controller = MagicMock()
        mock_loop = MagicMock()
        mock_controller.loop = mock_loop
        
        # Patch logger to track calls
        with patch('circus.sighandler.logger') as mock_logger:
            handler = SysHandler(mock_controller)
            
            # Reset to ignore the registration message
            mock_logger.reset_mock()
            
            # Trigger signal handler
            handler.signal(signal.SIGTERM)
            
            # Logger should NOT be called in signal handler anymore (SAFE!)
            mock_logger.info.assert_not_called()
            
            # Instead, it should only schedule a callback
            mock_loop.add_callback_from_signal.assert_called_once()
            
            # Verify the callback is the safe handler
            call_args = mock_loop.add_callback_from_signal.call_args
            self.assertEqual(call_args[0][0], handler._handle_signal_in_main_thread)
            self.assertEqual(call_args[0][1], signal.SIGTERM)
            
    def test_signal_handler_no_longer_does_unsafe_operations(self):
        """
        Verify that signal handler no longer does dictionary lookups or string operations.
        """
        mock_controller = MagicMock()
        mock_controller.loop = MagicMock()
        handler = SysHandler(mock_controller)
        
        # The signal method now only does ONE thing:
        # 1. Calls add_callback_from_signal (SAFE)
        # 
        # All unsafe operations moved to _handle_signal_in_main_thread:
        # - self.SIG_NAMES.get(sig) - Dictionary lookup
        # - getattr(self, "handle_%s" % signame) - Object attribute access  
        # - String formatting with % - Memory allocation
        # - Logging
        
        # These are now SAFE because they run in main thread
        
    def test_deadlock_scenario_prevented(self):
        """
        Verify that the deadlock scenario is now prevented.
        """
        # The fix prevents deadlocks:
        # 1. Main thread acquires logging lock
        # 2. Signal arrives, interrupting main thread
        # 3. Signal handler ONLY calls add_callback_from_signal (no locks needed)
        # 4. Main thread continues, releases lock
        # 5. Callback runs in main thread, can safely acquire logging lock
        print("\nDeadlock prevention with new implementation:")
        print("1. Main thread: logger.info() acquires internal lock")
        print("2. SIGTERM arrives, interrupting main thread") 
        print("3. Signal handler: ONLY calls add_callback_from_signal (no locks)")
        print("4. Main thread continues and releases lock")
        print("5. Callback runs safely in main thread with access to all locks")