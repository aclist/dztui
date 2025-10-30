# Introduction

Thank you for your interest in DZGUI!

This guide goes over development conventions and best practices for contributors.
If you are a developer, you can skip to the end.

# Requesting help

If you encounter a problem with DZGUI, you can submit tickets on the GitHub
(issue tracker)[https://github.com/aclist/dzgui-devel/issues] under the
`troubleshooting` tag.

# How can I help the project?

There are several ways to help this project.
1. Report bugs that you find
2. Request features that you would like
3. Contribute features and fixes to the codebase
4. Contribute documentation to the project

Before making any contribution, please read the `CODE_OF_CONDUCT.md` and act
accordingly.

## Submitting a ticket

Navigate to the GitHub (issue tracker)[https://github.com/aclist/dzgui-devel/issues].
From there, follow the onscreen prompts. You will be asked questions such as:

- What version are you using?
- What distribution are you using?
- What is the issue that you found?
- How can we reproduce the issue?

You can also attach screenshots, logs, or other data that can help us.

## Requesting a feature

You can also request features via the same issue tracker. It is good practice to
first search for your idea to see if a similar one has already been posted.
If not, open a ticket where you describe your feature and its possible benefits.

Please note that this is a community project, so it takes time for us to develop
features. Putting in a feature request does not mean that it will be implemented,
but we will do our best to support as many cool ideas as possible.

## Contributing code or documentation

If you would like to take ownership or assist with an issue on the issue tracker, or
contribute a new change, please follow the guidelines below.

Fork this repository and check out the code up to `prerelease/<latest-version>`.
If there is no pending prerelease PR, you can base your changes off of
the `testing` branch. You may later be asked to retarget your PR to the prerelease
branch once a new one is made. This is because out-of-band PRs are consolidated into
the next release before merging.

The following naming conventions apply for PRs:
- fix/<your-fix> - patch/hotfix branches
- feat/<your-feature> - feature branches
- doc/<your-doc-branch> - documentation branches
- infra/<your-infra-branch> - infrastructure branches

Implement your changes and test them locally. If they work you may
open a merge request, and then we review your changes. If everything is OK, it
will be merged to `prerelease/<latest-version>`, then `testing`, and after a live
testing phase, to `stable` as well.

It is recommended to follow
(Conventional Commits)[https://www.conventionalcommits.org/en/v1.0.0/], as this
integrates well with tooling and helps the project review your code.
