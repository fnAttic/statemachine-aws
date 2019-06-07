#!/usr/bin/env python
from runtime_context import LOGGER
from lib import fsm
from functions import document_tasks


class DocumentReviewMachine(fsm.StateMachineBase):
    """onboarding state machine"""
    _initial_state = 'initial'
    _states = [
        {'name': 'initial'},
        {'name': 'uploaded',    'lambda_call': document_tasks.notify_reviewer.FunctionName},
        {'name': 'processing',  'lambda_call': document_tasks.summarize_document.FunctionName,
                                'on_exit': document_tasks.archive_document.FunctionName},
        {'name': 'approved',    'lambda_call': document_tasks.notify_uploader.FunctionName},
        {'name': 'rejected',    'lambda_call': [document_tasks.delete_document.FunctionName,
                                                document_tasks.notify_uploader.FunctionName]}
    ]
    _transitions = [
        {'trigger': 'upload',       'source': 'initial',        'dest': 'uploaded'},
        {'trigger': 'approve',      'source': 'uploaded',       'dest': 'processing',
            'conditions': 'is_long'},
        {'trigger': 'approve',      'source': 'uploaded',       'dest': 'approved',
            'unless': 'is_long'},
        {'trigger': 'processed',    'source': 'processing',     'dest': 'approved'},
        {'trigger': 'reject',       'source': 'uploaded',       'dest': 'rejected'}
    ]

    ##############
    # conditions #
    ##############

    def is_long(self, event):
        """determine if the document is too long and needs summarizing"""
        # NOTE: this is a mock implementation
        import string
        val = (string.ascii_lowercase + string.digits).find(self.id[0]) < 18
        LOGGER.debug('DocumentReviewMachine.is_long = {}'.format(val))
        return val

    ####################
    # custom callbacks #
    ####################

    def archive_document(self, event):
        """archive the original document after summarizing it"""
        response = self.lambda_invoke('archive_original', event)


@fsm.cf_function(Path='/docreview/fsm')
def launch(event, context):
    handler = DocumentReviewMachine.get_launch_handler()
    return handler(event, context)


@fsm.cf_function(Path='/docreview/fsm/{id}/{transition}')
def transition(event, context):
    handler = DocumentReviewMachine.get_transition_handler()
    return handler(event, context)


@fsm.cf_function(Path='/docreview/fsm/{id}', Method='get')
def info(event, context):
    handler = DocumentReviewMachine.get_info_handler()
    return handler(event, context)
