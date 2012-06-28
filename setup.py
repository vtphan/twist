from distutils.core import setup

setup(
    name='Twist',
    version='0.2.2',
    author='Vinhthuy Phan',
    author_email='vphan@memphis.edu',
    packages=['twist'],
    scripts=['twist/twist.py'],
    url='https://github.com/vtphan/twist',
    license='MIT',
    description='A wsgi web framework.',
    long_description='A wsgi web framework.',
    install_requires=[
        "webob",
        "Jinja2",
    ],
)
