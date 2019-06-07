#!/usr/bin/env python
import sys
sys.path.append('source')  # add source to the Python path
from troposphere import Template, Output, Parameter
from functions import document_tasks, document_fsm


def main():
    """main function"""
    t = Template()
    t.set_transform('AWS::Serverless-2016-10-31')
    # add resources to the template
    resources = [] \
                + document_fsm.DocumentReviewMachine.cf_resources() \
                + document_fsm.launch.cf_resources() \
                + document_fsm.transition.cf_resources() \
                + document_fsm.info.cf_resources()

    resources += document_tasks.archive_document.cf_resources() \
                 + document_tasks.delete_document.cf_resources() \
                 + document_tasks.notify_reviewer.cf_resources() \
                 + document_tasks.notify_uploader.cf_resources() \
                 + document_tasks.summarize_document.cf_resources()
    for r in resources:
        t.add_resource(r)
    # output yaml template
    print(t.to_yaml())
    # could write to file, but rather print to stdout then pipe to somewhere
    # f = open('template.yaml', 'w')
    # f.write(t.to_yaml())
    # f.close()


if __name__ == '__main__':
    main()
