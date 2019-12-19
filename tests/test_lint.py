import pytest

from pytmc.bin.pragmalint import lint_source, LinterError
from pytmc import parser


def make_pragma(text):
    'Make a multiline pytmc pragma'
    return '''\
{attribute 'pytmc' := '
%s
'}''' % text


def make_source(pragma, variable, type):
    '''
    Make a wrapper for a pragma'd variable, to be used with `lint_source`
    '''

    source = f'''
{make_pragma(pragma)}
{variable} : {type};
'''

    class Wrapper:
        _source = source
        name = 'source-wrapper'
        tag = 'ST'

        def find(cls):
            if cls is parser.Declaration:
                yield Decl

    class Decl:
        parent = Wrapper
        text = source
        tag = 'Decl'

    return Wrapper


def make_source_param(pragma, variable='VAR', type='INT', **param_kw):
    'Make a pytest.param for use with `lint_source`'
    wrapper = make_source(pragma, variable, type)
    identifier = repr(wrapper._source)
    return pytest.param(wrapper, id=identifier, **param_kw)


@pytest.mark.parametrize(
    'source',
    [make_source_param('pv: test'),
     make_source_param('pv: test; io: io'),
     make_source_param('pv: test;; io: io'),
     make_source_param('pv: test\r\n\r io: io'),

     # Valid I/O types
     make_source_param('pv: test; io: i'),
     make_source_param('pv: test; io: o'),
     make_source_param('pv: test; io: io'),
     make_source_param('pv: test; io: input'),
     make_source_param('pv: test; io: output'),
     make_source_param('pv: test; io: rw'),
     make_source_param('pv: test; io: ro'),

     # Bad IO type
     make_source_param('io: foobar', marks=pytest.mark.xfail),

     # Missing delimiters
     make_source_param('pv: test io: test', marks=pytest.mark.xfail),
     make_source_param('pv: test test', marks=pytest.mark.xfail),

     # No PV
     make_source_param('io: io', marks=pytest.mark.xfail),
     make_source_param('abc', marks=pytest.mark.xfail),

     # $ character....
     make_source_param('pv: $(TEST)', marks=pytest.mark.xfail),

     # Update rates
     make_source_param('pv: test; update: 1HZ poll'),
     make_source_param('pv: test; update: 1s poll'),
     make_source_param('pv: test; update: 1HZ    notify'),
     make_source_param('pv: test; update:  1s  notify'),
     make_source_param('pv: test; update:  1HZ'),
     make_source_param('pv: test; update: 1s'),
     make_source_param('pv: test; update: 100es', marks=pytest.mark.xfail),
     make_source_param('pv: test; update: 1s test', marks=pytest.mark.xfail),
     make_source_param('pv: test; update: notify 1s', marks=pytest.mark.xfail),
     make_source_param('pv: test; field: SCAN I/O Intr'),
     make_source_param('pv: test; field: SCAN 1 second', marks=pytest.mark.xfail),

     # Archiver settings
     make_source_param('pv: test; archive: no'),
     make_source_param('pv: test; archive: 1s'),
     make_source_param('pv: test; archive: 1s'),
     make_source_param('pv: test; archive: 1s scan'),
     make_source_param('pv: test; archive: 1s monitor'),
     make_source_param('pv: test; archive: 1Hz scan'),
     make_source_param('pv: test; archive: 1Hz monitor'),
     make_source_param('pv: test; archive: 1Hz test', marks=pytest.mark.xfail),
     make_source_param('pv: test; archive: 1s test', marks=pytest.mark.xfail),
     make_source_param('pv: test; archive: 1Hz test', marks=pytest.mark.xfail),
     make_source_param('pv: test; archive: 1es', marks=pytest.mark.xfail),
     ]
)
def test_lint_pragma(source):
    print('Linting source:')
    print(source._source)
    for info in lint_source('filename', source, verbose=True):
        if info.exception:
            raise info.exception
