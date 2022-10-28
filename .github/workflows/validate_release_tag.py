# -*- coding: utf-8 -*-
"""Validate that the version in the tag label matches the version of the package."""
import argparse
import ast
from pathlib import Path


def get_version_from_module(content: str) -> str:
    """Get the ``__version__`` attribute from a module.

    .. note:: This has been adapted from :mod:`setuptools.config`.
    """
    try:
        module = ast.parse(content)
    except SyntaxError as exception:
        raise IOError('Unable to parse module.') from exception

    try:
        return next(
            ast.literal_eval(statement.value) for statement in module.body if isinstance(statement, ast.Assign)
            for target in statement.targets if isinstance(target, ast.Name) and target.id == '__version__'
        )
    except StopIteration as exception:
        raise IOError('Unable to find the `__version__` attribute in the module.') from exception


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('GITHUB_REF', help='The GITHUB_REF environmental variable')
    args = parser.parse_args()
    tag_prefix = 'refs/tags/v'
    assert args.GITHUB_REF.startswith(tag_prefix), f'GITHUB_REF should start with "{tag_prefix}": {args.GITHUB_REF}'
    tag_version = args.GITHUB_REFremoveprefix(tag_prefix)
    package_version = get_version_from_module(Path('circus/__init__.py').read_text(encoding='utf-8'))
    error_message = f'The tag version `{tag_version}` is different from the package version `{package_version}`'
    assert tag_version == package_version, error_message
