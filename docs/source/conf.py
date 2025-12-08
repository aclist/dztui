# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'DZGUI'
author = 'aclist'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

#html_theme = 'alabaster'
extensions = [
    'sphinx_rtd_theme',
    'sphinx_copybutton',
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.githubpages"
]
html_theme = "sphinx_rtd_theme"
html_static_path = ['_static']
html_show_sphinx = False
html_show_copyright = False
html_show_sourcelink = False

today_fmt = "%Y-%m-%d"
release = "5.8.x"
version = "5.8.x"
