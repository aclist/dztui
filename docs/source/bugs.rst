Submitting a ticket
==========================

Tickets are tracked at the `DZGUI issue tracker <https://github.com/aclist/dztui/issues>`_.

You will need to `register for a GitHub account <https://github.com/signup>`_ in order to submit one.

If have checked the :doc:`kb` and `closed issues <https://github.com/aclist/dztui/issues?q=is%3Aissue+is%3Aclosed>`_ area and did not find a solution, three ticket types are provided for your 
convenience:

- **Bug report**: for unexpected, breaking behavior in the application
- **Feature request**: to propose new functionality
- **Troubleshooting**: if all else fails, you can request help here

Reports by example
--------------------------

Below are some examples of how to format a constructive report that will ensure your problem can be resolved in a timely fashion.

A non-actionable report
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    Subject: add button

    hi, you must add a button to show how long I have to wait to join a full server, the app is useless without this...do your job, guys!!! ;-)


This report exhibits a number of problems:

- Vague title and summary: in addition to being unclear, this will slow down filing the incoming report.
- Problem space is poorly defined: it is not clear where the issue lies, where the feature is supposed to be implemented, nor why.
- Lack of context: the feature may already exist, but there is not enough information to go on. Alternatively, the feature may be technically impossible to implement, but there is not enough 
  information to go on.
- Incorrect report type: this is a feature request filed as a bug report.
- Unprofessional tone: the message is disrespectful towards project members and inserts the user's subjective opinion.

An actionable report
^^^^^^^^^^^^^^^^^^^^^^^^^^^

    Subject: Version 5.5.0-beta.2 crashes when selecting multiple table rows via Ctrl-click

    This occurs specifically on version 5.5.0-beta.2 if the setting ALLOW_MULTI is set to ON. I was able to reproduce it using the following steps:

    Distribution: Fedora
    
    - Ensure that ALLOW_MULTI is set to ON
    - Open the application and immediately navigate to the Server Browser
    - Uses the Ctrl-click binding to select multiple rows in the table
    - After >1 row is selected, the application crashes to the desktop with the following traceback (see attached dump)

    Thanks for looking into this.


This report is actionable because it is objective, specific, and detailed:

- The subject is clearly defined: specific details ensure it will be filed in a timely manner.
- Scope is explicit: the specific version, settings, and conditions under which the problem occur were given.
- Ample context: the user gave steps to reproduce the problem and clarified each one.
- Courteous tone: the user interacted with project members in a professional manner.
- Supporting information: the user provided a crash dump to expedite resolution of the issue.
