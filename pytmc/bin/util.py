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
