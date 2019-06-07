#!/usr/bin/env python
from lib.utils import pascal_case


def cf_function(**func_args):
    """decorator for CloudFormation AWS:Serverless::Function resource"""

    assert 'Path' in func_args, 'Missing Path argument'

    def wrap(f):
        name = f.__name__.capitalize()  # NOTE: capitalized Python function name
        function_name = func_args.get('FunctionName', pascal_case('{} Function'.format(name)))
        event_name = pascal_case('{} Http'.format(name))
        handler_str = '{}.{}'.format(f.__module__, f.__name__)

        def wrapped_f(*args, **kwargs):
            return f(*args, **kwargs)

        def cf_resources(**resource_args):
            """CloudFormation resources"""
            from troposphere import serverless
            f = serverless.Function(
                function_name,
                FunctionName=function_name,
                Handler=handler_str,
                Runtime='python3.7',
                MemorySize=128,
                Timeout=60,
                CodeUri='./source/',
                Events={
                    event_name: serverless.ApiEvent(
                        event_name,
                        Path=func_args.get('Path'),
                        Method='post'
                    )
                }
            )
            return [f]

        wrapped_f.FunctionName = function_name
        wrapped_f.cf_resources = cf_resources
        return wrapped_f

    return wrap
