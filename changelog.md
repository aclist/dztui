# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
- Clean up logging
- Server metadata caching
- Detect Steam Deck dynamically and set window resolution instead of hardcoding

## [1.1.2] 2022-06-08
### Fix array used for mod concatenation; fetch post-sanitized list of mods

## [1.1.1] 2022-06-05
### Fixed
- Stricter regex to parse upstream version number

## [1.1.0] 2022-06-05
### Added
- Main menu: fav server label on header
- Main menu: add servers by ID directly into config file
- Main menu: link to report a bug
- Main menu: quick connect to fav server
- Connect: mod compatibility check
- Connect: mod download prompt
- Connect: mod auto symlinks
- New version download prompt
- Additional visualization of progress/menus

### Fixed
- Menu recursion when navigating backwards

### Changed
- Reduced ping timeout interval
