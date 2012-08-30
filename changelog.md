Python Impact Web Server Changelog
==================================

## v1.1.2
- Fixed do_POST() to properly parse header
- Fixed file path in browse()
- Fixed save() so that the post_params are properly converted from bytes to string.

## v1.1.1
- Added Windows file structure fixes to browse() and glob() so that Weltmeister would load properly
- Added initial print message to reflect the changes added to the main repo.


## v1.1
- Fixed MIME requests so that the data is explicitly opened in binary mode. This is due to Windows treating text and binary files differently.
- Updated source from Python 2.x to 3.x