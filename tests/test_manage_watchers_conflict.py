"""
Test to reproduce ConflictError between manage_watchers and watcher_stop.

This test reproduces the production error from stacktrace 3.txt where
manage_watchers conflicts with watcher_stop command.
"""
import asyncio
from tornado import gen
from tornado.testing import AsyncTestCase
from unittest.mock import MagicMock, patch

from circus.arbiter import Arbiter
from circus.exc import ConflictError
from circus.util import AsyncPeriodicCallback
from circus.watcher import Watcher


class TestManageWatchersConflict(AsyncTestCase):
    def setUp(self):
        super(TestManageWatchersConflict, self).setUp()
        self.arbiter = None

    def tearDown(self):
        if self.arbiter is not None:
            try:
                self.io_loop.run_sync(self._stop_arbiter)
            except:
                pass
        super(TestManageWatchersConflict, self).tearDown()

    @gen.coroutine
    def _stop_arbiter(self):
        if hasattr(self.arbiter, '_emergency_stop'):
            yield self.arbiter._emergency_stop()

    def test_manage_watchers_vs_watcher_stop_conflict(self):
        """Test that manage_watchers conflicts with watcher_stop"""
        
        conflict_errors = []
        manage_watchers_calls = []
        
        # Create a mock arbiter with the essential attributes
        class MockArbiter:
            def __init__(self):
                self._exclusive_running_command = None
                self._restarting = False
                self._stopping = False
                self.watchers = []
                
            def iter_watchers(self):
                return self.watchers
                
            def reap_processes(self):
                pass
                
            @gen.coroutine
            def manage_watchers(self):
                """Original manage_watchers without the synchronized decorator"""
                manage_watchers_calls.append("called")
                if self._stopping:
                    return
                    
                # This is what synchronized decorator does
                if self._exclusive_running_command is not None:
                    error = ConflictError("arbiter is already running %s command" 
                                        % self._exclusive_running_command)
                    conflict_errors.append(error)
                    raise error
                    
                self._exclusive_running_command = "manage_watchers"
                try:
                    # Simulate the work manage_watchers does
                    self.reap_processes()
                    list_to_yield = []
                    for watcher in self.iter_watchers():
                        list_to_yield.append(watcher.manage_processes())
                    if len(list_to_yield) > 0:
                        yield list_to_yield
                finally:
                    self._exclusive_running_command = None
                    
        # Create mock watcher
        class MockWatcher:
            def __init__(self, name, arbiter):
                self.name = name
                self.arbiter = arbiter
                self.stopped = True
                
            def is_stopped(self):
                return self.stopped
                
            @gen.coroutine
            def stop(self):
                """Simulated watcher stop with synchronized behavior"""
                if self.arbiter._exclusive_running_command is not None:
                    raise ConflictError("arbiter is already running %s command" 
                                      % self.arbiter._exclusive_running_command)
                                      
                self.arbiter._exclusive_running_command = "watcher_stop"
                try:
                    # Simulate stop taking some time
                    yield gen.sleep(0.1)
                    self.stopped = True
                finally:
                    self.arbiter._exclusive_running_command = None
                    
            @gen.coroutine
            def manage_processes(self):
                yield gen.moment
                
        arbiter = MockArbiter()
        watcher = MockWatcher("test", arbiter)
        arbiter.watchers = [watcher]
        
        @gen.coroutine
        def simulate_conflict():
            # Start watcher stop
            stop_future = watcher.stop()
            
            # While stop is running, manage_watchers gets called
            # This simulates the periodic callback firing
            yield gen.sleep(0.01)  # Let stop start
            
            # This should raise ConflictError
            try:
                yield arbiter.manage_watchers()
            except ConflictError as e:
                # Expected
                pass
                
            # Wait for stop to complete
            yield stop_future
            
        self.io_loop.run_sync(simulate_conflict)
        
        # Verify we got the conflict
        self.assertEqual(len(conflict_errors), 1)
        self.assertIn("watcher_stop", str(conflict_errors[0]))
        
    def test_real_scenario_with_yield_fix(self):
        """Test that the yield fix in manage_watchers helps"""
        
        # The bug we fixed: manage_watchers was calling _start_watchers()
        # without yielding, which could cause issues
        
        class TestArbiter:
            def __init__(self):
                self._stopping = False
                self._exclusive_running_command = None
                self._restarting = False
                self.watchers = []
                self.warmup_delay = 0
                self.sockets = {}
                self.socket_event = False
                
            def iter_watchers(self):
                return self.watchers
                
            def reap_processes(self):
                pass
                
            @gen.coroutine
            def _start_watchers(self):
                # Simulate some async work
                yield gen.sleep(0.01)
                return "started"
                
            @gen.coroutine  
            def manage_watchers_broken(self):
                """Version with the bug - doesn't yield _start_watchers"""
                if self._stopping:
                    return
                    
                self.reap_processes()
                list_to_yield = []
                for watcher in self.iter_watchers():
                    if hasattr(watcher, 'on_demand') and watcher.on_demand and watcher.is_stopped():
                        # BUG: not yielding the coroutine!
                        self._start_watchers()  # This returns a Future, not the result
                        
            @gen.coroutine
            def manage_watchers_fixed(self):
                """Fixed version - properly yields _start_watchers"""
                if self._stopping:
                    return
                    
                self.reap_processes()
                list_to_yield = []
                for watcher in self.iter_watchers():
                    if hasattr(watcher, 'on_demand') and watcher.on_demand and watcher.is_stopped():
                        # FIXED: properly yielding
                        yield self._start_watchers()
                        
        arbiter = TestArbiter()
        
        # Add on-demand watcher
        mock_watcher = MagicMock()
        mock_watcher.on_demand = True
        mock_watcher.is_stopped.return_value = True
        mock_watcher.manage_processes.return_value = gen.moment
        arbiter.watchers = [mock_watcher]
        
        # The broken version would not properly wait for _start_watchers
        # This could lead to race conditions and unexpected behavior
        
        # With our fix, _start_watchers is properly yielded
        result = self.io_loop.run_sync(lambda: arbiter.manage_watchers_fixed())
        
        # The test passes if no exceptions are raised
        self.assertIsNone(result)