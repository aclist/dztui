# Introduction

Thank you for considering contributing to DZGUI!

This is a guide for contributors containing conventions best practices and rules
of development and aims to ease the beginning of a contribution.

# How can I request help?

There is an issue tracker on github
(link)[https://github.com/aclist/dzgui-devel/issues] where you can submit
tickets. If you need help troubleshooting a problem, submit a ticket. There is a
category called `troubleshooting` which is exactly what you need.

# How can I help the project?

There are several ways to help this project.
1. Report bugs that you find
2. Request features that you would like
3. Contribute features and fixes to the codebase
4. Contribute documentation to the project

Before making any contribution, please read the `CODE_OF_CONDUCT.md` and act
accordingly.

## How to report

Reproduce the bug that you found. Navigate to the issue tracker on github:
(link)[https://github.com/aclist/dzgui-devel/issues]
Create a ticket where you give us the following:
- What version are you using?
- What distribution are you using?
- What is the issue that you found?
- How can we reproduce the issue?
- Possible screenshots, logs, other data that can help us

## How to request a feature

Navigate to the projects issue tracker
(link)[https://github.com/aclist/dzgui-devel/issues]. Search for your idea to
see if anyone had posted a simmilar idea. If not, open a ticket where you
describe your feature and its possible benefits. Please note, that this is a
community project, it takes time for us to develop features, having a feature
request doesn't mean that it will be implemented, but we do our best to support
as many cool ideas as possible.

## How to contribute code or documentation

If you have an issue of interest in the issue tracker or any other change that
you would like to have implemented you can contribute code to this project. For
this, you may fork this repository and checkout to
`prerelease/<latest-version>`. All new features and fixes will be merged to this
branch, so open your branch from here. Name it according to our convention:
- fix/<your-fix> - fix branches
- feat/<your-feature> - feature branches
- doc/<your-doc-branch> - documentation branches
- infra/<your-infra-branch> - infrastructure branches

Now you can implement your changes and test it locally. If they work you may
open a merge request, and then we review your changes. If everything is OK, it
will be merged to `prerelease/<latest-version>`, then `testing` and after a live
testing phase, to `stable` as well.

During development, it is recommended to follow (conventional
commits)[https://www.conventionalcommits.org/en/v1.0.0/], it helps the project
maintainers when they review your code.
