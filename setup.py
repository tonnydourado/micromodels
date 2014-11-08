import os
import re
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


# Inspired by the example at https://pytest.org/latest/goodpractises.html
class NoseTestCommand(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # Run nose ensuring that argv simulates running nosetests directly
        import nose
        nose.run_exit(argv=['nosetests', 'tests'])


def rel_file(*args):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *args)


def read_from(filename):
    with open(filename) as f:
        return f.read()


def get_long_description():
    return read_from(rel_file('README.md'))


def get_version():
    data = read_from(rel_file('micromodels', '__init__.py'))
    return re.search(r"__version__ = '([^']+)'", data).group(1)

setup(
    name='micromodels',
    description='Declarative dictionary-based model classes for Python',
    long_description=get_long_description(),
    version=get_version(),
    packages=find_packages(),
    url='https://github.com/j4mie/micromodels/',
    author='Jamie Matthews',
    author_email='jamie.matthews@gmail.com',
    license='Public Domain',
    install_requires=["arrow"],
    tests_require=["nose"],
    cmdclass={'test': NoseTestCommand},
    classifiers=[
        'Programming Language :: Python',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: Public Domain',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
