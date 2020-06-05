import sys

import pytmc
from pytmc.parser import TwincatItem, TWINCAT_TYPES


def python_debug_session(namespace, message):
    debug_namespace = dict(pytmc=pytmc, TwincatItem=TwincatItem)
    debug_namespace.update(TWINCAT_TYPES)
    debug_namespace.update(
        **{k: v for k, v in namespace.items()
           if not k.startswith('__')}
    )
    globals().update(debug_namespace)

    print('\n-- pytmc debug --')
    print(message)
    print('-- pytmc debug --\n')

    try:
        from IPython import embed
    except ImportError:
        import pdb
        pdb.set_trace()
    else:
        embed()


def heading(text, *, file=sys.stdout):
    print(text, file=file)
    print('=' * len(text), file=file)
    print(file=file)


def sub_heading(text, *, file=sys.stdout):
    print(text, file=file)
    print('-' * len(text), file=file)
    print(file=file)


def sub_sub_heading(text, level=3, *, use_markdown=False, file=sys.stdout):
    if use_markdown:
        print('#' * level, text, file=file)
    else:
        print(' ' * level, '-', text, file=file)
    print(file=file)


def text_block(text, indent=4, markdown_language=None, *, file=sys.stdout):
    if markdown_language is not None:
        print(f'```{markdown_language}', file=file)
        print(text, file=file)
        print('```', file=file)
    else:
        for line in text.splitlines():
            print(' ' * indent, line, file=file)
    print(file=file)
