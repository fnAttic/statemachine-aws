#!/usr/bin/env python
from runtime_context import LOGGER
from lib.cf_utils import cf_function


@cf_function(Path='/docreview/notify/reviewer')
def notify_reviewer(event, context):
    """notify reviewer function"""
    LOGGER.info('Notify reviewer')
    LOGGER.info(event.get('body'))
    return {
        'statusCode': 200
    }


@cf_function(Path='/docreview/document/summarize')
def summarize_document(event, context):
    """summarize document function"""
    LOGGER.info('Summarize document')
    LOGGER.info(event.get('body'))
    return {
        'statusCode': 200
    }


@cf_function(Path='/docreview/notify/uploader')
def notify_uploader(event, context):
    """notify uploader function"""
    LOGGER.info('Notify uploader')
    LOGGER.info(event.get('body'))
    return {
        'statusCode': 200
    }


@cf_function(Path='/docreview/document/delete')
def delete_document(event, context):
    """delete document function"""
    LOGGER.info('Delete document')
    LOGGER.info(event.get('body'))
    return {
        'statusCode': 200
    }


@cf_function(Path='/docreview/document/archive')
def archive_document(event, context):
    """archive original document function"""
    LOGGER.info('Archive original document')
    LOGGER.info(event.get('body'))
    return {
        'statusCode': 200
    }
