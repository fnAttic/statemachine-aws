#!/usr/bin/env python
from runtime_context import LOGGER
from lib.utils import pascal_case
from datetime import datetime
import boto3
import json
from lib import ddb, utils
from transitions import Machine, State
from transitions.extensions.states import add_state_features


LAMBDA_CLIENT = boto3.client('lambda')
DDB_CLIENT = boto3.client('dynamodb')


class MachineModel(ddb.Model):
    """finite state machine model"""

    _TABLE_NAME = 'FSMMachines'
    _FIELDS = [
        ('id', ddb.StringAttribute),
        ('created_at', ddb.DateTimeAttribute),
        ('state', ddb.StringAttribute)
    ]

    @classmethod
    def create(cls, **kwargs):
        """create"""
        state = kwargs.get('state')
        assert state is not None, 'Missing attribute: state (String)'
        uid = kwargs.get('id') or utils.generate_id()
        # create item
        data = {
            'id': uid,
            'created_at': datetime.utcnow(),
            'state': state
        }
        super().create(data)
        return data

    @classmethod
    def get_by_id(cls, id):
        """get by id"""
        response = DDB_CLIENT.query(
            TableName=cls._TABLE_NAME,
            Limit=1,
            ExpressionAttributeValues={
                ':id': {
                    'S': id
                }
            },
            KeyConditionExpression='id = :id',
            ScanIndexForward=False
        )
        if response.get('Count', 0) == 1:
            return cls.deserialize(response.get('Items')[0])
        else:
            return None

    @classmethod
    def cf_resources(cls):
        """produce CF template"""
        from troposphere import dynamodb
        return [dynamodb.Table(
            cls._TABLE_NAME,
            TableName=cls._TABLE_NAME,
            BillingMode='PAY_PER_REQUEST',
            AttributeDefinitions=[
                dynamodb.AttributeDefinition(AttributeName='id', AttributeType='S'),
                dynamodb.AttributeDefinition(AttributeName='created_at', AttributeType='S')
            ],
            KeySchema=[
                dynamodb.KeySchema(AttributeName='id', KeyType='HASH'),
                dynamodb.KeySchema(AttributeName='created_at', KeyType='RANGE')
            ]
        )]

    """
    def list_history(cls, id):  # list all versions of an instance
    def list(cls):  # list all instances
    """


class LambdaCall(State):
    """ transitions extension
        Attributes:
            lambda_call (string): AWS lambda reference to call
    """

    def __init__(self, *args, **kwargs):
        """init"""
        lambda_call = kwargs.pop('lambda_call', [])  # NOTE: must use pop to remove the unexpected named variable
        self.lambda_call = lambda_call if type(lambda_call) == list else [lambda_call]
        super(LambdaCall, self).__init__(*args, **kwargs)

    def enter(self, event_data):
        """Extends `transitions.core.State.enter`
        see examples: https://github.com/pytransitions/transitions/blob/master/transitions/extensions/states.py
        """
        LOGGER.debug('LambdaCall.enter - call: {}'.format(self.lambda_call))
        if self.lambda_call:  # process calls if there is any defined
            self._process_lambda_call(event_data)
        super(LambdaCall, self).enter(event_data)

    def _process_lambda_call(self, event_data):
        """execute lambda calls"""
        payload = event_data.kwargs.get('data')
        payload['_meta'] = {
            'state': event_data.state.name,
            'event': event_data.event.name,
            'transition': {
                'source': event_data.transition.source,
                'dest': event_data.transition.dest
            }
        }
        print(payload)
        for lambda_ref in self.lambda_call:
            response = LAMBDA_CLIENT.invoke(FunctionName=lambda_ref,
                                            InvocationType='Event',
                                            LogType='None',
                                            Payload=json.dumps(payload))


@add_state_features(LambdaCall)
class LambdaStateMachine(Machine):
    """custom state machine"""


class StateMachineBase(object):
    """base state machine definition
    https://github.com/pytransitions/transitions
    """
    _initial_state = None
    _states = []  # {'name': 'initial'},  # initial state
    _transitions = []  # {'source': 'initial',   'trigger': 'move_to_a',  'dest': 'a'},

    def __init__(self, state=None, id=None):
        self.id = id
        self.machine = LambdaStateMachine(model=self,
                                          states=self._states,
                                          transitions=self._transitions,
                                          initial=state or self._initial_state,
                                          send_event=True,
                                          after_state_change='save')  # NOTE: the state is always saved after transition

    @classmethod
    def create(cls):
        """create a new state machine"""
        f = MachineModel.create(state=cls._initial_state)
        return f

    @classmethod
    def load(cls, fsm_id):
        """load state machine instance"""
        f = MachineModel.get_by_id(fsm_id)
        m = cls(id=fsm_id, state=f.get('state'))
        return m

    def save(self, event):
        """save state machine instance"""
        f = MachineModel.create(id=self.id, state=self.state)
        return f

    @staticmethod
    def lambda_invoke(lambda_ref, data, invocation_async=True, log_type='None'):
        """invoke lambda function"""
        return LAMBDA_CLIENT.invoke(FunctionName=lambda_ref,
                                    InvocationType='Event' if invocation_async else 'RequestResponse',
                                    LogType=log_type,
                                    Payload=data)

    def __str__(self):
        """string representation"""
        return '{} id={} state={}'.format(self.__class__.__name__, self.id, self.state)

    @classmethod
    def get_launch_handler(cls):
        """returns launch handler"""
        def handler(event, context):
            """initialise a new state machine"""
            f = cls.create()
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'id': f.get('id'),
                    'state': f.get('state')
                })
            }

        return handler

    @classmethod
    def get_transition_handler(cls):
        """returns transition handler"""
        def handler(event, context):
            """manage transitions"""
            fsm_id = event.get('pathParameters', {}).get('id')
            transition_name = event.get('pathParameters', {}).get('transition')
            body = event.get('body')
            data = body or {}
            f = cls.load(fsm_id)
            try:
                f.trigger(transition_name, data=data)
            except Exception as e:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': str(e)
                    })
                }
            return {
                'statusCode': 204
            }

        return handler

    @classmethod
    def get_info_handler(cls):
        """returns info handler"""
        def handler(event, context):
            """get machine instance information"""
            fsm_id = event.get('pathParameters', {}).get('id')
            m = cls.load(fsm_id)
            return {
                'statusCode': 200,
                'body': str(m)
            }

        return handler

    @classmethod
    def cf_resources(cls):
        """cloud formation resources"""
        return MachineModel.cf_resources()


def cf_function(**func_args):
    """decorator for function handlers"""

    assert 'Path' in func_args, 'Missing Path argument'

    def wrap(f):

        name = f.__name__.capitalize()  # NOTE: capitalized Python function name
        function_name = pascal_case('{} Function'.format(name))
        event_name = pascal_case('{} Http'.format(name))
        handler_str = '{}.{}'.format(f.__module__, f.__name__)

        def wrapped_f(*args, **kwargs):
            return f(*args, **kwargs)

        def cf_resources():
            from troposphere import serverless

            f = serverless.Function(
                function_name,
                FunctionName=function_name,
                Handler=handler_str,
                Runtime='python3.7',
                MemorySize=128,
                Timeout=60,
                CodeUri='./source/',
                Policies=[
                    {'DynamoDBCrudPolicy': {
                        'TableName': MachineModel.get_table_name()
                    }},
                    {'LambdaInvokePolicy': {
                        'FunctionName': '*'
                    }}
                ],
                Events={
                    event_name: serverless.ApiEvent(
                        event_name,
                        Path=func_args.get('Path'),
                        Method=func_args.get('Method', 'post')
                    )
                }
            )
            return [f]

        wrapped_f.FunctionName = function_name
        wrapped_f.cf_resources = cf_resources
        return wrapped_f

    return wrap
