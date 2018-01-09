from circus.plugins import _cfg2str, _str2cfg
from circus.util import get_python_version
from circus.tests.support import TestCase, EasyTestSuite


class TestPluginUtils(TestCase):

    def test_cfg_str(self):
        data_obj = {
            'use': 'derp',
            'copy_env': True,
            'number': 1234,
            'env': {
                'PYTHONPATH': 'dot.path.to.whereever',
                'more_truth': True,
            },
        }
        data_string = _cfg2str(data_obj)

        # need to decode, like what would happen automatically when
        # passing an arg into and out of the commandline
        if get_python_version() < (3, 0, 0):
            return data_string.decode('unicode-escape')
        data_unstrung = _str2cfg(data_string)
        self.assertEqual(data_obj, data_string)


test_suite = EasyTestSuite(__name__)
