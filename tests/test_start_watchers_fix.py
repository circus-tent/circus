"""
Test the fix for start_watchers to skip already-running watchers.
"""
from tornado import gen
from tornado.testing import AsyncTestCase
from unittest.mock import MagicMock, patch

from circus.watcher import Watcher


class TestStartWatchersFix(AsyncTestCase):
    def test_start_skips_running_watchers(self):
        """Test that _start_watchers skips watchers that are not stopped"""
        
        # Create a minimal arbiter-like object
        class MinimalArbiter:
            def __init__(self):
                self.warmup_delay = 0
                self.watchers = []
                
            def iter_watchers(self):
                return self.watchers
                
            @gen.coroutine
            def _start_watchers(self, watcher_iter_func=None):
                # This is our fixed version
                if watcher_iter_func is None:
                    watchers = self.iter_watchers()
                else:
                    watchers = watcher_iter_func()
                started_any = False
                for watcher in watchers:
                    if watcher.autostart and watcher.stopped:
                        yield watcher._start()
                        yield gen.sleep(self.warmup_delay)
                        started_any = True
                if not started_any:
                    print("All watchers already running")
                    
        arbiter = MinimalArbiter()
        
        # Create test watchers
        watcher1 = MagicMock()
        watcher1.autostart = True
        watcher1.stopped = True
        watcher1._start = MagicMock(return_value=gen.moment)
        
        watcher2 = MagicMock()
        watcher2.autostart = True
        watcher2.stopped = False  # Already running
        watcher2._start = MagicMock(return_value=gen.moment)
        
        arbiter.watchers = [watcher1, watcher2]
        
        # Run start_watchers
        self.io_loop.run_sync(lambda: arbiter._start_watchers())
        
        # Only watcher1 should have been started
        self.assertEqual(watcher1._start.call_count, 1)
        self.assertEqual(watcher2._start.call_count, 0)
        
        # Mark watcher1 as running now
        watcher1.stopped = False
        
        # Run again - neither should start
        self.io_loop.run_sync(lambda: arbiter._start_watchers())
        
        # Still the same counts
        self.assertEqual(watcher1._start.call_count, 1)
        self.assertEqual(watcher2._start.call_count, 0)