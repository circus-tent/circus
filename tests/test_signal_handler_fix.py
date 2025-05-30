"""
Test that validates the signal handler safety fix.
"""
import signal
from unittest import TestCase, skipIf
from unittest.mock import patch, MagicMock, call

from circus.sighandler import SysHandler
from circus.util import IS_WINDOWS


class TestSignalHandlerFix(TestCase):
    """Test that signal handler safety issues are fixed."""
    
    @skipIf(IS_WINDOWS, "Signal handling different on Windows")
    def test_signal_handler_defers_to_main_thread(self):
        """
        Test that signal handler only performs safe operations.
        """
        # Create a mock controller with loop
        mock_controller = MagicMock()
        mock_loop = MagicMock()
        mock_controller.loop = mock_loop
        
        # Patch logger to ensure it's NOT called in signal handler
        with patch('circus.sighandler.logger') as mock_logger:
            handler = SysHandler(mock_controller)
            
            # Reset mock to ignore the registration log message
            mock_logger.reset_mock()
            
            # Trigger signal handler
            handler.signal(signal.SIGTERM)
            
            # Logger should NOT have been called yet (would be unsafe)
            mock_logger.info.assert_not_called()
            
            # Verify that add_callback_from_signal was called (the only safe operation)
            mock_loop.add_callback_from_signal.assert_called_once()
            
            # Get the callback that was registered
            call_args = mock_loop.add_callback_from_signal.call_args
            callback_func = call_args[0][0]
            signal_arg = call_args[0][1]
            
            # Verify it's our handler method
            self.assertEqual(callback_func, handler._handle_signal_in_main_thread)
            self.assertEqual(signal_arg, signal.SIGTERM)
            
            # Now simulate the callback being called in main thread
            callback_func(signal.SIGTERM)
            
            # NOW logger should have been called (safe in main thread)
            mock_logger.info.assert_called_with('Got signal SIG_TERM')
            
    @skipIf(IS_WINDOWS, "Signal handling different on Windows")
    def test_quit_and_reload_work_correctly(self):
        """
        Test that quit and reload methods work from main thread.
        """
        mock_controller = MagicMock()
        mock_loop = MagicMock()
        mock_controller.loop = mock_loop
        
        handler = SysHandler(mock_controller)
        
        # Test SIGTERM -> quit flow
        handler.signal(signal.SIGTERM)
        
        # Get and call the callback
        callback = mock_loop.add_callback_from_signal.call_args[0][0]
        callback(signal.SIGTERM)
        
        # Should have called dispatch with quit command
        mock_controller.dispatch.assert_called_with(
            (None, b'{"command": "quit", "properties": {}}')
        )
        
        # Reset and test SIGHUP -> reload flow
        mock_controller.reset_mock()
        mock_loop.reset_mock()
        
        handler.signal(signal.SIGHUP)
        callback = mock_loop.add_callback_from_signal.call_args[0][0]
        callback(signal.SIGHUP)
        
        # Should have called dispatch with reload command
        mock_controller.dispatch.assert_called_with(
            (None, b'{"command": "reload", "properties": {"graceful": true}}')
        )
        
    @skipIf(IS_WINDOWS, "Signal handling different on Windows")
    def test_signal_handler_error_handling(self):
        """
        Test that signal handler handles errors safely.
        """
        mock_controller = MagicMock()
        mock_loop = MagicMock()
        mock_controller.loop = mock_loop
        
        # Make add_callback_from_signal raise an exception
        mock_loop.add_callback_from_signal.side_effect = Exception("Loop error")
        
        handler = SysHandler(mock_controller)
        
        # This should not raise but should write to stderr and exit
        with patch('os.write') as mock_write, patch('os._exit') as mock_exit:
            handler.signal(signal.SIGTERM)
            
            # Should have written error message
            mock_write.assert_called_with(2, b"CRITICAL: Failed to handle signal safely\n")
            # Should have exited
            mock_exit.assert_called_with(1)