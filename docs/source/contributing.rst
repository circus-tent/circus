.. _contribs:

Contributing to Circus
######################

Circus has been started at Mozilla but its goal is not to stay only there.
We're trying to build a tool that's useful for others, and easily extensible.

We really are open to any contributions, in the form of code, documentation,
discussions, feature proposal etc.

You can start a topic in our mailing list : http://tech.groups.yahoo.com/group/circus-dev/

Or add an issue in our `bug tracker <https://github.com/circus-tent/circus/>`_


Fixing typos and enhancing the documentation
============================================

It's totally possible that your eyes are bleeding while reading this
half-english half-french documentation, don't hesitate to contribute any
rephrasing / enhancement on the form in the documentation. You probably don't
even need to understand how Circus works under the hood to do that.


Adding new features
===================

New features are of course very much appreciated. If you have the need and the
time to work on new features, adding them to Circus shouldn't be that
complicated. We tried very hard to have a clean and understandable API, hope it
serves the purpose.

You will need to add documentation and tests alongside with the code of the new
feature. Otherwise we'll not be able to accept the patch.

How to submit your changes
==========================

We're using git as a DVCS. The best way to propose changes is to create a
branch on your side (via `git checkout -b branchname`) and commit your changes
there. Once you have something ready for prime-time, issue a pull request
against this branch.

We are following this model to allow to have low coupling between the features
you are proposing. For instance, we can accept one pull request while still
being in discussion for another one.

Before proposing your changes, double check that they are not breaking
anything! You can use the `tox` command to ensure this, it will run the
testsuite under the different supported python versions.

Please use : http://issue2pr.herokuapp.com/ to reference a commit to an
existing circus issue, if any.

Please also add a changelog entry in the 'unreleased' section with a short
description of the change and a reference to the issue (if any).

Avoiding merge commits
======================

Avoiding merge commits allows to have a clean and readable history. To do so,
instead of doing "git pull" and letting git handling the merges for you, using
git pull --rebase will put your changes after the changes that are commited in
the branch, or when working on master.

That is, for us core developers, it's not possible anymore to use the handy
github green button on pull requests if developers didn't rebased their work
themselves or if we wait too much time between the request and the actual
merge. Instead, the flow looks like this::

    git remote add name repo-url
    git fetch name
    git checkout feature-branch
    git rebase master

    # check that everything is working properly and then merge on master
    git checkout master
    git merge feature-branch

Discussing
==========

If you find yourself in need of any help while looking at the code of Circus,
you can go and find us on irc at `#mozilla-circus on irc.freenode.org
<irc://irc.freenode.net/mozilla-circus>`_ (or if you don't have any IRC client,
use `the webchat
<http://webchat.freenode.net/?channels=mozilla-circus&uio=d4>`_)

You can also start a thread in our mailing list - http://tech.groups.yahoo.com/group/circus-dev
