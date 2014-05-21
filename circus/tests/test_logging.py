try:
    from io import StringIO
    from io import BytesIO
except ImportError:
    from cStringIO import StringIO  # NOQA
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser  # NOQA
from circus.tests.support import TestCase
from circus.tests.support import EasyTestSuite
from circus.tests.support import skipIf
import os
import shutil
import tempfile
from pipes import quote as shell_escape_arg
import subprocess
import time
import yaml
import json
import logging.config
import sys


HERE = os.path.abspath(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(HERE, 'config', 'circus.ini')


def run_circusd(options=(), config=(), log_capture_path="log.txt",
                additional_files=()):
    options = list(options)
    additional_files = dict(additional_files)
    config_ini_update = {
        "watcher:touch.cmd": sys.executable,
        "watcher:touch.args": "-c \"open('workerstart.txt', 'w+').close()\"",
        "watcher:touch.respawn": 'False'
    }
    config_ini_update.update(dict(config))
    config_ini = ConfigParser()
    config_ini.read(CONFIG_PATH)
    for dottedkey in config_ini_update:
        section, key = dottedkey.split(".", 1)
        if section not in config_ini.sections():
            config_ini.add_section(section)
        config_ini.set(
            section, key, config_ini_update[dottedkey])
    temp_dir = tempfile.mkdtemp()
    try:
        circus_ini_path = os.path.join(temp_dir, "circus.ini")
        with open(circus_ini_path, "w") as fh:
            config_ini.write(fh)
        for relpath in additional_files:
            path = os.path.join(temp_dir, relpath)
            with open(path, "w") as fh:
                fh.write(additional_files[relpath])
        env = os.environ.copy()
        # We're going to run circus from a process with a different
        # cwd, so we need to make sure that Python will import the
        # current version of circus
        pythonpath = env.get('PYTHONPATH', '')
        pythonpath += ':%s' % os.path.abspath(
            os.path.join(HERE, os.pardir, os.pardir))
        env['PYTHONPATH'] = pythonpath
        argv = ["circus.circusd"] + options + [circus_ini_path]
        if sys.gettrace() is None:
            argv = [sys.executable, "-m"] + argv
        else:
            exe_dir = os.path.dirname(sys.executable)
            coverage = os.path.join(exe_dir, "coverage")
            if not os.path.isfile(coverage):
                coverage = "coverage"
            argv = [coverage, "run", "-p", "-m"] + argv

        child = subprocess.Popen(argv, cwd=temp_dir, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 env=env)
        try:
            touch_path = os.path.join(temp_dir, "workerstart.txt")
            while True:
                child.poll()
                if os.path.exists(touch_path):
                    break
                if child.returncode is not None:
                    break
                time.sleep(0.01)
        finally:
            child.terminate()
            child.wait()

        log_file_path = os.path.join(temp_dir, log_capture_path)

        try:
            if os.path.exists(log_file_path):
                with open(log_file_path, "r") as fh:
                    return fh.read()
            else:
                if child.stdout is not None:
                    raise Exception(child.stdout.read().decode("ascii"))
        finally:
            if child.stdout is not None:
                child.stdout.close()
            if child.stderr is not None:
                child.stderr.close()
            if child.stdin is not None:
                child.stdin.close()

        assert child.returncode == 0, \
            " ".join(shell_escape_arg(a) for a in argv)
    finally:
        for basename in sorted(os.listdir(temp_dir)):
            if basename.startswith(".coverage."):
                source = os.path.join(temp_dir, basename)
                target = os.path.abspath(basename)
                shutil.copy(source, target)
        shutil.rmtree(temp_dir)

EXAMPLE_YAML = """\
version: 1
disable_existing_loggers: false
formatters:
  simple:
    format: '%(asctime)s - %(name)s - [%(levelname)s] %(message)s'
handlers:
  logfile:
    class: logging.FileHandler
    filename: logoutput.txt
    level: DEBUG
    formatter: simple
loggers:
  circus:
    level: DEBUG
    handlers: [logfile]
    propagate: no
root:
  level: DEBUG
  handlers: [logfile]
"""

EXPECTED_LOG_MESSAGE = "[INFO] Arbiter now waiting for commands"


def logging_dictconfig_to_ini(config):
    assert config.get("version", 1) == 1, config
    ini = ConfigParser()
    ini.add_section("loggers")
    loggers = config.get("loggers", {})
    if "root" in config:
        loggers["root"] = config["root"]
    ini.set("loggers", "keys", ",".join(sorted(loggers.keys())))
    for logger in sorted(loggers.keys()):
        section = "logger_%s" % (logger.replace(".", "_"),)
        ini.add_section(section)
        for key, value in sorted(loggers[logger].items()):
            if key == "handlers":
                value = ",".join(value)
            if key == "propagate":
                value = "1" if value else "0"
            ini.set(section, key, value)
        ini.set(section, "qualname", logger)
    ini.add_section("handlers")
    handlers = config.get("handlers", {})
    ini.set("handlers", "keys", ",".join(sorted(handlers.keys())))
    for handler in sorted(handlers.keys()):
        section = "handler_%s" % (handler,)
        ini.add_section(section)
        args = []
        for key, value in sorted(handlers[handler].items()):
            if (handlers[handler]["class"] == "logging.FileHandler"
                    and key == "filename"):
                args.append(value)
            else:
                ini.set(section, key, value)
        ini.set(section, "args", repr(tuple(args)))
    ini.add_section("formatters")
    formatters = config.get("formatters", {})
    ini.set("formatters", "keys", ",".join(sorted(formatters.keys())))
    for formatter in sorted(formatters.keys()):
        section = "formatter_%s" % (formatter,)
        ini.add_section(section)
        for key, value in sorted(formatters[formatter].items()):
            ini.set(section, key, value)
    try:
        # Older Python (without io.StringIO/io.BytesIO) and Python 3 use
        # this code path.
        result = StringIO()
        ini.write(result)
        return result.getvalue()
    except TypeError:
        # Python 2.7 has io.StringIO and io.BytesIO but ConfigParser.write
        # has not been fixed to work with StringIO.
        result = BytesIO()
        ini.write(result)
        return result.getvalue().decode("ascii")


def hasDictConfig():
    return hasattr(logging.config, "dictConfig")


class TestLoggingConfig(TestCase):

    def test_loggerconfig_default_ini(self):
        logs = run_circusd(
            [], {"circus.logoutput": "log_ini.txt"},
            log_capture_path="log_ini.txt")
        self.assertTrue(EXPECTED_LOG_MESSAGE in logs, logs)

    def test_loggerconfig_default_opt(self):
        logs = run_circusd(
            ["--log-output", "log_opt.txt"], {},
            log_capture_path="log_opt.txt")
        self.assertTrue(EXPECTED_LOG_MESSAGE in logs, logs)

    @skipIf(not hasDictConfig(), "Needs logging.config.dictConfig()")
    def test_loggerconfig_yaml_ini(self):
        config = yaml.load(EXAMPLE_YAML)
        config["handlers"]["logfile"]["filename"] = "log_yaml_ini.txt"
        logs = run_circusd(
            [], {"circus.loggerconfig": "logging.yaml"},
            log_capture_path="log_yaml_ini.txt",
            additional_files={"logging.yaml": yaml.dump(config)})
        self.assertTrue(EXPECTED_LOG_MESSAGE in logs, logs)

    @skipIf(not hasDictConfig(), "Needs logging.config.dictConfig()")
    def test_loggerconfig_yaml_opt(self):
        config = yaml.load(EXAMPLE_YAML)
        config["handlers"]["logfile"]["filename"] = "log_yaml_opt.txt"
        logs = run_circusd(
            ["--logger-config", "logging.yaml"], {},
            log_capture_path="log_yaml_opt.txt",
            additional_files={"logging.yaml": yaml.dump(config)})
        self.assertTrue(EXPECTED_LOG_MESSAGE in logs, logs)

    @skipIf(not hasDictConfig(), "Needs logging.config.dictConfig()")
    def test_loggerconfig_json_ini(self):
        config = yaml.load(EXAMPLE_YAML)
        config["handlers"]["logfile"]["filename"] = "log_json_ini.txt"
        logs = run_circusd(
            [], {"circus.loggerconfig": "logging.json"},
            log_capture_path="log_json_ini.txt",
            additional_files={"logging.json": json.dumps(config)})
        self.assertTrue(EXPECTED_LOG_MESSAGE in logs, logs)

    @skipIf(not hasDictConfig(), "Needs logging.config.dictConfig()")
    def test_loggerconfig_json_opt(self):
        config = yaml.load(EXAMPLE_YAML)
        config["handlers"]["logfile"]["filename"] = "log_json_opt.txt"
        logs = run_circusd(
            ["--logger-config", "logging.json"], {},
            log_capture_path="log_json_opt.txt",
            additional_files={"logging.json": json.dumps(config)})
        self.assertTrue(EXPECTED_LOG_MESSAGE in logs, logs)

    def test_loggerconfig_ini_ini(self):
        config = yaml.load(EXAMPLE_YAML)
        config["handlers"]["logfile"]["filename"] = "log_ini_ini.txt"
        logs = run_circusd(
            [], {"circus.loggerconfig": "logging.ini"},
            log_capture_path="log_ini_ini.txt",
            additional_files={
                "logging.ini": logging_dictconfig_to_ini(config)})
        self.assertTrue(EXPECTED_LOG_MESSAGE in logs, logs)

    def test_loggerconfig_ini_opt(self):
        config = yaml.load(EXAMPLE_YAML)
        config["handlers"]["logfile"]["filename"] = "log_ini_opt.txt"
        logs = run_circusd(
            ["--logger-config", "logging.ini"], {},
            log_capture_path="log_ini_opt.txt",
            additional_files={
                "logging.ini": logging_dictconfig_to_ini(config)})
        self.assertTrue(EXPECTED_LOG_MESSAGE in logs, logs)

test_suite = EasyTestSuite(__name__)
