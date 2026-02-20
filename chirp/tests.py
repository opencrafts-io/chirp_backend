from django.test import TestCase

from .celery import debug_task


class TestCelery(TestCase):
    def setUp(self):
        pass

    def test_debug_task_executes(self):
        """Tests that the debug task executes without raising exception(s)"""
        result = debug_task.delay()
        self.assertIsNotNone(result)

    def test_debug_task_direct_call(self):
        """Tests a direct synchronous call happens immediately"""
        result = debug_task()
        self.assertIsNone(result)

