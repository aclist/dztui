Locale support
==================

For internationalization purposes, DZGUI will inherit the default locale setting on the system when displaying numbers.

This is used for thousands separators in long numbers and decimal separators in fractional numbers.

If you wish to use a specific regional numbering preference while retaining a different base system language (e.g., English language with German-style numbering), pass the desired locale as a variable before launching DZGUI:

``LC_ALL=de_DE.UTF-8 ./dzgui.sh``

If you intend to use this frequently, you could wrap the above in a script or alias.
